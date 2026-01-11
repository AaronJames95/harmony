class HarmonyPlugin:
    """Every feature must wear this uniform."""
    def __init__(self, event_bus, services):
        self.bus = event_bus
        self.services = services

    def register(self):
        """Tell the system what you listen for."""
        pass