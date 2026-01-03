import sys
import signal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from cursor_key_screen import OverlayWindow
from ingestor import Ingestor

def main():
    app = QApplication(sys.argv)
    gui = OverlayWindow()
    logger = Ingestor()
    gui.text_received.connect(logger.ingest)

    def shutdown():
        print("\nFinalizing logs...")
        if logger.buffer:
            logger.flush_buffer()
        print("Done. Exiting.")
        app.quit()

    signal.signal(signal.SIGINT, lambda *args: shutdown())
    
    timer = QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    print("🚀 Harmony System Active (Manual Write Mode).")
    print("Commands: 'Shema Write' to sync text, 'Shema Shutdown' to exit.")
    
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()