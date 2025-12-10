#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from datetime import datetime, timedelta, timezone

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
        "May":"மே","Jun":"ஜூன்","Jul":"ஜூன்","Aug":"ஆகஸ்ட்",
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

    # Sunrise / Sunset
    if clean(entry.get("சூரிய உதயம்")):
        caption += f"🌅 சூரிய உதயம்: {entry['சூரிய உதயம்']}\n"
    if clean(entry.get("சூரிய அஸ்தமனம்")):
        caption += f"🌇 சூரிய அஸ்தமனம்: {entry['சூரிய அஸ்தமனம்']}\n"

    caption += "\n"

    # Panchangam core
    if clean(entry.get("நாள்")):
        caption += f"📌 நாள்: {entry['நாள்']}\n"
    if clean(entry.get("பக்ஷம்")):
        caption += f"📌 பக்ஷம்: {entry['பக்ஷம்']}\n"
    if clean(entry.get("சந்திரராசி")):
        caption += f"📌 சந்திர ராசி: {entry['சந்திரராசி']}\n"

    # Good time
    nn = entry.get("நல்ல நேரம்", [])
    nn = [clean(n) for n in nn if clean(n)]
    if nn:
        caption += "\n📌 நல்ல நேரம்:\n"
        for n in nn:
            caption += f"   {n}\n\n"

    # Tithi / Nakshatra / Yogam
    tithi = clean(entry.get("திதி"))
    nak = clean(entry.get("நட்சத்திரம்"))
    yog = clean(entry.get("யோகம்"))

    if tithi or nak or yog:
  
        if tithi:
            caption += f"🕉 திதி: {tithi}\n\n"
        if nak:
            caption += f"🕉 நட்சத்திரம்: {nak}\n\n"
        if yog:
            caption += f"🕉 யோகம்: {yog}\n\n"

    caption += "\n"

    # Rahu / Yamagandam / Kuligai
    caption += f"⛔ ராகு காலம்: {clean(entry.get('ராகு காலம்')) or '—'}\n"
    caption += f"⚠️ யமகண்டம்: {clean(entry.get('யமகண்டம்')) or '—'}\n"
    caption += f"🕑 குளிகை: {clean(entry.get('குளிகை')) or '—'}\n"

    # Notes
    notes = [clean(n) for n in entry.get("சிறப்பு குறிப்புகள்", []) if clean(n)]
    if notes:
        caption += "\n🎉 சிறப்பு குறிப்புகள்:\n"
        for n in notes:
            caption += f"• {n}\n"

    return caption

# ---------------- FETCH JSON ----------------
def fetch_calendar():
    try:
        resp = requests.get(RAW_JSON_URL, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print("❌ Error fetching JSON:", e)
        return None

# ---------------- TELEGRAM SENDER ----------------
def send_caption_only(caption):
    if BOT_TOKEN.startswith("YOUR_"):
        print("❌ BOT_TOKEN not configured. Skipping send.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": caption,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        print("✅ Telegram send:", resp.text)
    except Exception as e:
        print("❌ Telegram send failed:", e)

# ---------------- MAIN (send tomorrow) ----------------
def main():
    dataset = fetch_calendar()
    if not dataset:
        return

    tomorrow = datetime.now(IST) + timedelta(days=1)
    target = tomorrow.strftime("%d %b %Y")

    entry = next((e for e in dataset if e.get("திகதி") == target), None)
    if not entry:
        print("❌ No entry found for", target)
        return

    caption = build_caption(entry)
    send_caption_only(caption)

if __name__ == "__main__":
    main()
