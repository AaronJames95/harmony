from flask import Flask, request, jsonify
import whisper
import torch
import gc
import threading
import os

app = Flask(__name__)

# Global State
whisper_model = None
idle_timer = None

def purge_vram():
    global whisper_model, idle_timer
    print("💤 Inactivity detected. Purging Whisper from GPU...")
    whisper_model = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    idle_timer = None

@app.route('/transcribe', methods=['POST'])
def transcribe():
    global whisper_model, idle_timer
    
    # 1. Cancel timer if it's running
    if idle_timer:
        idle_timer.cancel()
        idle_timer = None

    # 2. Check for GPU / Load Model
    if whisper_model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"⏳ Loading Whisper on {device}...")
        whisper_model = whisper.load_model("base", device=device)

    # 3. Transcribe
    file = request.files['file']
    file_path = f"./uploads/{file.filename}"
    file.save(file_path)
    
    # Use fp16=True only if on GPU to avoid the CPU warning
    result = whisper_model.transcribe(file_path, fp16=torch.cuda.is_available())
    os.remove(file_path)

    # 4. Restart the 5-second countdown
    idle_timer = threading.Timer(5.0, purge_vram)
    idle_timer.start()
    
    return jsonify({"text": result['text'].strip()})

if __name__ == '__main__':
    
    # Listen on all interfaces (0.0.0.0) so Tailscale can find it
    # Switch the port to 8000 to match your client
    print("🚀 Harmony Server opening on Port 8000...")
    if not os.path.exists('uploads'): os.makedirs('uploads')
    app.run(host='0.0.0.0', port=8000)
