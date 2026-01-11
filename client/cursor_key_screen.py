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

# --- THE SATELLITE WINDOW (Content) ---
class ContentPanel(QWidget):
    # ⚡ SIGNAL BRIDGE: This allows the background thread to talk to the GUI safely
    sig_stats_update = pyqtSignal(object) 

    def __init__(self):
        super().__init__()
        
        # ⚠️ VERIFY THIS IP MATCHES YOUR SERVER
        self.server_url = "http://100.94.65.56:8000" 

        # Window Flags
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.alignment_mode = "right" 

        # --- COMPONENTS ---
        self.init_conversation_panel()
        self.init_hud_panel()

        # --- SIGNALS ---
        # Connect the signal to the UI update function
        self.sig_stats_update.connect(self._update_hud_ui)

        # --- POLLING TIMER ---
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.poll_server)
        
    def init_conversation_panel(self):
        self.conversation_display = QTextEdit()
        self.conversation_display.setReadOnly(True)
        self.conversation_display.hide()
        self.layout.addWidget(self.conversation_display)

    def init_hud_panel(self):
        """Creates the Video Game Style HUD (Bottom Left)."""
        self.shalom_frame = QFrame()
        self.shalom_frame.hide()
        self.shalom_frame.setFixedSize(300, 120)
        
        # HIGH CONTRAST STYLE
        self.shalom_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(5, 15, 25, 250); 
                border: 2px solid #00e5ff; /* Bright Cyan Border */
                border-radius: 6px;
            }
        """)

        hud_layout = QVBoxLayout(self.shalom_frame)
        hud_layout.setSpacing(5)
        hud_layout.setContentsMargins(15, 15, 15, 15)
        
        # 1. STATUS HEADER
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        self.status_light = QLabel("●")
        self.status_light.setStyleSheet("color: #ff0000; font-size: 20px; border: none; margin-top: -4px;") 
        header_layout.addWidget(self.status_light)
        
        self.server_label = QLabel("INITIALIZING...")
        self.server_label.setStyleSheet("color: #ffffff; font-weight: bold; font-family: Consolas; font-size: 16px; border: none;")
        header_layout.addWidget(self.server_label)
        
        header_layout.addStretch()
        hud_layout.addLayout(header_layout)

        # 2. VRAM BAR
        self.vram_label = QLabel("GPU MEMORY")
        self.vram_label.setStyleSheet("color: #00e5ff; font-size: 12px; font-weight: bold; border: none; margin-top: 5px;")
        hud_layout.addWidget(self.vram_label)

        self.vram_bar = QProgressBar()
        self.vram_bar.setFixedHeight(10)
        self.vram_bar.setTextVisible(False)
        self.vram_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                background-color: #222;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #00e5ff; 
                border-radius: 4px;
            }
        """)
        hud_layout.addWidget(self.vram_bar)

        self.vram_text = QLabel("WAITING...")
        self.vram_text.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.vram_text.setStyleSheet("color: #cccccc; font-size: 11px; font-family: Consolas; border: none;")
        hud_layout.addWidget(self.vram_text)

        self.layout.addWidget(self.shalom_frame)

    def update_position(self):
        screen_geo = QApplication.primaryScreen().geometry()
        
        if self.shalom_frame.isVisible():
            width = 300
            height = 120
            x_pos = screen_geo.left() + 30
            y_pos = screen_geo.bottom() - height - 80 
            
            self.conversation_display.hide()
            self.setMinimumSize(width, height)
            self.setMaximumSize(width, height)
            self.resize(width, height)
            self.move(x_pos, y_pos)
            return

        # Normal conversation mode logic
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        
        y_pos = screen_geo.top() + 60
        height_ratio = 0.85
        target_height = int(screen_geo.height() * height_ratio)
        
        if self.alignment_mode == "center":
            pane_width = 650
            x_pos = screen_geo.x() + (screen_geo.width() - pane_width) // 2
        elif self.alignment_mode == "left":
            pane_width = int(screen_geo.width() * 0.30)
            x_pos = screen_geo.left()
        else: 
            pane_width = int(screen_geo.width() * 0.30)
            x_pos = screen_geo.right() - pane_width
            
        self.conversation_display.setFixedWidth(pane_width)
        self.resize(pane_width, target_height)
        self.move(x_pos, y_pos)
        self._apply_convo_styles()

    def _apply_convo_styles(self):
        base_style = """
            background-color: rgba(10, 30, 60, 180);
            padding: 10px; color: white;
            border: 1px solid white;
            font-family: 'Segoe UI'; font-size: 14px;
        """
        if self.alignment_mode == "left":
            specifics = "border-left: none; border-top-left-radius: 0px; border-bottom-left-radius: 0px; border-top-right-radius: 12px; border-bottom-right-radius: 12px;"
        elif self.alignment_mode == "right":
            specifics = "border-right: none; border-top-right-radius: 0px; border-bottom-right-radius: 0px; border-top-left-radius: 12px; border-bottom-left-radius: 12px;"
        else:
            specifics = "border-radius: 12px;"

        self.conversation_display.setStyleSheet(f"QTextEdit {{ {base_style} {specifics} }}")

    def show_content(self, content_type):
        if content_type == "conversation":
            self.stats_timer.stop()
            self.shalom_frame.hide()
            self.conversation_display.show()
            self.update_position()
            self.show()
        elif content_type == "shalom":
            if self.shalom_frame.isVisible():
                self.hide() 
                self.shalom_frame.hide()
                self.stats_timer.stop()
            else:
                self.conversation_display.hide()
                self.shalom_frame.show()
                self.update_position()
                self.show()
                self.poll_server() 
                self.stats_timer.start(2000) 

    def poll_server(self):
        threading.Thread(target=self._fetch_stats, daemon=True).start()

    def _fetch_stats(self):
        """Runs in background thread. Emits SIGNAL with data."""
        try:
            resp = requests.get(f"{self.server_url}/stats", timeout=1.0)
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    # ⚡ EMIT SIGNAL: Hand off data to Main Thread
                    self.sig_stats_update.emit(data)
                except:
                    self.sig_stats_update.emit({"error": "JSON ERROR"})
            else:
                self.sig_stats_update.emit({"error": f"ERR {resp.status_code}"})
                
        except requests.exceptions.ConnectionError:
            self.sig_stats_update.emit({"error": "NO LINK"})
        except Exception:
            self.sig_stats_update.emit({"error": "FAIL"})

    def _update_hud_ui(self, data):
        """Runs on Main Thread. Updates GUI elements."""
        
        # Check for errors passed from thread
        if "error" in data:
            self.status_light.setStyleSheet("color: #ff0000; font-size: 20px; border: none; margin-top: -4px;") 
            self.server_label.setText(data["error"])
            self.vram_bar.setValue(0)
            self.vram_text.setText("RETRYING...")
            return

        # Process Valid Data
        try:
            gpu_name = data.get('gpu', 'Unknown GPU')
            used = data.get('vram_used', 0)
            total = data.get('vram_total', 24)
            pct = data.get('vram_percent', 0)

            self.status_light.setStyleSheet("color: #00ff00; font-size: 20px; border: none; margin-top: -4px;") 
            self.server_label.setText(f"ONLINE ({gpu_name})")
            
            self.vram_bar.setValue(int(pct))
            self.vram_text.setText(f"{used} GB / {total} GB")
            
            if pct > 90:
                self.vram_bar.setStyleSheet("QProgressBar { border: 1px solid #555; background-color: #222; border-radius: 4px; } QProgressBar::chunk { background-color: #ff0000; border-radius: 4px; }")
            else:
                self.vram_bar.setStyleSheet("QProgressBar { border: 1px solid #555; background-color: #222; border-radius: 4px; } QProgressBar::chunk { background-color: #00e5ff; border-radius: 4px; }")
        
        except Exception as e:
            print(f"❌ HUD Render Error: {e}")
            self.server_label.setText("RENDER FAIL")

# --- THE ANCHOR WINDOW ---
class OverlayWindow(QMainWindow):
    text_received = pyqtSignal(str)
    sig_toggle = pyqtSignal(str)
    sig_message = pyqtSignal(str, str)
    sig_notify = pyqtSignal(str, str)
    sig_align = pyqtSignal(str) 

    def __init__(self):
        super().__init__()
        self.panel = ContentPanel() 
        
        self.sig_toggle.connect(self.panel.show_content)
        self.sig_align.connect(self._slot_set_alignment)
        self.sig_message.connect(self._slot_add_message)
        self.sig_notify.connect(self._slot_update_notification)
        
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
        self.command_frame.setFixedHeight(38)
        self.command_frame.setFixedWidth(650)
        
        self.command_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 30, 60, 240); 
                border: 1px solid white;
                border-top: none;
                border-bottom-right-radius: 12px;
                border-bottom-left-radius: 12px;
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

    def center_bar(self):
        screen_geo = QApplication.primaryScreen().geometry()
        x_pos = screen_geo.x() + (screen_geo.width() - 650) // 2
        y_pos = screen_geo.top()
        self.resize(650, 40) 
        self.move(x_pos, y_pos)

    def _slot_set_alignment(self, mode):
        self.panel.alignment_mode = mode.lower()
        self._slot_update_notification(f"ALIGN: {mode.upper()}", "cyan")
        if self.panel.isVisible() and self.panel.conversation_display.isVisible():
            self.panel.update_position()

    def _slot_add_message(self, sender, text):
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
                        <span style="font-size: 14px; color: {text_color};">{text}</span>
                    </div>
                </td>
            </tr>
        </table>
        """
        
        self.panel.conversation_display.append(html)
        self.panel.conversation_display.verticalScrollBar().setValue(
            self.panel.conversation_display.verticalScrollBar().maximum()
        )

        if not self.panel.isVisible():
            self.panel.show_content("conversation")

    def _slot_update_notification(self, text, color_code="white"):
        color_map = {
            "#69f0ae": "lime", "#81d4fa": "cyan", 
            "#ffab40": "orange", "#ffd740": "yellow", "#b3e5fc": "cyan"
        }
        final_color = color_map.get(color_code, color_code)
        if "#" in final_color: final_color = "white"
        
        self.status_dot.setStyleSheet(f"color: {final_color}; font-size: 10px; margin-top: 2px;")
        self.input_line.setPlaceholderText(f"STATUS: {text}...")

    def toggle_panel(self, panel_name):
        self.sig_toggle.emit(panel_name)
    
    def set_alignment(self, mode):
        self.sig_align.emit(mode)

    def add_message(self, sender, text):
        self.sig_message.emit(sender, text)

    def update_notification(self, text, color="white"):
        self.sig_notify.emit(text, color)