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

# --- THE WATCHDOG (Standard) ---
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

# --- THE STABLE GUI ---
class OverlayWindow(QMainWindow):
    text_received = pyqtSignal(str)
    sig_toggle = pyqtSignal(str)
    sig_message = pyqtSignal(str, str)
    sig_notify = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.watchdog = DictationWatchdog(timeout=12)
        self.watchdog.start()

        self.sig_toggle.connect(self._slot_toggle_panel)
        self.sig_message.connect(self._slot_add_message)
        self.sig_notify.connect(self._slot_update_notification)

        # Window Setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 1. STRUCTURAL FIX: Align everything to the TOP
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0) 

        # --- INIT COMPONENTS ---
        # 1. Command Bar (Anchor)
        self.init_command_bar()
        
        # 2. Spacer (Gap)
        self.spacer = QFrame()
        self.spacer.setFixedHeight(250) 
        self.spacer.setStyleSheet("background: transparent;")
        self.spacer.hide()
        self.main_layout.addWidget(self.spacer)
        
        # 3. Panels
        self.init_conversation_panel()
        self.init_shalom_panel()

        # Initial positioning (Compact)
        self.move_to_top_center(expanded=False)

    def init_command_bar(self):
        self.command_frame = QFrame()
        self.command_frame.setFixedHeight(34)
        self.command_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 30, 60, 255);
                border-top: none;
                border-left: 1px solid rgba(255, 255, 255, 100);
                border-right: 1px solid rgba(255, 255, 255, 100);
                border-bottom: 2px solid white; 
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)
        
        bar_layout = QHBoxLayout(self.command_frame)
        bar_layout.setContentsMargins(15, 0, 15, 0)
        bar_layout.setSpacing(10)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: white; font-size: 10px; margin-top: 2px;") 
        bar_layout.addWidget(self.status_dot)

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("awaiting command...")
        self.input_line.setStyleSheet("""
            QLineEdit {
                background: transparent; border: none; color: white;
                font-family: Consolas; font-size: 12px; font-weight: bold;
            }
        """)
        self.input_line.textChanged.connect(lambda text: self.text_received.emit(text))
        bar_layout.addWidget(self.input_line)
        self.main_layout.addWidget(self.command_frame)

    def init_conversation_panel(self):
        self.conversation_display = QTextEdit()
        self.conversation_display.setReadOnly(True)
        self.conversation_display.setMinimumHeight(300) 
        self.conversation_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(10, 30, 60, 230);
                border: 1px solid rgba(255, 255, 255, 150);
                border-radius: 8px; padding: 20px; color: white;
                font-family: 'Segoe UI'; font-size: 14px; line-height: 20px;
            }
        """)
        self.conversation_display.hide()
        self.main_layout.addWidget(self.conversation_display)

    def init_shalom_panel(self):
        self.shalom_frame = QFrame()
        self.shalom_frame.setStyleSheet("background: transparent;")
        self.shalom_frame.hide()

        cols_layout = QHBoxLayout(self.shalom_frame)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(15)

        def create_column(title, data_points):
            col_frame = QFrame()
            col_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(10, 30, 60, 230);
                    border: 1px solid rgba(255, 255, 255, 150);
                    border-radius: 8px; padding: 15px;
                }
            """)
            v_layout = QVBoxLayout(col_frame)
            title_lbl = QLabel(title.upper())
            title_lbl.setStyleSheet("color: white; font-weight: bold; font-family: Consolas; font-size: 14px; margin-bottom: 10px;")
            title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v_layout.addWidget(title_lbl)
            for dp in data_points:
                lbl = QLabel("• " + dp)
                lbl.setStyleSheet("color: lightgray; font-size: 13px; font-family: 'Segoe UI'; margin-bottom: 2px;")
                v_layout.addWidget(lbl)
            return col_frame

        cols_layout.addWidget(create_column("Guf (Body)", ["HR: --", "Steps: --", "Sleep: --"]))
        cols_layout.addWidget(create_column("Nefesh (Mind)", ["VRAM: Nominal", "Phone: Connected", "Tasks: 3 Pending"]))
        cols_layout.addWidget(create_column("Ruach (Spirit)", ["Meditate: Not yet", "Journal: Active", "Focus: High"]))
        self.main_layout.addWidget(self.shalom_frame)

    # ---------- LOGIC SLOTS ----------
    def move_to_top_center(self, expanded=False):
        """Calculates and applies the geometry."""
        screen_geo = QApplication.primaryScreen().geometry()
        target_width = 650
        
        x_pos = screen_geo.x() + (screen_geo.width() - target_width) // 2
        y_pos = screen_geo.top() - 10 # Always flush top
        
        # Explicit heights
        target_height = 600 if expanded else 38
        
        # 2. Apply Geometry
        self.resize(target_width, target_height)
        self.move(x_pos, y_pos)

    def _slot_toggle_panel(self, panel_name):
        target_widget = self.conversation_display if panel_name == "conversation" else self.shalom_frame
        other_widget = self.shalom_frame if panel_name == "conversation" else self.conversation_display
        
        if target_widget.isVisible():
            # CLOSING SEQUENCE
            target_widget.hide()
            self.spacer.hide()
            # 3. Use a Timer to FORCE the position back to top after the resize happens
            # This corrects the "falling" behavior.
            QTimer.singleShot(10, lambda: self.move_to_top_center(expanded=False))
        else:
            # OPENING SEQUENCE
            other_widget.hide()
            # Resize first to make room
            self.move_to_top_center(expanded=True)
            self.spacer.show()
            target_widget.show()

    def _slot_add_message(self, sender, text):
        prefix_color = "white" if sender == "SYSTEM" else "#cfd8dc"
        timestamp = time.strftime("%H:%M")
        message_html = f"<div style='margin-bottom: 8px;'><b style='color:{prefix_color};'>[{timestamp}] {sender}:</b> {text}</div>"
        self.conversation_display.append(message_html)
        self.conversation_display.verticalScrollBar().setValue(
            self.conversation_display.verticalScrollBar().maximum()
        )

    def _slot_update_notification(self, text, color_code):
        color_map = {
            "#69f0ae": "lime", "#81d4fa": "cyan", 
            "#ffab40": "orange", "#ffd740": "yellow", "#b3e5fc": "cyan"
        }
        final_color = color_map.get(color_code, "white")
        if "#" in final_color: final_color = "white"
        
        self.status_dot.setStyleSheet(f"color: {final_color}; font-size: 10px; margin-top: 2px;")
        self.input_line.setPlaceholderText(f"STATUS: {text}...")

    # --- PUBLIC API ---
    def toggle_panel(self, panel_name):
        self.sig_toggle.emit(panel_name)
    def add_message(self, sender, text):
        self.sig_message.emit(sender, text)
    def update_notification(self, text, color="white"):
        self.sig_notify.emit(text, color)