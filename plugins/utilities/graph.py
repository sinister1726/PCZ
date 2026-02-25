import time
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pyrogram import Client, filters
from plugins.game.team import ACTIVE_MATCHES

GRAPH_COOLDOWN = {}

async def get_graph_buffer(match):
    import io
    import matplotlib.pyplot as plt

    overs_limit = int(match.get("overs", 5))

    def build_over_worm(team_key):
        team = match["teams"].get(team_key, {})

        balls = int(team.get("balls", 0) or 0)
        if balls <= 0:
            return [], []

        # ✅ Per-ball runs (SOURCE OF TRUTH)
        per_ball = team.get("over_history", [])

        usable = min(len(per_ball), balls)
        padded = per_ball[:usable] + [0] * max(0, balls - usable)

        overs = []
        cumulative = []

        total = 0
        ball_no = 0

        for runs in padded:
            ball_no += 1
            total += runs

            # ⭐ fractional overs = real worm
            overs.append(ball_no / 6)
            cumulative.append(total)

        return overs, cumulative

    # ─── STYLE (KEEP YOUR THEME) ───
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 4.8))

    # ─── TEAM A ───
    xa, ya = build_over_worm("A")
    if xa:
        ax.plot(
            xa, ya,
            lw=3,
            color="#ff4c4c",
            label="Team A"
        )

    # ─── TEAM B ───
    xb, yb = build_over_worm("B")
    if xb:
        ax.plot(
            xb, yb,
            lw=3,
            color="#4da6ff",
            label="Team B"
        )

    # ─── TARGET + WIN % (UNCHANGED) ───
    if match.get("innings") == 2 and match.get("target"):
        target = int(match["target"])
        ax.axhline(target, ls="--", lw=2, color="gold", alpha=0.8)

        bat_team = match["teams"].get(match.get("batting_team"), {})
        runs_now = int(bat_team.get("runs", 0) or 0)
        balls_now = int(bat_team.get("balls", 0) or 0)

        balls_left = max(0, overs_limit * 6 - balls_now)
        runs_left = max(0, target - runs_now)

        if balls_left > 0 and runs_left > 0 and balls_now > 0:
            req_rr = (runs_left / balls_left) * 6
            cur_rr = (runs_now / balls_now) * 6
            win_prob = max(0, min(100, 50 + (cur_rr - req_rr) * 8))
        else:
            win_prob = 100 if runs_now >= target else 0

        ax.text(
            0.99, 0.93,
            f"Win % : {int(win_prob)}%",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=11,
            color="gold",
            weight="bold"
        )

    # ─── AXES ───
    ax.set_title("CRICKET WORM • OVER BY OVER", fontsize=13, weight="bold")
    ax.set_xlabel("Overs")
    ax.set_ylabel("Runs")

    ax.set_xlim(0, overs_limit)
    ax.set_xticks(range(0, overs_limit + 1))
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left")

    buf = io.BytesIO()
    plt.savefig(buf, dpi=130, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf

@Client.on_message(filters.command("graph") & filters.group)
async def score_graph(client, message):
    chat_id = message.chat.id
    now = time.time()

    if chat_id in GRAPH_COOLDOWN and (now - GRAPH_COOLDOWN[chat_id]) < 10:
        return await message.reply_text("⏳ **Cooldown active.**")

    match = ACTIVE_MATCHES.get(chat_id)
    if not match:
        return await message.reply_text("❌ **No active match.**")

    GRAPH_COOLDOWN[chat_id] = now
    buf = await get_graph_buffer(match)

    a_runs, a_wick = match["teams"]["A"]["runs"], match["teams"]["A"]["wickets"]
    b_runs, b_wick = match["teams"]["B"]["runs"], match["teams"]["B"]["wickets"]

    caption = (
        f"📊 <b>𝗦𝗖𝗢𝗥𝗘 𝗣𝗥𝗢𝗚𝗥𝗘𝗦𝗦𝗜𝗢𝗡</b>\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n"
        f"🔴 <b>Team A:</b> <code>{a_runs}/{a_wick}</code>\n"
        f"🔵 <b>Team B:</b> <code>{b_runs}/{b_wick}</code>\n"
        "────┈┄┄╌╌╌╌┄┄┈────"
    )

    await message.reply_photo(photo=buf, caption=caption)
