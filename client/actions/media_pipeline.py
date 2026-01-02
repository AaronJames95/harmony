import os, subprocess, requests, pyperclip
from common.constants import API_URL, LARGE_FILE_THRESHOLD_MB

def run_pipeline():
    # Split clipboard by newlines to handle bulk files
    raw_data = pyperclip.paste().strip()
    paths = [p.strip().strip('"') for p in raw_data.split('\n') if p.strip()]

    for path in paths:
        if not os.path.exists(path): continue
        
        # Smart Logic: Convert large videos locally
        size_mb = os.path.getsize(path) / (1024 * 1024)
        is_video = path.lower().endswith(('.mp4', '.mkv', '.mov'))
        
        if is_video and size_mb > LARGE_FILE_THRESHOLD_MB:
            print(f"📦 Converting {os.path.basename(path)} locally...")
            final_path = convert_locally(path)
        else:
            final_path = path

        send_to_server(final_path)
        if final_path != path: os.remove(final_path)

def convert_locally(path):
    output = os.path.splitext(path)[0] + "_payload.mp3"
    cmd = ['ffmpeg', '-i', path, '-q:a', '0', '-map', 'a', output, '-y']
    subprocess.run(cmd, check=True, capture_output=True)
    return output

def send_to_server(file_path):
    with open(file_path, 'rb') as f:
        requests.post(API_URL, files={'file': f})