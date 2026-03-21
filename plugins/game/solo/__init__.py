from plugins.game.team import ACTIVE_MATCHES


def get_next_solo_bowler(match):
    """
    Returns the uid of the next bowler in the rotation.
    Skips the current batter. Never returns None if there are
    at least 2 players (one batter + one other).
    """
    players = match["players"]
    current_batter = match["current_batter"]
    n = len(players)

    start_pos = match.get("bowler_rotation_pos", 1)

    for offset in range(n):
        pos = (start_pos + offset) % n
        candidate = players[pos]
        if candidate != current_batter:
            match["bowler_rotation_pos"] = (pos + 1) % n
            return candidate

    return None


def advance_solo_bowler(match):
    """
    Called after every 3 balls of the current bowler's spell.
    Picks the next bowler and resets spell counter.
    Does NOT check for current_batter conflict — caller must call
    get_next_solo_bowler instead.
    """
    next_b = get_next_solo_bowler(match)
    match["current_bowler"] = next_b
    match["balls_in_spell"] = 0
    return next_b


def get_batting_status_emoji(match, uid):
    if uid == match.get("current_batter"):
        return "🟣"
    p = match.get("player_stats", {}).get(uid, {})
    if p.get("is_out"):
        return "⚪️"
    return "⭕️"


def build_solo_score_text(match):
    players = match.get("players", [])
    user_cache = match.get("user_cache", {})
    stats = match.get("player_stats", {})
    current_bowler = match.get("current_bowler")
    current_batter = match.get("current_batter")

    lines = ["─────⊱ Sᴏʟᴏ Pʟᴀʏᴇʀ ⊰────\n"]

    for uid in players:
        p = stats.get(uid, {})
        name = user_cache.get(uid, "Player")
        runs = p.get("runs", 0)
        balls = p.get("balls_faced", 0)
        fours = p.get("fours_count", 0)
        sixes = p.get("sixes_count", 0)
        batting_balls = p.get("batting_balls", [])

        emoji = get_batting_status_emoji(match, uid)

        balls_display = ", ".join(str(b) for b in batting_balls) if batting_balls else "-"
        lines.append(
            f"{emoji} {name} = {runs}({balls})\n"
            f"╰⊚ 4️⃣s: {fours:02d}, 6️⃣s: {sixes:02d} - ID: {uid}\n"
            f"╰⊚ ({balls_display})"
        )

    if current_bowler:
        bowler_name = user_cache.get(current_bowler, "Bowler")
        bowler_stats = stats.get(current_bowler, {})
        bowler_balls = bowler_stats.get("bowling_balls", [])
        spell_balls = match.get("balls_in_spell", 0)
        current_spell = bowler_balls[-spell_balls:] if spell_balls and bowler_balls else []
        spell_display = ", ".join(str(b) for b in current_spell) if current_spell else "-"
        lines.append(
            f"\n⚾ <b>Bowling:</b> {bowler_name}\n"
            f"╰⊚ ({spell_display})"
        )

    return "\n".join(lines)
