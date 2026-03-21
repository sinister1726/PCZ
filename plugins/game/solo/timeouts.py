import asyncio
from pyrogram.enums import ParseMode


async def start_solo_timer(match, role):
    client = match.get("client")
    chat_id = match.get("chat_id")

    if not client or not chat_id:
        return

    user_id = match.get("current_bowler") if role == "bowler" else match.get("current_batter")
    name = match.get("user_cache", {}).get(user_id, role.capitalize())
    mention = f"<a href='tg://user?id={user_id}'>{name}</a>"

    await asyncio.sleep(30)
    if _already_played(match, role):
        return
    try:
        await client.send_message(
            chat_id,
            f"⏳ <b>30 seconds gone.</b>\n{mention} still thinking...\nThis is cricket 😭",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await asyncio.sleep(20)
    if _already_played(match, role):
        return
    try:
        await client.send_message(
            chat_id,
            f"⚠️ <b>10 seconds remaining.</b>\n{mention}, play now!",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await asyncio.sleep(10)
    if _already_played(match, role):
        return

    await _handle_solo_timeout(match, role)


def _already_played(match, role):
    if role == "bowler":
        return match.get("bowled", False)
    return match.get("batted", False) or not match.get("bowled", False)


async def _handle_solo_timeout(match, role):
    client = match.get("client")
    chat_id = match.get("chat_id")

    if not client or not chat_id or match.get("phase") != "LIVE":
        return

    if "timeouts" not in match:
        return

    t_info = match["timeouts"][role]
    user_id = match.get("current_bowler") if role == "bowler" else match.get("current_batter")

    if not user_id:
        return

    name = match.get("user_cache", {}).get(user_id, role.capitalize())
    mention = f"<a href='tg://user?id={user_id}'>{name}</a>"

    if t_info.get("fails", 0) == 0:
        t_info["fails"] = 1
        match["prompt_dispatched"] = False
        await client.send_message(
            chat_id,
            (
                "🚩 <b>TIME WARNING</b>\n"
                f"{mention} freezing under pressure.\n"
                "⚠️ <b>Next delay:</b> -6 runs penalty & action taken."
            ),
            parse_mode=ParseMode.HTML,
        )
        from plugins.game.solo.timeouts import start_solo_timer
        t_info["task"] = asyncio.create_task(start_solo_timer(match, role))
        return

    t_info["fails"] = 0
    match["total_runs"] = max(0, match.get("total_runs", 0) - 6)

    penalty_msg = (
        "🚫 <b>CLOCK WINS</b>\n\n"
        f"{mention} couldn't beat the timer ⏰\n"
        "🧮 <b>-6 runs</b> penalty applied.\n"
    )

    if role == "batter":
        penalty_msg += "☝️ <b>Batter is OUT</b> — defeated by the clock.\n"
        await client.send_message(chat_id, penalty_msg, parse_mode=ParseMode.HTML)
        from plugins.game.solo.engine import solo_advance_ball
        await solo_advance_ball(match, "W")
    else:
        penalty_msg += (
            "🎳 <b>Bowler skipped.</b> Next bowler steps in.\n"
        )
        match.update({"bowled": False, "batted": False, "prompt_dispatched": False, "last_bowl": None})
        match["balls_in_spell"] = 0

        from plugins.game.solo import get_next_solo_bowler
        from plugins.game.solo.state import send_solo_ball_prompt
        next_b = get_next_solo_bowler(match)
        match["current_bowler"] = next_b
        await client.send_message(chat_id, penalty_msg, parse_mode=ParseMode.HTML)
        await send_solo_ball_prompt(client, match)
