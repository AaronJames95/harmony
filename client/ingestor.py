import sqlite3
import time
import os
import threading
from datetime import datetime
from actions.registry import COMMANDS

class Ingestor:
    def __init__(self):
        # Anchor paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__)) 
        self.root_dir = os.path.dirname(self.script_dir)
        self.log_dir = os.path.join(self.root_dir, "logs")
        if not os.path.exists(self.log_dir): os.makedirs(self.log_dir)
        
        self.db_path = os.path.join(self.log_dir, "harmony_main.db")
        self.session_id = int(time.time()) 
        self.last_len = 0
        self.buffer = ""
        self.timer = None
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS text_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, timestamp TEXT, unix_time REAL, text_chunk TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS command_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, timestamp TEXT, command_type TEXT, raw_text TEXT)')
        conn.commit()
        conn.close()

    def _log_command(self, cmd_id, raw_text):
        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        conn = sqlite3.connect(self.db_path)
        conn.cursor().execute("INSERT INTO command_logs (session_id, timestamp, command_type, raw_text) VALUES (?, ?, ?, ?)", (self.session_id, ts, cmd_id, raw_text))
        conn.commit()
        conn.close()

    def ingest(self, full_text):
        current_len = len(full_text)
        if current_len > self.last_len:
            self.buffer += full_text[self.last_len:]
            self.last_len = current_len
            if self.timer: self.timer.cancel()
            self.timer = threading.Timer(0.3, self.flush_buffer)
            self.timer.start()
        elif current_len < self.last_len:
            self.last_len = current_len

    def flush_buffer(self):
        text_to_save = self.buffer.strip()
        if text_to_save:
            ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            unix = time.time()
            conn = sqlite3.connect(self.db_path)
            conn.cursor().execute("INSERT INTO text_logs (session_id, timestamp, unix_time, text_chunk) VALUES (?, ?, ?, ?)", (self.session_id, ts, unix, text_to_save))
            conn.commit()
            conn.close()
            self.process_commands(text_to_save)
        self.buffer = ""

    def process_commands(self, text):
        clean_text = text.lower()
        trigger_aliases = ["shema", "shima", "shimah", "shemah", "shaman", "shemale", "shama", "shuv"]
        
        if not any(alias in clean_text for alias in trigger_aliases):
            return
        print("")

        for cmd in COMMANDS:
            if any(t in clean_text for t in cmd["triggers"]):
                print(f"✨ HUD Action: {cmd['id']}")
                self._log_command(cmd["id"], clean_text)
                cmd["action"](self.db_path, self.log_dir)
                break