import sys
import os
import win32clipboard # pip install pywin32
import requests

# This adds the 'Harmony' root folder to Python's search path
# It calculates the path 2 levels up from this file
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if root_path not in sys.path:
    sys.path.append(root_path)

# NOW this will work
from common.constants import API_URL, LARGE_FILE_THRESHOLD_MB

# Add the project root (Harmony/src) to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def get_and_clear_clipboard_files():
    paths = []
    try:
        win32clipboard.OpenClipboard()
        # Only look for the file format (CF_HDROP)
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
            data = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
            paths = list(data)
            
            # --- THE FIX: Clear the clipboard after reading ---
            # This ensures these files are only processed once.
            win32clipboard.EmptyClipboard()
            print("🧹 Clipboard cleared to prevent double-processing.")
            
        win32clipboard.CloseClipboard()
    except Exception as e:
        print(f"❌ Clipboard Error: {e}")
    return paths

def run_pipeline():
    files = get_and_clear_clipboard_files()
    
    if not files:
        print("⚠️ No new files detected in clipboard.")
        return

    print(f"🎯 Processing {len(files)} new items...")
    for path in files:
        if os.path.exists(path):
            process_and_send(path)

def process_and_send(path):
    # Determine if we should convert or send raw
    file_size_mb = os.path.getsize(path) / (1024 * 1024)
    is_video = path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))
    
    if is_video and file_size_mb > LARGE_FILE_THRESHOLD_MB:
        print(f"📦 Large video detected. Converting locally: {os.path.basename(path)}")
        # (FFmpeg conversion logic here)
    else:
        print(f"🚀 Sending file directly: {os.path.basename(path)}")
        # (Requests.post logic here)