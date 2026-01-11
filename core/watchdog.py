import time
import threading
import pyperclip
from core.event_bus import bus, Events

class IngestorWatchdog(threading.Thread):
    """
    Monitors the clipboard for changes and feeds text to the Ingestor.
    """
    def __init__(self, ingestor):
        super().__init__()
        self.ingestor = ingestor
        self.daemon = True
        self.running = True
        self._last_value = ""

    def run(self):
        # Initial clear to prevent processing old clipboard data on startup
        self._last_value = pyperclip.paste()
        
        while self.running:
            try:
                current_value = pyperclip.paste()
                if current_value != self._last_value:
                    self._last_value = current_value
                    if current_value.strip():
                        # Feed the brain
                        self.ingestor.ingest(current_value)
            except Exception as e:
                print(f"🐕 Watchdog Error: {e}")
            
            time.sleep(0.5)

    def stop(self):
        self.running = False