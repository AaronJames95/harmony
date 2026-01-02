import time
import threading
import random
import winsound
import pygetwindow as gw
from PyQt6.QtGui import QCursor

class Watchdog:
    def __init__(self, overlay_window, timeout=12):
        self.overlay = overlay_window
        self.timeout = timeout
        self.last_activity = time.time()
        
    def is_dictation_active(self):
        # Checks for Windows 11 Voice Typing/Dictation bar
        titles = ["Dictation", "Voice typing", "Microsoft Text Input"]
        return any(len(gw.getWindowsWithTitle(t)) > 0 for t in titles)

    def is_cursor_inside(self):
        # Get cursor position and check if it's inside the input box geometry
        cursor_pos = QCursor.pos()
        box_geo = self.overlay.input_box.geometry()
        # mapToGlobal converts local coordinates to screen coordinates
        global_box = self.overlay.input_box.mapToGlobal(box_geo.topLeft())
        # Check boundaries...
        return self.overlay.input_box.rect().contains(self.overlay.input_box.mapFromGlobal(cursor_pos))

    def monitor_loop(self):
        while True:
            active = self.is_dictation_active()
            inside = self.is_cursor_inside()
            
            # If transcriber is on but idle, or cursor is lost...
            if (active and (time.time() - self.last_activity > self.timeout)) or not inside:
                self.trigger_alert()
            
            time.sleep(1)

    def trigger_alert(self):
        # Randomized frequency for the HUD 'beep'
        freq = random.randint(800, 1200) 
        winsound.Beep(freq, 200)
        print("HUD Alert: Check cursor or dictation status.")