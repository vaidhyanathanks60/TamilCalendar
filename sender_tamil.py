import json
import os
from datetime import datetime, timedelta, timezone
import requests

# ---------- IST TIME ----------
IST = timezone(timedelta(hours=5, minutes=30))

# ---------- ENV SECRETS ----------
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Comma-separated numbers: "91XXXXXXXXXX,91YYYYYYYYYY"
RECIPIENTS = os.getenv("RECIPIENT_NUMBERS", "")
RECIPIENTS = [x.strip() for x in RECIPIENTS.split(",") if x.strip()]

if not RECIPIENTS:
    raise Exception("RECIPIENT_NUMBERS secret not configured.")

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

    print("⚠️ No data for:", key)
    return None

def build_message(e):

    block = "\n".join(
        f" • {r['நேரம்']} – திதி: {r['திதி']} | நட்சத்திரம்: {r['நட்சத்திரம்']} | யோகம்: {r['யோகம்']} | கரணம்: {r['கரணம்']}"
        for r in e.get("திதி/நட்சத்திரம்/யோகம்/கரணம்", [])
    )

    festivals = "\n".join(f" • {f}" for f in e.get("சிறப்பு நாள்/பண்டிகைகள்", [])) or " • இல்லை"

    return f"""
📅 *{tamil_date(e['திகதி'])} — தமிழ் நாள்காட்டி*

🌅 சூரிய உதயம்: {e.get('சூரிய உதயம்')}
🌇 சூரிய அஸ்தமனம்: {e.get('சூரிய அஸ்தமனம்')}
🕒 நாள் நீளம்: {e.get('நாள் நீளம்')}

📌 மாசம்: {e.get('மாசம்')}
📌 பக்ஷம்: {e.get('பக்ஷம்')}
📌 ராசி (சூரியன்): {e.get('ராசி')}
📌 சந்திர ராசி: {e.get('சந்திரராசி')}

🕉 திதி / ✨ நட்சத்திரம் / 🧘 யோகம் / 🔥 கரணம்:
{block}

⛔ ராகு காலம்: {e.get('ராகு காலம்')}
⚠️ யமகண்டம்: {e.get('யமகண்ட')}
🕑 கூலிகை: {e.get('கூலிகை')}
✨ அப்ஜித் முகூர்த்தம்: {e.get('அப்ஜித் முகூர்த்தம்')}

🎉 சிறப்பு நாள் / பண்டிகைகள்:
{festivals}
"""

def send(msg):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    for number in RECIPIENTS:
        payload = {
            "messaging_product": "whatsapp",
            "to": f"whatsapp:{number}",
            "type": "text",
            "text": { "body": msg }
        }

        r = requests.post(url, headers=headers, json=payload)
        print(f"{number} → {r.status_code} → {r.text}")

def main():
    entry = load_today()
    if not entry:
        return
    msg = build_message(entry)
    print(msg)
    send(msg)

if __name__ == "__main__":
    main()
