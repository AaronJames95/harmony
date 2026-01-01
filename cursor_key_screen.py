import webview
import csv
import time
import os
from datetime import datetime

# --- 1. THE FRONTEND (The Gemini-style Input Field) ---
HTML = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
        textarea { 
            width: 90%; height: 150px; background: #1e1e1e; color: #81d4fa; 
            border: 1px solid #333; border-radius: 10px; padding: 15px; font-size: 18px;
        }
    </style>
</head>
<body>
    <textarea id="box" autofocus placeholder="Win+H and speak..."></textarea>
    <script>
        document.getElementById('box').addEventListener('input', (e) => {
            window.pywebview.api.ingest(e.target.value);
        });
    </script>
</body>
</html>
"""

# --- 2. THE BACKEND (The Python Ingestion) ---
import threading

class Ingestor:
    def __init__(self):
        self.log_dir = "logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.last_len = 0
        #self.log_name = f"ingest_{int(time.time())}.csv"
        self.log_name = os.path.join(self.log_dir, f"ingest_{int(time.time())}.csv")
        self.buffer = ""
        self.timer = None
        
        with open(self.log_name, 'w', newline='') as f:
            csv.writer(f).writerow(["Time", "Unix", "Text"])

    def ingest(self, full_text):
        current_len = len(full_text)
        
        if current_len > self.last_len:
            # Capture the new data
            new_data = full_text[self.last_len:]
            self.buffer += new_data
            self.last_len = current_len

            # Start or reset a timer to "wait" for more words
            if self.timer:
                self.timer.cancel()
            
            # 0.3 seconds is the "sweet spot" for human speech chunks
            self.timer = threading.Timer(0.3, self.flush_buffer)
            self.timer.start()

        elif current_len < self.last_len:
            self.last_len = current_len

    def flush_buffer(self):
        """This only runs when the speaker pauses for a split second."""
        text_to_save = self.buffer.strip()
        if text_to_save:
            ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            print(f"[{ts}] -> {text_to_save}")
            
            with open(self.log_name, 'a', newline='') as f:
                csv.writer(f).writerow([ts, time.time(), text_to_save])
        
        self.buffer = "" # Clear buffer for next chunk

# --- 3. THE RUNNER ---
def run():
    api = Ingestor()
    window = webview.create_window('Native Voice Ingestor', html=HTML, js_api=api, width=500, height=350)
    webview.start()