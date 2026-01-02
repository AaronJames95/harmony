import time
import threading
from win10check import ToastNotifier # pip install win10check
import pygetwindow as gw

class DictationWatchdog:
    def __init__(self, timeout=12):
        self.timeout = timeout
        self.last_activity = time.time()
        self.is_monitoring = True
        self.toaster = ToastNotifier()
        

    def update_activity(self):
        """Call this every time a word is ingested."""
        self.last_activity = time.time()

    def check_if_dictation_running(self):
        """Checks if the Win+H toolbar is actually open."""
        # Windows Dictation usually runs under this window title
        windows = gw.getWindowsWithTitle('Dictation') 
        return len(windows) > 0

    def start(self):
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def _watch_loop(self):
        while self.is_monitoring:
            if self.check_if_dictation_running():
                elapsed = time.time() - self.last_activity
                
                if elapsed > self.timeout:
                    self.notify_user()
                    # Reset timer so it doesn't spam notifications
                    self.last_activity = time.time() 
            
            time.sleep(1) # Check every second

    def notify_user(self):
        print("⚠️ Warning: 12 seconds of silence detected!")
        self.toaster.show_toast(
            "Reclaiming Joy 2026",
            "Dictation is active but quiet. Still there?",
            duration=5,
            threaded=True
        )