import sqlite3
import time
import os
import threading
import shutil
import subprocess
import requests
import win32clipboard  # Requires: pip install pywin32
import pyperclip
from datetime import datetime
from actions.registry import COMMANDS

class Ingestor:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.root_dir = os.path.dirname(self.script_dir)
        self.log_dir = os.path.join(self.root_dir, "logs")
        if not os.path.exists(self.log_dir): os.makedirs(self.log_dir)
        
        # --- CONFIGURATION ---
        # ⚠️ REPLACE with your actual server IP
        self.server_url = "http://100.94.65.56:8000/transcribe"
        self.large_file_threshold_mb = 25  # Convert videos larger than this
        
        self.obsidian_qc_path = r"C:\Users\AColl\Desktop\2_Areas\Harmony\QuickCapture.md" 
        # ---------------------

        self.db_path = os.path.join(self.log_dir, "harmony_main.db")
        self.session_id = int(time.time())
        self.last_len = 0
        self.buffer = ""
        self.timer = None
        
        # UI Reference
        self.gui = None 
        
        # State Management
        self.is_capturing = False
        self.temp_buffer = [] 
        self.save_timer = None
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS text_logs 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, timestamp TEXT, unix_time REAL, text_chunk TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS command_logs 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, timestamp TEXT, command_type TEXT, raw_text TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS temp_capture 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, text_fragment TEXT)''')
        conn.commit()
        conn.close()

    def _log_command(self, cmd_id, raw_text):
        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        conn = sqlite3.connect(self.db_path)
        conn.cursor().execute("INSERT INTO command_logs (session_id, timestamp, command_type, raw_text) VALUES (?, ?, ?, ?)", 
                             (self.session_id, ts, cmd_id, raw_text))
        conn.commit()
        conn.close()

    # --- MEDIA PIPELINE LOGIC (Restored from media_pipeline.py) ---
    def get_clipboard_files(self):
        """Extracts actual file paths from Windows Clipboard (CF_HDROP)."""
        paths = []
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
                paths = list(data)
                # We don't empty clipboard here immediately to allow user verify
            win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"❌ Clipboard Error: {e}")
        return paths

    def convert_to_audio(self, video_path):
        """Uses FFmpeg to strip audio from large video files."""
        output_audio = os.path.splitext(video_path)[0] + "_payload.mp3"
        print(f"🎬 Extracting audio: {os.path.basename(video_path)}...")
        
        if self.gui:
            self.gui.update_notification("CONVERTING...", "orange")
            self.gui.add_message("SYSTEM", f"🎬 <b>Compressing Video</b><br>Extracting audio from {os.path.basename(video_path)}...")

        cmd = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', output_audio, '-y']
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, shell=True)
            if os.path.exists(output_audio):
                return output_audio
        except Exception as e:
            print(f"❌ FFmpeg Error: {e}")
            if self.gui: self.gui.add_message("SYSTEM", f"❌ FFmpeg Error: {e}")
        return None

    def upload_file(self, file_path):
        """Uploads a single file to the Harmony Server."""
        filename = os.path.basename(file_path)
        print(f"🚀 Shipping: {filename}...")
        
        if self.gui:
            self.gui.update_notification("UPLOADING...", "cyan")
            self.gui.add_message("SYSTEM", f"🚀 <b>Sending to Server</b><br>{filename}")

        try:
            with open(file_path, 'rb') as f:
                response = requests.post(self.server_url, files={'file': f}, timeout=120)

            if response.status_code == 200:
                print(f"✅ Success! Job ID: {response.json().get('job_id')}")
                if self.gui:
                    self.gui.update_notification("SENT", "lime")
                    self.gui.add_message("SYSTEM", f"✅ <b>Upload Complete</b><br>Server processing Job: {response.json().get('job_id')}")
            else:
                print(f"❌ Server Error: {response.status_code}")
                if self.gui: self.gui.add_message("SYSTEM", f"❌ Upload Rejected: {response.status_code}")

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            if self.gui: self.gui.add_message("SYSTEM", f"❌ Connection Failed: {e}")

    def run_media_pipeline(self):
        """
        The Master Function triggered by 'Shema process audio'.
        Checks for files -> Converts if needed -> Uploads.
        """
        files = self.get_clipboard_files()
        
        if not files:
            print("⚠️ No files found on clipboard.")
            if self.gui: self.gui.add_message("SYSTEM", "⚠️ No files found on clipboard.")
            return

        for path in files:
            if not os.path.exists(path): continue
            
            # Check size and type
            size_mb = os.path.getsize(path) / (1024 * 1024)
            is_video = path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))
            
            # 1. Convert Large Video
            if is_video and size_mb > self.large_file_threshold_mb:
                temp_audio = self.convert_to_audio(path)
                if temp_audio:
                    self.upload_file(temp_audio)
                    try:
                        os.remove(temp_audio) # Cleanup temp mp3
                        print("🧹 Temp audio file cleaned up.")
                    except: pass
            
            # 2. Upload Audio/Small Files Directly
            else:
                self.upload_file(path)

        # Clear clipboard after processing to prevent duplicates?
        # win32clipboard.OpenClipboard()
        # win32clipboard.EmptyClipboard()
        # win32clipboard.CloseClipboard()
    # -------------------------------------------------------------

    def ingest(self, full_text):
        current_len = len(full_text)
        if current_len > self.last_len:
            new_chunk = full_text[self.last_len:]
            self.last_len = current_len

            if not self.is_capturing:
                self.buffer += new_chunk
                if self.timer: self.timer.cancel()
                self.timer = threading.Timer(0.3, self.flush_buffer)
                self.timer.start()
            else:
                self.temp_buffer.append(new_chunk)
                if not self.save_timer:
                    self.save_timer = threading.Timer(10.0, self._periodic_backup)
                    self.save_timer.start()
                if "shabbat" in new_chunk.lower():
                    self.stop_deep_state()
        elif current_len < self.last_len:
            self.last_len = current_len

    def _periodic_backup(self):
        if self.is_capturing and self.temp_buffer:
            text_to_backup = "".join(self.temp_buffer)
            try:
                conn = sqlite3.connect(self.db_path)
                conn.cursor().execute("INSERT INTO temp_capture (text_fragment) VALUES (?)", (text_to_backup,))
                conn.commit()
                conn.close()
                self.temp_buffer = [] 
            except Exception as e:
                print(f"❌ Backup failed: {e}")
        self.save_timer = None

    def save_quick_note(self, raw_text, source="voice"):
        if not raw_text: return
        final_content = raw_text.strip()
        
        if source == "voice":
            lower_text = raw_text.lower()
            if "note" in lower_text:
                final_content = raw_text.split("note", 1)[1].strip()
            elif "capture" in lower_text:
                final_content = raw_text.split("capture", 1)[1].strip()
        
        if not final_content:
            return

        timestamp = datetime.now().strftime('%H:%M')
        bullet_line = f"\n- [{timestamp}] {final_content}"

        try:
            if not os.path.exists(self.obsidian_qc_path):
                print(f"❌ File not found: {self.obsidian_qc_path}")
                if self.gui: self.gui.add_message("SYSTEM", f"❌ Error: QC File not found.")
                return

            with open(self.obsidian_qc_path, "a", encoding="utf-8") as f:
                f.write(bullet_line)

            print(f"📝 Quick Capture ({source}): {final_content[:30]}...")
            if self.gui:
                self.gui.update_notification("CAPTURED", "cyan")
                self.gui.add_message("SYSTEM", f"📝 <b>Saved to Obsidian:</b><br>\"{final_content}\"")

        except Exception as e:
            print(f"❌ File Write Error: {e}")
            if self.gui: self.gui.add_message("SYSTEM", f"❌ Write Error: {e}")

    def start_deep_state(self, text=None):
        if self.is_capturing: return
        print("🌑 Deep State Active: Optimized RAM Capture.")
        if self.gui:
            try:
                self.gui.update_notification("REC: DEEP STATE", "#ffab40")
                self.gui.add_message("SYSTEM", "🔴 <b>Dictation Started</b><br>Buffer cleared. Listening...")
            except Exception as e: print(f"UI Error: {e}")
        self.is_capturing = True
        self.temp_buffer = []
        try:
            conn = sqlite3.connect(self.db_path)
            conn.cursor().execute("DELETE FROM temp_capture")
            conn.commit()
            conn.close()
        except: pass

    def stop_deep_state(self, text=None):
        if not self.is_capturing: return
        print("☀️ Shabbat: Consolidating to clipboard...")
        self.is_capturing = False
        if self.save_timer: self.save_timer.cancel()

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT text_fragment FROM temp_capture ORDER BY id ASC")
            db_fragments = [row[0] for row in cursor.fetchall()]
            full_thought = "".join(db_fragments) + "".join(self.temp_buffer)
            final_text = full_thought.lower().replace("shema shabbat", "").strip()
            
            if final_text:
                pyperclip.copy(final_text)
                print(f"📋 Copied {len(final_text)} characters.")
                if self.gui:
                    try:
                        self.gui.update_notification("Standby", "white")
                        self.gui.add_message("SYSTEM", f"📋 <b>Copied to Clipboard</b><br>Captured {len(final_text)} chars.")
                    except Exception as e: print(f"UI Error: {e}")
            else:
                if self.gui: self.gui.add_message("SYSTEM", "⚠️ Dictation ended, but buffer was empty.")
            
            cursor.execute("DELETE FROM temp_capture")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Shabbat Error: {e}")
            if self.gui: self.gui.add_message("SYSTEM", f"❌ Error saving dictation: {e}")
        self.temp_buffer = []

    def flush_buffer(self):
        text_to_save = self.buffer.strip()
        if text_to_save:
            ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            unix = time.time()
            conn = sqlite3.connect(self.db_path)
            conn.cursor().execute("INSERT INTO text_logs (session_id, timestamp, unix_time, text_chunk) VALUES (?, ?, ?, ?)", 
                                 (self.session_id, ts, unix, text_to_save))
            conn.commit()
            conn.close()
            self.process_commands(text_to_save)
        self.buffer = ""

    def process_commands(self, text):
        clean_text = text.lower()
        if "shama shama" in clean_text:
            self._log_command("START_DEEP_STATE", clean_text)
            self.start_deep_state(clean_text)
            return

        trigger_aliases = ["shema", "shima", "shimah", "shemah", "shaman", "shemale", "shama", "shuv"]
        if not any(alias in clean_text for alias in trigger_aliases): return

        for cmd in COMMANDS:
            if any(t in clean_text for t in cmd["triggers"]):
                print(f"✨ HUD Action: {cmd['id']}")
                self._log_command(cmd["id"], clean_text)
                if cmd["id"] == "SYSTEM_SHUTDOWN":
                    print("🛑 FORCE EXIT TRIGGERED via OS call")
                    time.sleep(0.1) 
                    os._exit(0)
                try:
                    cmd["action"](self, clean_text)
                except Exception as e:
                    print(f"❌ Command Execution Error: {e}")
                break