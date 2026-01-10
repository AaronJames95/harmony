import sys
import os
import threading
import winsound
import time
import pygetwindow as gw
import random
from PyQt6.QtWidgets import (
    QMainWindow, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, 
    QLabel, QFrame, QApplication, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QFont
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

# --- THE GUI ---
class OverlayWindow(QMainWindow):
    text_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.watchdog = DictationWatchdog(timeout=12)
        self.watchdog.start()

        # Window Setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Main Container Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        # CRITICAL: Zero margins to hit the screen edge
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- INIT COMPONENTS ---
        self.init_command_bar()
        self.init_conversation_panel()
        self.init_shalom_panel()

        # Initial positioning
        self.move_to_top_center()
        
        # Adjust size after a split second to ensure layout is calculated
        QTimer.singleShot(10, self.adjustSize)

    # ---------- INITIALIZATION HELPERS ----------
    def init_command_bar(self):
        """The persistent top input bar."""
        self.command_frame = QFrame()
        self.command_frame.setFixedHeight(32) 
        # Using Named Colors and RGBA only - NO HASH SYMBOLS
        self.command_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 30, 60, 100);
                border: 1px solid rgba(255, 255, 255, 200);
                border-top: none;
                border-bottom-left-radius: 15px;
                border-bottom-right-radius: 15px;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }
        """)
        
        bar_layout = QHBoxLayout(self.command_frame)
        bar_layout.setContentsMargins(15, 0, 15, 0)
        bar_layout.setSpacing(10)

        # Status Icon
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: white; font-size: 12px; margin-top: 2px;") 
        bar_layout.addWidget(self.status_dot)

        # The Input Field
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("awaiting command...")
        self.input_line.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: white;
                font-family: Consolas;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.input_line.textChanged.connect(lambda text: self.text_received.emit(text))
        bar_layout.addWidget(self.input_line)
        
        self.main_layout.addWidget(self.command_frame)

    def init_conversation_panel(self):
        """The scrollable history view."""
        self.conversation_display = QTextEdit()
        self.conversation_display.setReadOnly(True)
        self.conversation_display.setMinimumHeight(250) 
        self.conversation_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(10, 30, 60, 220);
                border: 1px solid rgba(255, 255, 255, 100);
                border-top: none;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                padding: 15px;
                color: white;
                font-family: Segoe UI;
                font-size: 13px;
            }
        """)
        self.conversation_display.hide()
        self.main_layout.addWidget(self.conversation_display)

    def init_shalom_panel(self):
        """The 3-column wellness dashboard."""
        self.shalom_frame = QFrame()
        self.shalom_frame.setStyleSheet("background: transparent;")
        self.shalom_frame.hide()

        cols_layout = QHBoxLayout(self.shalom_frame)
        cols_layout.setContentsMargins(5, 5, 5, 5) 
        cols_layout.setSpacing(10)

        def create_column(title, data_points):
            col_frame = QFrame()
            col_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(10, 30, 60, 220);
                    border: 1px solid rgba(255, 255, 255, 150);
                    border-radius: 10px;
                    padding: 10px;
                }
            """)
            v_layout = QVBoxLayout(col_frame)
            title_lbl = QLabel(title.upper())
            title_lbl.setStyleSheet("color: white; font-weight: bold; font-family: Consolas; font-size: 14px; margin-bottom: 5px;")
            title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v_layout.addWidget(title_lbl)
            for dp in data_points:
                lbl = QLabel("• " + dp)
                lbl.setStyleSheet("color: lightgray; font-size: 12px; font-family: Segoe UI;")
                v_layout.addWidget(lbl)
            return col_frame

        cols_layout.addWidget(create_column("Guf (Body)", ["HR: --", "Steps: --", "Sleep: --"]))
        cols_layout.addWidget(create_column("Nefesh (Mind)", ["VRAM: Nominal", "Phone: Connected", "Tasks: 3 Pending"]))
        cols_layout.addWidget(create_column("Ruach (Spirit)", ["Meditate: Not yet", "Journal: 1 Entry", "Focus Lvl: High"]))

        self.main_layout.addWidget(self.shalom_frame)

    # ---------- LOGIC & TOGGLING ----------
    def move_to_top_center(self):
        screen_geo = QApplication.primaryScreen().geometry()
        target_width = 650
        self.setFixedWidth(target_width)
        
        # Center X
        x_pos = screen_geo.x() + (screen_geo.width() - target_width) // 2
        
        # NUCLEAR OPTION: Push up by 10 pixels to kill the Windows Shadow
        y_pos = screen_geo.top() - 36
        
        print(f"DEBUG: Moving to Y={y_pos}") # Check your terminal to see if this runs!
        self.move(x_pos, y_pos)

    def toggle_panel(self, panel_name):
        target_widget = self.conversation_display if panel_name == "conversation" else self.shalom_frame
        other_widget = self.shalom_frame if panel_name == "conversation" else self.conversation_display
        
        if target_widget.isVisible():
            target_widget.hide()
        else:
            other_widget.hide()
            target_widget.show()
        
        QTimer.singleShot(10, lambda: (self.adjustSize(), self.move_to_top_center()))

    def add_message(self, sender, text):
        prefix_color = "white" if sender == "SYSTEM" else "lightgray"
        timestamp = time.strftime("%H:%M")
        message_html = f"<div style='margin-bottom: 5px;'><b style='color:{prefix_color};'>[{timestamp}] {sender}:</b> {text}</div>"
        self.conversation_display.append(message_html)
        self.conversation_display.verticalScrollBar().setValue(
            self.conversation_display.verticalScrollBar().maximum()
        )