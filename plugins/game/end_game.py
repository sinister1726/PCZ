from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.permissions import admin_only
from database.games import is_game_active, end_game as close_db_game
from plugins.game.team import ACTIVE_MATCHES
from plugins.game.team.over_engine import end_match
from plugins.utilities.logger import send_match_log

@Client.on_message(filters.command("endgame") & filters.group)
@admin_only
async def end_game_command(client, message):
    chat_id = message.chat.id

    if not await is_game_active(chat_id):
        return await message.reply_text(
            "**𝗡𝗢 𝗔𝗖𝗧𝗜𝗩𝗘 𝗚𝗔𝗠𝗘**\n"
            "`Nothing to end.`"
        )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🛑 End Game", callback_data="confirm_endgame"),
                InlineKeyboardButton("✖ Cancel", callback_data="cancel_endgame"),
            ]
        ]
    )

    await message.reply_text(
        "⚠️ **𝗘𝗡𝗗 𝗚𝗔𝗠𝗘?**\n"
        "`This will force-end the match and save stats.`",
        reply_markup=buttons
    )

@Client.on_callback_query(filters.regex("^confirm_endgame$"))
@admin_only
async def confirm_endgame(client, query):
    chat_id = query.message.chat.id
    group_title = query.message.chat.title or "Private Match"

    await query.answer("Force ending match…")

    match = ACTIVE_MATCHES.get(chat_id)

    end_text = (
        "🛑 **𝗚𝗔𝗠𝗘 𝗙𝗢𝗥𝗖𝗘 𝗘𝗡𝗗𝗘𝗗**\n"
        "`Match summary & stats saved.`"
    )

    if match:
        match["client"] = client

        balls_played = match.get("total_balls", 0)
        early_force_end = balls_played < 6

        await end_match(match, forced=True)

        if early_force_end:
            end_text = (
                "🛑 **𝗚𝗔𝗠𝗘 𝗙𝗢𝗥𝗖𝗘 𝗘𝗡𝗗𝗘𝗗**\n"
                "`Match stopped early. Player stats saved.`"
            )

        # MATCH LOG
        log_match = {
            "game_id": str(match.get("game_id", "Unknown")),
            "chat_id": chat_id,
            "host_id": match.get("host_id"),
            "host_name": match.get("host_name", "Unknown")
        }

        await send_match_log(
            client,
            "🛑 MATCH FORCE ENDED",
            log_match,
            f"Match was force ended by admin in {group_title}."
        )

    await close_db_game(chat_id)

    await query.message.edit_text(end_text)

@Client.on_callback_query(filters.regex("^cancel_endgame$"))
@admin_only
async def cancel_endgame(client, query):
    await query.answer("Cancelled")
    await query.message.delete()
    
