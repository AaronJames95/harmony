import cursor_key_screen

def main():
    cursor_key_screen.run()
    try:
        while True:
            # We use input() because Ctrl+D specifically affects input streams
            data = input("Type something (or press Ctrl+D to exit): ")
            print(f"You entered: {data}")
            
    except EOFError:
        print("\nControl + D detected! Closing the program...")
    #navi.



import sys
from PyQt6.QtWidgets import QApplication

# Import your custom modules
#from overlay import OverlayWindow
from ingestor import Ingestor
from watchdog import Watchdog

def mafin():
    # 1. Initialize the App
    print("Hello, World!")

    app = QApplication(sys.argv)
    
    # 2. Initialize the Components
    # We pass 'None' to Watchdog initially or initialize after window
    gui = OverlayWindow()
    logger = Ingestor()
    
    # 3. CONNECT THE PIPES (The Signal Logic)
    # When GUI sends text -> Logger ingests it
    gui.text_received.connect(logger.ingest)
    
    # 4. INITIALIZE THE WATCHDOG
    # We pass the 'gui' object so the watchdog can check cursor position
    monitor = Watchdog(overlay_window=gui, timeout=12)
    
    # Connect GUI changes to Watchdog activity reset
    gui.text_received.connect(monitor.update_activity)
    
    # Start the monitoring thread
    monitor.start()

    # 5. Launch
    print("🚀 Harmony HUD Started: Reclaiming Joy 2026")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()