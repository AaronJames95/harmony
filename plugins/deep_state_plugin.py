import threading
import pyperclip
from core.event_bus import bus, Events

class DeepStatePlugin:
    def __init__(self, database_service):
        self.db = database_service
        self.is_active = False
        self.temp_buffer = []
        self.save_timer = None
        
        # Subscribe to events
        bus.subscribe(Events.TEXT_INGESTED, self.handle_text)
        
    def register(self, command_service):
        """Register our voice commands."""
        command_service.register("START_DEEP_STATE", ["shema shema", "deep state"], self.start_capture, "Activates continuous recording.")
        command_service.register("STOP_DEEP_STATE", ["shabbat", "stop recording"], self.stop_capture, "Stops recording and copies to clipboard.")
        command_service.register("FLUSH_BUFFER", ["amen", "flush"], self.flush_buffer, "Saves current buffer to logs.")

    def start_capture(self, text):
        if self.is_active: return
        self.is_active = True
        self.temp_buffer = []
        self.db.clear_temp_fragments()
        
        bus.emit(Events.STATUS_CHANGED, {"text": "REC: DEEP STATE", "color": "#ffab40"})
        bus.emit(Events.LOG_MESSAGE, "🔴 <b>Deep State Active</b><br>Listening...")

    def stop_capture(self, text):
        if not self.is_active: return
        self.is_active = False
        if self.save_timer: self.save_timer.cancel()
        
        # Retrieve consolidated text
        db_fragments = self.db.get_and_clear_temp_fragments()
        full_thought = "".join(db_fragments) + "".join(self.temp_buffer)
        final_text = full_thought.lower().replace("shema shabbat", "").strip()
        
        if final_text:
            pyperclip.copy(final_text)
            bus.emit(Events.STATUS_CHANGED, {"text": "COPIED", "color": "white"})
            bus.emit(Events.LOG_MESSAGE, f"📋 <b>Copied to Clipboard</b><br>{len(final_text)} chars.")
        
        self.temp_buffer = []

    def handle_text(self, text):
        """Listens to raw stream. If active, captures it."""
        if not self.is_active: return
        
        self.temp_buffer.append(text)
        
        # Backup every 10 seconds
        if not self.save_timer:
            self.save_timer = threading.Timer(10.0, self._backup_to_db)
            self.save_timer.start()

    def _backup_to_db(self):
        if self.is_active and self.temp_buffer:
            chunk = "".join(self.temp_buffer)
            self.db.save_temp_fragment(chunk)
            self.temp_buffer = []
        self.save_timer = None

    def flush_buffer(self, text):
        """Force save to main logs."""
        bus.emit(Events.STATUS_CHANGED, {"text": "SAVED", "color": "lime"})