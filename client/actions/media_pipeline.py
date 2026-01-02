import os
import sys
import subprocess
import win32clipboard # pip install pywin32
import requests

# Path Fix for Monorepo
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from common.constants import API_URL, LARGE_FILE_THRESHOLD_MB

def get_and_clear_clipboard_files():
    paths = []
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
            data = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
            paths = list(data)
            win32clipboard.EmptyClipboard() # Ensure files aren't re-processed
            print("🧹 Clipboard cleared.")
        win32clipboard.CloseClipboard()
    except Exception as e:
        print(f"❌ Clipboard Error: {e}")
    return paths

def convert_to_audio(video_path):
    """Extracts audio locally to save bandwidth."""
    output_audio = os.path.splitext(video_path)[0] + "_payload.mp3"
    print(f"🎬 Extracting audio from {os.path.basename(video_path)}...")
    
    # FFmpeg: Extract audio only, high quality, overwrite if exists
    cmd = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', output_audio, '-y']
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_audio
    except Exception as e:
        print(f"❌ FFmpeg failed: {e}")
        return None

def send_to_server(file_path):
    """Posts the file to the muscular server."""
    print(f"🚀 Shipping: {os.path.basename(file_path)}...")
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(API_URL, files={'file': f}, timeout=60)
            if response.status_code == 200:
                print(f"✅ Success! Job ID: {response.json().get('job_id')}")
            else:
                print(f"❌ Server rejected file (Status {response.status_code})")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def run_pipeline():
    files = get_and_clear_clipboard_files()
    if not files:
        print("⚠️ No new files in clipboard.")
        return

    for path in files:
        if not os.path.exists(path): continue
        
        size_mb = os.path.getsize(path) / (1024 * 1024)
        is_video = path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))
        
        if is_video and size_mb > LARGE_FILE_THRESHOLD_MB:
            temp_audio = convert_to_audio(path)
            if temp_audio:
                send_to_server(temp_audio)
                os.remove(temp_audio) # Cleanup local temp file
        else:
            send_to_server(path)

if __name__ == "__main__":
    run_pipeline()