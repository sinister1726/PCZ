import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified
import random

from plugins.game.team import ACTIVE_MATCHES
from Assets.files import SOLO_MODE_IMAGE

@Client.on_callback_query(filters.regex("^mode_solo$"))
async def init_solo_mode(client, query):
    chat_id = query.message.chat.id
    user = query.from_user

    ACTIVE_MATCHES[chat_id] = {
        "mode": "Solo",
        "phase": "REGISTRATION",
        "host_id": user.id,
        "host_name": user.first_name,
        "players": {}, 
        "batting_order": [],
        "user_cache": {user.id: user.first_name},
        "chat_id": chat_id,
        "client": client,
        "striker": None,
        "current_bowler": None,
        "bowler_balls": 0 
    }

    ACTIVE_MATCHES[chat_id]["players"][user.id] = {
        "runs": 0, "wickets": 0, "balls_faced": 0, "balls_bowled": 0, "is_out": False
    }
    ACTIVE_MATCHES[chat_id]["batting_order"].append(user.id)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✋ Join Solo", callback_data="join_solo")],
        [InlineKeyboardButton("▶️ Start Match", callback_data="start_solo_match")],
        [InlineKeyboardButton("✖ Cancel Match", callback_data="cancel_solo_match")]
    ])

    await query.answer("Solo Mode Selected! 🏏")
    try:
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=SOLO_MODE_IMAGE, 
                caption=(
                    "👤 <b>𝗦𝗢𝗟𝗢 𝗠𝗢𝗗𝗘 — 𝗥𝗘𝗚𝗜𝗦𝗧𝗥𝗔𝗧𝗜𝗢𝗡</b>\n\n"
                    "🔥 <b>Rules:</b>\n"
                    "• Every man for himself!\n"
                    "• No 0 (defend) allowed.\n"
                    "• 3 Balls per bowler.\n"
                    "• Timeout = -6 Runs penalty.\n\n"
                    f"👑 <b>Host:</b> {user.mention}\n"
                    "👥 <b>Joined:</b> 1\n\n"
                    "<i>Minimum 3 players required.</i>"
                )
            ),
            reply_markup=buttons
        )
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex("^join_solo$"))
async def join_solo(client, query):
    chat_id = query.message.chat.id
    user = query.from_user
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or match.get("mode") != "Solo" or match.get("phase") != "REGISTRATION":
        return await query.answer("No active solo registration.", show_alert=True)

    if user.id in match["players"]:
        return await query.answer("You are already in the match! 😂", show_alert=True)

    match["players"][user.id] = {"runs": 0, "wickets": 0, "balls_faced": 0, "balls_bowled": 0, "is_out": False}
    match["batting_order"].append(user.id)
    match["user_cache"][user.id] = user.first_name

    await query.answer("Joined successfully! ✅")
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✋ Join Solo", callback_data="join_solo")],
        [InlineKeyboardButton("▶️ Start Match", callback_data="start_solo_match")],
        [InlineKeyboardButton("✖ Cancel Match", callback_data="cancel_solo_match")]
    ])

    try:
        await query.message.edit_caption(
            caption=(
                "👤 <b>𝗦𝗢𝗟𝗢 𝗠𝗢𝗗𝗘 — 𝗥𝗘𝗚𝗜𝗦𝗧𝗥𝗔𝗧𝗜𝗢𝗡</b>\n\n"
                "🔥 <b>Rules:</b>\n"
                "• Every man for himself!\n"
                "• No 0 (defend) allowed.\n"
                "• 3 Balls per bowler.\n"
                "• Timeout = -6 Runs penalty.\n\n"
                f"👑 <b>Host:</b> <a href='tg://user?id={match['host_id']}'>{match['host_name']}</a>\n"
                f"👥 <b>Joined:</b> {len(match['players'])}\n\n"
                "<i>Minimum 3 players required.</i>"
            ),
            reply_markup=buttons, 
            parse_mode=ParseMode.HTML
        )
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex("^cancel_solo_match$"))
async def cancel_solo(client, query):
    chat_id = query.message.chat.id
    match = ACTIVE_MATCHES.get(chat_id)
    
    if not match or query.from_user.id != match["host_id"]:
        return await query.answer("Only the host can cancel the match.", show_alert=True)
        
    ACTIVE_MATCHES.pop(chat_id, None)
    await query.message.edit_caption("❌ <b>Solo Match Cancelled by Host.</b>", parse_mode=ParseMode.HTML)

@Client.on_callback_query(filters.regex("^start_solo_match$"))
async def start_solo_match(client, query):
    chat_id = query.message.chat.id
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or match.get("mode") != "Solo":
        return await query.answer("Invalid match.", show_alert=True)

    if query.from_user.id != match["host_id"]:
        return await query.answer("Only the Host can start the match! 👑", show_alert=True)

    if len(match["players"]) < 3:
        return await query.answer("❌ Minimum 3 players required to play solo!", show_alert=True)

    match["phase"] = "LIVE"
    random.shuffle(match["batting_order"]) 
    
    match["striker"] = match["batting_order"][0]
    match["current_bowler"] = match["batting_order"][1]
    match["current_batter_idx"] = 0
    match["bowler_balls"] = 0

    await query.message.edit_caption("🚀 <b>𝗦𝗢𝗟𝗢 𝗠𝗔𝗧𝗖𝗛 𝗦𝗧𝗔𝗥𝗧𝗘𝗗!</b>\n\nGet ready for the ultimate showdown!", parse_mode=ParseMode.HTML)
    await announce_solo_turn(client, chat_id, match)

async def announce_solo_turn(client, chat_id, match):
    batter_name = match["user_cache"][match["striker"]]
    bowler_name = match["user_cache"][match["current_bowler"]]
    
    await client.send_message(
        chat_id,
        f"🏏 <b>Game On!</b>\n\n"
        f"🤺 <b>Batsman:</b> <a href='tg://user?id={match['striker']}'>{batter_name}</a>\n"
        f"🎳 <b>Bowler:</b> <a href='tg://user?id={match['current_bowler']}'>{bowler_name}</a>\n\n"
        f"Hit the ball! (0 is not allowed)",
        parse_mode=ParseMode.HTML
    )

async def rotate_solo_players(client, chat_id, match, is_wicket=False):
    players = match["batting_order"]
    
    if is_wicket:
        match["players"][match["striker"]]["is_out"] = True
        match["current_batter_idx"] += 1
        
        if match["current_batter_idx"] >= len(players):
            return await end_solo_match(match)
            
        match["striker"] = players[match["current_batter_idx"]]
        match["bowler_balls"] = 0 
        
    else:
        match["bowler_balls"] += 1

    if match["bowler_balls"] >= 3:
        await client.send_message(chat_id, "🔄 <b>Bowler Changed! (3 Balls Completed)</b>", parse_mode=ParseMode.HTML)
        match["bowler_balls"] = 0
        
        curr_b_idx = players.index(match["current_bowler"])
        for _ in range(len(players)):
            curr_b_idx = (curr_b_idx + 1) % len(players)
            if players[curr_b_idx] != match["striker"]:
                match["current_bowler"] = players[curr_b_idx]
                break

    await announce_solo_turn(client, chat_id, match)

async def solo_timeout(match, role):
    client, chat_id = match["client"], match["chat_id"]
    user_id = match["current_bowler"] if role == "bowler" else match["striker"]
    mention = f"<a href='tg://user?id={user_id}'>{match['user_cache'][user_id]}</a>"

    match["players"][user_id]["runs"] -= 6

    msg = f"🚫 <b>CLOCK WINS</b>\n\n{mention} couldn't beat the timer ⏰\nPunished with <b>-6 runs</b>.\n"
    
    if role == "batter":
        msg += "☝️ <b>Batter is OUT!</b>"
        await client.send_message(chat_id, msg, parse_mode=ParseMode.HTML)
        await rotate_solo_players(client, chat_id, match, is_wicket=True)
    else:
        msg += "🎳 <b>Bowler removed from attack!</b>"
        match["bowler_balls"] = 3 
        await client.send_message(chat_id, msg, parse_mode=ParseMode.HTML)
        await rotate_solo_players(client, chat_id, match, is_wicket=False)

async def end_solo_match(match):
    client, chat_id = match["client"], match["chat_id"]
    players = match["players"]

    top_batsman_id = max(players, key=lambda k: players[k]["runs"])
    top_bowler_id = max(players, key=lambda k: players[k]["wickets"])

    def get_name(uid): return match["user_cache"].get(uid, "Player")

    res_text = "🏁 <b>𝗦𝗢𝗟𝗢 𝗠𝗔𝗧𝗖𝗛 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘𝗗</b> 🏁\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    res_text += "🏆 <b>𝗠𝗔𝗧𝗖𝗛 𝗪𝗜𝗡𝗡𝗘𝗥𝗦:</b>\n"
    res_text += f"🥇 <b>Best Batsman:</b> <a href='tg://user?id={top_batsman_id}'>{get_name(top_batsman_id)}</a> ➞ <b>{players[top_batsman_id]['runs']} Runs</b>\n"
    res_text += f"🎯 <b>Best Bowler:</b> <a href='tg://user?id={top_bowler_id}'>{get_name(top_bowler_id)}</a> ➞ <b>{players[top_bowler_id]['wickets']} Wickets</b>\n\n"
    
    res_text += "📊 <b>𝗙𝗨𝗟𝗟 𝗦𝗖𝗢𝗥𝗘𝗕𝗢𝗔𝗥𝗗:</b>\n"
    for uid, stats in players.items():
        status = "❌ Out" if stats["is_out"] else "✅ Not Out"
        res_text += f"👤 <b>{get_name(uid)}</b>: {stats['runs']}R ({stats['balls_faced']}b) | {stats['wickets']}W | {status}\n"

    await client.send_message(chat_id, res_text, parse_mode=ParseMode.HTML)
    ACTIVE_MATCHES.pop(chat_id, None)
  
