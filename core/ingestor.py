import time
import threading
import queue
from core.event_bus import bus, Events

class Ingestor(threading.Thread):
    def __init__(self, database_service):
        super().__init__()
        self.db = database_service
        self.last_len = 0
        
        # ⚡ THE FIX: A Mailbox for incoming text
        self.input_queue = queue.Queue()
        self.daemon = True  # Dies when main app dies
        self.running = True

        # Listen to the GUI, but only put data in the mailbox
        bus.subscribe(Events.GUI_INPUT_UPDATE, self.enqueue_input)

    def enqueue_input(self, full_text):
        """Called by UI thread. Returns INSTANTLY."""
        self.input_queue.put(full_text)

    def run(self):
        """The Background Worker that processes the mail."""
        print("🧠 Ingestor Engine Running in Background...")
        
        while self.running:
            try:
                # 1. Wait for mail (blocks here, not in UI)
                # timeout allows us to check self.running occasionally
                full_text = self.input_queue.get(timeout=1.0) 
                
                # 2. Process the text (Heavy lifting)
                self.process_text(full_text)
                
                # 3. Mark done
                self.input_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Ingestor Error: {e}")

    def process_text(self, full_text):
        """The logic that used to freeze the screen."""
        current_len = len(full_text)
        
        if current_len > self.last_len:
            # New text detected
            new_chunk = full_text[self.last_len:]
            self.last_len = current_len
            
            # Database Write (Slow IO) - Now safe in background
            self.db.log_text_chunk(0, new_chunk)
            
            # Fire Events
            bus.emit(Events.TEXT_INGESTED, new_chunk)
            
        elif current_len < self.last_len:
            # Backspace/Clear detected
            self.last_len = current_len

    def stop(self):
        self.running = False