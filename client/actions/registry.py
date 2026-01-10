import webbrowser
import os
import pyperclip
from PyQt6.QtCore import QTimer
from actions import media_pipeline, writer

# COMMAND REGISTRY
COMMANDS = [
    {
        "id": "HELP_MENU",
        "description": "Lists all available commands and their descriptions.",
        "triggers": ["help", "commands", "what can you do"],
        "action": lambda ing, *args: (
            ing.gui.update_notification("HELP MENU OPENED", "#81d4fa"),
            ing.gui.add_message("SYSTEM", "<b>Available Commands:</b>"),
            # Uses .get() to provide a fallback if 'description' is missing
            [ing.gui.add_message("SYSTEM", f"• {cmd['id']}: {cmd.get('description', 'No description provided.')}") for cmd in COMMANDS]
        )
    },
    {
        "id": "HELLO_WORLD",
        "description": "Verify the Harmony trigger system is active.",
        "triggers": ["hello", "testing"],
        "action": lambda ing, *args: (
            ing.gui.add_message("SYSTEM", "👋🏾 Harmony is online and listening!"),
            ing.gui.update_notification("READY", "#69f0ae")
        )
    },
    {
        "id": "START_DEEP_STATE",
        "description": "Activates continuous recording mode.",
        "triggers": ["shema shema", "deep state", "start recording"],
        "action": lambda ing, *args: (
            ing.start_capture(),
            ing.gui.add_message("SYSTEM", "🌑 DEEP STATE ACTIVE: Continuous recording enabled."),
            ing.gui.update_notification("RECORDING", "#ff5252")
        )
    },
    {
        "id": "STOP_DEEP_STATE",
        "description": "Exits continuous mode and flushes to clipboard.",
        "triggers": ["shema shabbat", "stop recording", "shabbat"],
        "action": lambda ing, *args: (
            ing.stop_capture(),
            ing.gui.add_message("SYSTEM", "☀️ SHABBAT: Content moved to clipboard."),
            ing.gui.update_notification("COPIED", "#69f0ae")
        )
    },
    {
        "id": "OPEN_GEMINI",
        "description": "Opens Gemini. Use 'clipboard' flag for context.",
        "triggers": ["gemini", "jimini", "germany"],
        "action": lambda ing, *args: (
            ing.gui.add_message("SYSTEM", "Opening Gemini..."),
            ing.gui.update_notification("WEB ACTION", "#81d4fa"),
            webbrowser.open(f"https://gemini.google.com/app?q={pyperclip.paste()}") 
            if args and "clipboard" in args[0].lower() else 
            webbrowser.open("https://gemini.google.com/app")
        )
    },
    {
        "id": "EXPORT_LOGS",
        "description": "Generates a human-readable audit.",
        "triggers": ["log", "write", "writer"],
        "action": lambda ing, *args: (
            writer.export_history_to_text(ing),
            ing.gui.add_message("SYSTEM", "📄 Logs exported to text file."),
            ing.gui.update_notification("LOGS WRITTEN", "#b3e5fc")
        )
    },
    {
        "id": "MEDIA_PROCESS",
        "description": "Processes media files in clipboard.",
        "triggers": ["process", "transcription"],
        "action": lambda ing, *args: (
            ing.gui.add_message("SYSTEM", "🎬 Processing media..."),
            ing.gui.update_notification("PROCESSING", "#ffd740"),
            media_pipeline.run_pipeline(ing.db_path, ing.log_dir)
        )
    },
    {
        "id": "SYSTEM_SHUTDOWN",
        "description": "Safely exits the Harmony application.",
        "triggers": ["exit", "stop harmony", "shutdown"],
        "action": lambda ing, *args: (
            ing.gui.add_message("SYSTEM", "Shutting down..."),
            ing.gui.update_notification("OFFLINE", "#ff1744"),
            QTimer.singleShot(1000, lambda: os._exit(0))
        )
    }
]