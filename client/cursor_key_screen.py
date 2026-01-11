import sys
import os
import time
import requests
import threading
from PyQt6.QtWidgets import (
    QMainWindow, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, 
    QLabel, QFrame, QApplication, QLineEdit, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

# ==========================================
# 1. THE COMPACT HUD (Flush Bottom-Left)
# ==========================================
class HudPanel(QWidget):
    sig_stats_update = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        # ⚠️ SERVER IP
        self.server_url = "http://100.94.65.56:8000" 

        # Window Setup
        # ToolTip flag often forces it above the Taskbar better than just Tool
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.sig_stats_update.connect(self._update_ui)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.init_ui()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_server)

    def init_ui(self):
        self.frame = QFrame()
        # ⚡ COMPACT SIZE: Fits in the corner taskbar area
        self.frame.setFixedSize(210, 55) 
        
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(5, 10, 15, 255); 
                border: 1px solid #00e5ff;
                border-left: none; /* Flush with screen edge */
                border-bottom: none; /* Flush with taskbar */
                border-top-right-radius: 6px;
                border-bottom-left-radius: 0px; /* Sharp corner for anchor */
            }
        """)
        
        layout = QVBoxLayout(self.frame)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 8, 8, 5) # Tight margins

        # ROW 1: Status Line
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        
        self.status_light = QLabel("●")
        self.status_light.setStyleSheet("color: #ff0000; font-size: 12px; border: none; margin-top: -1px;")
        row1.addWidget(self.status_light)
        
        self.server_label = QLabel("INITIALIZING...")
        self.server_label.setStyleSheet("color: white; font-weight: bold; font-family: 'Segoe UI'; font-size: 11px; border: none;")
        row1.addWidget(self.server_label)
        row1.addStretch()
        layout.addLayout(row1)

        # ROW 2: VRAM Bar + Text
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        self.vram_bar = QProgressBar()
        self.vram_bar.setFixedHeight(4) # Very thin
        self.vram_bar.setTextVisible(False)
        self.vram_bar.setStyleSheet("""
            QProgressBar { border: none; background-color: #222; border-radius: 2px; }
            QProgressBar::chunk { background-color: #00e5ff; border-radius: 2px; }
        """)
        row2.addWidget(self.vram_bar)
        
        # ⚡ CHANGED LABEL: "VRAM"
        self.vram_text = QLabel("VRAM") 
        self.vram_text.setStyleSheet("color: #90a4ae; font-size: 9px; font-weight: bold; font-family: Consolas; border: none;")
        row2.addWidget(self.vram_text)
        
        layout.addLayout(row2)
        self.layout.addWidget(self.frame)

    def toggle(self):
        if self.isVisible():
            self.hide()
            self.timer.stop()
        else:
            self.update_position()
            self.show()
            self.raise_() # ⚡ FORCE TO TOP (Above Taskbar)
            self.poll_server()
            self.timer.start(2000)

    def update_position(self):
        screen = QApplication.primaryScreen().geometry()
        width, height = 360, 48
        
        # ⚡ ABSOLUTE CORNER (0, MaxHeight)
        x = screen.left()
        y = screen.bottom() - height + 1 # +1 to ensure it kisses the bezel
        
        self.setGeometry(x, y, width, height)

    def poll_server(self):
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        try:
            resp = requests.get(f"{self.server_url}/stats", timeout=1.0)
            if resp.status_code == 200:
                self.sig_stats_update.emit(resp.json())
            else:
                self.sig_stats_update.emit({"error": f"ERR {resp.status_code}"})
        except:
            self.sig_stats_update.emit({"error": "OFFLINE"})

    def _update_ui(self, data):
        if "error" in data:
            self.status_light.setStyleSheet("color: #ff0000; font-size: 12px; border: none;")
            self.server_label.setText(data["error"])
            self.vram_bar.setValue(0)
            self.vram_text.setText("VRAM: --")
            return

        gpu = data.get('gpu', 'CPU').split("RTX")[-1].strip() # Shorten name (e.g. "3090")
        used = data.get('vram_used', 0)
        total = data.get('vram_total', 24)
        pct = int(data.get('vram_percent', 0))

        self.status_light.setStyleSheet("color: #00ff00; font-size: 12px; border: none;")
        self.server_label.setText(f"ONLINE: {gpu}")
        self.vram_bar.setValue(pct)
        # Display simplified VRAM stat
        self.vram_text.setText(f"VRAM: {int(used)}G")
        
        color = "#ff0000" if pct > 90 else "#00e5ff"
        self.vram_bar.setStyleSheet(f"""
            QProgressBar {{ border: none; background-color: #222; border-radius: 2px; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 2px; }}
        """)


# ==========================================
# 2. THE CONVERSATION PANEL (Top, Logs)
# ==========================================
class ConversationPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.layout.addWidget(self.display)
        
        self.alignment_mode = "right"
        self._apply_style()

    def _apply_style(self):
        base_style = """
            background-color: rgba(10, 30, 60, 180);
            padding: 10px; color: white;
            border: 1px solid white;
            font-family: 'Segoe UI'; font-size: 14px;
        """
        if self.alignment_mode == "left":
            corners = "border-left: none; border-top-left-radius: 0px; border-bottom-left-radius: 0px; border-top-right-radius: 12px; border-bottom-right-radius: 12px;"
        elif self.alignment_mode == "right":
            corners = "border-right: none; border-top-right-radius: 0px; border-bottom-right-radius: 0px; border-top-left-radius: 12px; border-bottom-left-radius: 12px;"
        else:
            corners = "border-radius: 12px;"
            
        self.display.setStyleSheet(f"QTextEdit {{ {base_style} {corners} }}")

    def set_alignment(self, mode):
        self.alignment_mode = mode
        self._apply_style()
        if self.isVisible():
            self.update_position()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.update_position()
            self.show()
            self.raise_()

    def update_position(self):
        screen = QApplication.primaryScreen().geometry()
        y = screen.top() + 60
        h = int(screen.height() * 0.85)
        
        if self.alignment_mode == "center":
            w = 650
            x = screen.x() + (screen.width() - w) // 2
        elif self.alignment_mode == "left":
            w = int(screen.width() * 0.30)
            x = screen.left()
        else: # right
            w = int(screen.width() * 0.30)
            x = screen.right() - w
            
        self.setGeometry(x, y, w, h)

    def add_html(self, html):
        self.display.append(html)
        self.display.verticalScrollBar().setValue(self.display.verticalScrollBar().maximum())
        if not self.isVisible():
            self.toggle()


# ==========================================
# 3. THE COMMAND BAR (Main Anchor)
# ==========================================
class OverlayWindow(QMainWindow):
    text_received = pyqtSignal(str)
    
    # Bridge Signals
    sig_toggle = pyqtSignal(str)
    sig_message = pyqtSignal(str, str)
    sig_notify = pyqtSignal(str, str)
    sig_align = pyqtSignal(str) 

    def __init__(self):
        super().__init__()
        
        self.convo_panel = ConversationPanel()
        self.hud_panel = HudPanel()
        
        self.sig_toggle.connect(self._handle_toggle)
        self.sig_align.connect(self._handle_align)
        self.sig_message.connect(self._handle_message)
        self.sig_notify.connect(self._handle_notify)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.init_command_bar()
        self.center_bar()

    def init_command_bar(self):
        self.command_frame = QFrame()
        self.command_frame.setFixedSize(650, 38)
        self.command_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 30, 60, 240); 
                border: 1px solid white; border-top: none;
                border-bottom-right-radius: 12px; border-bottom-left-radius: 12px;
            }
        """)
        
        layout = QHBoxLayout(self.command_frame)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: white; font-size: 10px; margin-top: 2px;") 
        layout.addWidget(self.status_dot)

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("awaiting command...")
        self.input_line.setStyleSheet("""
            QLineEdit { background: transparent; border: none; color: white; font-family: Consolas; font-size: 12px; font-weight: bold; }
        """)
        self.input_line.textChanged.connect(lambda text: self.text_received.emit(text))
        layout.addWidget(self.input_line)
        
        self.main_layout.addWidget(self.command_frame)

    def center_bar(self):
        screen = QApplication.primaryScreen().geometry()
        x = screen.x() + (screen.width() - 650) // 2
        y = screen.top()
        self.resize(650, 40) 
        self.move(x, y)

    def _handle_toggle(self, panel_name):
        if panel_name == "conversation":
            self.convo_panel.toggle()
        elif panel_name == "shalom":
            self.hud_panel.toggle()

    def _handle_align(self, mode):
        self.convo_panel.set_alignment(mode.lower())
        self._handle_notify(f"ALIGN: {mode.upper()}", "cyan")

    def _handle_message(self, sender, text):
        timestamp = time.strftime("%H:%M")
        display_name = "HARMONY🎵" if sender == "SYSTEM" else sender
        
        if sender == "SYSTEM":
            align = "left"
            bg = "rgba(255, 255, 255, 20)"
            col = "#ffffff"
            border = "1px solid rgba(255,255,255,50)"
        else:
            align = "right"
            bg = "rgba(0, 200, 255, 40)" 
            col = "#ffffff"
            border = "1px solid rgba(0, 255, 255, 100)"

        html = f"""
        <table width="100%" border="0" cellpadding="2">
            <tr><td align="{align}">
                <div style="background-color: {bg}; border: {border}; border-radius: 10px; padding: 8px 12px; margin-bottom: 5px; display: inline-block;">
                    <span style="font-size: 10px; color: #b0bec5; font-weight: bold;">{display_name} • {timestamp}</span><br>
                    <span style="font-size: 14px; color: {col};">{text}</span>
                </div>
            </td></tr>
        </table>
        """
        self.convo_panel.add_html(html)

    def _handle_notify(self, text, color_code="white"):
        color_map = { "#69f0ae":"lime", "#81d4fa":"cyan", "#ffab40":"orange", "#ffd740":"yellow", "#b3e5fc":"cyan" }
        final_color = color_map.get(color_code, color_code)
        if "#" in final_color: final_color = "white"
        
        self.status_dot.setStyleSheet(f"color: {final_color}; font-size: 10px; margin-top: 2px;")
        self.input_line.setPlaceholderText(f"STATUS: {text}...")

    def toggle_panel(self, panel_name): self.sig_toggle.emit(panel_name)
    def set_alignment(self, mode): self.sig_align.emit(mode)
    def add_message(self, sender, text): self.sig_message.emit(sender, text)
    def update_notification(self, text, color="white"): self.sig_notify.emit(text, color)