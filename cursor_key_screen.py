import webview
import csv
import time
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
class Ingestor:
    def __init__(self):
        self.last_text = ""
        self.log_name = f"ingest_{int(time.time())}.csv"
        with open(self.log_name, 'w', newline='') as f:
            csv.writer(f).writerow(["Time", "Unix", "Text"])

    def ingest(self, full_text):
        # Calculate only what was JUST added
        if full_text.startswith(self.last_text):
            new_chunk = full_text[len(self.last_text):].strip()
            if new_chunk:
                ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                print(f"[{ts}] -> {new_chunk}")
                
                # Log to CSV
                with open(self.log_name, 'a', newline='') as f:
                    csv.writer(f).writerow([ts, time.time(), new_chunk])
                
                self.last_text = full_text

# --- 3. THE RUNNER ---
def run():
    api = Ingestor()
    window = webview.create_window('Native Voice Ingestor', html=HTML, js_api=api, width=500, height=350)
    webview.start()