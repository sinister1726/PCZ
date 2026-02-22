from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from Assets.files import START_IMAGE_GROUP, SOLO_MODE_IMAGE
from database.games import is_game_active

# ───────────── MAINTENANCE SYSTEM ─────────────

OWNER_ID = 8294062042

# Global maintenance state
MAINTENANCE_MODE = {
    "status": False,
    "reason": "Bot is upgrading..."
}


# ───────────── DECORATOR ─────────────
def maintenance(func):
    async def wrapper(client, message, *args, **kwargs):
        if MAINTENANCE_MODE["status"]:

            text = f"""
╭━━━〔 🚧 𝗕𝗢𝗧 𝗨𝗡𝗗𝗘𝗥 𝗠𝗔𝗜𝗡𝗧𝗘𝗡𝗔𝗡𝗖𝗘 🚧 〕━━━╮

✨ Our services are temporarily unavailable.

📌 **Reason:**
{MAINTENANCE_MODE['reason']}

🔔 Please stay connected for updates.

📢 Contact:
[ʟᴇɢᴀᴄʏ ᴘʟᴀʏᴢᴏɴᴇ 🏏](https://t.me/+joF1bCfiMT9jMzVh)

"""

            return await message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )

        return await func(client, message, *args, **kwargs)

    return wrapper


# ───────────── COMMAND ─────────────
@Client.on_message(filters.command("maintenance") & filters.private)
async def toggle_maintenance(client, message: Message):

    if message.from_user.id != OWNER_ID:
        return await message.reply_text("🚫 Only Owner can use this command.")

    args = message.text.split(maxsplit=2)

    if len(args) < 2:
        return await message.reply_text(
            "Usage:\n"
            "`/maintenance on reason`\n"
            "`/maintenance off`",
            parse_mode=ParseMode.MARKDOWN
        )

    action = args[1].lower()

    if action == "on":
        reason = args[2] if len(args) > 2 else "Bot is under maintenance."

        MAINTENANCE_MODE["status"] = True
        MAINTENANCE_MODE["reason"] = reason

        return await message.reply_text(
            f"✅ Maintenance Mode Enabled.\n\n📌 Reason:\n{reason}"
        )

    elif action == "off":
        MAINTENANCE_MODE["status"] = False
        MAINTENANCE_MODE["reason"] = "Bot is upgrading..."

        return await message.reply_text("✅ Maintenance Mode Disabled.")

    else:
        return await message.reply_text("Invalid option. Use on/off.")
        
@Client.on_message(filters.command("start") & filters.group)
@maintenance
async def start_game(client, message):
    chat_id = message.chat.id

    # ❌ Do NOT create game here
    if await is_game_active(chat_id):
        return await message.reply_text(
            "⚠️ <b>Game already running</b>\nFinish it first 🏏",
            parse_mode=ParseMode.HTML
        )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏏 Team", callback_data="mode_team"),
                InlineKeyboardButton("👤 Solo", callback_data="mode_solo"),
            ],
            [
                InlineKeyboardButton("✖ Cancel", callback_data="mode_cancel")
            ]
        ]
    )

    await message.reply_photo(
        photo=START_IMAGE_GROUP,
        caption=(
            "🎮 <b>SELECT MODE</b>\n"
            "Choose how you want to play today 👇"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=buttons
    )



@Client.on_callback_query(filters.regex("^mode_solo$"))
async def solo_mode(client, query):
    await query.answer("Solo mode is currently under development.")

    await query.message.edit_media(
        media=InputMediaPhoto(
            media=SOLO_MODE_IMAGE,
            caption=(
                "👤 **𝗦𝗢𝗟𝗢 𝗠𝗢𝗗𝗘**\n"
                "`Coming soon in the next update!`"
            )
        ),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="mode_back")]])
    )

@Client.on_callback_query(filters.regex("^mode_cancel$"))
async def cancel_start(client, query):
    await query.answer("Cancelled")
    await query.message.delete()

@Client.on_callback_query(filters.regex("^mode_back$"))
async def back_to_start(client, query):
    """Returns user to the initial mode selection."""
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏏 Team", callback_data="mode_team"),
                InlineKeyboardButton("👤 Solo", callback_data="mode_solo"),
            ],
            [
                InlineKeyboardButton("✖ Cancel", callback_data="mode_cancel")
            ]
        ]
    )
    await query.message.edit_media(
        media=InputMediaPhoto(
            media=START_IMAGE_GROUP,
            caption="🎮 **𝗦𝗘𝗟𝗘𝗖𝗧 𝗠𝗢𝗗𝗘**\n`Choose how to play.`"
        ),
        reply_markup=buttons
    )
