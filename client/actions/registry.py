import webbrowser
import os
import pyperclip
from actions import media_pipeline, writer

# COMMAND REGISTRY
# id: Unique identifier for the command_logs table
# description: Human-readable explanation for documentation/help menus
# triggers: Phonetic variations captured by the speech-to-text engine
# action: Uses *args to catch optional flags (like "clipboard") without breaking

COMMANDS = [
    {
        "id": "HELLO_WORLD",
        "description": "A sanity check to verify the Harmony trigger system is active.",
        "triggers": ["hello", "testing"],
        "action": lambda ing, *args: print("👋🏾 Harmony is online and listening!")
    },
    {
        "id": "START_DEEP_STATE",
        "description": "Activates continuous recording mode (No 0.3s silence flush).",
        "triggers": ["shema shema", "deep state", "start recording"],
        "action": lambda ing, *args: ing.start_capture()
    },
    {
        "id": "STOP_DEEP_STATE",
        "description": "Exits continuous mode and flushes the massive buffer to your clipboard.",
        "triggers": ["shema shabbat", "stop recording", "shabbat"],
        "action": lambda ing, *args: ing.stop_capture()
    },
    {
        "id": "OPEN_GEMINI",
        "description": "Opens Gemini. Use 'clipboard' flag to include copied text.",
        "triggers": ["gemini", "jimini", "germany"],
        "action": lambda ing, *args: (
            webbrowser.open(f"https://gemini.google.com/app?q={pyperclip.paste()}") 
            if args and "clipboard" in args[0].lower() else 
            webbrowser.open("https://gemini.google.com/app")
        )
    },
    {
        "id": "EXPORT_LOGS",
        "description": "Generates a chronological audit of speech and actions.",
        "triggers": ["log", "write", "writer"],
        "action": lambda ing, *args: writer.export_history_to_text(ing)
    },
    {
        "id": "MEDIA_PROCESS",
        "description": "Extracts audio from video or processes audio files in clipboard.",
        "triggers": ["process", "transcription"],
        "action": lambda ing, *args: media_pipeline.run_pipeline(ing.db_path, ing.log_dir)
    },
    {
        "id": "SYSTEM_SHUTDOWN",
        "description": "Safely exits the Harmony application.",
        "triggers": ["sheol", "exit", "stop harmony", "shutdown"],
        "action": lambda ing, *args: os._exit(0)
    }
]