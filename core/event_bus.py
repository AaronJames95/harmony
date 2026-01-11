from enum import Enum, auto

class Events(Enum):
    # System
    STARTUP = auto()
    SHUTDOWN = auto()
    
    # Input Sources
    GUI_INPUT_UPDATE = auto()   # <--- NEW: Raw text from the Command Bar
    TEXT_INGESTED = auto()      # Processed chunk (ready for commands)
    COMMAND_DETECTED = auto()
    
    # Outputs
    STATUS_CHANGED = auto()
    LOG_MESSAGE = auto()
    HUD_UPDATE = auto()
    
    # Features
    QUICK_NOTE_SAVED = auto()

class EventBus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type, callback):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def emit(self, event_type, data=None):
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"❌ Event Error on {event_type}: {e}")

bus = EventBus()