import webbrowser
import os
from actions import media_pipeline, writer

# Define the data structure for all Harmony capabilities
COMMANDS = [
    {
        "id": "EXPORT_LOGS",
        "description": "Syncs the SQLite DB to a human-readable text file.",
        "triggers": ["write", "writes", "writer", "right"],
        "action": lambda db, log: writer.export_history_to_text(db, log)
    },
    {
        "id": "OPEN_GEMINI",
        "description": "Opens the Gemini AI web interface.",
        "triggers": ["gemini", "jimini", "germany", "jiminy"],
        "action": lambda db, log: webbrowser.open("https://gemini.google.com/app")
    },
    {
        "id": "MEDIA_PROCESS",
        "description": "Processes video/audio files from the clipboard.",
        "triggers": ["process", "transcription", "transcribe"],
        "action": lambda db, log: media_pipeline.run_pipeline(db, log)
    },
    {
        "id": "SYSTEM_SHUTDOWN",
        "description": "Safely exits the Harmony client.",
        "triggers": ["shutdown", "stop", "exit"],
        "action": lambda db, log: os._exit(0)
    }
]