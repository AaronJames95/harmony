from PyQt6.QtGui import QCursor # Add this to imports

class Watchdog:
    def __init__(self, overlay_window, timeout=12):
        self.overlay = overlay_window # Keep a reference to the GUI
        self.timeout = timeout
        self.last_activity = time.time()
        self.is_monitoring = True
        self.toaster = ToastNotifier()

    def check_if_dictation_running(self):
        # Broaden the search for the dictation bar titles
        titles = ['Dictation', 'Voice typing', 'Voice access', 'Microsoft Text Input']
        all_windows = gw.getAllTitles()
        return any(any(t.lower() in w.lower() for t in titles) for w in all_windows)

    def is_cursor_inside_box(self):
        # 1. Get current mouse position
        mouse_pos = QCursor.pos()
        # 2. Get the input box boundaries in screen coordinates
        box_rect = self.overlay.input_box.rect()
        global_top_left = self.overlay.input_box.mapToGlobal(box_rect.topLeft())
        
        # 3. Check if mouse is within those X/Y bounds
        within_x = global_top_left.x() <= mouse_pos.x() <= global_top_left.x() + box_rect.width()
        within_y = global_top_left.y() <= mouse_pos.y() <= global_top_left.y() + box_rect.height()
        return within_x and within_y

    def _watch_loop(self):
        while self.is_monitoring:
            # ALERT TRIGGERS:
            # - If Dictation is ON but you haven't spoken in 12s
            # - OR if your cursor has left the input box
            is_active = self.check_if_dictation_running()
            is_inside = self.is_cursor_inside_box()
            elapsed = time.time() - self.last_activity

            if (is_active and elapsed > self.timeout) or not is_inside:
                self.notify_user()
                self.last_activity = time.time() # Reset to prevent "machine gun" beeping
            
            time.sleep(1)

    def notify_user(self):
        # Randomized pitch for that 'HUD' feel (800Hz - 1300Hz)
        freq = random.randint(800, 1300)
        winsound.Beep(freq, 300)
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION) # Backup audio
        print(f"⚠️ Watchdog Alert: Cursor lost or 12s silence.")