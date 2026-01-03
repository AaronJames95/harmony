from flask import Flask, request, jsonify
import whisper
import requests
import os
from dotenv import load_dotenv

load_dotenv()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

app = Flask(__name__)

# Load Whisper at startup (it stays in VRAM, but is small)
print("⏳ Loading Whisper Model...")
model = whisper.load_model("base")

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    print(f"🎙️ Transcribing: {file.filename}")
    result = model.transcribe(file_path)
    
    # Clean up
    os.remove(file_path)
    
    return jsonify({"text": result['text'].strip()})

@app.route('/llm', methods=['POST'])
def llm_query():
    data = request.json
    payload = {
        "model": "llama3",
        "prompt": data.get("prompt"),
        "system": data.get("system", "You are Harmony."),
        "stream": False,
        "keep_alive": "30s" # 🚀 Frees VRAM after 30 seconds
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)