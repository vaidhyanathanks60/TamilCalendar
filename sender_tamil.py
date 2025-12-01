import os
import requests
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json
import io # Used for handling file data

# ===================== CONFIG & ENVIRONMENT VARIABLES =====================

# Timezone for IST (Indian Standard Time)
IST = timezone(timedelta(hours=5, minutes=30))

# --- MANDATORY ENVIRONMENT VARIABLES ---
# Set these in your execution environment (e.g., GitHub Actions, local shell)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_TELEGRAM_CHAT_ID_OR_CHANNEL_USERNAME")

# --- DATA & IMAGE CONFIG ---
RAW_JSON_URL = "https://raw.githubusercontent.com/vaidhyanathanks60/TamilCalendar/main/combined.json"
OUTPUT_FILE = "calendar_premium.png"

CANVAS_WIDTH = 1400
CANVAS_HEIGHT = 2000

# Colors
GOLD_LIGHT = (245, 210, 140)
GOLD = (225, 180, 90)
GOLD_DARK = (150, 90, 35)

BG_TOP = (35, 15, 40)
BG_BOTTOM = (10, 5, 20)

PANEL_TOP = (80, 35, 100)
PANEL_BOTTOM = (45, 18, 70)

BOX_BG = (35, 20, 55, 220)
TEXT_COLOR = GOLD_LIGHT

# ===================== FONT & IMAGE DRAWING HELPERS =====================

def load_font(size: int):
    """Loads a Tamil font or falls back to default."""
    candidates = ["Latha.ttf", "Vijaya.ttf", "Nirmala.ttf", "Nirmala UI.ttf"]
    for name in candidates:
        try:
            # Note: In a containerized environment, you must ensure these fonts are available.
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

def vertical_gradient(size, top, bottom):
    """Creates a vertical gradient image."""
    w, h = size
    img = Image.new("RGB", size, top)
    dr = ImageDraw.Draw(img)
    rt, gt, bt = top
    rb, gb, bb = bottom

    for y in range(h):
        t = y / (h - 1)
        r = int(rt + (rb - rt) * t)
        g = int(gt + (gb - gt) * t)
        b = int(bt + (bb - bt) * t)
        dr.line([(0, y), (w, y)], fill=(r, g, b))

    return img

def draw_rounded_panel(base, margin=70, radius=70):
    """Draws a main rounded panel with shadow and outline."""
    w, h = base.size
    px0, py0 = margin, margin + 60
    px1, py1 = w - margin, h - margin

    # Shadow
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle((px0 + 10, py0 + 10, px1 + 10, py1 + 10),
                            radius=radius, fill=(0, 0, 0, 180))
    shadow = shadow.filter(ImageFilter.GaussianBlur(40))
    base = Image.alpha_composite(base, shadow.convert("RGBA")) # Ensure base is RGBA for blending

    # Gradient Panel
    panel = vertical_gradient((px1 - px0, py1 - py0), PANEL_TOP, PANEL_BOTTOM).convert("RGBA")
    mask = Image.new("L", (px1 - px0, py1 - py0), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle((0, 0, px1 - px0, py1 - py0), radius=radius, fill=255)
    panel.putalpha(mask)

    base.alpha_composite(panel, (px0, py0))

    # Outline
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle((px0, py0, px1, py1),
                            radius=radius, outline=GOLD_LIGHT, width=4)

    return base, (px0, py0, px1, py1)

# ------------ ICONS ------------
from math import sin, cos, radians, pi

def icon_sun(draw, cx, cy, radius, color):
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=color)
    for a in range(0, 360, 45):
        ang = radians(a)
        x1 = cx + int((radius + 10) * cos(ang))
        y1 = cy + int((radius + 10) * sin(ang))
        x2 = cx + int((radius + 30) * cos(ang))
        y2 = cy + int((radius + 30) * sin(ang))
        draw.line((x1, y1, x2, y2), fill=color, width=4)

def icon_clock(draw, cx, cy, radius, color):
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
                  outline=color, width=4)
    draw.line((cx, cy, cx, cy-radius+14), fill=color, width=4)
    draw.line((cx, cy, cx+radius-20, cy), fill=color, width=4)

def icon_lamp(draw, cx, cy, radius, color):
    w = radius * 2.6
    h = radius * 1.0
    draw.rounded_rectangle(
        (cx-w/2, cy, cx+w/2, cy+h),
        radius=12, fill=color
    )
    draw.ellipse(
        (cx-radius*0.5, cy-radius*1.7, cx+radius*0.5, cy+radius*0.2),
        fill=color
    )

def icon_star(draw, cx, cy, radius, color):
    pts = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.45
        ang = i * (2 * pi / 10) - pi/2
        pts.append((cx + r*cos(ang), cy + r*sin(ang)))
    draw.polygon(pts, fill=color)

def draw_glow_icon(base, cx, cy, radius, outer, inner, shape):
    """Draws an icon with a soft glow effect."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # Draw glow layers
    for scale, alpha in [(1.9, 32), (1.4, 70)]:
        r = int(radius * scale)
        # Draw a translucent circle for the glow effect
        d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(*outer, alpha))

    # Apply blur to the glow
    layer = layer.filter(ImageFilter.GaussianBlur(14))

    # Draw the main icon shape on the glow layer
    shape(ImageDraw.Draw(layer), cx, cy, radius, inner)

    # Composite the glow + icon layer onto the base image
    base.alpha_composite(layer)
    return base

# ===================== IMAGE CREATION FUNCTION =====================

def create_premium_image(entry, out_path=OUTPUT_FILE):
    """Generates the calendar image for a given data entry."""
    base = vertical_gradient((CANVAS_WIDTH, CANVAS_HEIGHT), BG_TOP, BG_BOTTOM).convert("RGBA")

    base, panel_box = draw_rounded_panel(base, radius=70)
    px0, py0, px1, py1 = panel_box

    draw = ImageDraw.Draw(base)

    title_font = load_font(80)
    subtitle_font = load_font(40)
    body_font = load_font(36)
    small_font = load_font(30)

    # ---- HEADER ----
    tamil_date = to_tamil_date(entry["திகதி"])
    d, m, y = tamil_date.split()

    date_line = f"{d} {m} {y}"
    dw, dh = text_size(draw, date_line, subtitle_font)

    draw.text(((CANVAS_WIDTH - dw)//2, py0 + 24),
              date_line, font=subtitle_font, fill=TEXT_COLOR)

    title = "தமிழ் நாட்காட்டி" # Corrected spelling
    tw, th = text_size(draw, title, title_font)

    draw.text(((CANVAS_WIDTH - tw)//2, py0 + 24 + dh + 8),
              title, font=title_font, fill=TEXT_COLOR)

    line_y = py0 + 24 + dh + 8 + th + 26
    draw.rounded_rectangle((px0+80, line_y, px1-80, line_y+3),
                            radius=2, fill=TEXT_COLOR)

    # ---- CONTENT BOXES ----
    y_cursor = line_y + 40
    x_margin = px0 + 60
    box_width = px1 - px0 - 120
    gap = 52

    def section(h):
        """Draws a content box and updates the cursor position."""
        nonlocal y_cursor
        box = (x_margin, y_cursor, x_margin + box_width, y_cursor + h)

        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        # Background box with outline
        ld.rounded_rectangle(box, radius=35, fill=BOX_BG, outline=GOLD_LIGHT, width=3)
        base.alpha_composite(layer)

        y_cursor += h + 32
        return box

    # --- Box 1: Sunrise/Sunset ---
    box1 = section(260)
    b1x0, b1y0, _, _ = box1
    cx = b1x0 + 90
    cy = b1y0 + 90
    base = draw_glow_icon(base, cx, cy, 38, GOLD_DARK, GOLD_LIGHT, icon_sun)
    tx = cx + 90
    ty = b1y0 + 40
    draw.text((tx, ty), f"சூரிய உதயம்: {entry['சூரிய உதயம்']}", font=body_font, fill=TEXT_COLOR)
    ty += 60
    draw.text((tx, ty), f"சூரிய அஸ்தமனம்: {entry['சூரிய அஸ்தமனம்']}", font=body_font, fill=TEXT_COLOR)
    ty += gap
    draw.text((tx, ty), f"நாள் நீளம்: {entry['நாள் நீளம்']}", font=body_font, fill=TEXT_COLOR)

    # --- Box 2: Astrological Details ---
    box2 = section(320)
    b2x0, b2y0, _, _ = box2
    cx = b2x0 + 90
    cy = b2y0 + 100
    base = draw_glow_icon(base, cx, cy, 36, GOLD, GOLD_LIGHT, icon_star)
    tx = cx + 90
    ty = b2y0 + 42
    draw.text((tx, ty), f"மாசம்: {entry['மாசம்']}", font=body_font, fill=TEXT_COLOR); ty += gap
    draw.text((tx, ty), f"பக்ஷம்: {entry['பக்ஷம்']}", font=body_font, fill=TEXT_COLOR); ty += gap
    draw.text((tx, ty), f"ராசி (சூரியன்): {entry['ராசி']}", font=body_font, fill=TEXT_COLOR); ty += gap
    draw.text((tx, ty), f"சந்திர ராசி: {entry['சந்திரராசி']}", font=body_font, fill=TEXT_COLOR)

    # --- Box 3: Thithi/Natchathiram/Yogam/Karanam ---
    rows = entry.get("திதி/நட்சத்திரம்/யோகம்/கரணம்", [])
    box3 = section(130 + len(rows) * 60)
    b3x0, b3y0, b3x1, _ = box3
    cx = b3x0 + 80
    cy = b3y0 + 90
    base = draw_glow_icon(base, cx, cy, 34, GOLD_DARK, GOLD_LIGHT, icon_clock)
    header = "திதி · நட்சத்திரம் · யோகம் · கரணம்"
    header_font = load_font(42)
    draw.text((cx + 80, b3y0 + 32), header, font=header_font, fill=TEXT_COLOR)
    ty = b3y0 + 105
    ix = cx + 80
    max_w = b3x1 - ix - 40
    for r in rows:
        line = f"{r.get('நேரம்', '—')} - {r.get('திதி', '—')} | {r.get('நட்சத்திரம்', '—')} | {r.get('யோகம்', '—')} | {r.get('கரணம்', '—')}"
        lf = fit_text_font(draw, line, max_w, 30, 22)
        draw.text((ix, ty), line, font=lf, fill=TEXT_COLOR)
        ty += 52

    # --- Box 4: Inauspicious Times ---
    box4 = section(260)
    b4x0, b4y0, _, _ = box4
    cx = b4x0 + 90
    cy = b4y0 + 100
    base = draw_glow_icon(base, cx, cy, 34, GOLD, GOLD_LIGHT, icon_lamp)
    tx = cx + 90
    ty = b4y0 + 44
    draw.text((tx, ty), f"ராகு காலம்: {entry.get('ராகு காலம்', '—')}", font=body_font, fill=TEXT_COLOR); ty += gap
    # Unified key check for Yama Kandam
    yamagandam = entry.get('யமகண்டம்') or entry.get('யமகண்ட', '—')
    draw.text((tx, ty), f"யமகண்டம்: {yamagandam}", font=body_font, fill=TEXT_COLOR); ty += gap
    draw.text((tx, ty), f"கூலிகை: {entry.get('கூலிகை', '—')}", font=body_font, fill=TEXT_COLOR); ty += gap
    if entry.get("அப்ஜித் முகூர்த்தம்"):
        draw.text((tx, ty), f"அப்ஜித் முகூர்த்தம்: {entry['அப்ஜித் முகூர்த்தம்']}",
                  font=small_font, fill=TEXT_COLOR)

    # --- Festivals ---
    fests = entry.get("சிறப்பு நாள்/பண்டிகைகள்", [])
    if fests:
        ftext = " | ".join(fests)
        fw, fh = text_size(draw, ftext, small_font)
        draw.text(((CANVAS_WIDTH - fw)//2, py1 - fh - 50), ftext,
                  font=small_font, fill=TEXT_COLOR)

    # Save the image
    base.convert("RGB").save(out_path, quality=95)
    print("✅ Image Saved:", out_path)
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
    """Converts a English date string (e.g., '01 Dec 2025') to a Tamil month format."""
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

# ===================== TELEGRAM SENDER (MODIFIED FOR FILE UPLOAD) =====================

def send_photo_with_caption(filepath, caption):
    """
    Uploads a local file and sends it to Telegram with a caption.
    Uses multipart/form-data for file upload.
    """
    if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or CHAT_ID == "YOUR_TELEGRAM_CHAT_ID_OR_CHANNEL_USERNAME":
        print("❌ ERROR: BOT_TOKEN or CHAT_ID is not set. Cannot send to Telegram.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    
    # Payload for the Telegram API (parameters other than the file)
    payload = {
        "chat_id": CHAT_ID,
        "caption": caption,
        "parse_mode": "Markdown"
    }

    print(f"Uploading {filepath} to Telegram Chat ID: {CHAT_ID}...")
    
    # Open the file and prepare for upload
    try:
        with open(filepath, 'rb') as f:
            # 'files' argument is used for multipart/form-data
            files = {'photo': (filepath, f, 'image/png')}
            
            resp = requests.post(url, data=payload, files=files)
            resp.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            print("✅ Telegram Upload Successful!")
            # print("Response:", resp.json())
            return resp.json()
    
    except requests.exceptions.HTTPError as e:
        print(f"❌ Telegram API Error: {e}")
        try:
            print("API Response Body:", resp.json())
        except:
            print("API Response Body (non-JSON):", resp.text)
    except Exception as e:
        print(f"❌ An unexpected error occurred during file upload: {e}")


# ===================== MAIN ORCHESTRATOR =====================

def main():
    """Fetches data, generates the image, and posts it to Telegram."""
    calendar = fetch_calendar()
    if not calendar:
        return

    # Find today's entry (e.g., '01 Dec 2025')
    today_str = datetime.now(IST).strftime("%d %b %Y")
    entry = next((e for e in calendar if e.get("திகதி") == today_str), None)

    if not entry:
        print("❌ No data found for today:", today_str)
        # Optionally, send a text message about missing data
        # send_to_telegram(f"❌ Daily calendar data for {today_str} is missing.")
        return

    # 1. Generate the image
    image_path = create_premium_image(entry, OUTPUT_FILE)

    # 2. Build the structured caption
    caption = build_caption(entry)

    # 3. Upload the image and caption to Telegram
    send_photo_with_caption(image_path, caption)

if __name__ == "__main__":
    main()
