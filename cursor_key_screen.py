import sys
import csv
import time
import os
import threading
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer

class IngestorBackend:
    def __init__(self):
        self.log_dir = "logs"
        if not os.path.exists(self.log_dir): os.makedirs(self.log_dir)
        self.log_name = os.path.join(self.log_dir, f"ingest_{int(time.time())}.csv")
        self.last_text = ""
        with open(self.log_name, 'w', newline='') as f:
            csv.writer(f).writerow(["Time", "Unix", "Text"])

    def save_chunk(self, text):
        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        with open(self.log_name, 'a', newline='') as f:
            csv.writer(f).writerow([ts, time.time(), text.strip()])
        print(f"Saved: {text.strip()}")

class OverlayWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.backend = IngestorBackend()
        
        # 1. THE MAGIC FLAGS
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |       # No borders
            Qt.WindowType.WindowStaysOnTopHint |      # Always on top
            Qt.WindowType.Tool                        # Don't show in taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # The Transparency
        
        # 2. THE LAYOUT
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        # 3. THE INPUT BOX
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Reclaiming Joy 2026...")
        self.input_box.setFixedSize(300, 100)
        self.input_box.setStyleSheet("""
            QTextEdit {
                background-color: rgba(30, 30, 30, 200); 
                color: #81d4fa;
                border: 2px solid #444;
                border-radius: 10px;
                font-size: 16px;
                padding: 10px;
            }
        """)
        self.layout.addWidget(self.input_box)

        # 4. CAPTURE LOGIC
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.flush_to_csv)
        self.input_box.textChanged.connect(self.handle_typing)

        # Set to full screen size but keep it transparent
        self.showFullScreen()

    def handle_typing(self):
        # Reset the "silence" timer every time you type/speak
        self.timer.start(500) # 0.5 seconds of silence = save

    def flush_to_csv(self):
        current_text = self.input_box.toPlainText()
        if current_text:
            self.backend.save_chunk(current_text)
            # Optional: clear the box after saving to keep the HUD clean
            # self.input_box.clear() 

def run():
    app = QApplication(sys.argv)
    overlay = OverlayWindow()
    sys.exit(app.exec())