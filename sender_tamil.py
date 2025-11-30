import json
import os
import requests
from datetime import datetime, timezone, timedelta

# ----- IST TIME -----
IST = timezone(timedelta(hours=5, minutes=30))

# ----- ENV VARIABLES -----
BOT_TOKEN = os.getenv("8587330162")
CHAT_ID = os.getenv("TamilCalendars")          # Channel ID or @channelusername


if not BOT_TOKEN or not CHAT_ID:
    raise Exception("BOT_TOKEN or CHAT_ID not set in environment variables.")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

MONTH_TA = {
    "Jan": "ஜனவரி", "Feb": "பிப்ரவரி", "Mar": "மார்ச்", "Apr": "ஏப்ரல்",
    "May": "மே", "Jun": "ஜூன்", "Jul": "ஜூலை", "Aug": "ஆகஸ்ட்",
    "Sep": "செப்டம்பர்", "Oct": "அக்டோபர்", "Nov": "நவம்பர்", "Dec": "டிசம்பர்"
}

def tamil_date(date_str):
    d, m, y = date_str.split()
    return f"{d} {MONTH_TA.get(m, m)} {y}"

def load_today():
    today_ist = datetime.now(IST)
    key = today_ist.strftime("%d %b %Y")

    with open("combined.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for entry in data:
        if entry.get("திகதி") == key:
            return entry

    return None

def build_message(e):
    # Create Tamil Panchang message
    msg = f"📅 *{tamil_date(e['திகதி'])} — தமிழ் நாள்காட்டி*\n\n"
    msg += f"🌅 சூரிய உதயம்: {e['சூரிய உதயம்']}\n"
    msg += f"🌇 சூரிய அஸ்தமனம்: {e['சூரிய அஸ்தமனம்']}\n"
    msg += f"🕒 நாள் நீளம்: {e['நாள் நீளம்']}\n\n"

    msg += f"📌 மாசம்: {e['மாசம்']}\n"
    msg += f"📌 பக்ஷம்: {e['பக்ஷம்']}\n"
    msg += f"📌 ராசி (சூரியன்): {e['ராசி']}\n"
    msg += f"📌 சந்திர ராசி: {e['சந்திரராசி']}\n\n"

    msg += "🕉 திதி / ✨ நட்சத்திரம் / 🧘 யோகம் / 🔥 கரணம்:\n"
    for r in e["திதி/நட்சத்திரம்/யோகம்/கரணம்"]:
        msg += f" • {r['நேரம்']} – {r['திதி']} | {r['நட்சத்திரம்']} | {r['யோகம்']} | {r['கரணம்']}\n"

    msg += f"\n⛔ ராகு காலம்: {e['ராகு காலம்']}\n"
    msg += f"⚠️ யமகண்டம்: {e['யமகண்ட']}\n"
    msg += f"🕑 கூலிகை: {e['கூலிகை']}\n"
    msg += f"✨ அப்ஜித் முகூர்த்தம்: {e['அப்ஜித் முகூர்த்தம்']}\n\n"

    msg += "🎉 சிறப்பு நாள் / பண்டிகைகள்:\n"
    for f in e["சிறப்பு நாள்/பண்டிகைகள்"]:
        msg += f" • {f}\n"

    return msg

def send_message(text):
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    r = requests.post(url, json=payload)
    print("Message sent:", r.text)

def send_image(img_url, caption):
    url = f"{API_URL}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "photo": img_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    r = requests.post(url, json=payload)
    print("Image sent:", r.text)

def main():
    entry = load_today()
    if not entry:
        print("No entry for today.")
        return

    msg = build_message(entry)

    if IMAGE_URL:
        send_image(IMAGE_URL, msg)
    else:
        send_message(msg)

if __name__ == "__main__":
    main()

