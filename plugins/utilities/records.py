"""
/records — Group-specific all-time records with pagination.

Page 1: Individual records (7 entries)
Page 2: Group milestone counters
"""

import html
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

from database.group_records import get_group_records

DIVIDER  = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
DIVIDER2 = "━━━━━━━━━━━━━━━━━━━━━━━━"


def _link(uid: int, name: str) -> str:
    return f"<a href='tg://user?id={uid}'>{html.escape(name)}</a>"


def _sr(sr: float) -> str:
    return f"{sr:.1f}"


def _ov(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}"


def _medal(pos: int) -> str:
    return ["🥇", "🥈", "🥉"].get(pos - 1, "🏅")  # unused but kept for future


def _nav_buttons(page: int) -> InlineKeyboardMarkup:
    total = 2
    if page == 1:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🏆 Records", callback_data="rec_p_1"),
            InlineKeyboardButton(f"1 / {total}", callback_data="rec_noop"),
            InlineKeyboardButton("Milestones ▶️", callback_data="rec_p_2"),
        ]])
    else:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Records", callback_data="rec_p_1"),
            InlineKeyboardButton(f"2 / {total}", callback_data="rec_noop"),
            InlineKeyboardButton("🌟 Milestones", callback_data="rec_p_2"),
        ]])


async def _build_page1(chat_id: int, chat_title: str) -> str:
    r = await get_group_records(chat_id)

    if not r or not any(
        k in r for k in ("highest_score", "most_sixes_match", "most_fours_match",
                         "best_bowling", "highest_team_total")
    ):
        return (
            "📭 <b>No records yet!</b>\n\n"
            "Play some matches in this group and records will appear here. 🏏"
        )

    title = html.escape(chat_title)
    lines = [
        f"🏆 <b>{title}</b>",
        f"<i>All-Time Group Records</i>",
        DIVIDER2,
    ]

    # ── BATTING ──────────────────────────────────────────────────────────────
    lines.append("\n🏏  <b>B A T T I N G</b>")
    lines.append(DIVIDER)

    hs = r.get("highest_score")
    if hs:
        sr_note = f"  SR <b>{_sr(hs['sr'])}</b>" if hs.get("sr") else ""
        lines.append(
            f"🔥 <b>Highest Score</b>\n"
            f"   {_link(hs['uid'], hs['name'])}  "
            f"<b>{hs['runs']}</b> off {hs.get('balls','?')}b{sr_note}\n"
            f"   <i>{hs.get('date','')}</i>"
        )

    sixes = r.get("most_sixes_match")
    if sixes:
        lines.append(
            f"6️⃣ <b>Most Sixes in a Match</b>\n"
            f"   {_link(sixes['uid'], sixes['name'])}  "
            f"<b>{sixes['count']} sixes</b>\n"
            f"   <i>{sixes.get('date','')}</i>"
        )

    fours = r.get("most_fours_match")
    if fours:
        lines.append(
            f"4️⃣ <b>Most Fours in a Match</b>\n"
            f"   {_link(fours['uid'], fours['name'])}  "
            f"<b>{fours['count']} fours</b>\n"
            f"   <i>{fours.get('date','')}</i>"
        )

    bsr = r.get("best_sr_match")
    if bsr:
        lines.append(
            f"⚡ <b>Best Strike Rate</b>  <i>(min 15 balls)</i>\n"
            f"   {_link(bsr['uid'], bsr['name'])}  "
            f"SR <b>{_sr(bsr['sr'])}</b>  ({bsr['runs']}/{bsr['balls']}b)\n"
            f"   <i>{bsr.get('date','')}</i>"
        )

    # ── BOWLING ──────────────────────────────────────────────────────────────
    lines.append("\n🎯  <b>B O W L I N G</b>")
    lines.append(DIVIDER)

    bb = r.get("best_bowling")
    if bb:
        lines.append(
            f"🏆 <b>Best Bowling Figures</b>\n"
            f"   {_link(bb['uid'], bb['name'])}  "
            f"<b>{bb['wickets']}/{bb['runs_conceded']}</b>  ({_ov(bb.get('balls',0))} ov)\n"
            f"   <i>{bb.get('date','')}</i>"
        )

    hat_tricks = r.get("hat_tricks", [])
    if hat_tricks:
        ht_counts: dict = {}
        for ht in hat_tricks:
            uid, name = ht["uid"], ht["name"]
            ht_counts[uid] = (name, ht_counts.get(uid, (name, 0))[1] + 1)
        parts = []
        for uid, (name, cnt) in ht_counts.items():
            suffix = f" <b>×{cnt}</b>" if cnt > 1 else ""
            parts.append(f"{_link(uid, name)}{suffix}")
        lines.append(
            f"🎩 <b>Hat-Trick Heroes</b>\n"
            f"   {',  '.join(parts)}"
        )

    # ── TEAM ─────────────────────────────────────────────────────────────────
    ht = r.get("highest_team_total")
    if ht:
        lines.append("\n🏟️  <b>T E A M</b>")
        lines.append(DIVIDER)
        lines.append(
            f"📈 <b>Highest Team Total</b>\n"
            f"   <b>{html.escape(ht.get('team_name','Team'))}</b>  "
            f"<b>{ht['runs']}</b> ({_ov(ht.get('balls',0))} ov)\n"
            f"   <i>{ht.get('date','')}</i>"
        )

    lines.append(f"\n{DIVIDER2}")
    lines.append("✨ <i>Tap ▶️ for Group Milestones</i>")
    return "\n".join(lines)


async def _build_page2(chat_id: int, chat_title: str) -> str:
    r = await get_group_records(chat_id)

    if not r:
        return (
            "📭 <b>No milestones yet!</b>\n\n"
            "Keep playing to unlock group records! 🏏"
        )

    title        = html.escape(chat_title)
    total_50s    = r.get("total_fifties", 0)
    total_100s   = r.get("total_centuries", 0)
    total_6s     = r.get("total_sixes", 0)
    total_4s     = r.get("total_fours", 0)
    hat_tricks   = r.get("hat_tricks", [])
    total_hts    = len(hat_tricks)

    lines = [
        f"🌟 <b>{title}</b>",
        f"<i>Group Milestone Counters</i>",
        DIVIDER2,
        "\n💫  <b>M I L E S T O N E S</b>",
        DIVIDER,
    ]

    if total_50s:
        lines.append(f"⭐ <b>Fifties:</b>  {total_50s:,}")
    if total_100s:
        lines.append(f"💯 <b>Centuries:</b>  {total_100s:,}")
    if total_6s:
        lines.append(f"6️⃣ <b>Total Sixes:</b>  {total_6s:,}")
    if total_4s:
        lines.append(f"4️⃣ <b>Total Fours:</b>  {total_4s:,}")
    if total_hts:
        lines.append(f"🎩 <b>Hat-Tricks:</b>  {total_hts}")

    if not any([total_50s, total_100s, total_6s, total_4s, total_hts]):
        lines.append("No milestones recorded yet.")

    lines.append(f"\n{DIVIDER2}")
    lines.append("✨ <i>Tap ◀️ to see individual records</i>")
    return "\n".join(lines)


# ─── Commands & Callbacks ─────────────────────────────────────────────────────

@Client.on_message(filters.command("records") & filters.group)
async def records_cmd(client: Client, message: Message):
    chat_id    = message.chat.id
    chat_title = message.chat.title or "This Group"

    text = await _build_page1(chat_id, chat_title)
    await message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=_nav_buttons(1),
    )


@Client.on_callback_query(filters.regex(r"^rec_p_[12]$"))
async def records_page_cb(client: Client, query: CallbackQuery):
    page       = int(query.data.split("_")[-1])
    chat_id    = query.message.chat.id
    chat_title = query.message.chat.title or "This Group"

    if page == 1:
        text = await _build_page1(chat_id, chat_title)
    else:
        text = await _build_page2(chat_id, chat_title)

    try:
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=_nav_buttons(page),
        )
    except Exception:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^rec_noop$"))
async def records_noop_cb(client: Client, query: CallbackQuery):
    await query.answer("You're already on this page!")
