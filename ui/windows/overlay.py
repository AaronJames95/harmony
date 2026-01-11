import sys
import time
import threading
import requests
from PyQt6.QtWidgets import (
    QMainWindow, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, 
    QLabel, QFrame, QApplication, QLineEdit, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core.event_bus import bus, Events

# ... [HudPanel class stays the same as previous step] ...
# (I will skip repeating HudPanel code to save space, assuming you have it. 
#  If not, I can repost it. The focus here is ConversationPanel.)

class HudPanel(QWidget):
    # Internal signal to update UI safely from background threads
    sig_update = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.server_url = "http://100.94.65.56:8000" 

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.init_ui()

        self.sig_update.connect(self._apply_ui_update)
        bus.subscribe(Events.HUD_UPDATE, self.handle_bus_event)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_server)

    def init_ui(self):
        self.frame = QFrame()
        self.frame.setFixedSize(210, 55)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(5, 10, 15, 255); 
                border: 1px solid #00e5ff;
                border-left: none; border-bottom: none;
                border-top-right-radius: 6px; border-bottom-left-radius: 0px;
            }
        """)
        
        layout = QVBoxLayout(self.frame)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 8, 8, 5)

        row1 = QHBoxLayout()
        self.status_light = QLabel("●")
        self.status_light.setStyleSheet("color: #ff0000; font-size: 12px; border: none; margin-top: -1px;")
        row1.addWidget(self.status_light)
        
        self.server_label = QLabel("INITIALIZING...")
        self.server_label.setStyleSheet("color: white; font-weight: bold; font-family: 'Segoe UI'; font-size: 11px; border: none;")
        row1.addWidget(self.server_label)
        row1.addStretch()
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.vram_bar = QProgressBar()
        self.vram_bar.setFixedHeight(4)
        self.vram_bar.setTextVisible(False)
        self.vram_bar.setStyleSheet("QProgressBar { border: none; background-color: #222; border-radius: 2px; }")
        row2.addWidget(self.vram_bar)
        
        self.vram_text = QLabel("VRAM")
        self.vram_text.setStyleSheet("color: #90a4ae; font-size: 9px; font-weight: bold; font-family: Consolas; border: none;")
        row2.addWidget(self.vram_text)
        layout.addLayout(row2)
        
        self.layout.addWidget(self.frame)

    def handle_bus_event(self, data):
        if data.get("action") == "toggle" and data.get("panel") == "shalom":
            self.toggle()

    def toggle(self):
        if self.isVisible():
            self.hide()
            self.timer.stop()
        else:
            self.update_position()
            self.show()
            self.raise_()
            self.poll_server()
            self.timer.start(2000)

    def update_position(self):
        screen = QApplication.primaryScreen().geometry()
        x = screen.left()
        y = screen.bottom() - 55 + 1
        self.setGeometry(x, y, 210, 55)

    def poll_server(self):
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        try:
            resp = requests.get(f"{self.server_url}/stats", timeout=1.0)
            if resp.status_code == 200:
                self.sig_update.emit(resp.json())
            else:
                self.sig_update.emit({"error": f"ERR {resp.status_code}"})
        except:
            self.sig_update.emit({"error": "OFFLINE"})

    def _apply_ui_update(self, data):
        if "error" in data:
            self.status_light.setStyleSheet("color: #ff0000; font-size: 12px; border: none;")
            self.server_label.setText(data["error"])
            self.vram_bar.setValue(0)
            return

        gpu = data.get('gpu', 'CPU').split("RTX")[-1].strip()
        used = int(data.get('vram_used', 0))
        pct = int(data.get('vram_percent', 0))

        self.status_light.setStyleSheet("color: #00ff00; font-size: 12px; border: none;")
        self.server_label.setText(f"ONLINE: {gpu}")
        self.vram_bar.setValue(pct)
        self.vram_text.setText(f"VRAM: {used}G")
        
        color = "#ff0000" if pct > 90 else "#00e5ff"
        self.vram_bar.setStyleSheet(f"""
            QProgressBar {{ border: none; background-color: #222; border-radius: 2px; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 2px; }}
        """)

# ==========================================
# 2. THE CONVERSATION PANEL (Rich Formatting Restored)
# ==========================================
class ConversationPanel(QWidget):
    sig_log = pyqtSignal(str, str) # Changed signature to take (sender, message)

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

        # Connect signals
        self.sig_log.connect(self._render_message)
        
        # Subscribe to Bus
        bus.subscribe(Events.LOG_MESSAGE, self.handle_log_event)
        bus.subscribe(Events.HUD_UPDATE, self.handle_hud_event)

    def handle_log_event(self, data):
        """
        Expects data to be a string OR a dict.
        String -> assumed SYSTEM message.
        Dict -> {"sender": "USER", "text": "..."}
        """
        sender = "SYSTEM"
        text = str(data)
        
        if isinstance(data, dict):
            sender = data.get("sender", "SYSTEM")
            text = data.get("text", "")
            
        self.sig_log.emit(sender, text)

    def handle_hud_event(self, data):
        if data.get("action") == "toggle" and data.get("panel") == "conversation":
            self.toggle()
        elif data.get("action") == "align":
            self.set_alignment(data.get("mode"))

    def set_alignment(self, mode):
        self.alignment_mode = mode
        self._apply_style()
        if self.isVisible():
            self.update_position()

    def _apply_style(self):
        base = "background-color: rgba(10, 30, 60, 180); padding: 10px; color: white; border: 1px solid white;"
        radius = "border-radius: 12px;"
        
        if self.alignment_mode == "left":
            radius = "border-top-right-radius: 12px; border-bottom-right-radius: 12px;"
        elif self.alignment_mode == "right":
            radius = "border-top-left-radius: 12px; border-bottom-left-radius: 12px;"
        
        self.display.setStyleSheet(f"QTextEdit {{ {base} {radius} }}")

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

    def _render_message(self, sender, text):
        """Restored HTML Logic from original code."""
        timestamp = time.strftime("%H:%M")
        display_name = "HARMONY🎵" if sender == "SYSTEM" else sender
        
        if sender == "SYSTEM":
            align = "left"
            bg_color = "rgba(255, 255, 255, 20)" 
            text_color = "#ffffff"
            meta_color = "#b0bec5"
            border = "1px solid rgba(255,255,255,50)"
        else:
            align = "right"
            bg_color = "rgba(0, 200, 255, 40)" 
            text_color = "#ffffff"
            meta_color = "#e0f7fa"
            border = "1px solid rgba(0, 255, 255, 100)"

        html = f"""
        <table width="100%" border="0" cellpadding="2">
            <tr>
                <td align="{align}">
                    <div style="
                        background-color: {bg_color}; border: {border};
                        border-radius: 10px; padding: 8px 12px; margin-bottom: 5px;
                        display: inline-block;">
                        <span style="font-size: 10px; color: {meta_color}; font-weight: bold;">
                            {display_name} • {timestamp}
                        </span><br>
                        <span style="font-size: 14px; color: {text_color}; font-family: 'Segoe UI';">{text}</span>
                    </div>
                </td>
            </tr>
        </table>
        """
        
        self.display.append(html)
        self.display.verticalScrollBar().setValue(
            self.display.verticalScrollBar().maximum()
        )
        
        if not self.isVisible():
            self.toggle()

# ==========================================
# 3. THE COMMAND BAR (Main Anchor)
# ==========================================
class OverlayWindow(QMainWindow):
    sig_notify = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        
        self.convo_panel = ConversationPanel()
        self.hud_panel = HudPanel()
        
        # Subscribe to Events
        bus.subscribe(Events.STATUS_CHANGED, self.handle_status_event)
        self.sig_notify.connect(self._update_notification_ui)

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
        
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: white; font-size: 10px; margin-top: 2px;") 
        layout.addWidget(self.status_dot)

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("awaiting command...")
        self.input_line.setStyleSheet("background: transparent; border: none; color: white; font-family: Consolas; font-size: 12px; font-weight: bold;")
        self.input_line.textChanged.connect(self.broadcast_input)
        layout.addWidget(self.input_line)
        
        self.main_layout.addWidget(self.command_frame)

    def center_bar(self):
        screen = QApplication.primaryScreen().geometry()
        x = screen.x() + (screen.width() - 650) // 2
        y = screen.top()
        self.resize(650, 40) 
        self.move(x, y)

    def broadcast_input(self, text):
        bus.emit(Events.GUI_INPUT_UPDATE, text)

    def handle_status_event(self, data):
        text = data.get("text", "READY")
        color = data.get("color", "white")
        self.sig_notify.emit(text, color)

    def _update_notification_ui(self, text, color_code):
        color_map = { "lime":"#69f0ae", "cyan":"#81d4fa", "orange":"#ffab40", "white":"#ffffff" }
        hex_color = color_map.get(color_code, color_code)
        
        self.status_dot.setStyleSheet(f"color: {hex_color}; font-size: 10px; margin-top: 2px;")
        self.input_line.setPlaceholderText(f"STATUS: {text}...")