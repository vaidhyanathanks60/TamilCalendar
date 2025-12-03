import os
import requests
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json
import io  # Used for handling file data
from math import sin, cos, radians, pi

# ===================== CONFIG & ENVIRONMENT VARIABLES =====================

# Timezone for IST (Indian Standard Time)
IST = timezone(timedelta(hours=5, minutes=30))

# --- MANDATORY ENVIRONMENT VARIABLES ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_TELEGRAM_CHAT_ID_OR_CHANNEL_USERNAME")

# --- DATA & IMAGE CONFIG ---
RAW_JSON_URL = "https://raw.githubusercontent.com/vaidhyanathanks60/TamilCalendar/main/combined.json"
OUTPUT_FILE = "calendar_cyberpunk.png"

CANVAS_WIDTH = 1400
CANVAS_HEIGHT = 2000

# ===================== COLOURS =====================

# Classic gold (kept in case you want later)
GOLD_LIGHT = (245, 210, 140)
GOLD = (225, 180, 90)
GOLD_DARK = (150, 90, 35)

# Cyberpunk background colours (radial gradient centre -> edge)
CYBER_BG_CENTER = (18, 20, 60)   # bright-ish centre
CYBER_BG_EDGE = (3, 3, 15)       # dark edges

# Neon palette used for border & text lines
NEON_PALETTE = [
    (255, 255, 120),  # yellow
    (120, 255, 255),  # cyan
    (255, 150, 255),  # magenta
    (255, 190, 120),  # orange
    (140, 255, 200),  # mint
    (140, 190, 255),  # blue
    (255, 130, 190),  # pink
]

# A slightly stronger version for glows
def neon_with_alpha(rgb, a):
    r, g, b = rgb
    return (r, g, b, a)


# ===================== FONT & TEXT HELPERS =====================

def load_font(size: int):
    """Loads a Tamil-capable font or falls back to default."""
    candidates = ["Latha.ttf", "Vijaya.ttf", "Nirmala.ttf", "Nirmala UI.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    print("⚠️ WARNING: No Tamil font found. Using default.")
    return ImageFont.load_default()


def text_size(draw, text, font):
    """Calculates text size."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def fit_text_font(draw, text, max_width, start_size, min_size=20):
    """Finds the largest font size that fits within max_width."""
    size = start_size
    while size >= min_size:
        f = load_font(size)
        w, _ = text_size(draw, text, f)
        if w <= max_width:
            return f
        size -= 2
    return load_font(min_size)


# ===================== GRADIENT BACKGROUNDS =====================

def radial_gradient(size, inner_color, outer_color):
    """Creates a radial gradient from the centre to edges."""
    w, h = size
    cx, cy = w / 2, h / 2
    max_dist = (cx**2 + cy**2) ** 0.5

    img = Image.new("RGB", size, outer_color)
    px = img.load()

    ri, gi, bi = inner_color
    ro, go, bo = outer_color

    for y in range(h):
        for x in range(w):
            dx = x - cx
            dy = y - cy
            d = (dx*dx + dy*dy) ** 0.5
            t = min(d / max_dist, 1.0)
            r = int(ri + (ro - ri) * t)
            g = int(gi + (go - gi) * t)
            b = int(bi + (bo - bi) * t)
            px[x, y] = (r, g, b)

    return img


# ===================== NEON DRAW HELPERS =====================

def draw_neon_border(base, margin=60, width=12):
    """Draws a multi-colour neon border with glow."""
    w, h = base.size
    left, top = margin, margin
    right, bottom = w - margin, h - margin

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # Split each side into segments and cycle through colours
    segments = 80
    colors = NEON_PALETTE
    n = len(colors)

    def lerp(a, b, t):
        return a + (b - a) * t

    # Top
    for i in range(segments):
        t0 = i / segments
        t1 = (i + 1) / segments
        x0 = lerp(left, right, t0)
        x1 = lerp(left, right, t1)
        c = colors[i % n]
        d.line((x0, top, x1, top), fill=neon_with_alpha(c, 255), width=width)

    # Bottom
    for i in range(segments):
        t0 = i / segments
        t1 = (i + 1) / segments
        x0 = lerp(left, right, t0)
        x1 = lerp(left, right, t1)
        c = colors[(i + 20) % n]
        d.line((x0, bottom, x1, bottom), fill=neon_with_alpha(c, 255), width=width)

    # Left
    for i in range(segments):
        t0 = i / segments
        t1 = (i + 1) / segments
        y0 = lerp(top, bottom, t0)
        y1 = lerp(top, bottom, t1)
        c = colors[(i + 40) % n]
        d.line((left, y0, left, y1), fill=neon_with_alpha(c, 255), width=width)

    # Right
    for i in range(segments):
        t0 = i / segments
        t1 = (i + 1) / segments
        y0 = lerp(top, bottom, t0)
        y1 = lerp(top, bottom, t1)
        c = colors[(i + 60) % n]
        d.line((right, y0, right, y1), fill=neon_with_alpha(c, 255), width=width)

    # Blur glow
    glow = layer.filter(ImageFilter.GaussianBlur(18))
    base.alpha_composite(glow)
    # Sharp border on top
    base.alpha_composite(layer)
    return base


def draw_neon_text_center(base, text, y, font, color):
    """Draws centre-aligned neon text with glow."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = text_size(d, text, font)
    x = (base.size[0] - w) // 2

    d.text((x, y), text, font=font, fill=neon_with_alpha(color, 255))
    glow = layer.filter(ImageFilter.GaussianBlur(10))
    base.alpha_composite(glow)

    layer2 = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d2 = ImageDraw.Draw(layer2)
    d2.text((x, y), text, font=font, fill=color)
    base.alpha_composite(layer2)
    return base


def draw_neon_text_left(base, text, x, y, font, color):
    """Draws left-aligned neon text with glow."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((x, y), text, font=font, fill=neon_with_alpha(color, 255))
    glow = layer.filter(ImageFilter.GaussianBlur(9))
    base.alpha_composite(glow)

    layer2 = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d2 = ImageDraw.Draw(layer2)
    d2.text((x, y), text, font=font, fill=color)
    base.alpha_composite(layer2)
    return base


def draw_neon_line(base, x0, y, x1, color, width=4):
    """Horizontal neon line."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.line((x0, y, x1, y), fill=neon_with_alpha(color, 255), width=width)
    glow = layer.filter(ImageFilter.GaussianBlur(6))
    base.alpha_composite(glow)
    base.alpha_composite(layer)
    return base


# ------------ ICONS (REUSED, BUT IN NEON STYLE) ------------

def icon_sun(draw, cx, cy, radius, color):
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=color, width=4)
    for a in range(0, 360, 45):
        ang = radians(a)
        x1 = cx + int((radius + 6) * cos(ang))
        y1 = cy + int((radius + 6) * sin(ang))
        x2 = cx + int((radius + 18) * cos(ang))
        y2 = cy + int((radius + 18) * sin(ang))
        draw.line((x1, y1, x2, y2), fill=color, width=3)


def icon_clock(draw, cx, cy, radius, color):
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=color, width=4)
    draw.line((cx, cy, cx, cy-radius+10), fill=color, width=4)
    draw.line((cx, cy, cx+radius-10, cy), fill=color, width=4)


def icon_star(draw, cx, cy, radius, color):
    pts = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.45
        ang = i * (2 * pi / 10) - pi/2
        pts.append((cx + r*cos(ang), cy + r*sin(ang)))
    draw.polygon(pts, outline=color, fill=None)


def icon_drop(draw, cx, cy, radius, color):
    # Simple water / flame-like drop
    draw.polygon(
        [
            (cx, cy-radius),
            (cx-radius*0.7, cy+radius*0.8),
            (cx+radius*0.7, cy+radius*0.8),
        ],
        outline=color,
    )


def draw_glow_icon(base, cx, cy, radius, color, shape_func):
    """Draws an icon with neon glow."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # Soft glow circle
    for scale, alpha in [(2.1, 40), (1.4, 90)]:
        r = int(radius * scale)
        d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=neon_with_alpha(color, alpha))

    layer = layer.filter(ImageFilter.GaussianBlur(12))

    # Draw crisp icon
    d2 = ImageDraw.Draw(layer)
    shape_func(d2, cx, cy, radius, neon_with_alpha(color, 255))

    base.alpha_composite(layer)
    return base


def draw_ganesha_neon(base, cx, cy, scale=1.0, color=(255, 255, 120)):
    """Very stylised simple Ganesha outline with neon glow."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    head_r = int(90 * scale)
    body_r = int(120 * scale)

    # Halo
    d.ellipse(
        (cx-head_r-35, cy-head_r-35, cx+head_r+35, cy+head_r+35),
        outline=neon_with_alpha(color, 255),
        width=4,
    )
    # Head
    d.ellipse(
        (cx-head_r, cy-head_r, cx+head_r, cy+head_r),
        outline=neon_with_alpha(color, 255),
        width=4,
    )
    # Trunk
    d.line(
        (cx, cy-head_r//2, cx, cy+body_r//3, cx+head_r//3, cy+body_r//2),
        fill=neon_with_alpha(color, 255),
        width=5,
        joint="curve",
    )
    # Ears
    d.arc(
        (cx-head_r-25, cy-head_r//2, cx-10, cy+head_r),
        start=200,
        end=20,
        fill=neon_with_alpha(color, 255),
        width=4,
    )
    d.arc(
        (cx+10, cy-head_r//2, cx+head_r+25, cy+head_r),
        start=160,
        end=-20,
        fill=neon_with_alpha(color, 255),
        width=4,
    )
    # Simple sitting legs
    d.arc(
        (cx-body_r, cy+head_r//2, cx, cy+head_r+body_r),
        start=200,
        end=340,
        fill=neon_with_alpha(color, 255),
        width=4,
    )
    d.arc(
        (cx, cy+head_r//2, cx+body_r, cy+head_r+body_r),
        start=200,
        end=340,
        fill=neon_with_alpha(color, 255),
        width=4,
    )

    # Glow
    glow = layer.copy().filter(ImageFilter.GaussianBlur(18))
    base.alpha_composite(glow)
    base.alpha_composite(layer)
    return base


# ===================== IMAGE CREATION FUNCTION =====================

def create_premium_image(entry, out_path=OUTPUT_FILE):
    """
    Generates the Cyberpunk Multicolour Neon calendar image
    (Style A – 'perfect' version).
    """
    # --- Background with radial gradient ---
    base = radial_gradient(
        (CANVAS_WIDTH, CANVAS_HEIGHT),
        CYBER_BG_CENTER,
        CYBER_BG_EDGE
    ).convert("RGBA")

    # --- Neon border ---
    base = draw_neon_border(base, margin=70, width=12)

    draw = ImageDraw.Draw(base)

    # Fonts
    title_font = load_font(110)
    subtitle_font = load_font(60)
    body_font = load_font(44)
    small_font = load_font(34)

    # --- Neon Ganesha at top ---
    ganesha_color = NEON_PALETTE[0]
    base = draw_ganesha_neon(base, CANVAS_WIDTH // 2, 260, scale=0.9, color=ganesha_color)

    # --- Header text (date + label) ---
    tamil_date = to_tamil_date(entry["திகதி"])
    header_color1 = NEON_PALETTE[0]  # yellow
    header_color2 = NEON_PALETTE[1]  # cyan

    base = draw_neon_text_center(base, tamil_date, 380, title_font, header_color1)

    header2 = "தமிழ் நாட்காட்டி"
    base = draw_neon_text_center(base, header2, 380 + 120, subtitle_font, header_color2)

    # Separator line
    sep_y = 380 + 120 + 80
    base = draw_neon_line(base, 180, sep_y, CANVAS_WIDTH - 180, NEON_PALETTE[3], width=4)

    # --- Content lines (sunrise, etc.) ---
    x_text = 210
    x_icon = 150
    y_start = sep_y + 70
    line_gap = 60

    # Build lines list: (text, icon_func or None, palette_index)
    lines = []

    # Time info
    lines.append((f"சூரிய உதயம்: {entry.get('சூரிய உதயம்', '—')}", icon_sun, 0))
    lines.append((f"சூரிய அஸ்தமனம்: {entry.get('சூரிய அஸ்தமனம்', '—')}", icon_sun, 1))
    lines.append((f"நாள் நீளம்: {entry.get('நாள் நீளம்', '—')}", icon_clock, 2))

    # Astro info
    lines.append((f"மாசம்: {entry.get('மாசம்', '—')}", icon_star, 3))
    lines.append((f"பக்ஷம்: {entry.get('பக்ஷம்', '—')}", icon_star, 4))
    lines.append((f"ராசி (சூரியன்): {entry.get('ராசி', '—')}", icon_star, 5))
    lines.append((f"சந்திர ராசி: {entry.get('சந்திரராசி', '—')}", icon_star, 6))

    # Thithi / Nakshatram / Yogam / Karanam table header
    lines.append(("திதி · நட்சத்திரம் · யோகம் · கரணம்:", icon_clock, 0))

    # Rows for thithi/nakshatram/yogam/karanam
    for r in entry.get("திதி/நட்சத்திரம்/யோகம்/கரணம்", []):
        line_text = f"{r.get('நேரம்', '—')} – {r.get('திதி', '—')} | {r.get('நட்சத்திரம்', '—')} | {r.get('யோகம்', '—')} | {r.get('கரணம்', '—')}"
        lines.append((line_text, None, None))

    # Inauspicious times
    yamagandam = entry.get('யமகண்டம்') or entry.get('யமகண்ட', '—')
    lines.append((f"ராகு காலம்: {entry.get('ராகு காலம்', '—')}", icon_drop, 2))
    lines.append((f"யமகண்டம்: {yamagandam}", icon_drop, 3))
    lines.append((f"கூலிகை: {entry.get('கூலிகை', '—')}", icon_drop, 4))

    if entry.get("அப்ஜித் முகூர்த்தம்"):
        lines.append((f"அப்ஜித் முகூர்த்தம்: {entry.get('அப்ஜித் முகூர்த்தம்', '—')}", icon_star, 5))

    # --- Draw lines with neon colours ---
    y = y_start
    for idx, (text, icon_func, palette_idx) in enumerate(lines):
        color = NEON_PALETTE[idx % len(NEON_PALETTE)] if palette_idx is None else NEON_PALETTE[palette_idx]

        # Icon (if any)
        if icon_func is not None:
            base = draw_glow_icon(base, x_icon, y + 18, 18, color, icon_func)

        # Text
        base = draw_neon_text_left(base, text, x_text, y, body_font, color)
        y += line_gap

    # --- Festivals at bottom centre (if any) ---
    fests = entry.get("சிறப்பு நாள்/பண்டிகைகள்", [])
    if fests:
        ftext = " | ".join(fests)
        fest_color = NEON_PALETTE[0]
        base = draw_neon_text_center(base, f"சிறப்பு நாள்/பண்டிகைகள்: {ftext}", CANVAS_HEIGHT - 180, small_font, fest_color)

    # Save image
    base.convert("RGB").save(out_path, quality=95)
    print("✅ Cyberpunk calendar image saved:", out_path)
    return out_path


# ===================== DATA FETCH & MESSAGE BUILDERS =====================

def fetch_calendar():
    """Fetches the calendar data from the JSON URL."""
    print("Fetching calendar data...")
    try:
        resp = requests.get(RAW_JSON_URL)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        return None


def to_tamil_date(dstr: str) -> str:
    """Converts an English date string (e.g., '01 Dec 2025') to a Tamil month format."""
    MONTH_TA = {
        "Jan": "ஜனவரி", "Feb": "பிப்ரவரி", "Mar": "மார்ச்",
        "Apr": "ஏப்ரல்", "May": "மே", "Jun": "ஜூன்",
        "Jul": "ஜூலை", "Aug": "ஆகஸ்ட்", "Sep": "செப்டம்பர்",
        "Oct": "அக்டோபர்", "Nov": "நவம்பர்", "Dec": "டிசம்பர்"
    }
    try:
        dstr = dstr.replace("\u00A0", " ").strip()
        parts = dstr.split()
        if len(parts) != 3:
            return dstr

        d, m, y = parts
        m = m[:3].title()
        tamil_month = MONTH_TA.get(m, m)
        return f"{d} {tamil_month} {y}"
    except Exception:
        return dstr


def build_caption(entry):
    """Generates the Markdown caption for the Telegram post."""
    msg = f"📅 *{to_tamil_date(entry['திகதி'])} — தமிழ் நாட்காட்டி* \n\n"

    # Time Info
    msg += f"🌅 சூரிய உதயம்: {entry.get('சூரிய உதயம்','—')} \n"
    msg += f"🌇 சூரிய அஸ்தமனம்: {entry.get('சூரிய அஸ்தமனம்','—')} \n"
    msg += f"🕒 நாள் நீளம்: {entry.get('நாள் நீளம்','—')} \n\n"

    # Astrological Info
    msg += f"📌 மாசம்: {entry.get('மாசம்','—')} \n"
    msg += f"📌 பக்ஷம்: {entry.get('பக்ஷம்','—')} \n"
    msg += f"📌 ராசி (சூரியன்): {entry.get('ராசி','—')} \n"
    msg += f"📌 சந்திர ராசி: {entry.get('சந்திரராசி','—')} \n\n"

    # Details Table
    msg += "🕉 *திதி / ✨ நட்சத்திரம் / 🧘 யோகம் / 🔥 கரணம்:* \n"
    for r in entry.get("திதி/நட்சத்திரம்/யோகம்/கரணம்", []):
        msg += f" • {r.get('நேரம்', '—')} – {r.get('திதி', '—')} | {r.get('நட்சத்திரம்', '—')} | {r.get('யோகம்', '—')} | {r.get('கரணம்', '—')} \n"

    # Inauspicious Times
    yamagandam = entry.get('யமகண்டம்') or entry.get('யமகண்ட', '—')
    msg += f"\n⛔ ராகு காலம்: {entry.get('ராகு காலம்','—')} \n"
    msg += f"⚠️ யமகண்டம்: {yamagandam} \n"
    msg += f"🕑 கூலிகை: {entry.get('கூலிகை','—')} \n"
    if entry.get("அப்ஜித் முகூர்த்தம்"):
        msg += f"✨ அப்ஜித் முகூர்த்தம்: {entry.get('அப்ஜித் முகூர்த்தம்','—')} \n\n"
    else:
        msg += "\n"

    # Festivals
    fests = entry.get("சிறப்பு நாள்/பண்டிகைகள்", [])
    if fests:
        msg += "🎉 *சிறப்பு நாள்/பண்டிகைகள்:* \n"
        for f in fests:
            msg += f" • {f} \n"

    return msg


# ===================== TELEGRAM SENDER =====================

def send_photo_with_caption(filepath, caption):
    """
    Uploads a local file and sends it to Telegram with a caption.
    Uses multipart/form-data for file upload.
    """
    if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or CHAT_ID == "YOUR_TELEGRAM_CHAT_ID_OR_CHANNEL_USERNAME":
        print("❌ ERROR: BOT_TOKEN or CHAT_ID is not set. Cannot send to Telegram.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    payload = {
        "chat_id": CHAT_ID,
        "caption": caption,
        "parse_mode": "Markdown"
    }

    print(f"Uploading {filepath} to Telegram Chat ID: {CHAT_ID}...")

    try:
        with open(filepath, 'rb') as f:
            files = {'photo': (os.path.basename(filepath), f, 'image/png')}
            resp = requests.post(url, data=payload, files=files)
            resp.raise_for_status()
            print("✅ Telegram Upload Successful!")
            return resp.json()

    except requests.exceptions.HTTPError as e:
        print(f"❌ Telegram API Error: {e}")
        try:
            print("API Response Body:", resp.json())
        except Exception:
            print("API Response Body (non-JSON):", resp.text)
    except Exception as e:
        print(f"❌ An unexpected error occurred during file upload: {e}")


# ===================== MAIN ORCHESTRATOR =====================

def main():
    """Fetches data, generates the image, and posts it to Telegram."""
    calendar = fetch_calendar()
    if not calendar:
        return

    today_str = datetime.now(IST).strftime("%d %b %Y")
    entry = next((e for e in calendar if e.get("திகதி") == today_str), None)

    if not entry:
        print("❌ No data found for today:", today_str)
        return

    # 1. Generate the cyberpunk image
    image_path = create_premium_image(entry, OUTPUT_FILE)

    # 2. Build the caption
    caption = build_caption(entry)

    # 3. Send to Telegram
    send_photo_with_caption(image_path, caption)


if __name__ == "__main__":
    main()