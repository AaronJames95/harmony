import sys
import os
import threading
import winsound
import time
import pygetwindow as gw
import random
from PyQt6.QtWidgets import QMainWindow, QTextEdit, QVBoxLayout, QWidget, QLabel, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QFont
from win10toast import ToastNotifier

# --- THE WATCHDOG (Internal Logic) ---
class DictationWatchdog:
    def __init__(self, timeout=12):
        self.timeout = timeout
        self.last_activity = time.time()
        self.is_monitoring = True
        self.toaster = ToastNotifier()

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
        self.toaster.show_toast("Harmony 2026", "Silence detected.", duration=2, threaded=True)

# --- THE GUI ---
class OverlayWindow(QMainWindow):
    text_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.watchdog = DictationWatchdog(timeout=12)
        self.watchdog.start()

        # Window Config
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.drag_pos = QPoint()

        # Layout Container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # 1. NOTIFICATION BAR
        self.notif_label = QLabel("SYSTEM ACTIVE")
        self.notif_label.setStyleSheet("""
            background-color: rgba(30, 30, 30, 230); color: #ffab40;
            border: 1px solid #ffab40; border-radius: 4px; padding: 4px;
            font-size: 10px; font-family: 'Consolas';
        """)
        self.notif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.notif_label)

        # 2. RESPONSE DISPLAY (The "Gemini-style" chat screen)
        self.response_display = QTextEdit()
        self.response_display.setReadOnly(True)
        self.response_display.setPlaceholderText("System logs and AI responses will appear here...")
        self.response_display.setStyleSheet("""
            background-color: rgba(15, 15, 15, 210); color: #e0e0e0;
            border: 1px solid #444; border-top-left-radius: 8px; border-top-right-radius: 8px;
            font-size: 14px; padding: 10px;
        """)
        self.layout.addWidget(self.response_display)

        # 3. INPUT BOX (Transcription source)
        self.input_box = QTextEdit()
        self.input_box.setFixedHeight(60)
        self.input_box.setPlaceholderText("Transcription goes here...")
        self.input_box.setStyleSheet("""
            background-color: rgba(30, 30, 30, 240); color: #81d4fa;
            border: 2px solid #0091ea; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;
            font-size: 16px; padding: 8px;
        """)
        self.input_box.textChanged.connect(self.on_text_changed)
        self.layout.addWidget(self.input_box)

        self.setFixedSize(400, 500) # Taller window for the chat history
        self.move(100, 100)

    # --- FUNCTIONALITY ---
    def add_message(self, sender, text):
        """Adds a message to the response screen."""
        color = "#81d4fa" if sender == "YOU" else "#ffab40"
        timestamp = time.strftime("%H:%M")
        message_html = f"<br><b style='color:{color};'>[{timestamp}] {sender}:</b> {text}"
        self.response_display.append(message_html)
        
        # Auto-scroll to bottom
        self.response_display.verticalScrollBar().setValue(
            self.response_display.verticalScrollBar().maximum()
        )

    def update_notification(self, message, color="#ffab40"):
        self.notif_label.setText(message.upper())
        self.notif_label.setStyleSheet(f"background-color: rgba(30,30,30,230); color: {color}; border: 1px solid {color}; padding:4px;")

    def on_text_changed(self):
        text = self.input_box.toPlainText()
        if text:
            self.text_received.emit(text)
            self.watchdog.update_activity()

    # --- DRAGGING ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()