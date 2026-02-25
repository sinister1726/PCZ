import asyncio
import random
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

from Assets.files import RUN_VIDEOS
from plugins.game.team import ACTIVE_MATCHES
from plugins.game.team.over_engine import advance_ball
from plugins.game.team.timeouts import start_timer

# 10-second command cooldown tracking per chat
GROUP_COOLDOWN = {}

def get_mention(match, user_id):
    """Stable HTML mention helper to prevent ENTITY_BOUNDS_INVALID."""
    name = match.get("user_cache", {}).get(user_id, "Player")
    return f'<a href="tg://user?id={user_id}">{name}</a>'

async def send_result_visuals(client, chat_id, key, caption):
    """
    FIX: Logic to handle both Videos and GIFs (Animations).
    """
    try:
        videos = RUN_VIDEOS.get(str(key))
        if not videos:
            raise ValueError(f"No visuals found for result: {key}")

        file_id = random.choice(videos)

        # Check if the file is likely a GIF or Video based on attributes isn't always possible 
        # via string ID alone, but we try-except the video send.
        try:
            await client.send_video(
                chat_id, 
                video=file_id, 
                caption=caption, 
                parse_mode=ParseMode.HTML
            )
        except Exception:
            # If video fails, it might be an animation (GIF)
            await client.send_animation(
                chat_id, 
                animation=file_id, 
                caption=caption, 
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        print(f"Visual Error: {e}")
        await client.send_message(chat_id, caption, parse_mode=ParseMode.HTML)

def get_display_ball_no(match):
    """
    Always shows the correct current delivery number.
    Source of truth = current_over_balls
    """
    balls_bowled = len(match.get("current_over_balls", []))
    return min(balls_bowled + 1, 6)



import asyncio
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def start_first_ball(client, match):
    """Trigger for the Over/Match sequence with Prompt Lock & Auto-Recovery."""

    # 🔒 PROMPT LOCK (Prevents Double Messages)
    if match.get("prompt_dispatched"):
        return
    match["prompt_dispatched"] = True

    # 🛠️ Client Recovery Layer
    if client is None:
        client = match.get("client")

    if client is None:
        match["prompt_dispatched"] = False
        print(f"❌ Critical: Client missing for Match {match.get('game_id')}")
        return

    chat_id = match.get("chat_id")
    bowler_id = match.get("current_bowler")
    striker_id = match.get("striker")

    # 🛑 HARD STATE GUARD
    if not chat_id or not bowler_id:
        match["prompt_dispatched"] = False
        return

    # ─────────────────────────────────────────────
    # ✅ FIX #1: STRIKER LIVENESS VALIDATION (CRITICAL)
    # ─────────────────────────────────────────────
    players = match.get("players", {})
    bat_team_key = match.get("batting_team")
    bat_team = match.get("teams", {}).get(bat_team_key, {})
    team_players = bat_team.get("players", [])

    def is_alive(uid):
        return uid and uid in team_players and not players.get(uid, {}).get("is_out", False)

    # If striker is dead / missing → auto-heal
    if not is_alive(striker_id):
        alive = [u for u in team_players if is_alive(u)]
        match["striker"] = alive[0] if alive else None
        striker_id = match["striker"]

    # Fix non-striker too (safety)
    if not is_alive(match.get("non_striker")):
        remaining = [u for u in team_players if is_alive(u) and u != striker_id]
        match["non_striker"] = remaining[0] if remaining else None

    # Still no striker? STOP.
    if not striker_id:
        match["prompt_dispatched"] = False
        return
    # ─────────────────────────────────────────────

    # 🛠️ Bot Username Caching
    if "bot_username" not in match:
        try:
            me = await client.get_me()
            match["bot_username"] = me.username
        except Exception:
            match["bot_username"] = "NexoraCricketBot"

    bot_username = match["bot_username"]

    # Initialize timeouts structure if missing
    if "timeouts" not in match:
        match["timeouts"] = {
            "bowler": {"fails": 0, "task": None},
            "batter": {"fails": 0, "task": None},
        }

    # Safe access to user names
    user_cache = match.get("user_cache", {})
    bowler_name = user_cache.get(bowler_id, "Bowler")
    striker_name = user_cache.get(striker_id, "Batter")

    # 1️⃣ GROUP NOTIFICATION
    group_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton("ᴅᴇʟɪᴠᴇʀ ʙᴀʟʟ ⚾", url=f"https://t.me/{bot_username}")
    ]])

    bowler_mention = f"<a href='tg://user?id={bowler_id}'>{bowler_name}</a>"
    caption = (
        f"🏟️ <b>𝗡𝗘𝗫𝗧 𝗗𝗘𝗟𝗜𝗩𝗘𝗥𝗬</b>\n"
        f"──┈┄┄╌╌╌╌┄┄┈──\n"
        f"🎯 {bowler_mention} ɪꜱ ʙᴏᴡʟɪɴɢ ᴛᴏ <b>{striker_name}</b>\n"
        f"🔢 Bowler, check your PM to deliver!"
    )

    from plugins.game.team.state import try_send_video
    try:
        await try_send_video(client, chat_id, "Bowling", caption, group_btn)
    except Exception as e:
        print(f"Group Notify Error: {e}")

    # 2️⃣ BOWLER DM
    ball_no = get_display_ball_no(match)

    try:
        await client.send_message(
            bowler_id,
            (
                "🏏 <b>𝗬𝗢𝗨𝗥 𝗧𝗨𝗥𝗡 𝗧𝗢 𝗕𝗢𝗪𝗟!</b>\n"
                "──┈┄┄╌╌╌╌┄┄┈──\n"
                f"👤 <b>Batter:</b> {striker_name}\n"
                "🔢 Send a number (<b>1-6</b>) to bowl.\n"
                "──┈┄┄╌╌╌╌┄┄┈──\n"
                f"🎯 <b>Over Ball :</b> {ball_no} / 6"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        match["prompt_dispatched"] = False
        await client.send_message(
            chat_id,
            f"⚠️ <b>Error:</b> Could not DM {bowler_name}. Please start the bot in PM!"
        )
        print(f"⚠️ DM Fail: {e}")
        return

    # 3️⃣ TIMEOUT LOGIC
    t_data = match["timeouts"]["bowler"]
    if t_data.get("task") and not t_data["task"].done():
        t_data["task"].cancel()

    from plugins.game.team.state import start_timer
    match["timeouts"]["bowler"]["task"] = asyncio.create_task(
        start_timer(match, "bowler")
    )

@Client.on_message(filters.private & filters.text)
async def bowler_dm_handler(client, message):
    uid = message.from_user.id

    # 🔍 Find active match where this user is the current bowler
    match = next(
        (m for m in list(ACTIVE_MATCHES.values()) if m.get("current_bowler") == uid),
        None
    )

    # 1️⃣ SAFETY CHECK
    if not match or match.get("phase") != "LIVE" or match.get("bowled"):
        return

    # 2️⃣ VALIDATE INPUT
    if not message.text.isdigit() or not (1 <= int(message.text) <= 6):
        return await message.reply_text(
            "❗ <b>Invalid delivery.</b>\nSend a number between <b>1 and 6</b>.",
            parse_mode=ParseMode.HTML
        )

    # 3️⃣ LOCK STATE (PREVENT DOUBLE DELIVERY)
    match["last_bowl"] = int(message.text)
    match["bowled"] = True

    # 4️⃣ TIMEOUT HANDLING — CANCEL BOWLER TIMER
    if "timeouts" not in match:
        match["timeouts"] = {
            "bowler": {"fails": 0, "task": None},
            "batter": {"fails": 0, "task": None},
        }

    t_bowler = match["timeouts"]["bowler"]
    if t_bowler.get("task"):
        try:
            t_bowler["task"].cancel()
        except Exception:
            pass

    # 5️⃣ UI FEEDBACK IN DM (SEQUENTIAL)
    chat_id = match["chat_id"]
    group_username = match.get("group_username")

    if group_username:
        group_url = f"https://t.me/{group_username}"
    else:
        clean_chat_id = str(chat_id).replace("-100", "")
        group_url = f"https://t.me/c/{clean_chat_id}"

    back_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back to Group 🏏", url=group_url)]
    ])

    # Emoji first (guaranteed order)
    await message.reply_text("⚾️", quote=True)

    # Confirmation text (fire-and-forget)
    asyncio.create_task(
        message.reply_text(
            f"✅ <b>Ball Delivered:</b> <b>{message.text}</b>\n\n"
            "Return to the group to watch the outcome unfold!",
            reply_markup=back_btn,
            parse_mode=ParseMode.HTML
        )
    )

    # 6️⃣ GROUP NOTIFICATION
    striker_id = match.get("striker")
    striker_name = match.get("user_cache", {}).get(striker_id, "Batter")

    ball_no = get_display_ball_no(match)

    caption = (
        f"⚾ <b>Ball Delivered!</b>  <b>Over Ball:</b> {ball_no} / 6\n"
        f"🏏 Batter <a href='tg://user?id={striker_id}'>{striker_name}</a>, "
        f"send your shot (0–6) in the group!"
    )

    # 7️⃣ TRIGGER GROUP MEDIA & START BATTER TIMER (PARALLEL)
    from plugins.game.team.state import try_send_video, start_timer

    asyncio.create_task(
        try_send_video(client, chat_id, "Batting", caption)
    )

    t_batter = match["timeouts"]["batter"]
    if t_batter.get("task"):
        try:
            t_batter["task"].cancel()
        except Exception:
            pass

    match["timeouts"]["batter"]["task"] = asyncio.create_task(
        start_timer(match, "batter")
    )

# ───────────────── BATTER GROUP HANDLER ─────────────────

import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.group & filters.text, group=1)
async def batter_handler(client, message):
    uid = message.from_user.id
    chat_id = message.chat.id

    match = ACTIVE_MATCHES.get(chat_id)

    # 1️⃣ SAFETY & STATE CHECKS
    if (
        not match
        or not match.get("bowled")
        or match.get("batted")
        or match.get("phase") != "LIVE"
    ):
        return

    # Only striker can bat
    if uid != match.get("striker"):
        return

    # Validate input
    if not message.text.isdigit() or not (0 <= int(message.text) <= 6):
        return

    bat_num = int(message.text)

    # ─────────────────────────────────────────
    # 🧢 HAT-TRICK RULE (NO NEW STATE USED)
    # If last 2 balls in THIS OVER were wickets,
    # this delivery is the HAT-TRICK BALL
    # ─────────────────────────────────────────
    over_balls = match.get("current_over_balls", [])

    is_hat_trick_ball = (
        len(over_balls) >= 2
        and over_balls[-1] == "W"
        and over_balls[-2] == "W"
    )

    if is_hat_trick_ball and bat_num == 0:
        # ❌ Do NOT lock batter
        await message.reply_text(
            "🧢 <b>Hat-trick ball!</b>\n"
            "❌ Dot (0) not allowed\n"
            "💥 Play a shot!",
            parse_mode=ParseMode.HTML,
            quote=True
        )
        return
    # ─────────────────────────────────────────

    # 🔒 LOCK BATTER IMMEDIATELY (prevents double hit)
    match["batted"] = True

    # 👍 ACK
    await message.reply_text("👍", quote=True)

    bowl_num = match.get("last_bowl")
    bowler_id = match.get("current_bowler")

    # ⏱ Cancel batter timeout
    t = match.get("timeouts", {}).get("batter", {}).get("task")
    if t:
        try:
            t.cancel()
        except:
            pass

    from plugins.game.team.state import try_send_video
    from plugins.game.team.over_engine import advance_ball

    is_out = (bat_num == bowl_num)
    runs = 0 if bat_num == 0 else bat_num

    # ───────────────── WICKET ─────────────────
    if is_out:
        mention = get_mention(match, uid)
        bowler_mention = get_mention(match, bowler_id)

        caption = (
            f"☝️ <b>OUT!</b>\n\n"
            f"👤 {mention} dismissed!\n"
            f"🎯 {bowler_mention} is on fire 🔥"
        )

        # 🎥 Visuals async
        asyncio.create_task(
            try_send_video(client, chat_id, "Out", caption)
        )

        await advance_ball(match, "W")

    # ───────────────── RUNS ─────────────────
    else:
        comms_list = {
            0: [
                # Funny / Savage
                "Dead bat. Crowd boos 😴",
                "Stonewall defence.",
                "Dot ball pressure builds…",
                "Bat says no, runs say bye 👋",
                "That ball died a lonely death.",
                "Even the bowler looks bored.",
                "Dot ball sponsored by patience.",
                "Defense so solid, WiFi can’t pass through.",
                "Crowd checks phone. Nothing happened.",
                "Pure defence, zero entertainment.",
                "A dot so quiet you can hear regrets.",
                "Commentator running out of words.",
                "Batting like it’s a test match 😐",
                "Kya hi ukhaad liya? Dot ball.",
                "Yeh shot nahi tha, majboori thi.",
                "Bowler smiling for no reason.",
                "Fielders relax, nothing to do.",
                "That ball deserves a refund.",
                "Momentum paused. Completely.",
                "Silence louder than crowd noise.",

                # Professional
                "Solid defensive technique on display.",
                "Good line respected by the batter.",
                "No scoring opportunity created.",
                "Bowler wins that mini battle.",
                "Textbook block.",
                "Correct shot for the situation.",

                # Savage
                "Scoreboard unchanged. Ego unchanged.",
                "That was cricket ASMR.",
                "Ball met bat. Nothing else happened.",
                "This over needs caffeine."
            ],

            1: [
                "Quick single!",
                "Sharp running!",
                "Keeps the scoreboard ticking.",
                "Steal of the century 🏃‍♂️",
                "Blink and you miss it!",
                "Just enough to survive.",
                "One run, infinite relief 😌",
                "Bowler annoyed, batter satisfied.",
                "Chori pakdi gayi, par run mil gaya 😏",
                "Fitness check passed.",
                "Ek run bhi aaj kal mehenga hai!",
                "Risk liya… bach gaye!",
                "Soft hands, smart feet.",
                "Sneaky but effective.",
                "Bowler not impressed.",
                "Captain sighs in disappointment.",
                "Hard-earned single.",
                "Minimal risk, maximum sense.",
                "Strike rotated successfully.",
                "Game awareness on point.",

                # Savage
                "One run and a long breath.",
                "Not pretty, but it works.",
                "Survival mode activated.",

                # Pro
                "Good placement into the gap.",
                "Rotates strike nicely.",
                "Keeps pressure manageable."
            ],

            2: [
                "Placed perfectly.",
                "Good awareness!",
                "Easy two.",
                "Threaded the gap like a needle 🪡",
                "Lazy fielding punished.",
                "They’ll take that all day.",
                "Smooth as butter 🧈",
                "Running between wickets: 10/10.",
                "Do run, no tension.",
                "Gap mila, mauka mila!",
                "Fielders still loading…",
                "Placement coaching DVD mein jayega.",
                "Timing beats power.",
                "Comfortable running.",
                "Good communication between batters.",
                "Bowler not happy.",
                "Safe cricket, smart cricket.",
                "Two runs without fuss.",
                "Pressure released slightly.",
                "Ground fielding exposed.",

                # Savage
                "Fielding standards questioned.",
                "That gap was illegal.",

                # Pro
                "Excellent shot selection.",
                "Perfect use of the field."
            ],

            3: [
                "Risky but rewarding!",
                "Great hustle!",
                "All legs, no brakes 😤",
                "Fielders confused, batters amused.",
                "That needed commitment — and lungs!",
                "Calculated madness!",
                "Captain screaming, crowd screaming louder.",
                "Teen run ya heart attack!",
                "Galti ki gunjaish zero thi 😬",
                "Yeh running nahi, sprint thi!",
                "Stadium mein oxygen kam pad gayi.",
                "Close call but worth it.",
                "Pressure cricket at its finest.",
                "Fielding chaos unlocked.",
                "Bowler furious.",
                "Crowd loves the drama.",
                "Risk meter full.",
                "Pure adrenaline.",
                "That was brave.",
                "Almost disaster!",

                # Savage
                "One bad throw and it was over.",
                "Bowler aged 5 years.",

                # Pro
                "Excellent commitment between wickets.",
                "High-risk, high-reward running."
            ],

            4: [
                "CRACKED! 💥",
                "That raced away!",
                "Boundary finds the rope!",
                "Pure timing. Chef’s kiss 👨‍🍳💋",
                "Bowler tried. Ball didn’t listen.",
                "Placed where the fielder isn’t.",
                "That’s a textbook boundary!",
                "Sponsors very happy right now.",
                "Chaar run aur bowler pareshaan!",
                "Shot mein class, bowler mein sass.",
                "Yeh ground shot ke liye chhota pad gaya!",
                "Ball bole: bas karo bhai!",
                "Elegant stroke play.",
                "No chance for anyone.",
                "Crowd on its feet!",
                "That was effortless.",
                "Boundary like a statement.",
                "Timing > power.",
                "Bowler loses length.",
                "Confidence booster!",

                # Savage
                "Bowler absolutely cooked.",
                "That gap was personal.",

                # Pro
                "Exquisite timing and placement.",
                "Classic cricketing shot."
            ],

            5: [
                "Chaos in the field!",
                "Overthrows galore!",
                "Fielding.exe has stopped working 💀",
                "Everyone running, nobody stopping!",
                "Bowler questioning life choices.",
                "Captain hiding behind the cap.",
                "This is comedy cricket 🤡",
                "Yeh fielding nahi, blooper reel hai!",
                "Ball bhi confused, fielder bhi!",
                "Coach ne aankhein band kar li 👀",
                "Five runs… aur izzat free mein!",
                "Absolute panic stations.",
                "Pressure causes mistakes.",
                "Fielding meltdown.",
                "Communication? Missing.",
                "One error, big damage.",
                "Bowler helpless.",
                "Crowd laughing hard.",
                "Chaos unlocked.",
                "Defensive drills incoming.",

                # Savage
                "That was illegal fielding.",
                "Someone getting benched.",

                # Pro
                "Capitalized on fielding errors.",
                "Awareness to keep running."
            ],

            6: [
                "🚀 INTO ORBIT!",
                "HUGE MAXIMUM!",
                "Bowler in shambles 😭",
                "That ball needs a passport!",
                "Satellite launched successfully 🛰️",
                "Clean hit, cleaner vibes 🔥",
                "Crowd loses its mind!",
                "Somewhere a fielder just gave up.",
                "Six runs and emotional damage 💔",
                "Yeh shot nahi, warning thi!",
                "Ball milne ka koi chance nahi!",
                "Bowler bole: bas bhai, over khatam karo!",
                "Stadium ke bahar giri hai yeh!",
                "SHOT ITNI BADI, SCOREBOARD HIL GAYA 💣",
                "Absolutely smoked!",
                "That’s gone miles.",
                "Pure power!",
                "No doubts, no drama.",
                "Bowler looks at the sky.",
                "Momentum completely flipped.",

                # Savage
                "Bowler needs therapy.",
                "That landed in another district.",

                # Pro
                "Perfect swing, perfect connection.",
                "Clean striking at its best."
            ]
        }


        caption = (
            f"🏏 <b>{runs} Run(s)!</b>\n"
            f"╰⊚ {random.choice(comms_list[runs])}"
        )

        asyncio.create_task(
            try_send_video(client, chat_id, str(runs), caption)
        )

        await advance_ball(match, runs)

# 3️⃣ High Speed Video Fallback Helper (Safe 5-Argument Version)
async def try_send_video(client, chat_id, key, caption, reply_markup=None):
    """
    Tries to send a video. If it's an animation (GIF) hidden in a video 
    structure, it catches the error and retries with the correct method.
    """
    video_list = RUN_VIDEOS.get(str(key), [])
    if not video_list:
        return await client.send_message(chat_id, caption, parse_mode=ParseMode.HTML)

    file_id = random.choice(video_list)
    if not file_id or file_id.startswith("FILE_ID"):
        return await client.send_message(chat_id, caption, parse_mode=ParseMode.HTML)

    try:
        # Attempt 1: Standard Video
        return await client.send_video(
            chat_id=chat_id,
            video=file_id,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        err = str(e).upper()
        # Check if Telegram specifically says this should be an animation
        if "ANIMATION" in err or "CONTENT_TYPE" in err or "VIDEO_CONTENT_REQUIRED" in err:
            try:
                # Attempt 2: Retry as Animation
                return await client.send_animation(
                    chat_id=chat_id,
                    animation=file_id,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            except Exception as anim_e:
                print(f"❌ Both media types failed: {anim_e}")

        # FINAL FALLBACK: Send as Text if all media calls fail
        return await client.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

# ───────────────── HELPER: COMMAND COOLDOWN ─────────────────

@Client.on_message(filters.command(["score", "userinfo", "graph"]) & filters.group, group=-1)
async def check_cooldown(client, message):
    chat_id = message.chat.id
    now = time.time()
    if chat_id in GROUP_COOLDOWN:
        diff = now - GROUP_COOLDOWN[chat_id]
        if diff < 10:
            await message.reply_text(f"⏳ **Slow down!** Try again after {int(10 - diff)}s.")
            await message.stop_propagation()
    GROUP_COOLDOWN[chat_id] = now
