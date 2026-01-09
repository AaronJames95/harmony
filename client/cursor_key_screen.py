import sys
import os
import threading
import winsound
import time
import pygetwindow as gw
import random # Needed for the alert sounds
from PyQt6.QtWidgets import QMainWindow, QTextEdit, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from win10toast import ToastNotifier # <--- FIX: Ensure this is imported

# --- THE WATCHDOG ---
class DictationWatchdog:
    def __init__(self, timeout=12):
        self.timeout = timeout
        self.last_activity = time.time()
        self.is_monitoring = True
        self.toaster = ToastNotifier() #

    def update_activity(self):
        self.last_activity = time.time()

    def check_if_dictation_running(self):
        titles = ['Dictation', 'Voice typing', 'Voice access', 'Microsoft Text Input']
        all_windows = gw.getAllTitles()
        return any(any(t.lower() in w.lower() for t in titles) for w in all_windows)

    def start(self):
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def _watch_loop(self):
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
            "Harmony 2026",
            "Still there? 12s of silence detected.",
            duration=3,
            threaded=True
        )

# --- THE GUI ---
class OverlayWindow(QMainWindow):
    text_received = pyqtSignal(str) #

    def __init__(self):
        super().__init__()
        # Initialize Watchdog
        self.watchdog = DictationWatchdog(timeout=12) #
        self.watchdog.start()

        # Window Setup
        # Frameless and Always on Top
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) #
        
        # Dragging State
        self.drag_pos = QPoint()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        # 1. NOTIFICATION AREA
        self.notif_label = QLabel("SYSTEM ONLINE")
        self.notif_label.setFixedWidth(350)
        self.notif_label.setStyleSheet("""
            background-color: rgba(30, 30, 30, 220);
            color: #ffab40;
            border: 1px solid #ffab40;
            border-radius: 5px;
            padding: 5px;
            font-size: 12px;
            font-family: 'Consolas', monospace;
        """)
        self.notif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.notif_label)

        # 2. INPUT / TRANSCRIPTION BOX
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Transcription will appear here...")
        self.input_box.setFixedSize(350, 120) #
        self.input_box.setStyleSheet("""
            background-color: rgba(20, 20, 20, 200); 
            color: #81d4fa; 
            border: 2px solid #333; 
            border-radius: 12px; 
            font-size: 18px; 
            padding: 10px;
        """) #
        self.input_box.textChanged.connect(self.on_text_changed)
        self.layout.addWidget(self.input_box)

        # Set initial window size and position
        self.setFixedSize(400, 250)
        self.move(100, 100)

    # --- DRAGGING LOGIC ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    # --- UI UPDATES ---
    def update_notification(self, message, color="#ffab40"):
        """Update the UI notification bar text and color."""
        self.notif_label.setText(message.upper())
        self.notif_label.setStyleSheet(f"""
            background-color: rgba(30, 30, 30, 220);
            color: {color};
            border: 1px solid {color};
            border-radius: 5px;
            padding: 5px;
            font-size: 12px;
        """)

    def on_text_changed(self):
        text = self.input_box.toPlainText()
        self.text_received.emit(text) #
        self.watchdog.update_activity() #