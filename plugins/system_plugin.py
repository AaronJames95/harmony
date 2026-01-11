import os
import webbrowser
import pyperclip
import threading
from core.event_bus import bus, Events

class SystemPlugin:
    def __init__(self):
        self.cmd_service = None # 1. Placeholder for the brain

    def register(self, command_service):
        # 2. Store the reference so we can look up commands later
        self.cmd_service = command_service
        
        # --- UI COMMANDS ---
        command_service.register(
            "HELP_MENU", 
            ["help", "commands", "what can you do"], 
            self.show_help,
            "Lists all available commands."
        )
        command_service.register(
            "TOGGLE_CONVO", 
            ["shema conversation", "shema logs", "open logs"], 
            lambda t: self.emit_ui("toggle", "conversation"),
            "Toggles the conversation history."
        )
        command_service.register(
            "TOGGLE_SHALOM", 
            ["shema shalom", "check status", "shema aretz"], 
            lambda t: self.emit_ui("toggle", "shalom"),
            "Toggles the wellness dashboard."
        )
        
        # --- ALIGNMENT COMMANDS ---
        command_service.register("HUD_ALIGN_LEFT", ["shema left", "move left", "align left", "align port"], lambda t: self.emit_ui("align", mode="left"), "Moves chat to the left.")
        command_service.register("HUD_ALIGN_RIGHT", ["shema right", "move right", "align right", "align starboard"], lambda t: self.emit_ui("align", mode="right"), "Moves chat to the right.")
        command_service.register("HUD_ALIGN_CENTER", ["shema center", "move center", "align center"], lambda t: self.emit_ui("align", mode="center"), "Moves chat to the center.")

        # --- SYSTEM COMMANDS ---
        command_service.register(
            "HELLO_WORLD", 
            ["hello", "testing"], 
            lambda t: (bus.emit(Events.LOG_MESSAGE, "👋🏾 Harmony is online."), bus.emit(Events.STATUS_CHANGED, {"text":"READY", "color":"lime"})),
            "Connectivity Test."
        )
        
        command_service.register(
            "WEB_SEARCH",
            ["search", "google", "look up"],
            self.web_search,
            "Opens Google/Gemini search."
        )
        
        command_service.register(
            "SYSTEM_SHUTDOWN", 
            ["exit", "stop system", "shutdown", "shut down", "shema exit"], 
            self.shutdown,
            "Safely exits Harmony."
        )

    def emit_ui(self, action, panel=None, mode=None):
        bus.emit(Events.HUD_UPDATE, {"action": action, "panel": panel, "mode": mode})
        if action == "toggle" and panel == "shalom":
            bus.emit(Events.STATUS_CHANGED, {"text": "SHALOM CHECK", "color": "orange"})

    def show_help(self, text):
        bus.emit(Events.STATUS_CHANGED, {"text": "HELP OPENED", "color": "cyan"})
        
        # 3. Dynamic Generation logic
        help_text = "<b>Available Commands:</b><br>"
        
        # Iterate over the live registry from the CommandService
        for cmd in self.cmd_service.commands:
            trigger_preview = cmd['triggers'][0] if cmd['triggers'] else 'No trigger'
            desc = cmd.get('description', 'No description.')
            
            help_text += f"• <b>{cmd['id']}</b> ({trigger_preview}): {desc}<br>"
            
        bus.emit(Events.LOG_MESSAGE, help_text)

    def shutdown(self, text):
        bus.emit(Events.LOG_MESSAGE, "🛑 Shutting down...")
        bus.emit(Events.SHUTDOWN, None)
        threading.Timer(1.0, lambda: os._exit(0)).start()

    def web_search(self, text):
        query = pyperclip.paste()
        bus.emit(Events.STATUS_CHANGED, {"text": "SEARCHING", "color": "cyan"})
        bus.emit(Events.LOG_MESSAGE, f"🌐 Searching: {query}")
        webbrowser.open(f"https://gemini.google.com/app?q={query}")