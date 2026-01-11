import os
import subprocess
import requests
import win32clipboard 
from core.event_bus import bus, Events

class MediaPlugin:
    def __init__(self):
        # ⚠️ Replace with config value later
        self.server_url = "http://100.94.65.56:8000/transcribe"
        
        # Subscribe to the command
        bus.subscribe(Events.COMMAND_DETECTED, self.handle_command)

    def handle_command(self, data):
        """Listens for 'PROCESS_AUDIO' command."""
        if data.get("id") == "PROCESS_AUDIO":
            bus.emit(Events.STATUS_CHANGED, {"text": "CHECKING CLIPBOARD...", "color": "cyan"})
            self.run_pipeline()

    def run_pipeline(self):
        files = self.get_and_clear_clipboard_files()
        if not files:
            bus.emit(Events.LOG_MESSAGE, "⚠️ No files in clipboard.")
            return

        for path in files:
            if not os.path.exists(path): continue
            
            ext = path.lower()
            if ext.endswith(('.mp4', '.mkv', '.mov', '.avi')):
                audio_payload = self.convert_to_audio(path)
                if audio_payload:
                    self.upload_file(audio_payload)
                    try: os.remove(audio_payload)
                    except: pass
            elif ext.endswith(('.mp3', '.wav', '.m4a', '.flac')):
                self.upload_file(path)

    def upload_file(self, file_path):
        filename = os.path.basename(file_path)
        bus.emit(Events.STATUS_CHANGED, {"text": "UPLOADING...", "color": "orange"})
        
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(self.server_url, files={'file': f}, timeout=60)
            
            if response.status_code == 200:
                job_id = response.json().get('job_id')
                bus.emit(Events.STATUS_CHANGED, {"text": "SENT", "color": "lime"})
                bus.emit(Events.LOG_MESSAGE, f"✅ Uploaded: {filename} (Job: {job_id})")
            else:
                bus.emit(Events.LOG_MESSAGE, f"❌ Upload Failed: {response.status_code}")
        except Exception as e:
            bus.emit(Events.LOG_MESSAGE, f"❌ Connection Error: {e}")

    def convert_to_audio(self, video_path):
        output = os.path.splitext(video_path)[0] + "_payload.mp3"
        bus.emit(Events.LOG_MESSAGE, f"🎬 Extracting audio from {os.path.basename(video_path)}...")
        try:
            cmd = f'ffmpeg -y -i "{video_path}" -q:a 0 -map a "{output}"'
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
            return output
        except Exception as e:
            bus.emit(Events.LOG_MESSAGE, f"❌ FFmpeg Error: {e}")
            return None

    def get_and_clear_clipboard_files(self):
        paths = []
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
                paths = list(data)
                win32clipboard.EmptyClipboard() 
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        return paths