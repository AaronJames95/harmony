import csv
import time
import os
import threading
import webbrowser
from datetime import datetime
from actions import media_pipeline

class Ingestor:
    def __init__(self):
        self.log_dir = "logs"
        if not os.path.exists(self.log_dir): os.makedirs(self.log_dir)
        self.last_len = 0
        self.log_name = os.path.join(self.log_dir, f"ingest_{int(time.time())}.csv")
        self.buffer = ""
        self.timer = None
        
        with open(self.log_name, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(["Time", "Unix", "Text"])

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
            with open(self.log_name, 'a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow([ts, time.time(), text_to_save])
            
            # This is where the magic happens
            self.process_commands(text_to_save)
            
        self.buffer = ""

    def process_commands(self, text):
        clean_text = text.lower()
        
        if "shema" in clean_text:
            print(f"✨ HUD Command Detected: {clean_text}")
            
            if "gemini" in clean_text:
                webbrowser.open("https://gemini.google.com/app")
                
            elif "process" in clean_text or "transcription" in clean_text:
                # Call the specific media pipeline action
                media_pipeline.run_pipeline()
                
            elif "shutdown" in clean_text:
                print("🚨 Shutdown initiated...")
                os._exit(0)