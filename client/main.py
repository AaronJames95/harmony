import sys
import signal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from cursor_key_screen import OverlayWindow
from ingestor import Ingestor

def main():
    # 1. Initialize the App
    app = QApplication(sys.argv)
    
    # 2. Handle Ctrl+C (SIGINT)
    # We use a lambda to trigger the app's quit function
    signal.signal(signal.SIGINT, lambda *args: app.quit())
    
    # 3. Required for PyQt to process Python signals on Windows
    timer = QTimer()
    timer.start(500) # Check every 500ms
    timer.timeout.connect(lambda: None) 

    # 4. Initialize the Components
    gui = OverlayWindow()
    logger = Ingestor()
    
    # 5. Connect the signal logic
    # Connect GUI output to Ingestor input
    gui.text_received.connect(logger.ingest)
    
    print("🚀 Harmony System Active. Press Ctrl+C in this terminal to exit.")
    
    gui.show()
    
    # 6. Execute the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()