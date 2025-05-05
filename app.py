from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from openai import OpenAI
import requests
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

# Load API keys from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default: Rachel

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)

# Memory (optional: can be connected to a DB)
memory = {}
conversation = []

# Homepage
@app.route('/')
def home():
    return render_template('index.html')

# Speech transcription endpoint
@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio uploaded'}), 400

    audio_file = request.files['audio']

    try:
        # Whisper transcription (OpenAI 1.x)
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        user_text = transcript.text
        print("User said:", user_text)
    except Exception as e:
        return jsonify({'error': f"Transcription failed: {str(e)}"}), 500

    try:
        # ChatGPT response
        messages = [
            {"role": "system", "content": "You are C.O.R.A., a warm, friendly, personal AI assistant."},
            *conversation[-4:],
            {"role": "user", "content": user_text}
        ]
        chat_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        reply = chat_response.choices[0].message.content
        conversation.append({"role": "user", "content": user_text})
        conversation.append({"role": "assistant", "content": reply})
        print("CORA says:", reply)
    except Exception as e:
        return jsonify({'error': f"ChatGPT failed: {str(e)}"}), 500

    try:
        # ElevenLabs speech synthesis
        audio_url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        data = {
            "text": reply,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.4,
                "similarity_boost": 0.75
            }
        }

        response = requests.post(audio_url, headers=headers, json=data)
        if response.status_code != 200:
            return jsonify({'error': f"ElevenLabs failed: {response.text}"}), 500

        filename = f"static/cora_{uuid.uuid4()}.mp3"
        with open(filename, "wb") as f:
            f.write(response.content)

    except Exception as e:
        return jsonify({'error': f"Voice failed: {str(e)}"}), 500

    return jsonify({
        'text': reply,
        'audio_url': filename
    })

# Optional background reminder tasks
def reminder_task():
    print("🔔 Reminder: This would trigger notifications or calendar actions.")

scheduler = BackgroundScheduler()
scheduler.add_job(func=reminder_task, trigger="interval", minutes=30)
scheduler.start()

# Run locally (Render uses gunicorn, so this line is ignored in production)
if __name__ == '__main__':
    app.run(debug=True)