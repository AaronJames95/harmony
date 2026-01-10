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
        "id": "HUD_ALIGN_LEFT",
        "description": "Moves conversation panel to the left.",
        "triggers": ["shema left", "move left", "align left"],
        "action": lambda ing, *args: ing.gui.set_alignment("left")
    },
    {
        "id": "HUD_ALIGN_RIGHT",
        "description": "Moves conversation panel to the right.",
        "triggers": ["shema right", "move right", "align right"],
        "action": lambda ing, *args: ing.gui.set_alignment("right")
    },
    {
        "id": "HUD_ALIGN_CENTER",
        "description": "Moves conversation panel to the center.",
        "triggers": ["shema center", "move center", "align center"],
        "action": lambda ing, *args: ing.gui.set_alignment("center")
    },
    {
        # --- THE RESTORED MEDIA PIPELINE ---
        "id": "PROCESS_AUDIO",
        "description": "Uploads clipboard files (Video/Audio) to Harmony Server.",
        "triggers": ["process audio", "transcribe", "ingest file", "process media"],
        "action": lambda ing, *args: ing.run_media_pipeline()
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
        "id": "QUICK_NOTE",
        "description": "Saves spoken text OR clipboard to Obsidian.",
        "triggers": ["note", "capture"], 
        "action": lambda ing, text: (
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
        "triggers": ["exit", "stop system", "shutdown", "shut down"],
        "action": lambda ing, *args: (
            ing.gui.add_message("SYSTEM", "Shutting down..."),
            QTimer.singleShot(1000, lambda: os._exit(0))
        )
    }
]