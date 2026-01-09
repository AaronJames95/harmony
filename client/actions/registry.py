import webbrowser
import os
import pyperclip
from actions import media_pipeline, writer

# COMMAND REGISTRY
# id: Unique identifier for the command_logs table
# description: Human-readable explanation for documentation/help menus
# triggers: Phonetic variations; index 0 is used as the 'Primary Trigger'
# action: Uses *args to catch optional flags (like "clipboard") without breaking

COMMANDS = [
    {
        "id": "HELP_MENU",
        "description": "Lists all available commands and their descriptions.",
        "triggers": ["help", "commands", "what can you do"],
        "action": lambda ing, *args: (
            ing.gui.update_notification("HELP MENU OPENED", "#81d4fa"),
            ing.gui.add_message("SYSTEM", "Available Commands:"),
            [ing.gui.add_message("SYSTEM", f"• {cmd['id']}: {cmd['description']}") for cmd in COMMANDS]
        )
    },
    {
        "id": "HELLO_WORLD",
        "description": "A sanity check to verify the Harmony trigger system is active.",
        "triggers": ["hello", "testing"],
        "action": lambda ing, *args: (
            ing.gui.add_message("SYSTEM", "👋🏾 Harmony is online and listening!"),
            ing.gui.update_notification("READY", "#69f0ae")
        )
    },
    {
        "id": "START_DEEP_STATE",
        "description": "Activates continuous recording mode (No 0.3s silence flush).",
        "triggers": ["shema shema", "deep state", "start recording"],
        "action": lambda ing, *args: (
            ing.start_capture(),
            ing.gui.add_message("SYSTEM", "🌑 DEEP STATE ACTIVE: Continuous recording enabled."),
            ing.gui.update_notification("RECORDING", "#ff5252")
        )
    },
    {
        "id": "STOP_DEEP_STATE",
        "description": "Exits continuous mode and flushes the buffer to your clipboard.",
        "triggers": ["shema shabbat", "stop recording", "shabbat"],
        "action": lambda ing, *args: (
            ing.stop_capture(),
            ing.gui.add_message("SYSTEM", "☀️ SHABBAT: Recording ended. Content moved to clipboard."),
            ing.gui.update_notification("COPIED", "#69f0ae")
        )
    },
    {
        "id": "OPEN_GEMINI",
        "description": "Opens Gemini. Use 'clipboard' flag to include copied text.",
        "triggers": ["gemini", "jimini", "germany"],
        "action": lambda ing, *args: (
            ing.gui.add_message("SYSTEM", "Opening Gemini in your browser..."),
            ing.gui.update_notification("WEB ACTION", "#81d4fa"),
            webbrowser.open(f"https://gemini.google.com/app?q={pyperclip.paste()}") 
            if args and "clipboard" in args[0].lower() else 
            webbrowser.open("https://gemini.google.com/app")
        )
    },
    {
        "id": "EXPORT_LOGS",
        "description": "Generates a human-readable audit of speech and actions.",
        "triggers": ["log", "write", "writer"],
        "action": lambda ing, *args: (
            writer.export_history_to_text(ing),
            ing.gui.add_message("SYSTEM", "📄 Logs exported to human_readable_history.txt"),
            ing.gui.update_notification("LOGS WRITTEN", "#b3e5fc")
        )
    },
    {
        "id": "MEDIA_PROCESS",
        "description": "Extracts audio from video or processes audio files in clipboard.",
        "triggers": ["process", "transcription"],
        "action": lambda ing, *args: (
            ing.gui.add_message("SYSTEM", "🎬 Processing media from clipboard..."),
            ing.gui.update_notification("PROCESSING", "#ffd740"),
            media_pipeline.run_pipeline(ing.db_path, ing.log_dir)
        )
    },
    {
        "id": "SYSTEM_SHUTDOWN",
        "description": "Safely exits the Harmony application.",
        "triggers": ["exit", "stop harmony", "shutdown"],
        "action": lambda ing, *args: (
            ing.gui.add_message("SYSTEM", "Shutting down... Goodbye."),
            ing.gui.update_notification("OFFLINE", "#ff1744"),
            QTimer.singleShot(1000, lambda: os._exit(0)) # Brief delay so you see the message
        )
    }
]