import os
import pyperclip
from datetime import datetime
from core.event_bus import bus, Events

class ObsidianPlugin:
    def __init__(self):
        # ⚠️ HARDCODED PATH (From your previous ingestor.py)
        # In the future, move this to config.yaml
        self.qc_path = r"C:\Users\AColl\OneDrive\One Drive before 11_16_2023\Documents\vault-alpha\💡 Quick Capture.md"

    def register(self, command_service):
        command_service.register(
            "QUICK_NOTE", 
            ["note", "capture", "quick note"], 
            self.handle_note,
            "Appends text (or clipboard) to Obsidian."
        )

    def handle_note(self, text):
        """Decides if we are saving voice text or clipboard text."""
        clean_text = text.lower()
        
        # Check for "Clipboard" override
        if "clipboard" in clean_text:
            content = pyperclip.paste()
            source = "Clipboard"
        else:
            # Strip the trigger word ("Note...") to get the actual content
            content = text
            for trigger in ["note", "capture", "quick note"]:
                if trigger in clean_text:
                    # Split on the first occurrence and take the rest
                    parts = clean_text.split(trigger, 1)
                    if len(parts) > 1:
                        content = parts[1].strip()
                    break
            source = "Voice"

        if content:
            self.save_to_file(content, source)

    def save_to_file(self, content, source):
        if not os.path.exists(self.qc_path):
            bus.emit(Events.LOG_MESSAGE, f"❌ Error: QC File not found at {self.qc_path}")
            return

        timestamp = datetime.now().strftime('%H:%M')
        bullet_line = f"\n- [{timestamp}] {content}"

        try:
            with open(self.qc_path, "a", encoding="utf-8") as f:
                f.write(bullet_line)
            
            # Notify User
            bus.emit(Events.STATUS_CHANGED, {"text": "CAPTURED", "color": "cyan"})
            bus.emit(Events.LOG_MESSAGE, f"📝 <b>{source} Note Saved:</b><br>\"{content}\"")
            
        except Exception as e:
            bus.emit(Events.LOG_MESSAGE, f"❌ Write Error: {e}")