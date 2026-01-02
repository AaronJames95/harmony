import csv
import time
import os
import threading
import webbrowser
import pyperclip
import requests
from datetime import datetime

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
            
            print(f"DEBUG: Processed phrase: {text_to_save}")
            self.process_commands(text_to_save)
            
        self.buffer = ""

    def process_commands(self, text):
        clean_text = text.lower()
        watchword = "shema"
        if watchword in clean_text:
            print("✨ Trigger Detected: Shema")
            
            if watchword + " gemini" in clean_text:
                print("🚀 Opening Gemini...")
                webbrowser.open("https://gemini.google.com/app")
                
            elif watchword + " process" in clean_text or "transcription" in clean_text:
                print("🚀 Transcription Trigger Detected.")
                self.trigger_transcription_pipeline()

    def trigger_transcription_pipeline(self):
        raw_clipboard = pyperclip.paste().strip()
        paths = [p.strip().strip('"') for p in raw_clipboard.split('\n') if p.strip()]
        
        if not paths:
            print("⚠️ No paths in clipboard.")
            return

        print(f"📦 Shipping {len(paths)} items to AI Workstation...")
        # (This is where your requests.post logic from the roadmap goes)