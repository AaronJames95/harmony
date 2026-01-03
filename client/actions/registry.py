import webbrowser
import os
from actions import media_pipeline, writer

# The Registry acts as a centralized "Switch Board"
COMMANDS = [
    {
        "id": "EXPORT_LOGS",
        "triggers": ["write", "writes", "writer"],
        "action": lambda db, log: writer.export_history_to_text(db, log)
    },
    {
        "id": "OPEN_GEMINI",
        "triggers": ["gemini", "jimini", "germany"],
        "action": lambda db, log: webbrowser.open("https://gemini.google.com/app")
    },
    {
        "id": "MEDIA_PROCESS",
        "triggers": ["process", "transcription", "transcribe"],
        "action": lambda db, log: media_pipeline.run_pipeline()
    },
    {
        "id": "SYSTEM_SHUTDOWN",
        "triggers": ["shutdown", "stop", "exit"],
        "action": lambda db, log: os._exit(0)
    }
]