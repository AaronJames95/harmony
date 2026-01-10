import webbrowser
import os
import pyperclip
from PyQt6.QtCore import QTimer
from actions import media_pipeline, writer
import threading
import requests
from datetime import datetime

# COMMAND REGISTRY
COMMANDS = [
    {
        "id": "HELP_MENU",
        "description": "Lists all available commands.",
        "triggers": ["help", "commands", "what can you do"],
        "action": lambda ing, *args: (
            ing.gui.update_notification("HELP MENU OPENED", "cyan"),
            # UPDATED: Just adds the message. Does NOT force the panel open.
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
        "action": lambda ing, *args: (
            ing.gui.toggle_panel("conversation")
        )
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
            ing.gui.add_message("SYSTEM", "🎙️ Deep State Active."),
            ing.gui.update_notification("RECORDING", "orange"),
            ing.start_deep_state()
        )
    },
    {
        "id": "FLUSH_BUFFER",
        "description": "Saves the current Deep State buffer.",
        "triggers": ["amen", "flush", "save that"],
        "action": lambda ing, *args: (
            ing.flush_buffer()
        )
    },
    {
        "id": "QUICK_NOTE",
        "description": "Saves a quick note.",
        "triggers": ["note", "capture"],
        "action": lambda ing, text: (
            ing.save_quick_note(text.split("note")[-1].strip()) if "note" in text else None,
            ing.gui.update_notification("NOTE SAVED", "cyan")
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