import sys
import os
import time
from PyQt6.QtWidgets import (
    QMainWindow, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, 
    QLabel, QFrame, QApplication, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

# --- THE SATELLITE WINDOW (Content) ---
class ContentPanel(QWidget):
    def __init__(self):
        super().__init__()
        
        # Window Flags: Tool, Frameless, Always on Top, No Background
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.alignment_mode = "right" # Default

        # --- COMPONENTS ---
        self.init_conversation_panel()
        self.init_shalom_panel()

    def init_conversation_panel(self):
        self.conversation_display = QTextEdit()
        self.conversation_display.setReadOnly(True)
        self.conversation_display.hide()
        self.layout.addWidget(self.conversation_display)

    def init_shalom_panel(self):
        self.shalom_frame = QFrame()
        self.shalom_frame.setStyleSheet("background: transparent;")
        self.shalom_frame.hide()

        cols_layout = QHBoxLayout(self.shalom_frame)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(15)

        def create_column(title, data_points):
            col_frame = QFrame()
            # UPDATED: 70% Opacity (180 alpha) & Solid White Border
            col_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(10, 30, 60, 180);
                    border: 1px solid white;
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
        
        self.layout.addWidget(self.shalom_frame)

    def _apply_styles(self):
        """Update border radius to make it look attached to the screen edge."""
        # UPDATED: 70% Opacity (180 alpha)
        base_style = """
            background-color: rgba(10, 30, 60, 180);
            padding: 10px; color: white;
            font-family: 'Segoe UI'; font-size: 14px;
        """
        
        # Logic: If docked to a side, flatten that side
        # UPDATED: Borders are now '1px solid white'
        if self.alignment_mode == "left":
            specifics = """
                border: 1px solid white;
                border-left: none; /* Open to the side */
                border-top-left-radius: 0px; 
                border-bottom-left-radius: 0px;
                border-top-right-radius: 12px; 
                border-bottom-right-radius: 12px;
            """
            
        elif self.alignment_mode == "right":
            specifics = """
                border: 1px solid white;
                border-right: none; /* Open to the side */
                border-top-right-radius: 0px; 
                border-bottom-right-radius: 0px;
                border-top-left-radius: 12px; 
                border-bottom-left-radius: 12px;
            """
            
        else: # Center
            specifics = """
                border: 1px solid white;
                border-radius: 12px;
            """

        self.conversation_display.setStyleSheet(f"QTextEdit {{ {base_style} {specifics} }}")

    def update_position(self):
        """Moves this panel to the correct spot on screen, flush with edges."""
        screen_geo = QApplication.primaryScreen().geometry()
        
        # Vertical Position: Below the Command Bar (approx 60px down)
        y_pos = screen_geo.top() + 60
        height_ratio = 0.85
        target_height = int(screen_geo.height() * height_ratio)
        
        if self.alignment_mode == "center":
            pane_width = 650
            x_pos = screen_geo.x() + (screen_geo.width() - pane_width) // 2
        
        elif self.alignment_mode == "left":
            pane_width = int(screen_geo.width() * 0.30)
            x_pos = screen_geo.left() # EXACTLY 0 (Flush)
            
        else: # right
            pane_width = int(screen_geo.width() * 0.30)
            x_pos = screen_geo.right() - pane_width # EXACTLY Width (Flush)
            
        self.conversation_display.setFixedWidth(pane_width)
        self.resize(pane_width, target_height)
        self.move(x_pos, y_pos)
        self._apply_styles()

    def show_content(self, content_type):
        """Switches between Conversation and Shalom modes."""
        if content_type == "conversation":
            if self.conversation_display.isVisible():
                self.hide()
                self.conversation_display.hide()
            else:
                self.shalom_frame.hide()
                self.conversation_display.show()
                self.update_position()
                self.show()
        elif content_type == "shalom":
            if self.shalom_frame.isVisible():
                self.hide()
                self.shalom_frame.hide()
            else:
                self.conversation_display.hide()
                self.shalom_frame.show()
                self.update_position()
                self.show()

# --- THE ANCHOR WINDOW (Command Bar) ---
class OverlayWindow(QMainWindow):
    text_received = pyqtSignal(str)
    
    # Internal Signals to talk to Panel
    sig_toggle = pyqtSignal(str)
    sig_message = pyqtSignal(str, str)
    sig_notify = pyqtSignal(str, str)
    sig_align = pyqtSignal(str) 

    def __init__(self):
        super().__init__()
        
        # --- DUAL WINDOW SETUP ---
        self.panel = ContentPanel() # The satellite
        
        # Connect Signals
        self.sig_toggle.connect(self.panel.show_content)
        self.sig_align.connect(self._slot_set_alignment)
        
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

    # --- SLOTS ---
    def _slot_set_alignment(self, mode):
        self.panel.alignment_mode = mode.lower()
        self.update_notification(f"ALIGN: {mode.upper()}", "cyan")
        
        if self.panel.isVisible():
            self.panel.update_position()

    def add_message(self, sender, text):
        timestamp = time.strftime("%H:%M")
        display_name = "HARMONY🎵" if sender == "SYSTEM" else sender
        
        # Style Logic
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

    def update_notification(self, text, color_code="white"):
        color_map = {
            "#69f0ae": "lime", "#81d4fa": "cyan", 
            "#ffab40": "orange", "#ffd740": "yellow", "#b3e5fc": "cyan"
        }
        final_color = color_map.get(color_code, color_code)
        if "#" in final_color: final_color = "white"
        
        self.status_dot.setStyleSheet(f"color: {final_color}; font-size: 10px; margin-top: 2px;")
        self.input_line.setPlaceholderText(f"STATUS: {text}...")

    # --- PUBLIC API ---
    def toggle_panel(self, panel_name):
        self.sig_toggle.emit(panel_name)
    
    def set_alignment(self, mode):
        self.sig_align.emit(mode)