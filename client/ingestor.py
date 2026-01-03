import sqlite3
import time
import os
import threading
import webbrowser
from datetime import datetime
from actions import media_pipeline, writer # Added writer import

class Ingestor:
    def __init__(self):
        self.log_dir = "logs"
        if not os.path.exists(self.log_dir): 
            os.makedirs(self.log_dir)
        
        self.db_path = os.path.join(self.log_dir, "harmony_main.db")
        self.session_id = int(time.time()) 
        self.last_len = 0
        self.buffer = ""
        self.timer = None
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS text_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp TEXT,
                unix_time REAL,
                text_chunk TEXT
            )
        ''')
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
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO text_logs (session_id, timestamp, unix_time, text_chunk) VALUES (?, ?, ?, ?)",
                    (self.session_id, ts, unix, text_to_save)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"❌ Database Error: {e}")
            
            self.process_commands(text_to_save)
        self.buffer = ""

    def process_commands(self, text):
        clean_text = text.lower()
        if "shema" in clean_text:
            print(f"✨ HUD Command Detected: {clean_text}")
            
            # NEW COMMAND: Trigger manual file write
            if "write" in clean_text:
                writer.export_history_to_text(self.db_path, self.log_dir)
            
            elif "gemini" in clean_text:
                webbrowser.open("https://gemini.google.com/app")
            elif "process" in clean_text or "transcription" in clean_text:
                media_pipeline.run_pipeline()
            elif "shutdown" in clean_text:
                print("🚨 Shutdown initiated...")
                os._exit(0)