import os
import sys
import subprocess
import win32clipboard # pip install pywin32
import requests

# Path Fix for Monorepo (Assuming 'common' is in the root)
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# Import constants (Adjust these to match your actual common/constants.py)
try:
    from common.constants import API_URL
except ImportError:
    API_URL = "http://your-server-ip:8000/transcribe"

def get_and_clear_clipboard_files():
    paths = []
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
            data = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
            paths = list(data)
            win32clipboard.EmptyClipboard() 
            print("🧹 Clipboard cleared.")
        win32clipboard.CloseClipboard()
    except Exception as e:
        print(f"❌ Clipboard Error: {e}")
    return paths

def convert_to_audio(video_path):
    output_audio = os.path.splitext(video_path)[0] + "_payload.mp3"
    print(f"🎬 Extracting audio: {os.path.basename(video_path)}...")
    try:
        # Extracts audio from video using FFmpeg
        cmd = f'ffmpeg -y -i "{video_path}" -q:a 0 -map a "{output_audio}"'
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        return output_audio
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg Error: {e}")
        return None

def send_to_server(file_path):
    """Posts the file to the transcription server."""
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

def run_pipeline(db_path=None, log_dir=None):
    """Main entry point called by the Registry."""
    files = get_and_clear_clipboard_files()
    if not files:
        print("⚠️ No new files in clipboard.")
        return

    # Supported formats
    video_exts = ('.mp4', '.mkv', '.mov', '.avi')
    audio_exts = ('.mp3', '.wav', '.m4a', '.flac')

    for path in files:
        if not os.path.exists(path): continue
        
        ext = path.lower()
        if ext.endswith(video_exts):
            # It's a video: extract audio first
            audio_payload = convert_to_audio(path)
            if audio_payload:
                send_to_server(audio_payload)
        elif ext.endswith(audio_exts):
            # It's already audio: send it directly
            print(f"🎵 Audio file detected: {os.path.basename(path)}")
            send_to_server(path)
        else:
            print(f"🚫 Unsupported file type: {ext}")