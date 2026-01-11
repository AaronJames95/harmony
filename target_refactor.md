Harmony/
├── main.py                  # Entry point (Bootstrapper)
├── config.yaml              # All those hardcoded IPs and paths go here
├── core/                    # THE ENGINE (Stable, rarely changes)
│   ├── event_bus.py         # The "Nervous System" (Pub/Sub)
│   ├── service_locator.py   # Registry for Database, Network, etc.
│   ├── interfaces.py        # Abstract Base Classes (Rules for Plugins)
│   └── logger.py            # Centralized logging
├── services/                # SHARED UTILITIES (Used by multiple plugins)
│   ├── database_service.py  # SQLite logic extracted from Ingestor
│   ├── network_service.py   # Requests/API logic
│   ├── audio_service.py     # Whisper/VAD logic
│   └── gui_service.py       # Wrapper around your PyQt windows
├── plugins/                 # THE "MODS" (Add/Remove these freely)
│   ├── system_plugin.py     # Shutdown, Restart, Help
│   ├── obsidian_plugin.py   # Quick Note logic
│   ├── media_plugin.py      # The Media Pipeline logic
│   └── deep_state_plugin.py # The Dictation buffer logic
└── ui/                      # VISUALS (Dumb display logic only)
    ├── styles.py            # CSS definitions
    └── windows/             # Your actual PyQt classes
        ├── overlay.py
        ├── hud.py
        └── conversation.py