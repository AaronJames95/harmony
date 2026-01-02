import sys
import os
import threading
import winsound
import time
import pygetwindow as gw
from PyQt6.QtWidgets import QMainWindow, QTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from win10toast import ToastNotifier

# --- THE WATCHDOG ---
class DictationWatchdog:
    def __init__(self, timeout=12):
        self.timeout = timeout
        self.last_activity = time.time()
        self.is_monitoring = True
        self.toaster = ToastNotifier()

    def update_activity(self):
        self.last_activity = time.time()

    def check_if_dictation_running(self):
        # Broaden search for Windows Dictation bar
        titles = ['Dictation', 'Voice typing', 'Voice access', 'Microsoft Text Input']
        all_windows = gw.getAllTitles()
        return any(any(t.lower() in w.lower() for t in titles) for w in all_windows)

    def start(self):
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def _watch_loop(self):
        import time # Ensure local import for thread
        while self.is_monitoring:
            if self.check_if_dictation_running():
                elapsed = time.time() - self.last_activity
                if elapsed > self.timeout:
                    self.notify_user()
                    self.last_activity = time.time()
            time.sleep(1)

    def notify_user(self):
        winsound.Beep(1000, 300)
        self.toaster.show_toast(
            "Reclaiming Joy 2026",
            "Still there? 12s of silence detected.",
            duration=3,
            threaded=True
        )

# --- THE GUI ---
class OverlayWindow(QMainWindow):
    text_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # Initialize Watchdog
        self.watchdog = DictationWatchdog(timeout=12)
        self.watchdog.start()

        # Window Setup
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

    def on_text_changed(self):
        text = self.input_box.toPlainText()
        # EMIT SIGNAL: This is what connects to your external Ingestor
        self.text_received.emit(text) 
        self.watchdog.update_activity() # Reset the 12s timer