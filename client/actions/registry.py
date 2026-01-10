import webbrowser
import os
import pyperclip
from PyQt6.QtCore import QTimer
import threading
from datetime import datetime

COMMANDS = [
    {
        "id": "HELP_MENU",
        "description": "Lists all available commands.",
        "triggers": ["help", "commands", "what can you do"],
        "action": lambda ing, *args: (
            ing.gui.update_notification("HELP MENU OPENED", "cyan"),
            ing.gui.add_message("SYSTEM", 
                "<b>Available Commands:</b><br>" + 
                "<br>".join([f"• <b>{cmd['id']}</b>: {cmd.get('description', 'No description.')}" for cmd in COMMANDS])
            )
        )
    },
    {
        "id": "TOGGLE_CONVO",
        "description": "Toggles the conversation history.",
        "triggers": ["shema conversation", "shema logs", "open logs"],
        "action": lambda ing, *args: ing.gui.toggle_panel("conversation")
    },
    {
        "id": "TOGGLE_SHALOM",
        "description": "Toggles the wellness dashboard.",
        "triggers": ["shema shalom", "check status", "shema aretz"],
        "action": lambda ing, *args: (
            ing.gui.toggle_panel("shalom"),
            ing.gui.update_notification("SHALOM CHECK", "orange")
        )
    },
    {
        "id": "HELLO_WORLD",
        "description": "Verify system is active.",
        "triggers": ["hello", "testing"],
        "action": lambda ing, *args: (
            ing.gui.add_message("SYSTEM", "👋🏾 Harmony is online."),
            ing.gui.update_notification("READY", "lime")
        )
    },
    {
        "id": "START_DEEP_STATE",
        "description": "Activates continuous recording.",
        "triggers": ["shema shema", "deep state", "start recording"],
        "action": lambda ing, *args: (
            ing.start_deep_state()
        )
    },
    {
        "id": "FLUSH_BUFFER",
        "description": "Saves the current Deep State buffer.",
        "triggers": ["amen", "flush", "save that"],
        "action": lambda ing, *args: ing.flush_buffer()
    },
    {
        # --- SMART QUICK NOTE ---
        # Handles both Voice and Clipboard logic in one command
        "id": "QUICK_NOTE",
        "description": "Saves spoken text OR clipboard to Obsidian.",
        "triggers": ["note", "capture"], 
        "action": lambda ing, text: (
            # If the user says "clipboard" anywhere in the command (e.g. "Note the clipboard")
            # we switch source to 'clipboard' and grab content from pyperclip.
            ing.save_quick_note(pyperclip.paste(), source="clipboard") 
            if "clipboard" in text.lower() 
            else ing.save_quick_note(text, source="voice")
        )
    },
    {
        "id": "WEB_SEARCH",
        "description": "Opens Google/Gemini search.",
        "triggers": ["search", "google", "look up"],
        "action": lambda ing, *args: (
            ing.gui.update_notification("WEB ACTION", "cyan"),
            webbrowser.open(f"https://gemini.google.com/app?q={pyperclip.paste()}") 
        )
    },
    {
        "id": "SYSTEM_SHUTDOWN",
        "description": "Safely exits Harmony.",
        "triggers": ["exit", "stop system", "shutdown"],
        "action": lambda ing, *args: (
            ing.gui.add_message("SYSTEM", "Shutting down..."),
            QTimer.singleShot(1000, lambda: os._exit(0))
        )
    }
]