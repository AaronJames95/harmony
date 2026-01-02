import sys
from PyQt6.QtWidgets import QApplication
from cursor_key_screen import OverlayWindow
from ingestor import Ingestor

def main():
    # 1. Create the application instance
    app = QApplication(sys.argv)
    
    # 2. Create the components
    gui = OverlayWindow()
    logger = Ingestor()
    
    # 3. CONNECT THE HANDSHAKE
    # GUI signal -> Ingestor logic
    gui.text_received.connect(logger.ingest)
    
    # 4. Show the UI and run the event loop
    print("🚀 Harmony System Active.")
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()