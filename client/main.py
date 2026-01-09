import sys
import signal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from cursor_key_screen import OverlayWindow
from ingestor import Ingestor

def main():
    app = QApplication(sys.argv)
    
    # 1. Initialize GUI
    gui = OverlayWindow()
    
    # 2. Initialize Ingestor
    logger = Ingestor()
    
    # 3. LINKING: Give logger access to GUI for notifications
    logger.gui = gui 

    # Connect transcription signal to database/logic
    gui.text_received.connect(logger.ingest)

    def shutdown():
        print("\n[Harmony] Finalizing logs...")
        if logger.buffer:
            logger.flush_buffer()
        print("[Harmony] System offline.")
        app.quit()

    signal.signal(signal.SIGINT, lambda *args: shutdown())
    
    timer = QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    print("--------------------------------------------------")
    print("🚀 Harmony System Active")
    print(f"📂 Root Directory: {logger.root_dir}")
    print(f"📄 DB Location: {logger.db_path}")
    print("--------------------------------------------------")
    
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()