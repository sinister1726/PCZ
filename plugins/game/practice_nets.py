"""
Practice Nets Mode — DM-only AI cricket game.
Player bats or bowls against AI. Stats not saved.
"""
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.enums import ParseMode

NETS: dict = {}  # uid -> session

_COMMS_BAT = {
    6: ["💥 SIX! Into the stands! Absolutely massive!", "🚀 Maximum! That's gone all the way!", "🔥 SIX! Pure class shot!"],
    5: ["😱 FIVE! Incredible placement between the fielders!", "⚡ Five runs! Scrambling to the boundary!"],
    4: ["🔥 FOUR! Racing to the boundary!", "💥 Boundary! Perfectly timed!", "🎯 FOUR! Cracking shot through covers!"],
    3: ["🏃 THREE! Great running — pushed it into the gap!", "Smart cricket! Three all the way!"],
    2: ["✌️ Two runs, good rotation of strike.", "🤝 A couple — sensible cricket."],
    1: ["Quick single! Sharp running. One run.", "🎯 Nudged into the leg side for one."],
    0: ["🔒 Dot ball. Tight line and length.", "😤 Defended solidly — no run.", "🧱 Beaten outside off! Dot ball."],
}
_COMMS_OUT = [
    "☝️ <b>OUT! Bowled!</b> What a delivery — pegged back middle stump!",
    "💀 <b>CAUGHT!</b> Went for the big shot and found the fielder!",
    "🚨 <b>LBW!</b> Struck right in front — plumb!",
    "☝️ <b>BOWLED!</b> The numbers matched — you're dismissed!",
]
_COMMS_WICKET = [
    "🎉 <b>WICKET!</b> Clean bowled — the AI can't believe it!",
    "⚾ <b>BOWLED!</b> Ripped through the defence — got 'em!",
    "🏆 <b>WICKET!</b> Perfect delivery — the AI is walking back!",
    "☝️ <b>OUT!</b> Numbers matched — that's a wicket!",
]
_COMMS_BOWL = {
    6: ["💀 SIX! AI launches it into the stands! What a swing!", "🚀 AI takes you for a massive SIX!"],
    5: ["😤 Five! AI finds a gap and runs hard!", "⚡ Five runs conceded — AI on a roll!"],
    4: ["🔥 FOUR! AI drives effortlessly to the boundary!", "💥 AI gets a boundary — back to the fence!"],
    3: ["🏃 Three for AI. Running between the wickets well.", "AI scampers three — good running."],
    2: ["Two for AI. Rotating the strike.", "AI nudges for a couple."],
    1: ["AI takes a quick single — 1 run.", "Played and nudged for one by AI."],
    0: ["🎯 Dot ball! Tight delivery — AI couldn't score!", "👏 Blocked! Excellent dot ball.", "0! Beat the AI — well bowled!"],
}


def _ai_bowl(history: list) -> int:
    """AI picks 1-6. If batter spammed the same number 3 times, trap them."""
    if len(history) >= 3 and history[-1] == history[-2] == history[-3]:
        return history[-1]
    return random.randint(1, 6)


def _ai_bat(history: list) -> int:
    """AI bats 0-6. Slightly avoids repeating bowler's last delivery."""
    choices = list(range(7))
    if history:
        last = history[-1]
        weights = [1 if i == last else 3 for i in choices]
    else:
        weights = [2, 3, 3, 2, 2, 2, 1]
    return random.choices(choices, weights=weights)[0]


def _bar(balls: int, score: int, wickets: int, mode: str) -> str:
    ov = f"{balls // 6}.{balls % 6}"
    if mode == "bat":
        sr = f"  SR {score / balls * 100:.0f}" if balls else ""
        return f"🏏 <b>{score}/{wickets}</b>  ({ov} ov){sr}"
    else:
        return f"🎯 Figures: <b>{wickets}–{score}</b>  ({ov} ov)"


_STOP_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 End Session", callback_data="nets_stop")]])


@Client.on_message(filters.command(["nets", "practicenets"]) & filters.private)
async def nets_cmd(client, message: Message):
    uid = message.from_user.id
    if uid in NETS:
        return await message.reply_text(
            "⚡ You already have an active nets session!\n"
            "Send a number to keep playing, or /stopnets to end.",
            parse_mode=ParseMode.HTML,
        )
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🏏 Bat", callback_data="nets_role_bat"),
        InlineKeyboardButton("⚾ Bowl", callback_data="nets_role_bowl"),
    ]])
    await message.reply_text(
        "🏏 <b>Practice Nets</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Train against the AI — stats are <b>not saved</b>.\n\n"
        "🏏 <b>Bat</b> — score as many runs as you can before getting out\n"
        "⚾ <b>Bowl</b> — get 5 wickets or bowl 6 overs\n\n"
        "🎮 Choose your role:",
        parse_mode=ParseMode.HTML,
        reply_markup=markup,
    )


@Client.on_message(filters.command("stopnets") & filters.private)
async def stopnets_cmd(client, message: Message):
    uid = message.from_user.id
    if uid not in NETS:
        return await message.reply_text("No active nets session to stop!")
    session = NETS.pop(uid)
    sc, balls, wkts, role = session["score"], session["balls"], session["wickets"], session["role"]
    ov = f"{balls // 6}.{balls % 6}"
    if role == "bat":
        sr = f"{sc / balls * 100:.1f}" if balls else "0.0"
        text = (
            f"🏁 <b>Nets Session Ended</b>\n"
            f"🏏 Score: <b>{sc}/{wkts}</b> off {ov} ov\n"
            f"⚡ Strike Rate: <b>{sr}</b>"
        )
    else:
        text = (
            f"🏁 <b>Nets Session Ended</b>\n"
            f"🎯 Figures: <b>{wkts}–{sc}</b> off {ov} ov"
        )
    await message.reply_text(text, parse_mode=ParseMode.HTML)


@Client.on_callback_query(filters.regex("^nets_role_"))
async def nets_role_callback(client, query: CallbackQuery):
    await query.answer()
    uid  = query.from_user.id
    role = query.data.split("_")[2]

    if uid in NETS:
        return await query.answer("Session already running!", show_alert=True)

    session = {
        "role": role, "score": 0, "balls": 0,
        "wickets": 0, "history": [], "last_ai": None,
    }
    NETS[uid] = session

    if role == "bat":
        first_ai = _ai_bowl([])
        session["last_ai"] = first_ai
        text = (
            "⚡ <b>Practice Nets — Batting</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🎯 AI has delivered! Send your shot <b>(0–6)</b>:\n"
            "<i>Your number = AI's number → OUT!</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"{_bar(0, 0, 0, 'bat')}"
        )
    else:
        text = (
            "⚡ <b>Practice Nets — Bowling</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🎳 AI is ready to bat. Send your delivery <b>(1–6)</b>:\n"
            "<i>Your number = AI's number → WICKET!</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"{_bar(0, 0, 0, 'bowl')}"
        )

    try:
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=_STOP_BTN)
    except Exception:
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=_STOP_BTN)


@Client.on_callback_query(filters.regex("^nets_stop$"))
async def nets_stop_callback(client, query: CallbackQuery):
    await query.answer()
    uid = query.from_user.id
    if uid not in NETS:
        return await query.answer("No active session!", show_alert=True)
    session = NETS.pop(uid)
    sc, balls, wkts, role = session["score"], session["balls"], session["wickets"], session["role"]
    ov = f"{balls // 6}.{balls % 6}"
    if role == "bat":
        sr = f"{sc / balls * 100:.1f}" if balls else "0.0"
        text = f"🏁 <b>Session Over!</b>  Score: <b>{sc}/{wkts}</b> off {ov} ov  •  SR <b>{sr}</b>"
    else:
        text = f"🏁 <b>Session Over!</b>  Figures: <b>{wkts}–{sc}</b> off {ov} ov"
    try:
        await query.message.edit_text(text + "\n\n💡 /nets to play again!", parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, parse_mode=ParseMode.HTML)


@Client.on_message(filters.private & filters.regex("^[0-6]$"), group=1)
async def nets_ball_handler(client, message: Message):
    uid = message.from_user.id
    if uid not in NETS:
        return

    session = NETS[uid]
    role    = session["role"]
    num     = int(message.text)

    session["balls"] += 1
    balls = session["balls"]

    # ── Batting mode ──────────────────────────────────────────────────────────
    if role == "bat":
        ai_num = session["last_ai"]
        hist   = session["history"]
        hist.append(num)
        if len(hist) > 10:
            hist.pop(0)

        if num == ai_num:
            sc   = session["score"]
            NETS.pop(uid)
            sr   = f"{sc / balls * 100:.1f}" if balls else "0.0"
            comm = random.choice(_COMMS_OUT)
            await message.reply_text(
                f"{comm}\n\n"
                f"🏁 <b>You're dismissed!</b>\n"
                f"🏏 Final Score: <b>{sc}/1</b> off {balls // 6}.{balls % 6} ov\n"
                f"⚡ Strike Rate: <b>{sr}</b>\n\n"
                "💡 /nets to bat again!",
                parse_mode=ParseMode.HTML,
            )
        else:
            runs = num
            session["score"] += runs
            sc   = session["score"]
            comm = random.choice(_COMMS_BAT.get(runs, [f"+{runs} runs!"]))
            next_ai = _ai_bowl(hist)
            session["last_ai"] = next_ai
            await message.reply_text(
                f"{comm}\n"
                f"<b>+{runs}</b>  •  {_bar(balls, sc, 0, 'bat')}\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "🎯 AI delivered again! Send your shot <b>(0–6)</b>:",
                parse_mode=ParseMode.HTML,
                reply_markup=_STOP_BTN,
            )

    # ── Bowling mode ──────────────────────────────────────────────────────────
    else:
        if num == 0:
            session["balls"] -= 1
            return await message.reply_text("⚠️ Bowlers send <b>1–6</b> only!", parse_mode=ParseMode.HTML, quote=True)

        hist   = session["history"]
        hist.append(num)
        if len(hist) > 10:
            hist.pop(0)

        ai_num = _ai_bat(hist)
        session["last_ai"] = ai_num

        if ai_num == num:
            session["wickets"] += 1
            wkts = session["wickets"]
            sc   = session["score"]
            comm = random.choice(_COMMS_WICKET)
            bar  = _bar(balls, sc, wkts, "bowl")

            if wkts >= 5 or balls >= 36:
                NETS.pop(uid)
                await message.reply_text(
                    f"{comm}\n\n"
                    f"🏁 <b>{'5 wickets' if wkts >= 5 else '6 Overs Complete'}!</b>\n"
                    f"🎯 Final Figures: <b>{wkts}–{sc}</b> off {balls // 6}.{balls % 6} ov\n\n"
                    "💡 /nets to bowl again!",
                    parse_mode=ParseMode.HTML,
                )
            else:
                await message.reply_text(
                    f"{comm}\n"
                    f"<b>{wkts} wicket(s)!</b>  •  {bar}\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "New batter in! Send your delivery <b>(1–6)</b>:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=_STOP_BTN,
                )
        else:
            runs = ai_num
            session["score"] += runs
            sc   = session["score"]
            comm = random.choice(_COMMS_BOWL.get(runs, [f"AI scores {runs}."]))
            bar  = _bar(balls, sc, session["wickets"], "bowl")

            if balls >= 36:
                NETS.pop(uid)
                await message.reply_text(
                    f"{comm}\n\n"
                    f"🏁 <b>6 Overs Complete!</b>\n"
                    f"🎯 Final Figures: <b>{session['wickets']}–{sc}</b> off {balls // 6}.{balls % 6} ov\n\n"
                    "💡 /nets to bowl again!",
                    parse_mode=ParseMode.HTML,
                )
            else:
                await message.reply_text(
                    f"{comm}\n"
                    f"AI scores <b>+{runs}</b>  •  {bar}\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "Send your next delivery <b>(1–6)</b>:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=_STOP_BTN,
                )
