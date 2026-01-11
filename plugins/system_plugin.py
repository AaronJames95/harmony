import os
import webbrowser
from core.event_bus import bus, Events

class SystemPlugin:
    def __init__(self):
        pass

    def register(self, command_service):
        # UI Toggles
        command_service.register("TOGGLE_CONVO", ["shema conversation", "open logs"], lambda t: self.emit_ui("conversation"))
        command_service.register("TOGGLE_SHALOM", ["shema shalom", "check status"], lambda t: self.emit_ui("shalom"))
        
        # Windows Management
        command_service.register("EXIT", ["shutdown", "exit system"], self.shutdown)
        command_service.register("HELLO", ["hello", "testing"], lambda t: bus.emit(Events.LOG_MESSAGE, "👋 Harmony Online."))
        
        # Web
        command_service.register("SEARCH", ["search", "google"], self.web_search)

    def emit_ui(self, panel_name):
        # We emit an event that the UI listens for
        bus.emit(Events.HUD_UPDATE, {"action": "toggle", "panel": panel_name})

    def shutdown(self, text):
        bus.emit(Events.LOG_MESSAGE, "🛑 Shutting down...")
        bus.emit(Events.SHUTDOWN, None)
        os._exit(0)

    def web_search(self, text):
        import pyperclip
        query = pyperclip.paste()
        bus.emit(Events.STATUS_CHANGED, {"text": "SEARCHING", "color": "cyan"})
        webbrowser.open(f"https://gemini.google.com/app?q={query}")