from utils.mentions import mention_html
import random

def format_player_line(name, runs, balls, bowling=None, is_striker=False):
    star = " 🏏" if is_striker else ""
    line = f"✧ <b>{name}</b>{star} = {runs} ({balls}b)"

    if bowling and len(bowling) > 0:
        balls_str = " • ".join(map(str, bowling))
        line += f"\n╰⊚ ʙᴏᴡʟɪɴɢ: ({balls_str})"
    else:
        line += "\n╰⊚ ʙᴏᴡʟɪɴɢ: Yet to bowl"
    return line

async def build_over_summary(client, match):

    bat_team_key = match.get("batting_team", "A")
    bowl_team_key = match.get("bowling_team", "B")
    user_cache = match.get("user_cache", {})

    striker_id = match.get("striker")
    non_striker_id = match.get("non_striker")

    team_balls = match.get("teams", {}).get(bat_team_key, {}).get("balls", 0)
    completed_over = max(1, team_balls // 6)

    partnership_runs = match.get("partnership", 0)
    partnership_balls = match.get("partnership_balls", 0)

    next_bowler_id = match.get("current_bowler")
    next_bowler_name = user_cache.get(next_bowler_id, "TBD") if next_bowler_id else "TBD"

    lines = [
        "🏏 <b>𝗟𝗜𝗩𝗘 𝗠𝗔𝗧𝗖𝗛 𝗦𝗖𝗢𝗥𝗘𝗖𝗔𝗥𝗗</b>",
        f"<b>Over {completed_over} Complete</b>\n",
        f"📊 <b>Batting:</b> Team {bat_team_key}",
        f"🎯 <b>Bowling:</b> Team {bowl_team_key}",
        "× ──────┈┄┄╌╌╌╌┄┄┈────── ×",
        f"🤝 <b>Partnership:</b> {partnership_runs} ({partnership_balls}b)",
        f"⚾ <b>Next Bowler:</b> {next_bowler_name}",
        ""
    ]

    for t_key in ["A", "B"]:
        t_stats = match["teams"].get(t_key, {"runs": 0, "wickets": 0, "balls": 0})
        icon = "🌊" if t_key == "A" else "🔥"
        ov_str = f"{t_stats['balls']//6}.{t_stats['balls']%6}"

        lines.append(f"{icon} <b>𝗧𝗘𝗔𝗠 {t_key}: {t_stats['runs']}/{t_stats['wickets']}</b> ({ov_str} ov)")

        team_players = [uid for uid, p in match["players"].items() if p.get("team") == t_key]

        if not team_players:
            lines.append("<i>   No players active yet</i>")
        else:
            for uid in team_players:
                p = match["players"][uid]
                p_name = user_cache.get(uid, "Player")

                status_tag = ""
                if uid == striker_id:
                    status_tag = " 🏏"
                elif uid == non_striker_id:
                    status_tag = " 🏃"

                cap_tag = " 👑" if p.get("is_captain") else ""
                out_tag = " ◼️" if p.get("is_out") else ""

                lines.append(
                    f"   • {p_name}{cap_tag}{status_tag}: "
                    f"<b>{p['runs']}</b>({p['balls_faced']}){out_tag}"
                )

        lines.append("")

    recent_list = match.get("current_over_balls", [])
    recent = " • ".join(map(str, recent_list)) if recent_list else "Over completed"

    next_batter = user_cache.get(striker_id, "Batter")

    lines.extend([
        "× ──────┈┄┄╌╌╌╌┄┄┈────── ×",
        f"🕒 <b>Last Over:</b> [ {recent} ]",
        f"👉 <b>Next on Strike:</b> {next_batter}",
        f"\n─────⊱ 📯 ᕼOՏT: {match.get('host_name', 'Admin')} ⊰─────"
    ])

    return "\n".join(lines)

async def build_innings_summary(client, match):
    finished_team_key = match["bowling_team"] 
    new_batting_team = match["batting_team"]

    data = match["teams"][finished_team_key]
    user_cache = match.get("user_cache", {})
    target = match.get("target", "N/A")

    lines = [
        f"🏁 <b>ɪɴɴɪɴɢs ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>",
        "× •-•-•-•-•-••-•-•⟮ 🏏 ⟯•-•-•-•-•-•-•-•-• ×\n",
        f"🏏 <b>Tᴇᴀᴍ {finished_team_key} Fɪɴᴀʟ Sᴄᴏʀᴇ: {data['runs']}/{data['wickets']}</b> ⊰─\n"
    ]

    team_players = [uid for uid, p in match["players"].items() if p.get('team') == finished_team_key]

    if not team_players:
        lines.append("✧ <i>No player stats available</i>")
    else:
        player_lines = []
        for uid in team_players:
            p = match["players"][uid]
            p_name = user_cache.get(uid, "Player")
            player_lines.append(format_player_line(p_name, p["runs"], p["balls_faced"], p.get("bowling_balls", [])))
        lines.append("\n\n".join(player_lines))

    lines.append("\n× •-•-•-•-•-••-•-•⟮ 🎯 ⟯•-•-•-•-•-•-•-•-• ×\n")
    lines.append(f"🎯 <b>ᴛᴀʀɢᴇᴛ sᴇᴛ: {target} ʀᴜɴs</b>\n")
    lines.append(f"🔄 <b>sᴡɪᴛᴄʜɪɴɢ sɪᴅᴇs...</b>")
    lines.append(f"ᴛᴇᴀᴍ <b>{new_batting_team}</b> captain, use <code>/batting</code>\n")
    lines.append("─────⊱◈◈◈⊰─────")

    return "\n".join(lines)

async def build_match_summary(client, match, winner):
    if winner == "Tie":
        return "🤝 <b>ᴍᴀᴛᴄʜ ᴛɪᴇᴅ!</b>\n\nWhat a spectacular finish! Both teams played brilliantly."

    user_cache = match.get("user_cache", {})
    res = [
        "🏆 <b>ᴍᴀᴛᴄʜ ᴄᴏɴᴄʟᴜᴅᴇᴅ</b> 🏆",
        f"✨ <b>ᴡɪɴɴᴇʀ: ᴛᴇᴀᴍ {winner}</b>\n",
        "× •-•-•-•-•-••-•-•⟮ 📊 ⟯•-•-•-•-•-•-•-•-• ×"
    ]

    motm_name = "N/A"
    motm_score = -1

    for t_key in ["A", "B"]:
        t_data = match["teams"][t_key]
        emoji = "🅰️" if t_key == "A" else "🅱️"
        res.append(f"\n{emoji} <b>ᴛᴇᴀᴍ {t_key}: {t_data['runs']}/{t_data['wickets']}</b>")

        team_players = {uid: p for uid, p in match["players"].items() if p.get('team') == t_key}

        if team_players:
            best_bat_id = max(team_players, key=lambda x: team_players[x].get("runs", 0))
            bb = team_players[best_bat_id]

            best_bowl_id = max(team_players, key=lambda x: (team_players[x].get("wickets", 0), -team_players[x].get("runs_conceded", 999)))
            bw = team_players[best_bowl_id]

            res.append(f"🔥 <b>ʙᴇsᴛ ʙᴀᴛᴛᴇʀ:</b> {user_cache.get(best_bat_id, 'Player')}")
            res.append(f"╰ {bb['runs']} runs ({bb['balls_faced']}b)")

            res.append(f"💎 <b>ʙᴇsᴛ ʙᴏᴡʟᴇʀ:</b> {user_cache.get(best_bowl_id, 'Player')}")
            res.append(f"╰ {bw.get('wickets', 0)} wkts | {bw.get('runs_conceded', 0)} runs conceded")

        for uid, p in team_players.items():
            p_score = p["runs"] + (p.get("wickets", 0) * 25)
            if p_score > motm_score:
                motm_score = p_score
                motm_name = user_cache.get(uid, "Player")

    res.append("\n× •-•-•-•-•-••-•-•⟮ 🎖 ⟯•-•-•-•-•-•-•-•-• ×")
    res.append(f"\n🎖 <b>ᴍᴀɴ ᴏғ ᴛʜᴇ ᴍᴀᴛᴄʜ</b>")
    res.append(f"🌟 <b>{motm_name}</b> ({motm_score} pts)")
    res.append("\n─────⊱◈◈◈⊰─────")
    res.append("ᴛʜᴀɴᴋs ғᴏʀ ᴘʟᴀʏɪɴɢ! 🎉")

    return "\n".join(res)
