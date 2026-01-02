import sys
import csv
import time
import os
import threading
import winsound
from datetime import datetime
from win10toast import ToastNotifier
import pygetwindow as gw  # This 'as gw' is what defines the name

# GUI Imports
from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

# Watchdog Imports (Install via: pip install pygetwindow win10check)
try:
    import pygetwindow as gw
    from win10check import ToastNotifier
except ImportError:
    print("Missing libraries. Run: pip install pygetwindow win10check")

# --- 1. THE WATCHDOG (Definition) ---
class DictationWatchdog:
    def __init__(self, timeout=12):
        self.timeout = timeout
        self.last_activity = time.time()
        self.is_monitoring = True
        self.toaster = ToastNotifier()

    def update_activity(self):
        self.last_activity = time.time()

    def check_if_dictation_running(self):
        # Look for the Windows Dictation toolbar
        return len(gw.getWindowsWithTitle('Dictation')) > 0

    def start(self):
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def _watch_loop(self):
        while self.is_monitoring:
            if self.check_if_dictation_running():
                elapsed = time.time() - self.last_activity
                if elapsed > self.timeout:
                    self.notify_user()
                    self.last_activity = time.time() # Reset to avoid spamming
            time.sleep(1)

    def notify_user(self):
        # Play a HUD-style beep (Frequency: 1000Hz, Duration: 300ms)
        winsound.Beep(1000, 300)
        self.toaster.show_toast(
            "Reclaiming Joy 2026",
            "Still there? 12s of silence detected.",
            duration=3,
            threaded=True
        )

# --- 2. THE INGESTOR (Log Logic) ---
class Ingestor:
    def __init__(self):
        self.log_dir = "logs"
        if not os.path.exists(self.log_dir): os.makedirs(self.log_dir)
        self.last_len = 0
        self.log_name = os.path.join(self.log_dir, f"ingest_{int(time.time())}.csv")
        self.buffer = ""
        self.timer = None
        
        with open(self.log_name, 'w', newline='') as f:
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
            with open(self.log_name, 'a', newline='') as f:
                csv.writer(f).writerow([ts, time.time(), text_to_save])
            print(f"[{ts}] -> {text_to_save}")
        self.buffer = ""
from PyQt6.QtCore import pyqtSignal


       
# --- 3. THE GUI ---
class OverlayWindow(QMainWindow):
    # Create a custom signal that sends a string
    text_received = pyqtSignal(str)


    def __init__(self):
        super().__init__()
        self.api = Ingestor()
        self.watchdog = DictationWatchdog(timeout=12) # Now defined!
        self.watchdog.start()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 50, 50, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        self.input_box = QTextEdit()
        self.input_box.setFixedSize(350, 120)
        self.input_box.setStyleSheet("background-color: rgba(20, 20, 20, 200); color: #81d4fa; border: 2px solid #333; border-radius: 12px; font-size: 18px; padding: 10px;")
        self.input_box.textChanged.connect(self.on_text_changed)
        
        self.layout.addWidget(self.input_box)
        self.showFullScreen()


        # 1. Grab the text FIRST
        text = self.input_box.toPlainText()
        
        # 2. NOW it's safe to use the 'text' variable
        self.text_received.emit(text) 
        self.api.ingest(text)
        self.watchdog.update_activity() # Resets the 12s timer

    def on_text_changed(self):
        # 1. Grab the text FIRST
        text = self.input_box.toPlainText()
        
        # Emit the signal so other modules can 'hear' it
        self.text_received.emit(text)
        text = self.input_box.toPlainText()
        self.api.ingest(text)
        self.watchdog.update_activity() # Reset the 12s timer

def run():
    app = QApplication(sys.argv)
    window = OverlayWindow()
    sys.exit(app.exec())