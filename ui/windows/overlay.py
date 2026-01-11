import sys
import threading
import requests
from PyQt6.QtWidgets import (
    QMainWindow, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, 
    QLabel, QFrame, QApplication, QLineEdit, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QObject

# ⚡ NEW ARCHITECTURE IMPORT
from core.event_bus import bus, Events

# ==========================================
# 1. THE COMPACT HUD (Flush Bottom-Left)
# ==========================================
class HudPanel(QWidget):
    # Internal signal to update UI safely from background threads
    sig_update = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        # ⚠️ We will eventually move this URL to config.yaml
        self.server_url = "http://100.94.65.56:8000" 

        # Window Flags
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.init_ui()

        # Connect internal signal
        self.sig_update.connect(self._apply_ui_update)
        
        # Subscribe to Bus Events
        bus.subscribe(Events.HUD_UPDATE, self.handle_bus_event)
        
        # Start Polling
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

        # Row 1
        row1 = QHBoxLayout()
        self.status_light = QLabel("●")
        self.status_light.setStyleSheet("color: #ff0000; font-size: 12px; border: none; margin-top: -1px;")
        row1.addWidget(self.status_light)
        
        self.server_label = QLabel("INITIALIZING...")
        self.server_label.setStyleSheet("color: white; font-weight: bold; font-family: 'Segoe UI'; font-size: 11px; border: none;")
        row1.addWidget(self.server_label)
        row1.addStretch()
        layout.addLayout(row1)

        # Row 2
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
        """Reacts to 'TOGGLE_SHALOM' or similar events."""
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
# 2. THE CONVERSATION PANEL
# ==========================================
class ConversationPanel(QWidget):
    sig_log = pyqtSignal(str)

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

        # Wire up signals
        self.sig_log.connect(self._append_html)
        
        # Subscribe to Event Bus
        bus.subscribe(Events.LOG_MESSAGE, self.handle_log_event)
        bus.subscribe(Events.HUD_UPDATE, self.handle_hud_event)

    def handle_log_event(self, message):
        """Called when system wants to print a message."""
        # Simple HTML formatting
        html = f"<span style='color: #ffffff; font-family: Segoe UI; font-size: 14px;'>{message}</span>"
        self.sig_log.emit(html)

    def handle_hud_event(self, data):
        if data.get("action") == "toggle" and data.get("panel") == "conversation":
            self.toggle()

    def _apply_style(self):
        base = "background-color: rgba(10, 30, 60, 180); padding: 10px; color: white; border: 1px solid white;"
        radius = "border-radius: 12px;"
        if self.alignment_mode == "left":
            radius = "border-top-right-radius: 12px; border-bottom-right-radius: 12px;"
        elif self.alignment_mode == "right":
            radius = "border-top-left-radius: 12px; border-bottom-left-radius: 12px;"
        
        self.display.setStyleSheet(f"QTextEdit {{ {base} {radius} }}")

    def toggle(self):
        if self.isVisible(): self.hide()
        else:
            self.update_position()
            self.show()
            self.raise_()

    def update_position(self):
        screen = QApplication.primaryScreen().geometry()
        y = screen.top() + 60
        h = int(screen.height() * 0.85)
        w = int(screen.width() * 0.30)
        
        if self.alignment_mode == "center":
            w = 650
            x = screen.x() + (screen.width() - w) // 2
        elif self.alignment_mode == "left":
            x = screen.left()
        else: 
            x = screen.right() - w
            
        self.setGeometry(x, y, w, h)

    def _append_html(self, html):
        self.display.append(html)
        self.display.verticalScrollBar().setValue(self.display.verticalScrollBar().maximum())
        if not self.isVisible(): self.toggle()

# ==========================================
# 3. THE COMMAND BAR (Main Anchor)
# ==========================================
class OverlayWindow(QMainWindow):
    # Internal signal for thread-safe UI updates
    sig_notify = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        
        self.convo_panel = ConversationPanel()
        self.hud_panel = HudPanel()
        
        # Subscribe to Status Events
        bus.subscribe(Events.STATUS_CHANGED, self.handle_status_event)
        self.sig_notify.connect(self._update_notification_ui)

        # Window Setup
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
        # Note: We are not wiring up text input yet in this refactor step
        layout.addWidget(self.input_line)
        
        self.main_layout.addWidget(self.command_frame)

    def broadcast_input(self, text):
        """Fires whenever the input text changes (typing or dictation)."""
        bus.emit(Events.GUI_INPUT_UPDATE, text)

    def center_bar(self):
        screen = QApplication.primaryScreen().geometry()
        x = screen.x() + (screen.width() - 650) // 2
        y = screen.top()
        self.resize(650, 40) 
        self.move(x, y)

    def handle_status_event(self, data):
        """Called when backend says 'STATUS_CHANGED'."""
        text = data.get("text", "READY")
        color = data.get("color", "white")
        self.sig_notify.emit(text, color)

    def _update_notification_ui(self, text, color_code):
        color_map = { "lime":"#69f0ae", "cyan":"#81d4fa", "orange":"#ffab40", "white":"#ffffff" }
        hex_color = color_map.get(color_code, color_code)
        
        self.status_dot.setStyleSheet(f"color: {hex_color}; font-size: 10px; margin-top: 2px;")
        self.input_line.setPlaceholderText(f"STATUS: {text}...")