import time
from core.event_bus import bus, Events

class Ingestor:
    def __init__(self, database_service):
        self.db = database_service
        self.last_len = 0
        
        # ⚡ THE FIX: Listen to the GUI text box
        bus.subscribe(Events.GUI_INPUT_UPDATE, self.ingest)

    def ingest(self, full_text):
        """
        Calculates the 'new' text added to the box and broadcasts it.
        """
        current_len = len(full_text)
        
        if current_len > self.last_len:
            # We have new text!
            new_chunk = full_text[self.last_len:]
            self.last_len = current_len
            
            # 1. Log to DB
            self.db.log_text_chunk(0, new_chunk)
            
            # 2. Fire "I heard something" event
            bus.emit(Events.TEXT_INGESTED, new_chunk)
            
        elif current_len < self.last_len:
            # Text box was cleared (backspace or reset)
            self.last_len = current_len