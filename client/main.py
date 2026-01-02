import sys
import signal # NEW: Import the signal module
from PyQt6.QtWidgets import QApplication
from cursor_key_screen import OverlayWindow
from ingestor import Ingestor

def main():
    app = QApplication(sys.argv)
    
    # NEW: Allow Ctrl+C to shut down the app
    # This connects the system interrupt to the Qt quit function
    signal.signal(signal.SIGINT, lambda *args: app.quit())
    
    # Optional: Create a timer that occasionally lets Python process signals
    from PyQt6.QtCore import QTimer
    timer = QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    gui = OverlayWindow()
    logger = Ingestor()
    gui.text_received.connect(logger.ingest)
    
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()