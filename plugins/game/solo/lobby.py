import asyncio
import time
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.connection import db
from database.games import (
    get_active_game,
    end_game as close_db_game,
    user_in_other_game,
)
from plugins.game.team import ACTIVE_MATCHES
from Assets.files import MEMBERS_IMAGE

SOLO_JOIN_SECONDS = 120


async def ensure_user_exists(conn, user):
    await conn.execute(
        "INSERT INTO users (user_id, name) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
        user.id,
        user.first_name or "Player",
    )


@Client.on_callback_query(filters.regex("^mode_solo$"))
async def solo_mode_selected(client, query):
    await query.answer()
    chat_id = query.message.chat.id
    user = query.from_user
    group_title = query.message.chat.title or "Cricket Arena"

    existing = await get_active_game(chat_id)
    if existing:
        return await query.answer(
            "⚠️ A game is already running in this group.", show_alert=True
        )

    other = await user_in_other_game(user.id, chat_id)
    if other:
        return await query.answer(
            f"⚠️ You are already playing in {other['title']}.", show_alert=True
        )

    try:
        import uuid
        game_id = uuid.uuid4()
        async with db.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO games (game_id, chat_id, title, mode, host_id, status, phase) "
                "VALUES ($1, $2, $3, $4, $5, 'active', 'SOLO_JOIN')",
                game_id, chat_id, group_title, "solo", user.id,
            )
            await ensure_user_exists(conn, user)
    except Exception as e:
        print(f"Solo game DB create error: {e}")
        return await query.answer("Failed to create game. Try again.", show_alert=True)

    ACTIVE_MATCHES[chat_id] = {
        "chat_id": chat_id,
        "game_id": game_id,
        "host_id": user.id,
        "host_name": user.first_name,
        "client": client,
        "mode": "Solo",
        "phase": "SOLO_JOIN",
        "players": [user.id],
        "user_cache": {user.id: user.first_name or "Player"},
        "player_stats": {
            user.id: _fresh_player_stats()
        },
        "current_batter": None,
        "current_bowler": None,
        "bowler_rotation_pos": 1,
        "balls_in_spell": 0,
        "total_runs": 0,
        "total_wickets": 0,
        "total_balls": 0,
        "bowled": False,
        "batted": False,
        "last_bowl": None,
        "prompt_dispatched": False,
        "join_timer_task": None,
        "timeouts": {
            "bowler": {"fails": 0, "task": None},
            "batter": {"fails": 0, "task": None},
        },
        "last_active": time.time(),
        "announced_achievements": {
            "batting": {},
            "bowling": {},
        },
    }

    match = ACTIVE_MATCHES[chat_id]

    try:
        await query.message.edit_caption(
            caption=(
                "👤 <b>𝗦𝗢𝗟𝗢 𝗠𝗢𝗗𝗘 𝗦𝗘𝗟𝗘𝗖𝗧𝗘𝗗</b>\n"
                "────┈┄┄╌╌╌╌┄┄┈────\n"
                f"👑 Host: {user.first_name}\n\n"
                "📢 Join the game using <code>/joingame</code>\n"
                "📤 Leave using <code>/leave</code>\n"
                f"⏳ Lobby closes in <b>{SOLO_JOIN_SECONDS // 60} minutes</b>.\n"
                "⚡ Minimum <b>3 players</b> required to start."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        await client.send_message(
            chat_id,
            "👤 <b>𝗦𝗢𝗟𝗢 𝗠𝗢𝗗𝗘 𝗦𝗘𝗟𝗘𝗖𝗧𝗘𝗗</b>\n\n"
            "📢 Join via <code>/joingame</code>\n"
            "📤 Leave via <code>/leave</code>\n"
            f"⏳ Lobby closes in <b>{SOLO_JOIN_SECONDS // 60} minutes</b>.",
            parse_mode=ParseMode.HTML,
        )

    match["join_timer_task"] = asyncio.create_task(
        _solo_join_timer(client, chat_id)
    )


def _fresh_player_stats():
    return {
        "runs": 0,
        "balls_faced": 0,
        "is_out": False,
        "batting_balls": [],
        "bowling_balls": [],
        "wickets": 0,
        "runs_conceded": 0,
        "balls_bowled": 0,
        "fours_count": 0,
        "sixes_count": 0,
    }


@Client.on_message(filters.command("joingame") & filters.group)
async def join_solo_game(client, message):
    chat_id = message.chat.id
    user = message.from_user
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or match.get("mode") != "Solo":
        return await message.reply_text(
            "😴 No solo game lobby right now. Start one with /start"
        )

    if match.get("phase") != "SOLO_JOIN":
        return await message.reply_text("🔒 Lobby is closed. Game is in progress.")

    if user.id in match["players"]:
        return await message.reply_text("😏 You're already in the lobby.")

    other = await user_in_other_game(user.id, chat_id)
    if other:
        return await message.reply_text(
            f"⚠️ You're already playing in <b>{other['title']}</b>. Finish that game first.",
            parse_mode=ParseMode.HTML,
        )

    match["players"].append(user.id)
    match["user_cache"][user.id] = user.first_name or "Player"
    match["player_stats"][user.id] = _fresh_player_stats()

    try:
        async with db.pool.acquire() as conn:
            await ensure_user_exists(conn, user)
            await conn.execute(
                "INSERT INTO game_players (game_id, user_id, team) "
                "VALUES ($1, $2, 'solo') ON CONFLICT DO NOTHING",
                match["game_id"], user.id,
            )
    except Exception as e:
        print(f"Solo join DB error: {e}")

    count = len(match["players"])
    await message.reply_text(
        f"✅ <b>{user.first_name}</b> joined the solo lobby! "
        f"({count} player{'s' if count != 1 else ''})",
        parse_mode=ParseMode.HTML,
    )


@Client.on_message(filters.command("leave") & filters.group)
async def leave_solo_game(client, message):
    chat_id = message.chat.id
    user = message.from_user
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or match.get("mode") != "Solo":
        return

    if match.get("phase") != "SOLO_JOIN":
        return await message.reply_text("🏏 Can't leave during a live game.")

    if user.id not in match["players"]:
        return await message.reply_text("You're not in the lobby.")

    if user.id == match["host_id"]:
        return await message.reply_text(
            "👑 You are the host. Use /endgame to cancel the match."
        )

    match["players"].remove(user.id)
    match["user_cache"].pop(user.id, None)
    match["player_stats"].pop(user.id, None)

    try:
        async with db.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM game_players WHERE game_id=$1 AND user_id=$2",
                match["game_id"], user.id,
            )
    except Exception as e:
        print(f"Solo leave DB error: {e}")

    count = len(match["players"])
    await message.reply_text(
        f"👋 <b>{user.first_name}</b> left the lobby. ({count} remaining)",
        parse_mode=ParseMode.HTML,
    )


async def _solo_join_timer(client, chat_id):
    try:
        half = SOLO_JOIN_SECONDS // 2
        await asyncio.sleep(half)

        match = ACTIVE_MATCHES.get(chat_id)
        if not match or match.get("phase") != "SOLO_JOIN":
            return

        count = len(match["players"])
        await client.send_message(
            chat_id,
            f"⏳ <b>1 minute left</b> to join the solo game!\n"
            f"Players so far: <b>{count}</b>\n"
            "📢 Join with <code>/joingame</code>",
            parse_mode=ParseMode.HTML,
        )

        await asyncio.sleep(SOLO_JOIN_SECONDS - half - 10)

        match = ACTIVE_MATCHES.get(chat_id)
        if not match or match.get("phase") != "SOLO_JOIN":
            return

        await client.send_message(
            chat_id,
            "⚠️ <b>10 seconds remaining!</b> Last chance to /joingame",
            parse_mode=ParseMode.HTML,
        )

        await asyncio.sleep(10)

        match = ACTIVE_MATCHES.get(chat_id)
        if not match or match.get("phase") != "SOLO_JOIN":
            return

        count = len(match["players"])
        if count < 3:
            await client.send_message(
                chat_id,
                f"❌ <b>Game Cancelled!</b>\n"
                f"Only <b>{count}</b> player(s) joined. Minimum <b>3 required</b> to start.",
                parse_mode=ParseMode.HTML,
            )
            ACTIVE_MATCHES.pop(chat_id, None)
            await close_db_game(chat_id)
            return

        await start_solo_game(client, chat_id)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Solo join timer error: {e}")


async def start_solo_game(client, chat_id):
    match = ACTIVE_MATCHES.get(chat_id)
    if not match:
        return

    match["phase"] = "LIVE"
    match["current_batter"] = match["players"][0]
    match["bowler_rotation_pos"] = 1

    from plugins.game.solo import get_next_solo_bowler
    first_bowler = get_next_solo_bowler(match)
    match["current_bowler"] = first_bowler
    match["balls_in_spell"] = 0

    players = match["players"]
    user_cache = match["user_cache"]

    batter_id = match["current_batter"]
    bowler_id = match["current_bowler"]
    batter_name = user_cache.get(batter_id, "Player")
    bowler_name = user_cache.get(bowler_id, "Player")

    player_list = "\n".join(
        f"{i+1}. {user_cache.get(uid, 'Player')}" for i, uid in enumerate(players)
    )

    try:
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE games SET phase='LIVE' WHERE chat_id=$1 AND status='active'",
                chat_id,
            )
    except Exception as e:
        print(f"Solo start DB error: {e}")

    await client.send_message(
        chat_id,
        f"🏏 <b>𝗦𝗢𝗟𝗢 𝗖𝗥𝗜𝗖𝗞𝗘𝗧 𝗕𝗘𝗚𝗜𝗡𝗦!</b>\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n"
        f"👥 <b>Players ({len(players)}):</b>\n{player_list}\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n"
        f"🏏 <b>First Batter:</b> {batter_name}\n"
        f"⚾ <b>First Bowler:</b> {bowler_name}\n\n"
        "🎯 No dot balls (0) allowed for the batter!\n"
        "⚡ Same number = OUT!",
        parse_mode=ParseMode.HTML,
    )

    await asyncio.sleep(1)

    await client.send_message(
        chat_id,
        f"🎉 Hey {batter_name}, now you're batter!",
        parse_mode=ParseMode.HTML,
    )

    await asyncio.sleep(1)

    await client.send_message(
        chat_id,
        f"🎯 Hey {bowler_name}, now you're bowling!",
        parse_mode=ParseMode.HTML,
    )

    from plugins.game.solo.state import send_solo_ball_prompt
    await send_solo_ball_prompt(client, match)
