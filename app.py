from dotenv import load_dotenv
import os
load_dotenv()

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import openai
import json
import tempfile
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# 🔐 KEYS
openai.api_key = os.getenv("OPENAI_API_KEY")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

app = Flask(__name__)
CORS(app)

# 🧠 Memory
MEMORY_FILE = "memory.json"
PROFILE_FILE = "profile.json"
REMINDERS = []

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

memory = load_json(MEMORY_FILE)
profile = load_json(PROFILE_FILE)
conversation = []

# 🧠 GPT logic
def ask_cora(message):
    messages = [
        {"role": "system", "content": "You are C.O.R.A., a helpful, warm, and human-like assistant. Respond casually but intelligently."},
        {"role": "user", "content": f"Memory: {json.dumps(memory)} Profile: {json.dumps(profile)}"},
        *conversation[-4:],
        {"role": "user", "content": message}
    ]
    try:
        res = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
        reply = res['choices'][0]['message']['content']
        conversation.append({"role": "user", "content": message})
        conversation.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"Something went wrong: {str(e)}"

# 🗣️ ElevenLabs voice
def text_to_speech(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    r = requests.post(url, headers=headers, json=data)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        f.write(r.content)
        return f.name

# 🧠 ROUTES

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    
    # Simple reminder detection
    if "remind me" in message.lower():
        REMINDERS.append({"text": message, "time": datetime.now().isoformat()})
        return jsonify({"reply": "Okay, I set a reminder."})

    reply = ask_cora(message)
    return jsonify({"reply": reply})

@app.route("/speak", methods=["POST"])
def speak():
    data = request.get_json()
    text = data.get("text", "")
    file_path = text_to_speech(text)
    return send_file(file_path, mimetype="audio/mpeg")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    audio = request.files["audio"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        audio.save(f.name)
        with open(f.name, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return jsonify({"text": transcript["text"]})

# 🔁 Reminder print (demo purpose)
def show_reminders():
    if REMINDERS:
        print(f"[REMINDER] You asked me to remember: {REMINDERS[-1]['text']}")

# ⏰ Background reminder check
scheduler = BackgroundScheduler()
scheduler.add_job(show_reminders, 'interval', seconds=30)
scheduler.start()

if __name__ == "__main__":
    app.run(debug=True)