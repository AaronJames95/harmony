import sys
import os
import signal
from PyQt6.QtWidgets import QApplication
# --- 1. SETUP ENVIRONMENT ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)

# --- 2. IMPORTS ---
from core.event_bus import bus, Events
from core.ingestor import Ingestor
from core.watchdog import IngestorWatchdog
# from core.transcript_listener import TranscriptListener  <-- DELETED
from services.database_service import DatabaseService
from services.command_service import CommandService
from plugins.system_plugin import SystemPlugin
from plugins.deep_state_plugin import DeepStatePlugin
from plugins.media_plugin import MediaPlugin
from plugins.obsidian_plugin import ObsidianPlugin # <--- NEW IMPORT
from ui.windows.overlay import OverlayWindow

def main():
    """Harmony Entry Point"""
    
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    print(f"🚀 Booting Harmony from: {ROOT_DIR}")

    # --- A. INITIALIZE SERVICES ---
    print("💾 Starting Services...")
    db_path = os.path.join(ROOT_DIR, "logs", "harmony_main.db")
    db_service = DatabaseService(db_path)
    command_service = CommandService(db_service)

    # --- B. LOAD PLUGINS ---
    print("🔌 Loading Plugins...")
    SystemPlugin().register(command_service)
    DeepStatePlugin(db_service).register(command_service)
    ObsidianPlugin().register(command_service)
    
    media_plugin = MediaPlugin()
    command_service.register("PROCESS_AUDIO", ["process audio", "transcribe"], 
                             lambda t: bus.emit(Events.COMMAND_DETECTED, {"id": "PROCESS_AUDIO"}),
                             "Uploads media from clipboard.")

    # --- C. CORE ENGINE ---
    print("🧠 Starting Engine...")
    ingestor = Ingestor(db_service)
    ingestor.start()  # <--- CRITICAL ADDITION
    
    # 1. The Watchdog (Eyes - Clipboard)
    clipboard_dog = IngestorWatchdog(ingestor)
    
    # 2. The Listener (Ears) -> REMOVED. 
    # The 'Ears' are now the GUI OverlayWindow itself.

    # --- D. START UI ---
    print("🎨 Launching GUI...")
    app = QApplication(sys.argv)
    window = OverlayWindow()
    window.show()

    # --- E. LIFTOFF ---
    print("🐕 Sensors Active (Clipboard + Text Input).")
    clipboard_dog.start()
    
    bus.emit(Events.STARTUP, None)
    bus.emit(Events.STATUS_CHANGED, {"text": "READY", "color": "lime"})
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()