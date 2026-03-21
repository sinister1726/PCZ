import asyncio
import html
from pyrogram.enums import ParseMode

from plugins.game.team import ACTIVE_MATCHES
from plugins.game.solo import get_next_solo_bowler, build_solo_score_text


def _mention(match, uid):
    name = match.get("user_cache", {}).get(uid, "Player")
    return f"<a href='tg://user?id={uid}'>{html.escape(name)}</a>"


async def solo_advance_ball(match, result):
    """
    Core ball resolution for solo mode.
    result: int (runs) or "W" (wicket)
    """
    client = match.get("client")
    chat_id = match.get("chat_id")

    if not client or not chat_id:
        return

    batter_id = match.get("current_batter")
    bowler_id = match.get("current_bowler")
    stats = match.get("player_stats", {})

    batter_stats = stats.setdefault(batter_id, _blank_stats())
    bowler_stats = stats.setdefault(bowler_id, _blank_stats())

    try:
        if result == "W":
            batter_stats["balls_faced"] += 1
            batter_stats["is_out"] = True
            batter_stats["batting_balls"].append("W")

            bowler_stats["wickets"] += 1
            bowler_stats["balls_bowled"] += 1
            bowler_stats["bowling_balls"].append("W")

            match["total_balls"] += 1
            match["total_wickets"] += 1
            match["balls_in_spell"] = match.get("balls_in_spell", 0) + 1

            await _check_bowler_achievements(client, chat_id, match, bowler_id, bowler_stats)

            await _next_batter_or_end(match)

        else:
            runs = int(result)
            batter_stats["runs"] += runs
            batter_stats["balls_faced"] += 1
            batter_stats["batting_balls"].append(runs)
            if runs == 4:
                batter_stats["fours_count"] += 1
            elif runs == 6:
                batter_stats["sixes_count"] += 1

            bowler_stats["runs_conceded"] += runs
            bowler_stats["balls_bowled"] += 1
            bowler_stats["bowling_balls"].append(runs)

            match["total_runs"] += runs
            match["total_balls"] += 1
            match["balls_in_spell"] = match.get("balls_in_spell", 0) + 1

            await _check_batter_achievements(client, chat_id, match, batter_id, batter_stats)

            if match.get("balls_in_spell", 0) >= 3:
                await _rotate_bowler(client, match)
            else:
                await _next_ball(client, match)

    except Exception as e:
        print(f"solo_advance_ball error: {e}")
    finally:
        match["bowled"] = False
        match["batted"] = False
        match["prompt_dispatched"] = False
        match["last_bowl"] = None


def _blank_stats():
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


async def _rotate_bowler(client, match):
    """Move to the next bowler after a 3-ball spell."""
    chat_id = match["chat_id"]
    match["balls_in_spell"] = 0

    next_bowler = get_next_solo_bowler(match)
    match["current_bowler"] = next_bowler

    if next_bowler:
        name = match.get("user_cache", {}).get(next_bowler, "Player")
        await client.send_message(
            chat_id,
            f"🎯 Hey {name}, now you're bowling!",
            parse_mode=ParseMode.HTML,
        )
        await asyncio.sleep(0.5)
        await _next_ball(client, match)
    else:
        await _end_solo_match(match)


async def _next_batter_or_end(match):
    """Called when a wicket falls. Bring in next batter or end game."""
    client = match.get("client")
    chat_id = match.get("chat_id")
    players = match["players"]

    current_batter = match.get("current_batter")
    try:
        current_idx = players.index(current_batter)
    except ValueError:
        await _end_solo_match(match)
        return

    next_idx = current_idx + 1
    if next_idx >= len(players):
        await _end_solo_match(match)
        return

    next_batter = players[next_idx]
    match["current_batter"] = next_batter

    current_bowler = match.get("current_bowler")
    if current_bowler == next_batter:
        match["balls_in_spell"] = 0
        new_bowler = get_next_solo_bowler(match)
        match["current_bowler"] = new_bowler
        bname = match.get("user_cache", {}).get(new_bowler, "Player")
        await client.send_message(
            chat_id,
            f"🔄 Bowler swap! {bname} now bowling (can't bat & bowl same player).",
            parse_mode=ParseMode.HTML,
        )

    new_batter_name = match.get("user_cache", {}).get(next_batter, "Player")
    await client.send_message(
        chat_id,
        f"🎉 Hey {new_batter_name}, now you're batter!",
        parse_mode=ParseMode.HTML,
    )

    await asyncio.sleep(0.5)
    await _next_ball(client, match)


async def _next_ball(client, match):
    from plugins.game.solo.state import send_solo_ball_prompt
    match["prompt_dispatched"] = False
    await send_solo_ball_prompt(client, match)


async def _end_solo_match(match, forced=False):
    client = match.get("client")
    chat_id = match.get("chat_id")

    if not client or not chat_id:
        match["phase"] = "finished"
        return

    match["phase"] = "finished"

    players = match.get("players", [])
    stats = match.get("player_stats", {})
    user_cache = match.get("user_cache", {})

    if not forced:
        scorecard = _build_final_scorecard(match)
        await client.send_message(
            chat_id,
            scorecard,
            parse_mode=ParseMode.HTML,
        )

    try:
        from database.games import end_game as close_db_game
        await close_db_game(chat_id)
    except Exception as e:
        print(f"Solo end DB error: {e}")

    try:
        from database.connection import db
        async with db.pool.acquire() as conn:
            for uid, p in stats.items():
                is_win = 0
                is_out = 1 if p.get("is_out") else 0
                runs = p.get("runs", 0)
                wickets = p.get("wickets", 0)
                fours = p.get("fours_count", 0)
                sixes = p.get("sixes_count", 0)
                b_faced = p.get("balls_faced", 0)
                b_bowled = p.get("balls_bowled", 0)
                r_conceded = p.get("runs_conceded", 0)
                is_50 = 1 if 50 <= runs < 100 else 0
                is_100 = 1 if runs >= 100 else 0
                is_duck = 1 if runs == 0 and is_out else 0

                await conn.execute(
                    """
                    INSERT INTO user_stats (
                        user_id, matches, wins, losses, runs, wickets,
                        balls_faced, balls_bowled, runs_conceded, fours, sixes,
                        moms, centuries, fifties, ducks
                    )
                    VALUES ($1, 1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 0, $11, $12, $13)
                    ON CONFLICT (user_id) DO UPDATE SET
                        matches = user_stats.matches + 1,
                        runs = user_stats.runs + $4,
                        wickets = user_stats.wickets + $5,
                        balls_faced = user_stats.balls_faced + $6,
                        balls_bowled = user_stats.balls_bowled + $7,
                        runs_conceded = user_stats.runs_conceded + $8,
                        fours = user_stats.fours + $9,
                        sixes = user_stats.sixes + $10,
                        centuries = user_stats.centuries + $11,
                        fifties = user_stats.fifties + $12,
                        ducks = user_stats.ducks + $13
                    """,
                    uid, is_win, is_out, runs, wickets, b_faced, b_bowled,
                    r_conceded, fours, sixes, is_100, is_50, is_duck,
                )
    except Exception as e:
        print(f"Solo stats save error: {e}")

    ACTIVE_MATCHES.pop(chat_id, None)
    print(f"✅ Solo match in {chat_id} ended.")


def _build_final_scorecard(match):
    players = match.get("players", [])
    stats = match.get("player_stats", {})
    user_cache = match.get("user_cache", {})

    lines = ["─────⊱ Sᴏʟᴏ Pʟᴀʏᴇʀ ⊰────\n"]

    top_scorer_id = None
    top_runs = -1
    top_wickets_id = None
    top_wickets = -1

    for uid in players:
        p = stats.get(uid, {})
        name = user_cache.get(uid, "Player")
        runs = p.get("runs", 0)
        balls = p.get("balls_faced", 0)
        fours = p.get("fours_count", 0)
        sixes = p.get("sixes_count", 0)
        batting_balls = p.get("batting_balls", [])
        is_out = p.get("is_out", False)

        if runs > top_runs:
            top_runs = runs
            top_scorer_id = uid

        if p.get("wickets", 0) > top_wickets:
            top_wickets = p.get("wickets", 0)
            top_wickets_id = uid

        if is_out:
            emoji = "⚪️"
        else:
            emoji = "🟠"

        balls_display = ", ".join(str(b) for b in batting_balls) if batting_balls else "-"
        lines.append(
            f"{emoji} {name} = {runs}({balls})\n"
            f"╰⊚ 4️⃣s: {fours:02d}, 6️⃣s: {sixes:02d} - ID: {uid}\n"
            f"╰⊚ ({balls_display})"
        )

    lines.append("\n────┈┄┄╌╌╌╌┄┄┈────")

    if top_scorer_id:
        ts_name = user_cache.get(top_scorer_id, "Player")
        ts_runs = stats.get(top_scorer_id, {}).get("runs", 0)
        ts_balls = stats.get(top_scorer_id, {}).get("balls_faced", 0)
        lines.append(f"🏆 <b>Top Scorer:</b> {ts_name} — {ts_runs}({ts_balls})")

    if top_wickets_id and top_wickets > 0:
        tw_name = user_cache.get(top_wickets_id, "Player")
        lines.append(f"🎯 <b>Best Bowler:</b> {tw_name} — {top_wickets} wicket(s)")

    total_runs = match.get("total_runs", 0)
    total_balls = match.get("total_balls", 0)
    overs = f"{total_balls // 6}.{total_balls % 6}"
    lines.append(f"📊 <b>Total:</b> {total_runs} runs in {overs} overs")
    lines.append("────┈┄┄╌╌╌╌┄┄┈────")
    lines.append("✨ Thanks for playing! | @NexoraSystems")

    return "\n".join(lines)


async def _check_batter_achievements(client, chat_id, match, batter_id, p):
    announced = match.get("announced_achievements", {}).get("batting", {})
    batter_announced = announced.setdefault(batter_id, set())
    runs = p.get("runs", 0)
    for milestone, line in [(50, "{p} brings up a classy 50 🏏"), (100, "CENTURY 💯 {p} is on fire!"), (150, "150 up 😬 Domination by {p}"), (250, "🚨 HISTORY 🚨 {p} smashes 250!")]:
        if runs >= milestone and milestone not in batter_announced:
            batter_announced.add(milestone)
            name = f"<a href='tg://user?id={batter_id}'>{html.escape(match.get('user_cache', {}).get(batter_id, 'Player'))}</a>"
            try:
                await client.send_message(
                    chat_id,
                    f"🏆 <b>Achievement!</b>\n<i>{line.format(p=name)}</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass


async def _check_bowler_achievements(client, chat_id, match, bowler_id, p):
    announced = match.get("announced_achievements", {}).get("bowling", {})
    bowl_announced = announced.setdefault(bowler_id, set())
    wkts = p.get("wickets", 0)
    msgs = {3: "{p} picks up a 3-fer 🎯", 5: "FIVE-FOR 🖐️ {p} destroys the batting!"}
    if wkts in msgs and wkts not in bowl_announced:
        bowl_announced.add(wkts)
        name = f"<a href='tg://user?id={bowler_id}'>{html.escape(match.get('user_cache', {}).get(bowler_id, 'Player'))}</a>"
        try:
            await client.send_message(
                chat_id,
                f"🏆 <b>Achievement!</b>\n<i>{msgs[wkts].format(p=name)}</i>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
