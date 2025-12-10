#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------- CONFIG ----------------
IST = timezone(timedelta(hours=5, minutes=30))

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_TELEGRAM_CHAT_ID_OR_CHANNEL_USERNAME")

RAW_JSON_URL = "https://raw.githubusercontent.com/vaidhyanathanks60/TamilCalendar/main/combined.json"

# ---------------- UTILITIES ----------------

def normalize(val):
    if not val:
        return None
    s = str(val).strip()
    if s in ["", "---", "—"]:
        return None
    return s

def to_tamil_date(dstr: str) -> str:
    MONTH_TA = {
        "Jan":"ஜனவரி","Feb":"பிப்ரவரி","Mar":"மார்ச்","Apr":"ஏப்ரல்",
        "May":"மே","Jun":"ஜூன்","Jul":"ஜூலை","Aug":"ஆகஸ்ட்",
        "Sep":"செப்டம்பர்","Oct":"அக்டோபர்","Nov":"நவம்பர்","Dec":"டிசம்பர்"
    }
    try:
        d, m, y = dstr.split()
        return f"{d} {MONTH_TA.get(m, m)} {y}"
    except:
        return dstr

# ---------------- CAPTION BUILDER ----------------

def build_caption(entry):
    def clean(v):
        v = normalize(v)
        return v

    caption = f"📅 *{to_tamil_date(entry.get('திகதி',''))} — தமிழ் நாட்காட்டி*\n"

    if clean(entry.get("சூரிய உதயம்")):
        caption += f"🌅 சூரிய உதயம்: {entry['சூரிய உதயம்']}\n"
    if clean(entry.get("சூரிய அஸ்தமனம்")):
        caption += f"🌇 சூரிய அஸ்தமனம்: {entry['சூரிய அஸ்தமனம்']}\n"

    caption += "\n"

    if clean(entry.get("நாள்")):
        caption += f"📌 நாள்: {entry['நாள்']}\n"
    if clean(entry.get("பக்ஷம்")):
        caption += f"📌 பக்ஷம்: {entry['பக்ஷம்']}\n"
    if clean(entry.get("சந்திரராசி")):
        caption += f"📌 சந்திர ராசி: {entry['சந்திரராசி']}\n"

    nn = entry.get("நல்ல நேரம்", [])
    nn = [clean(n) for n in nn if clean(n)]
    if nn:
        caption += "\n📌 நல்ல நேரம்:\n"
        for n in nn:
            caption += f"   {n}\n"

    tithi = clean(entry.get("திதி"))
    nak = clean(entry.get("நட்சத்திரம்"))
    yog = clean(entry.get("யோகம்"))

    if tithi or nak or yog:
        if tithi:
            caption += f"\n🕉 திதி: {tithi}\n\n"
        if nak:
            caption += f"🕉 நட்சத்திரம்: {nak}\n\n"
        if yog:
            caption += f"🕉 யோகம்: {yog}\n\n"

    caption += "\n"

    caption += f"⛔ ராகு காலம்: {clean(entry.get('ராகு காலம்')) or '—'}\n"
    caption += f"⚠️ யமகண்டம்: {clean(entry.get('யமகண்டம்')) or '—'}\n"
    caption += f"🕑 குளிகை: {clean(entry.get('குளிகை')) or '—'}\n"

    notes = [clean(n) for n in entry.get("சிறப்பு குறிப்புகள்", []) if clean(n)]
    if notes:
        caption += "\n🎉 சிறப்பு குறிப்புகள்:\n"
        for n in notes:
            caption += f"• {n}\n"

    return caption


# ---------------- IMAGE GENERATOR (LATHA) ----------------

def create_image(entry, out_path="calendar.png"):

    W, H = 1500, 3000
    img = Image.new("RGB", (W, H), (15, 10, 40))
    draw = ImageDraw.Draw(img)

    # Background gradient
    for y in range(H):
        r = int(30 + (y / H) * 70)
        g = int(0 + (y / H) * 20)
        b = int(70 + (y / H) * 160)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Load Latha font
    FONT_PATH = os.path.join(os.path.dirname(__file__), "Latha.ttf")

    title_font = ImageFont.truetype(FONT_PATH, 150)
    header_font = ImageFont.truetype(FONT_PATH, 90)
    text_font = ImageFont.truetype(FONT_PATH, 75)

    # Title
    tamil_date = to_tamil_date(entry["திகதி"])
    x, y = 120, 160
    draw.text((x, y), tamil_date, font=title_font, fill="white")
    y += 220

    # Caption lines
    caption = build_caption(entry).replace("*", "")
    lines = caption.split("\n")

    for line in lines:
        if not line.strip():
            y += 40
            continue

        # Bold simulation for section headers
        if line.startswith(("📅", "📌", "🕉", "⛔", "⚠️", "🕑", "🎉")):
            font = header_font
            # Fake stroke = simulate bold
            draw.text((x-2, y), line, font=font, fill="white")
            draw.text((x+2, y), line, font=font, fill="white")
        else:
            font = text_font

        draw.text((x, y), line, font=font, fill="white")
        y += font.size + 35

    img.save(out_path)
    return out_path


# ---------------- FETCH JSON ----------------

def fetch_calendar():
    try:
        resp = requests.get(RAW_JSON_URL, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print("❌ Error fetching JSON:", e)
        return None


# ---------------- SEND IMAGE ----------------

def send_image_with_caption(image_path, caption):
    if BOT_TOKEN.startswith("YOUR_"):
        print("❌ BOT_TOKEN not configured.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    with open(image_path, "rb") as f:
        files = {"photo": f}
        data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
        resp = requests.post(url, data=data, files=files)
        print("Telegram response:", resp.text)


# ---------------- MAIN ----------------

def main():
    dataset = fetch_calendar()
    if not dataset:
        return

    tomorrow = datetime.now(IST) + timedelta(days=1)
    target = tomorrow.strftime("%d %b %Y")

    entry = next((e for e in dataset if e.get("திகதி") == target), None)
    if not entry:
        print("❌ No entry for:", target)
        return

    caption = build_caption(entry)
    img_path = create_image(entry)

    send_image_with_caption(img_path, caption)


if __name__ == "__main__":
    main()
