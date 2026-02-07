
from pyrogram.types import Message
from pyrogram import Client, filters
from database.connection import db

import io
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pyrogram import Client, filters

# ─────────── ASSETS ───────────
NAME_FONT = "Assets/namefont.ttf"
TEXT_FONT = "Assets/fonts.ttf"

W, H = 1280, 720

# ─────────── COLORS ───────────
DARK = (10, 12, 18)
WHITE = (245, 245, 245)
MUTED = (180, 180, 180)

RARITY_COLORS = {
    "COMMON": (180, 180, 180),
    "RARE": (80, 160, 255),
    "EPIC": (170, 90, 255),
    "LEGEND": (255, 200, 60),
    "MYTHIC": (255, 80, 80),
}

# ─────────── HELPERS ───────────

def circle_avatar(pfp: Image.Image, size=320, glow=(255, 200, 60)):
    pfp = pfp.resize((size, size)).convert("RGBA")

    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, size, size), fill=255)

    base = Image.new("RGBA", (size+30, size+30), (0, 0, 0, 0))
    glow_layer = Image.new("RGBA", base.size, glow + (120,))
    glow_mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(glow_mask).ellipse((5, 5, size+25, size+25), fill=255)
    glow_layer.putalpha(glow_mask)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(18))

    base.paste(glow_layer, (0, 0), glow_layer)
    base.paste(pfp, (15, 15), mask)
    return base


def draw_stat(draw, x, y, label, value, font):
    draw.text((x, y), label, fill=MUTED, font=font)
    draw.text((x+260, y), str(value), fill=WHITE, font=font)


def fetch_avatar(client, user):
    bio = io.BytesIO()
    client.download_media(user.photo.big_file_id, file_name=bio)
    bio.seek(0)
    return Image.open(bio)

# ─────────── BASE DATA ───────────

def mock_stats():
    return {
        "matches": random.randint(50, 300),
        "runs": random.randint(800, 6000),
        "wickets": random.randint(20, 300),
        "sr": round(random.uniform(120, 280), 2),
        "hs": random.randint(40, 180),
        "50s": random.randint(1, 30),
        "100s": random.randint(0, 15),
    }

def pick_rarity(stats):
    if stats["runs"] > 5000:
        return "MYTHIC"
    if stats["runs"] > 3500:
        return "LEGEND"
    if stats["runs"] > 2000:
        return "EPIC"
    if stats["runs"] > 1000:
        return "RARE"
    return "COMMON"

# ─────────────────────────────────────────────
# 🟡 BANNER 1 – BRUSH + AUTHORITY
# /banner1
# ─────────────────────────────────────────────

@Client.on_message(filters.command("banner1"))
async def banner_1(client, message):
    user = message.from_user
    stats = mock_stats()
    rarity = pick_rarity(stats)

    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)

    name_f = ImageFont.truetype(NAME_FONT, 64)
    text_f = ImageFont.truetype(TEXT_FONT, 34)

    # Brush stroke
    draw.rectangle((0, 0, 460, H), fill=RARITY_COLORS[rarity])

    draw.text((40, 40), "PLAY CRICKET GAME", fill=WHITE, font=text_f)
    draw.text((40, 120), user.first_name.upper(), fill=WHITE, font=name_f)

    y = 220
    for k, v in [
        ("MATCHES", stats["matches"]),
        ("RUNS", stats["runs"]),
        ("WICKETS", stats["wickets"]),
        ("STRIKE RATE", stats["sr"]),
        ("HIGHEST", stats["hs"]),
    ]:
        draw_stat(draw, 40, y, k, v, text_f)
        y += 52

    # Avatar
    try:
        pfp = await client.download_media(user.photo.big_file_id, in_memory=True)
        avatar = circle_avatar(Image.open(pfp), glow=RARITY_COLORS[rarity])
        img.paste(avatar, (820, 180), avatar)
    except:
        pass

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    await message.reply_photo(buf, caption=f"🏷️ {rarity} PLAYER")

# ─────────────────────────────────────────────
# 🟡 BANNER 2 – SPLIT PANEL
# /banner2
# ─────────────────────────────────────────────

@Client.on_message(filters.command("banner2"))
async def banner_2(client, message):
    user = message.from_user
    stats = mock_stats()
    rarity = pick_rarity(stats)

    img = Image.new("RGB", (W, H), (18, 18, 30))
    draw = ImageDraw.Draw(img)

    name_f = ImageFont.truetype(NAME_FONT, 60)
    text_f = ImageFont.truetype(TEXT_FONT, 30)

    draw.rectangle((W//2, 0, W, H), fill=RARITY_COLORS[rarity])

    draw.text((60, 80), user.first_name, fill=WHITE, font=name_f)

    y = 180
    for k, v in stats.items():
        draw_stat(draw, 60, y, k.upper(), v, text_f)
        y += 45

    try:
        pfp = await client.download_media(user.photo.big_file_id, in_memory=True)
        avatar = circle_avatar(Image.open(pfp), glow=RARITY_COLORS[rarity])
        img.paste(avatar, (820, 200), avatar)
    except:
        pass

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    await message.reply_photo(buf)

# ─────────────────────────────────────────────
# 🟡 BANNER 3 – DARK PRO
# /banner3
# ─────────────────────────────────────────────

@Client.on_message(filters.command("banner3"))
async def banner_3(client, message):
    user = message.from_user
    stats = mock_stats()
    rarity = pick_rarity(stats)

    img = Image.new("RGB", (W, H), (5, 5, 8))
    draw = ImageDraw.Draw(img)

    name_f = ImageFont.truetype(NAME_FONT, 58)
    text_f = ImageFont.truetype(TEXT_FONT, 28)

    draw.text((W//2, 50), user.first_name.upper(),
              fill=RARITY_COLORS[rarity], font=name_f, anchor="mm")

    try:
        pfp = await client.download_media(user.photo.big_file_id, in_memory=True)
        avatar = circle_avatar(Image.open(pfp), glow=RARITY_COLORS[rarity])
        img.paste(avatar, (W//2 - 170, 140), avatar)
    except:
        pass

    y = 500
    x = 140
    for k, v in stats.items():
        draw.text((x, y), f"{k.upper()}: {v}", fill=WHITE, font=text_f)
        x += 260

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    await message.reply_photo(buf)

# ─────────────────────────────────────────────
# 🔥 POSTER 1 – MVP
# /poster1
# ─────────────────────────────────────────────

@Client.on_message(filters.command("poster1"))
async def poster_1(client, message):
    user = message.from_user
    stats = mock_stats()

    img = Image.new("RGB", (720, 1080), DARK)
    draw = ImageDraw.Draw(img)

    name_f = ImageFont.truetype(NAME_FONT, 56)
    text_f = ImageFont.truetype(TEXT_FONT, 32)

    draw.text((360, 80), "PLAYER OF THE MATCH", fill=(255, 200, 60),
              font=text_f, anchor="mm")

    draw.text((360, 160), user.first_name, fill=WHITE,
              font=name_f, anchor="mm")

    try:
        pfp = await client.download_media(user.photo.big_file_id, in_memory=True)
        avatar = circle_avatar(Image.open(pfp), size=360, glow=(255, 200, 60))
        img.paste(avatar, (180, 240), avatar)
    except:
        pass

    y = 700
    for k, v in stats.items():
        draw.text((360, y), f"{k.upper()} : {v}",
                  fill=WHITE, font=text_f, anchor="mm")
        y += 42

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    await message.reply_photo(buf)

# ─────────────────────────────────────────────
# 🔥 POSTER 2 – HERO
# /poster2
# ─────────────────────────────────────────────

@Client.on_message(filters.command("poster2"))
async def poster_2(client, message):
    user = message.from_user
    stats = mock_stats()

    img = Image.new("RGB", (720, 1080), (20, 5, 5))
    draw = ImageDraw.Draw(img)

    name_f = ImageFont.truetype(NAME_FONT, 54)
    text_f = ImageFont.truetype(TEXT_FONT, 30)

    draw.text((360, 60), "MATCH HERO", fill=(255, 80, 80),
              font=text_f, anchor="mm")

    try:
        pfp = await client.download_media(user.photo.big_file_id, in_memory=True)
        avatar = circle_avatar(Image.open(pfp), size=400, glow=(255, 80, 80))
        img.paste(avatar, (160, 180), avatar)
    except:
        pass

    draw.text((360, 640), user.first_name.upper(),
              fill=WHITE, font=name_f, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    await message.reply_photo(buf)

# ─────────────────────────────────────────────
# 💎 CARD – COLLECTIBLE
# /card
# ─────────────────────────────────────────────

@Client.on_message(filters.command("card"))
async def collectible_card(client, message):
    user = message.from_user
    stats = mock_stats()
    rarity = pick_rarity(stats)

    img = Image.new("RGB", (420, 620), DARK)
    draw = ImageDraw.Draw(img)

    name_f = ImageFont.truetype(NAME_FONT, 36)
    text_f = ImageFont.truetype(TEXT_FONT, 22)

    draw.rectangle((0, 0, 420, 80), fill=RARITY_COLORS[rarity])
    draw.text((210, 40), rarity, fill=WHITE, font=text_f, anchor="mm")

    try:
        pfp = await client.download_media(user.photo.big_file_id, in_memory=True)
        avatar = circle_avatar(Image.open(pfp), size=220,
                               glow=RARITY_COLORS[rarity])
        img.paste(avatar, (100, 110), avatar)
    except:
        pass

    draw.text((210, 360), user.first_name,
              fill=WHITE, font=name_f, anchor="mm")

    y = 420
    for k, v in list(stats.items())[:4]:
        draw.text((210, y), f"{k.upper()} {v}",
                  fill=MUTED, font=text_f, anchor="mm")
        y += 34

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    await message.reply_photo(buf, caption="🎴 Collectible Player Card")



@Client.on_message(filters.command("fileid"))
async def get_file_id(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply:
        return await message.reply_text("Reply to a media to get its file_id.")
    
    media = reply.photo or reply.video or reply.document or reply.sticker or reply.animation or reply.voice or reply.video_note
    if media:
        await message.reply_text(f"File ID: `{media.file_id}`")
    else:
        await message.reply_text("No media found in the replied message.")

import time

COOLDOWN_DATA = {}

def is_allowed(user_id):
    current_time = time.time()
    last_time = COOLDOWN_DATA.get(user_id, 0)
    if current_time - last_time < 5:
        return False, int(5 - (current_time - last_time))
    COOLDOWN_DATA[user_id] = current_time
    return True, 0

