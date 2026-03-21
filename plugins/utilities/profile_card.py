import io
import os
import random
from PIL import Image, ImageDraw, ImageFont

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "Assets")
FONT_BOLD_PATH = os.path.join(ASSETS, "namefont.ttf")
FONT_REG_PATH  = os.path.join(ASSETS, "fonts.ttf")

W, H = 920, 510

# ── helpers ──────────────────────────────────────────────────────────────────

def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def _make_circle_mask(size):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    return mask

def _shadow_text(draw, xy, text, font, fill, shadow=(0, 0, 0), radius=2):
    x, y = xy
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)

# ── brush-stroke patterns ─────────────────────────────────────────────────────

def _strokes_diagonal(d, ac, acd, dark):
    """Classic diagonal slash — original style."""
    def s(pts, c, a): d.polygon(pts, fill=c + (a,))
    s([(0, int(H*.45)),(0,H),(70,H),(45,int(H*.35))], acd, 230)
    s([(0, int(H*.15)),(0,int(H*.50)),(110,int(H*.38)),(75,int(H*.05))], acd, 200)
    s([(0, int(H*.50)),(0,H),(100,H),(60,int(H*.40))], ac, 155)
    s([(0, int(H*.20)),(0,int(H*.55)),(50,int(H*.45)),(20,int(H*.12))], ac, 95)
    s([(85,H),(260,int(H*.08)),(340,int(H*.22)),(165,H)], acd, 215)
    s([(40,H),(195,int(H*.05)),(270,int(H*.20)),(115,H)], ac, 135)
    s([(140,H),(310,int(H*.12)),(390,int(H*.30)),(225,H)], acd, 165)
    s([(0,0),(200,0),(160,55),(0,70)], acd, 175)
    s([(0,0),(130,0),(95,38),(0,50)], ac, 110)
    s([(W-60,0),(W,0),(W,int(H*.35)),(W-80,int(H*.25))], acd, 180)
    s([(W-100,0),(W-55,0),(W-35,int(H*.25)),(W-115,int(H*.15))], ac, 115)
    s([(55,int(H*.65)),(85,int(H*.60)),(175,H),(135,H)], dark, 200)
    s([(235,int(H*.10)),(295,int(H*.02)),(365,int(H*.22)),(300,int(H*.30))], dark, 175)

def _strokes_horizontal_frost(d, ac, acd, dark):
    """Horizontal frost-streak slabs — Arctic / Ice style."""
    def s(pts, c, a): d.polygon(pts, fill=c + (a,))
    # Wide horizontal streaks across the full width
    s([(0,int(H*.06)),(W,int(H*.06)),(W,int(H*.18)),(0,int(H*.14))], acd, 80)
    s([(0,int(H*.40)),(W,int(H*.36)),(W,int(H*.52)),(0,int(H*.56))], acd, 70)
    s([(0,int(H*.80)),(W,int(H*.76)),(W,int(H*.86)),(0,int(H*.90))], acd, 75)
    # Bright thin accent lines
    s([(0,int(H*.10)),(W*0.6,int(H*.09)),(W*0.6,int(H*.12)),(0,int(H*.13))], ac, 160)
    s([(0,int(H*.44)),(W*0.55,int(H*.42)),(W*0.55,int(H*.46)),(0,int(H*.48))], ac, 145)
    s([(0,int(H*.82)),(W*0.65,int(H*.80)),(W*0.65,int(H*.83)),(0,int(H*.85))], ac, 155)
    # Corner top-left ice slab
    s([(0,0),(W*0.35,0),(W*0.28,int(H*.22)),(0,int(H*.28))], acd, 190)
    s([(0,0),(W*0.20,0),(W*0.14,int(H*.14)),(0,int(H*.18))], ac, 130)
    # Bottom-right ice slab
    s([(W*0.50,H),(W,H),(W,int(H*.70)),(W*0.60,int(H*.78))], acd, 175)

def _strokes_bottom_explosion(d, ac, acd, dark):
    """Spikes rising from the bottom — Toxic / Energy style."""
    def s(pts, c, a): d.polygon(pts, fill=c + (a,))
    # Spikes shooting upward from bottom
    s([(0,H),(120,H),(80,int(H*.30)),(20,int(H*.42))], acd, 220)
    s([(60,H),(200,H),(155,int(H*.15)),(100,int(H*.28))], ac, 160)
    s([(170,H),(310,H),(265,int(H*.22)),(210,int(H*.35))], acd, 200)
    s([(260,H),(360,H),(330,int(H*.40)),(285,int(H*.50))], ac, 130)
    s([(W*0.55,H),(W*0.70,H),(W*0.66,int(H*.55)),(W*0.58,int(H*.62))], acd, 150)
    # Top-left slash accent
    s([(0,0),(160,0),(120,int(H*.28)),(0,int(H*.38))], acd, 170)
    s([(0,0),(90,0),(60,int(H*.18)),(0,int(H*.24))], ac, 115)
    # Right edge spike
    s([(W-50,H),(W,H),(W,int(H*.45)),(W-70,int(H*.55))], acd, 175)
    s([(W-90,H),(W-45,H),(W-40,int(H*.60)),(W-100,int(H*.68))], ac, 120)
    s([(50,int(H*.70)),(90,int(H*.65)),(160,H),(110,H)], dark, 200)

def _strokes_corner_blobs(d, ac, acd, dark):
    """Four-corner accent blobs with a center spine — Steel / Cyber style."""
    def s(pts, c, a): d.polygon(pts, fill=c + (a,))
    # TL corner
    s([(0,0),(W*0.30,0),(W*0.22,int(H*.45)),(0,int(H*.50))], acd, 210)
    s([(0,0),(W*0.18,0),(W*0.12,int(H*.30)),(0,int(H*.35))], ac, 155)
    # TR corner
    s([(W,0),(W-W*0.28,0),(W-W*0.20,int(H*.38)),(W,int(H*.45))], acd, 190)
    s([(W,0),(W-W*0.15,0),(W-W*0.10,int(H*.22)),(W,int(H*.28))], ac, 130)
    # BL corner
    s([(0,H),(W*0.28,H),(W*0.20,int(H*.58)),(0,int(H*.52))], acd, 200)
    s([(0,H),(W*0.16,H),(W*0.10,int(H*.72)),(0,int(H*.66))], ac, 140)
    # BR corner
    s([(W,H),(W-W*0.25,H),(W-W*0.18,int(H*.60)),(W,int(H*.55))], acd, 185)
    # Center vertical spine
    cx = W // 2
    s([(cx-28,0),(cx+28,0),(cx+20,H),(cx-20,H)], acd, 45)
    s([(cx-12,0),(cx+12,0),(cx+8,H),(cx-8,H)], ac, 60)
    # Depth darks
    s([(W*0.18,int(H*.48)),(W*0.24,int(H*.44)),(W*0.32,int(H*.60)),(W*0.26,int(H*.64))], dark, 190)

# map theme id → stroke function
STROKE_FUNCS = {
    "neon_green":     _strokes_diagonal,
    "crimson_fire":   _strokes_diagonal,
    "cosmic_purple":  _strokes_diagonal,
    "cyber_gold":     _strokes_corner_blobs,
    "arctic_ice":     _strokes_horizontal_frost,
    "toxic_orange":   _strokes_bottom_explosion,
    "steel_blue":     _strokes_corner_blobs,
}

# ── themes ────────────────────────────────────────────────────────────────────

THEMES = [
    # ── EXISTING 3 ──────────────────────────────────────────────────────────
    {
        "id": "neon_green",
        "bg":          ( 6,  12,  26),
        "accent":      (50, 235,  10),
        "accent_dark": (20, 120,   5),
        "accent_glow": (80, 255,  40),
        "title_color": (50, 235,  10),
        "label_color": (220, 255, 220),
        "value_color": (255, 255, 255),
        "id_color":    (50,  235,  10),
        "divider":     (45, 110,  45),
        "ring_color":  (50,  235,  10),
        "box_bg":      (10,  30,   10),
        "subtitle":    (160, 220, 160),
    },
    {
        "id": "crimson_fire",
        "bg":          (15,   5,   8),
        "accent":      (255,  25,  55),
        "accent_dark": (140,  10,  25),
        "accent_glow": (255,  80, 100),
        "title_color": (255,  55,  80),
        "label_color": (255, 210, 210),
        "value_color": (255, 255, 255),
        "id_color":    (255,  80, 100),
        "divider":     (110,  35,  45),
        "ring_color":  (255,  25,  55),
        "box_bg":      (30,    8,  12),
        "subtitle":    (240, 160, 170),
    },
    {
        "id": "cosmic_purple",
        "bg":          ( 6,   0,  20),
        "accent":      (150,  40, 255),
        "accent_dark": (80,   10, 160),
        "accent_glow": (190, 100, 255),
        "title_color": (200, 110, 255),
        "label_color": (230, 210, 255),
        "value_color": (255, 255, 255),
        "id_color":    (200, 110, 255),
        "divider":     (80,   35, 130),
        "ring_color":  (150,  40, 255),
        "box_bg":      (18,    5,  40),
        "subtitle":    (210, 165, 255),
    },
    # ── 4 NEW STYLES ────────────────────────────────────────────────────────
    {
        "id": "cyber_gold",
        "bg":          (10,   8,   2),
        "accent":      (255, 200,   0),
        "accent_dark": (160, 110,   0),
        "accent_glow": (255, 230,  80),
        "title_color": (255, 210,  20),
        "label_color": (255, 240, 185),
        "value_color": (255, 255, 255),
        "id_color":    (255, 210,  20),
        "divider":     (110,  80,   5),
        "ring_color":  (255, 200,   0),
        "box_bg":      (28,  20,   2),
        "subtitle":    (240, 190,  80),
    },
    {
        "id": "arctic_ice",
        "bg":          ( 4,  12,  28),
        "accent":      ( 0, 220, 255),
        "accent_dark": ( 0,  90, 160),
        "accent_glow": (80, 240, 255),
        "title_color": ( 0, 230, 255),
        "label_color": (185, 240, 255),
        "value_color": (255, 255, 255),
        "id_color":    ( 0, 230, 255),
        "divider":     (20,  90, 130),
        "ring_color":  ( 0, 220, 255),
        "box_bg":      ( 5,  25,  50),
        "subtitle":    (130, 210, 240),
    },
    {
        "id": "toxic_orange",
        "bg":          (12,   6,   2),
        "accent":      (255, 110,   0),
        "accent_dark": (160,  50,   0),
        "accent_glow": (255, 160,  40),
        "title_color": (255, 130,  10),
        "label_color": (255, 225, 190),
        "value_color": (255, 255, 255),
        "id_color":    (255, 140,  20),
        "divider":     (120,  55,  10),
        "ring_color":  (255, 110,   0),
        "box_bg":      (30,  14,   3),
        "subtitle":    (240, 170,  90),
    },
    {
        "id": "steel_blue",
        "bg":          ( 5,  10,  22),
        "accent":      (30, 120, 255),
        "accent_dark": (10,  55, 160),
        "accent_glow": (80, 165, 255),
        "title_color": (60, 145, 255),
        "label_color": (190, 215, 255),
        "value_color": (255, 255, 255),
        "id_color":    (80, 160, 255),
        "divider":     (25,  65, 130),
        "ring_color":  (30, 120, 255),
        "box_bg":      (10,  20,  55),
        "subtitle":    (140, 190, 255),
    },
]

# ── drawing ───────────────────────────────────────────────────────────────────

def _draw_brush_strokes(img: Image.Image, theme: dict):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d  = ImageDraw.Draw(overlay)
    ac  = theme["accent"]
    acd = theme["accent_dark"]
    dark = tuple(max(0, c - 18) for c in theme["bg"])

    fn = STROKE_FUNCS.get(theme["id"], _strokes_diagonal)
    fn(d, ac, acd, dark)

    img.paste(overlay, mask=overlay.split()[3])


def _draw_profile_box(card: Image.Image, photo_bytes, theme: dict):
    glow_color = theme["accent_glow"]
    ring_color = theme["ring_color"]
    box_bg     = theme["box_bg"]

    box_size = 280
    bx = W - box_size - 38
    by = (H - box_size) // 2

    # Outer glow behind box
    glow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    for spread in range(22, 0, -1):
        alpha = int(140 * (spread / 22) ** 1.6)
        gd.rounded_rectangle(
            [bx - spread, by - spread, bx + box_size + spread, by + box_size + spread],
            radius=30 + spread, fill=glow_color + (alpha,)
        )
    card.paste(glow, mask=glow.split()[3])

    # Rounded box background
    box_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(box_layer)
    bd.rounded_rectangle([bx, by, bx + box_size, by + box_size],
                         radius=26, fill=box_bg + (255,))
    card.paste(box_layer, mask=box_layer.split()[3])

    # Profile photo
    circle_d = 220
    cx = bx + (box_size - circle_d) // 2
    cy = by + (box_size - circle_d) // 2

    if photo_bytes:
        try:
            pfp = Image.open(photo_bytes).convert("RGBA")
            pfp = pfp.resize((circle_d, circle_d), Image.LANCZOS)
        except Exception:
            pfp = None
    else:
        pfp = None

    if pfp is None:
        pfp = Image.new("RGBA", (circle_d, circle_d), (40, 40, 40, 255))
        ImageDraw.Draw(pfp).ellipse((0, 0, circle_d - 1, circle_d - 1), fill=(55, 55, 55, 255))

    mask = _make_circle_mask(circle_d)

    # Glow ring
    ring_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring_layer)
    for i in range(14, 0, -1):
        a = int(210 * (i / 14) ** 2)
        rd.ellipse([cx - i, cy - i, cx + circle_d + i, cy + circle_d + i],
                   outline=glow_color + (a,), width=2)
    card.paste(ring_layer, mask=ring_layer.split()[3])

    # Hard ring border (white + accent)
    border_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    bld = ImageDraw.Draw(border_layer)
    bld.ellipse([cx - 6, cy - 6, cx + circle_d + 6, cy + circle_d + 6],
                outline=(255, 255, 255, 210), width=5)
    bld.ellipse([cx - 2, cy - 2, cx + circle_d + 2, cy + circle_d + 2],
                outline=ring_color + (255,), width=3)
    card.paste(border_layer, mask=border_layer.split()[3])

    # Paste photo
    pfp_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    pfp_layer.paste(pfp, (cx, cy), mask=mask)
    card.paste(pfp_layer, mask=pfp_layer.split()[3])


def _draw_stats_text(card: Image.Image, user, stats: dict, theme: dict):
    d = ImageDraw.Draw(card)

    # ALL fonts are bold (namefont.ttf) — only footer uses reg at bigger size
    f_huge   = _load_font(FONT_BOLD_PATH, 42)
    f_large  = _load_font(FONT_BOLD_PATH, 30)
    f_med    = _load_font(FONT_BOLD_PATH, 22)
    f_small  = _load_font(FONT_BOLD_PATH, 17)
    f_footer = _load_font(FONT_BOLD_PATH, 15)

    pad_x = 34
    SHADOW = (0, 0, 0)

    # ── Player ID badge ──
    uid_text = f"#PLAYER ID: {user.id}"
    d.rounded_rectangle([pad_x - 2, 12, pad_x + 20, 35], radius=5, fill=theme["accent"])
    _shadow_text(d, (pad_x + 26, 15), uid_text, f_small, theme["id_color"], SHADOW, radius=2)

    # ── Player name ──
    name_upper = (user.first_name or "Player").upper()
    _shadow_text(d, (pad_x, 44), name_upper, f_huge, theme["title_color"], SHADOW, radius=3)

    # ── Rank subtitle ──
    try:
        from plugins.utilities.userinfo import calculate_rank, calculate_title
        score, tier = calculate_rank(stats)
        title_str   = calculate_title(stats)
    except Exception:
        score, tier, title_str = 0, "—", "—"

    sub = title_str if title_str != "—" else tier
    _shadow_text(d, (pad_x, 96), sub.upper(), f_med, theme["subtitle"], SHADOW, radius=2)

    # ── Divider bar under subtitle ──
    d.line([(pad_x, 124), (480, 124)], fill=theme["accent"], width=2)

    # ── Stat rows ──
    runs      = stats.get("runs", 0)
    wickets   = stats.get("wickets", 0)
    matches   = stats.get("matches", 0)
    fifties   = stats.get("fifties", 0)
    centuries = stats.get("centuries", 0)
    balls     = stats.get("balls_faced", 0)
    highest   = stats.get("highest_score", 0)
    sr        = round(runs / balls * 100, 1) if balls > 0 else 0.0

    rows = [
        ("MATCHES",       str(matches)),
        ("RUNS",          str(runs)),
        ("WICKETS",       str(wickets)),
        ("50s / 100s",    f"{fifties}  /  {centuries}"),
        ("STRIKE RATE",   str(sr)),
        ("HIGHEST SCORE", str(highest)),
    ]

    row_y  = 134
    row_h  = 58
    col2_x = 300

    for i, (label, value) in enumerate(rows):
        y = row_y + i * row_h
        if i > 0:
            d.line([(pad_x, y - 1), (col2_x + 140, y - 1)],
                   fill=theme["divider"], width=1)
        _shadow_text(d, (pad_x, y + 8),  label, f_med,   theme["label_color"], SHADOW, radius=2)
        _shadow_text(d, (col2_x, y + 5), value, f_large, theme["value_color"], SHADOW, radius=2)

    # ── Footer ──
    tag = f"#CricketLegacy  •  Perf Score: {score}"
    _shadow_text(d, (pad_x, H - 32), tag, f_footer, theme["subtitle"], SHADOW, radius=1)


# ── public API ────────────────────────────────────────────────────────────────

def generate_card(photo_bytes, user, stats: dict) -> io.BytesIO:
    theme = random.choice(THEMES)

    card = Image.new("RGB", (W, H), theme["bg"])
    _draw_brush_strokes(card, theme)

    # Subtle centre-left dark vignette to keep text legible
    vignette = Image.new("RGBA", card.size, (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i in range(200, 0, -1):
        a  = int(120 * (1 - i / 200) ** 2)
        x0 = W // 2 - 40 + (200 - i) // 2
        vd.rectangle([x0, 0, x0 + 1, H], fill=(0, 0, 0, a))
    card.paste(vignette, mask=vignette.split()[3])

    card = card.convert("RGBA")
    _draw_profile_box(card, photo_bytes, theme)
    card = card.convert("RGB")
    _draw_stats_text(card, user, stats, theme)

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def download_user_photo(client, user_id: int):
    try:
        photos = await client.get_profile_photos(user_id, limit=1)
        if not photos:
            return None
        data = await client.download_media(photos[0], in_memory=True)
        if data:
            data.seek(0)
            return data
        return None
    except Exception:
        return None
