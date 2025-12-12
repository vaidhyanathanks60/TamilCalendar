# -*- coding: utf-8 -*-

import os
import json
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify

IST = timezone(timedelta(hours=5, minutes=30))

RAW_JSON_URL = "https://raw.githubusercontent.com/vaidhyanathanks60/TamilCalendar/main/combined.json"

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "MySecretToken")

app = Flask(__name__)

@app.route("/")
def home():
    return "Tamil calendar API running successfully!"
def normalize(val):
    if not val:
        return None
    s = str(val).strip()
    if s in ["", "---", "—"]:
        return None
    return s

def to_tamil_date(dstr: str) -> str:
    MONTH_TA = {
        "Jan": "ஜனவரி", "Feb": "பிப்ரவரி", "Mar": "மார்ச்", "Apr": "ஏப்ரல்",
        "May": "மே", "Jun": "ஜூன்", "Jul": "ஜூலை", "Aug": "ஆகஸ்ட்",
        "Sep": "செப்டம்பர்", "Oct": "அக்டோபர்", "Nov": "நவம்பர்", "Dec": "டிசம்பர்"
    }
    try:
        d, m, y = dstr.split()
        return f"{d} {MONTH_TA.get(m, m)} {y}"
    except:
        return dstr

def build_caption(entry):
    def clean(v):
        return normalize(v)

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

    if tithi:
        caption += f"\n🕉 திதி: {tithi}\n"
    if nak:
        caption += f"🕉 நட்சத்திரம்: {nak}\n"
    if yog:
        caption += f"🕉 யோகம்: {yog}\n"

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

def fetch_calendar():
    try:
        resp = requests.get(RAW_JSON_URL, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except:
        return None

def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    r = requests.post(url, headers=headers, json=payload)
    return r.text

def get_entry_for(choice, dataset):
    now = datetime.now(IST)

    if choice == "today":
        dt = now
    elif choice == "tomorrow":
        dt = now + timedelta(days=1)
    elif choice == "yesterday":
        dt = now - timedelta(days=1)
    else:
        return None

    key = dt.strftime("%d %b %Y")
    entry = next((e for e in dataset if e.get("திகதி") == key), None)
    return entry

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Invalid token", 403

    data = request.get_json()

    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = msg["from"]
        text = msg.get("text", {}).get("body", "").strip().lower()
    except:
        return jsonify({"status": "ignored"}), 200

    dataset = fetch_calendar()
    if not dataset:
        send_whatsapp_message(sender, "Error fetching calendar data.")
        return "ok"

    if text not in ["today", "tomorrow", "yesterday"]:
        send_whatsapp_message(sender,
            "Welcome! Type:\n\n• Today\n• Tomorrow\n• Yesterday"
        )
        return "ok"

    entry = get_entry_for(text, dataset)
    if not entry:
        send_whatsapp_message(sender, "No data available.")
        return "ok"

    caption = build_caption(entry)
    send_whatsapp_message(sender, caption)

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
