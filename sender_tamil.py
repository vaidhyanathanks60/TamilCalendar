import json
import os
import requests
from datetime import datetime, timezone, timedelta

# Timezone for IST
IST = timezone(timedelta(hours=5, minutes=30))

BOT_TOKEN = os.getenv("BOT_TOKEN")  # set in environment / .env
CHAT_ID = os.getenv("CHAT_ID", "@TamilCalendars")  # fallback to channel username
IMAGE_URL = os.getenv("IMAGE_URL", "")  # optional

RAW_JSON_URL = "https://raw.githubusercontent.com/vaidhyanathanks60/TamilCalendar/main/combined.json"

def fetch_calendar():
    resp = requests.get(RAW_JSON_URL)
    resp.raise_for_status()
    return resp.json()

def to_tamil_date(dstr):
    MONTH_TA = {
        "Jan":"ஜனவரி","Feb":"பிப்ரவரி","Mar":"மார்ச்","Apr":"ஏப்ரல்",
        "May":"மே","Jun":"ஜூன்","Jul":"ஜூலை","Aug":"ஆகஸ்ட்",
        "Sep":"செப்டம்பர்","Oct":"அக்டோபர்","Nov":"நவம்பர்","Dec":"டிசம்பர்"
    }
    d, m, y = dstr.split()
    return f"{d} {MONTH_TA.get(m, m)} {y}"

def build_message(entry):
    msg = f"📅 *{to_tamil_date(entry['திகதி'])} — தமிழ் நாள்காட்டி*  \n\n"
    msg += f"🌅 சூரிய உதயம்: {entry.get('சூரிய உதயம்','—')}  \n"
    msg += f"🌇 சூரிய அஸ்தமனம்: {entry.get('சூரிய அஸ்தமனம்','—')}  \n"
    msg += f"🕒 நாள் நீளம்: {entry.get('நாள் நீளம்','—')}  \n\n"

    msg += f"📌 மாசம்: {entry.get('மாசம்','—')}  \n"
    msg += f"📌 பக்ஷம்: {entry.get('பக்ஷம்','—')}  \n"
    msg += f"📌 ராசி (சூரியன்): {entry.get('ராசி','—')}  \n"
    msg += f"📌 சந்திர ராசி: {entry.get('சந்திரராசி','—')}  \n\n"

    msg += "🕉 திதி / ✨ நட்சத்திரம் / 🧘 யோகம் / 🔥 கரணம்:  \n"
    for r in entry.get("திதி/நட்சத்திரம்/யோகம்/கரணம்", []):
        msg += f" • {r.get('நேரம்')} – {r.get('திதி')} | {r.get('நட்சத்திரம்')} | {r.get('யோகம்')} | {r.get('கரணம்')}  \n"

    msg += f"\n⛔ ராகு காலம்: {entry.get('ராகு காலம்','—')}  \n"
    msg += f"⚠️ யமகண்டம்: {entry.get('யமகண்ட','—')}  \n"
    msg += f"🕑 கூலிகை: {entry.get('கூலிகை','—')}  \n"
    msg += f"✨ அப்ஜித் முகூர்த்தம்: {entry.get('அப்ஜித் முகூர்த்தம்','—')}  \n\n"

    msg += "🎉 சிறப்பு நாள்/பண்டிகைகள்:  \n"
    for f in entry.get("சிறப்பு நாள்/பண்டிகைகள்", []):
        msg += f" • {f}  \n"

    return msg

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    resp = requests.post(url, json=payload)

    # DEBUG PRINT
    print("STATUS:", resp.status_code)
    print("RESPONSE:", resp.text)

    resp.raise_for_status()


def send_photo_with_caption(img_url, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "photo": img_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    print("Sent photo:", resp.json())

def main():
    calendar = fetch_calendar()
    today = datetime.now(IST).strftime("%d %b %Y")
    entry = next((e for e in calendar if e.get("திகதி")==today), None)
    if not entry:
        print("No data for today:", today)
        return

    msg = build_message(entry)
    if IMAGE_URL:
        send_photo_with_caption(IMAGE_URL, msg)
    else:
        send_to_telegram(msg)

if __name__ == "__main__":
    main()
