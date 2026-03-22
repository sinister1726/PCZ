import asyncio
import random
from pyrogram import Client
from pyrogram.enums import ParseMode
from database.connection import db

NUDGE_INTERVAL = 3600 * 6
INACTIVITY_DAYS = 3

NUDGE_MESSAGES = [
    "🏏 <b>The pitch misses you, Captain!</b>\nYou haven't played in a while. Your rank is gathering dust 😤\nHead to your group and smash some runs! 🔥",
    "⚡ <b>Your rivals are grinding!</b>\nWhile you're away, others are climbing the leaderboard 📈\nCome back and reclaim your spot — the crease is calling! 🏟️",
    "🦆 <b>Don't let your legacy fade!</b>\nIt's been {days} days since your last match. Every day idle is a day your rivals get stronger 💀\nBack to the pitch! 🏏",
    "🌟 <b>You've been inactive for {days} days!</b>\nYour Cricket DNA is waiting to evolve — but only if you play 🧬\nCome join a match and show what you're made of! ⚔️",
    "🔥 <b>ALERT: Rank under threat!</b>\n{days} days without a match? Someone might just overtake you soon 👀\nLog in and defend your legacy! 🏆",
]

async def _run_nudge_loop(client: Client):
    await asyncio.sleep(60)
    while True:
        try:
            await _send_nudges(client)
        except Exception as e:
            print(f"Nudge loop error: {e}")
        await asyncio.sleep(NUDGE_INTERVAL)


async def _send_nudges(client: Client):
    try:
        await db.ensure_pool()
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT us.user_id, us.first_name, 
                       EXTRACT(EPOCH FROM (NOW() - us.last_played_at)) / 86400 AS days_inactive
                FROM user_stats us
                JOIN users u ON us.user_id = u.user_id
                WHERE us.last_played_at IS NOT NULL
                  AND us.last_played_at < NOW() - INTERVAL '3 days'
                  AND us.matches > 0
                  AND COALESCE(u.notify_enabled, TRUE) = TRUE
                LIMIT 50
                """
            )
    except Exception as e:
        print(f"Nudge DB fetch error: {e}")
        return

    sent = 0
    for row in rows:
        uid = row["user_id"]
        days = int(row.get("days_inactive", INACTIVITY_DAYS))
        name = row.get("first_name") or "Captain"

        msg = random.choice(NUDGE_MESSAGES).format(days=days, name=name)

        try:
            await client.send_message(uid, msg, parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.5)
        except Exception:
            pass

    if sent:
        print(f"✅ Nudge: Sent {sent} inactivity reminders.")


def start_nudge_task(client: Client):
    asyncio.create_task(_run_nudge_loop(client))
    print("✅ Inactivity nudge task started.")
