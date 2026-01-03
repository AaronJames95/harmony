import sqlite3
import time
import os
import threading
import webbrowser
from datetime import datetime
from actions import media_pipeline, writer #

class Ingestor:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__)) #
        self.root_dir = os.path.dirname(self.script_dir) #
        self.log_dir = os.path.join(self.root_dir, "logs") #
        
        if not os.path.exists(self.log_dir): 
            os.makedirs(self.log_dir) #
        
        self.db_path = os.path.join(self.log_dir, "harmony_main.db") #
        self.session_id = int(time.time()) #
        self.last_len = 0
        self.buffer = ""
        self.timer = None
        self._init_db() #

    def _init_db(self):
        conn = sqlite3.connect(self.db_path) #
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS text_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp TEXT,
                unix_time REAL,
                text_chunk TEXT
            )
        ''') #
        conn.commit()
        conn.close()

    def ingest(self, full_text):
        current_len = len(full_text)
        if current_len > self.last_len:
            self.buffer += full_text[self.last_len:] #
            self.last_len = current_len
            if self.timer: self.timer.cancel()
            self.timer = threading.Timer(0.3, self.flush_buffer) #
            self.timer.start()
        elif current_len < self.last_len:
            self.last_len = current_len #

    def flush_buffer(self):
        text_to_save = self.buffer.strip()
        if text_to_save:
            ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            unix = time.time()
            try:
                conn = sqlite3.connect(self.db_path) #
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO text_logs (session_id, timestamp, unix_time, text_chunk) VALUES (?, ?, ?, ?)",
                    (self.session_id, ts, unix, text_to_save)
                ) #
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"❌ Database Error: {e}")
            
            self.process_commands(text_to_save) #
        self.buffer = ""

    def process_commands(self, text):
        clean_text = text.lower()
        
        # 1. Expanded list based on your actual log data
        trigger_aliases = [
            "shema", "shima", "shimah", "shemah", 
            "shama"
        ]
        
        # 2. Check if ANY of those words are in the text
        if not any(alias in clean_text for alias in trigger_aliases):
            return

        print(f"✨ HUD Command Detected (Trigger matched): {clean_text}")

        # 3. COMMAND MAPPING (The "Switch Statement")
        commands = {
            "hello": lambda: print("👋🏾 Hello World!"),
            "print log": lambda: writer.export_history_to_text(self.db_path, self.log_dir),
            "gemini": lambda: webbrowser.open("https://gemini.google.com/app"),
            "transcribe": lambda: media_pipeline.run_pipeline(),
            "quit": lambda: os._exit(0)
        }

        # 4. Check for action words
        for cmd_word, action in commands.items():
            # Using 'cmd_word in clean_text' allows 'write' to match 'writes' or 'writer'
            if cmd_word in clean_text:
                action()
                break