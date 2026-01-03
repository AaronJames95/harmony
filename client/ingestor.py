import sqlite3
import time
import os
import threading
import pyperclip
from datetime import datetime
from actions.registry import COMMANDS

class Ingestor:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.root_dir = os.path.dirname(self.script_dir)
        self.log_dir = os.path.join(self.root_dir, "logs")
        if not os.path.exists(self.log_dir): os.makedirs(self.log_dir)
        
        self.db_path = os.path.join(self.log_dir, "harmony_main.db")
        self.session_id = int(time.time())
        self.last_len = 0
        self.buffer = ""
        self.timer = None
        
        # State Management
        self.is_capturing = False
        self.temp_buffer = []  # RAM buffer for high-speed capture
        self.save_timer = None # Timer for safety-net backups
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
                # FAST: Append to RAM instead of Disk
                self.temp_buffer.append(new_chunk)
                
                # OPTIONAL: Backup to disk every 10s so it's not ONLY in RAM
                if not self.save_timer:
                    self.save_timer = threading.Timer(10.0, self._periodic_backup)
                    self.save_timer.start()
                
                if "shabbat" in new_chunk.lower():
                    self.stop_capture()
        elif current_len < self.last_len:
            self.last_len = current_len

    def _periodic_backup(self):
        """Saves RAM buffer to DB safety net without blocking the UI."""
        if self.is_capturing and self.temp_buffer:
            text_to_backup = "".join(self.temp_buffer)
            try:
                conn = sqlite3.connect(self.db_path)
                conn.cursor().execute("INSERT INTO temp_capture (text_fragment) VALUES (?)", (text_to_backup,))
                conn.commit()
                conn.close()
                self.temp_buffer = [] # Clear RAM once moved to Disk
            except Exception as e:
                print(f"❌ Backup failed: {e}")
        self.save_timer = None

    def start_capture(self):
        if self.is_capturing: return
        print("🌑 Deep State Active: Optimized RAM Capture.")
        self.is_capturing = True
        self.temp_buffer = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.cursor().execute("DELETE FROM temp_capture")
            conn.commit()
            conn.close()
        except: pass

    def stop_capture(self):
        if not self.is_capturing: return
        print("☀️ Shabbat: Consolidating to clipboard...")
        self.is_capturing = False
        if self.save_timer: self.save_timer.cancel()

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Pull fragments from safety net + current RAM
            cursor.execute("SELECT text_fragment FROM temp_capture ORDER BY id ASC")
            db_fragments = [row[0] for row in cursor.fetchall()]
            full_thought = "".join(db_fragments) + "".join(self.temp_buffer)
            
            # Clean up and copy
            final_text = full_thought.lower().replace("shema shabbat", "").strip()
            if final_text:
                pyperclip.copy(final_text)
                print(f"📋 Copied {len(final_text)} characters.")
            
            cursor.execute("DELETE FROM temp_capture")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Shabbat Error: {e}")
        
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
        trigger_aliases = ["shema", "shima", "shimah", "shemah", "shaman", "shemale", "shama", "shuv"]
        if not any(alias in clean_text for alias in trigger_aliases): return

        for cmd in COMMANDS:
            if any(t in clean_text for t in cmd["triggers"]):
                print(f"✨ HUD Action: {cmd['id']}")
                self._log_command(cmd["id"], clean_text)
                cmd["action"](self, clean_text) 
                break