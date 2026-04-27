"""Group game entry: `/start` (and aliases `/play`, `/newgame`) open the
mode picker — Team / Solo / 1v1 Duel.

When global maintenance mode is ON, the maintenance gate in
`plugins/admin/maintenance.py` intercepts these commands and shows the
"Bot is under maintenance" notice instead.
"""

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)

from Assets.files import START_IMAGE_GROUP
from database.games import is_game_active


PICKER_CAPTION = (
    "🎮 <b>SELECT MODE</b>\n"
    "──┈┄┄╌╌╌╌┄┄┈──\n"
    "Choose how you want to play 👇\n\n"
    "⚔️ <i>1v1 Duel runs in the bot DM — tap to queue.</i>"
)


def _mode_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏏 Team", callback_data="mode_team"),
                InlineKeyboardButton("👤 Solo", callback_data="mode_solo"),
            ],
            [
                InlineKeyboardButton("⚔️ 1v1 Duel", callback_data="mode_duel"),
            ],
            [InlineKeyboardButton("✖ Cancel", callback_data="mode_cancel")],
        ]
    )


async def _bot_can_send_media(client: Client, chat_id: int) -> bool:
    try:
        me = await client.get_me()
        member = await client.get_chat_member(chat_id, me.id)
        if member.status.name == "ADMINISTRATOR":
            return getattr(member.privileges, "can_send_media_messages", True) is not False
        return True
    except Exception:
        return True


async def _send_mode_picker(client: Client, message) -> None:
    chat_id = message.chat.id

    if await is_game_active(chat_id):
        await message.reply_text(
            "⚠️ <b>Game already running</b>\nFinish the current match first 🏏",
            parse_mode=ParseMode.HTML,
        )
        return

    if await _bot_can_send_media(client, chat_id):
        try:
            await message.reply_photo(
                photo=START_IMAGE_GROUP,
                caption=PICKER_CAPTION,
                parse_mode=ParseMode.HTML,
                reply_markup=_mode_buttons(),
            )
            return
        except Exception:
            pass

    await message.reply_text(
        PICKER_CAPTION,
        parse_mode=ParseMode.HTML,
        reply_markup=_mode_buttons(),
    )


# ─── /start in groups → mode picker ──────────────────────────────────────────

@Client.on_message(filters.command("start") & filters.group)
async def start_in_group(client: Client, message):
    await _send_mode_picker(client, message)


# ─── /play and /newgame aliases ──────────────────────────────────────────────

@Client.on_message(filters.command(["play", "newgame"]) & filters.group)
async def play_cmd(client: Client, message):
    await _send_mode_picker(client, message)


# ─── callbacks ───────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^mode_cancel$"))
async def cancel_start(client, query):
    try:
        await query.message.delete()
    except Exception:
        try:
            await query.message.edit_text("✖ Cancelled.")
        except Exception:
            pass
    await query.answer("Cancelled")


@Client.on_callback_query(filters.regex("^mode_back$"))
async def back_to_start(client, query):
    await query.answer()
    try:
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=START_IMAGE_GROUP,
                caption=PICKER_CAPTION,
                parse_mode=ParseMode.HTML,
            ),
            reply_markup=_mode_buttons(),
        )
    except MessageNotModified:
        pass
    except Exception:
        try:
            await query.message.edit_text(
                PICKER_CAPTION,
                parse_mode=ParseMode.HTML,
                reply_markup=_mode_buttons(),
            )
        except Exception:
            pass
