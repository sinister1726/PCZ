from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
from database.users import add_user


HELP_HOME_TEXT = (
    "📘 <b>Help & Guide</b>\n\n"
    "Pick a topic below and we'll break it down."
)


def _home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎮 How to Play", callback_data="help_play"),
                InlineKeyboardButton("🏏 Game Modes",  callback_data="help_modes"),
            ],
            [
                InlineKeyboardButton("👤 Profile & Stats", callback_data="help_user"),
                InlineKeyboardButton("📋 All Commands",    callback_data="help_commands"),
            ],
        ]
    )


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Back", callback_data="help_back")]]
    )


HELP_PLAY_TEXT = (
    "🎮 <b>How to Play</b>\n\n"
    "🏏 <b>Batting</b>\n"
    "• Team Mode: batters pick <b>0–6</b>\n"
    "• Solo Mode: batters pick <b>1–6</b>\n"
    "• Bowlers send <b>1–6</b> privately in DM\n\n"
    "📊 <b>Scoring</b>\n"
    "• Same number as bowler = <b>OUT ❌</b>\n"
    "• 0 = Dot ball · Otherwise = runs scored\n"
    "• Odd runs → strike rotates\n"
    "• 6 balls = 1 over · Over end → strike rotates\n\n"
    "⏱ <b>Timeouts</b>\n"
    "• 1 minute per move (default)\n"
    "• 2 consecutive misses → -6 runs penalty\n\n"
    "⚠️ <b>Special Rule</b>\n"
    "• 0 is <b>NOT allowed</b> on hat-trick bowling"
)

HELP_MODES_TEXT = (
    "🏏 <b>Game Modes</b>\n\n"
    "👥 <b>Team Mode</b>\n"
    "1. /play → Team Mode → I'm the Host\n"
    "2. /create_teams → players /join_teamA or /join_teamB\n"
    "3. /choose_cap → /set_overs → game begins!\n\n"
    "🧍 <b>Solo Mode</b>\n"
    "1. /play → Solo Mode\n"
    "2. Players /joingame to enter\n"
    "3. Wait for timer or /forcestart\n\n"
    "⚔️ <b>Duel Mode  (DM only)</b>\n"
    "1. DM the bot and send /duel\n"
    "2. Gets matched with another player\n"
    "3. Play head-to-head in DM — wins count toward duel rating"
)

HELP_USER_TEXT = (
    "👤 <b>Profile & Stats</b>\n\n"
    "📊 <b>Commands</b>\n"
    "/userinfo — full profile card\n"
    "/stats — global bot stats\n"
    "/user_ranks — top players leaderboard\n"
    "/achievements — your unlocked badges\n"
    "/compare @user1 @user2 — head-to-head comparison\n"
    "/analyze — AI playstyle analysis\n\n"
    "💬 <b>Other</b>\n"
    "/start — main menu (DM)\n"
    "/help — this help menu"
)

HELP_COMMANDS_TEXT = (
    "📋 <b>All Commands</b>\n\n"
    "🟢 <b>Basics</b>\n"
    "/start · /help · /play · /duel\n\n"
    "👥 <b>Team Mode</b>\n"
    "/create_teams · /join_teamA · /join_teamB\n"
    "/teams · /changeside · /shiftteam\n"
    "/add · /remove · /changehost · /changecap\n"
    "/choose_cap · /set_overs · /batting · /bowling\n"
    "/rejointeams · /restore · /endgame\n\n"
    "🧍 <b>Solo Mode</b>\n"
    "/joingame · /leavegame · /extend · /forcestart\n\n"
    "⚔️ <b>Duel</b>\n"
    "/duel (DM only)\n\n"
    "📊 <b>Live Match</b>\n"
    "/score · /graph · /members · /endgame\n\n"
    "👤 <b>Profile</b>\n"
    "/userinfo · /stats · /user_ranks · /achievements\n"
    "/compare · /analyze"
)


@Client.on_message(filters.command("help"))
async def help_cmd(client, message):
    try:
        await add_user(message.from_user.id)
    except Exception:
        pass

    try:
        await message.reply_text(
            HELP_HOME_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=_home_keyboard(),
        )
    except Exception:
        pass


@Client.on_callback_query(filters.regex("^help_"))
async def help_callback(client, cb):
    pages = {
        "help_play":     HELP_PLAY_TEXT,
        "help_modes":    HELP_MODES_TEXT,
        "help_user":     HELP_USER_TEXT,
        "help_commands": HELP_COMMANDS_TEXT,
    }

    try:
        data = cb.data

        if data == "help_back":
            text    = HELP_HOME_TEXT
            buttons = _home_keyboard()
        elif data in pages:
            text    = pages[data]
            buttons = _back_keyboard()
        else:
            return await cb.answer("Expired 😴", show_alert=True)

        await cb.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=buttons,
        )
        await cb.answer()

    except Exception:
        try:
            await cb.answer("Something glitched 😅", show_alert=True)
        except Exception:
            pass
