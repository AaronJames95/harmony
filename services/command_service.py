from core.event_bus import bus, Events

class CommandService:
    def __init__(self, database_service):
        self.db = database_service
        self.commands = []
        # Listen for raw text entering the system
        bus.subscribe(Events.TEXT_INGESTED, self.process_text)

    def register(self, cmd_id, triggers, action_func, description=""):
        """Plugins use this to register their voice triggers."""
        self.commands.append({
            "id": cmd_id,
            "triggers": triggers,
            "action": action_func,
            "description": description
        })

    def process_text(self, text):
        """Checks text against all registered triggers."""
        if not text: return
        clean_text = text.lower()
        
        # We look for the "Wake Words"
        trigger_aliases = ["shema", "shima", "shimah", "shemah", "shaman", "shama", "shuv"]
        if not any(alias in clean_text for alias in trigger_aliases): 
            return

        for cmd in self.commands:
            if any(t in clean_text for t in cmd["triggers"]):
                # Log it
                print(f"✨ Command Detected: {cmd['id']}")
                self.db.log_command(0, cmd['id'], clean_text)
                
                # Fire the action
                try:
                    cmd["action"](clean_text)
                    # Announce it to the system
                    bus.emit(Events.COMMAND_DETECTED, {"id": cmd['id'], "text": clean_text})
                except Exception as e:
                    print(f"❌ Command Error ({cmd['id']}): {e}")
                break