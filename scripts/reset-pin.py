"""Reset the kiosk PIN. Run inside the container:
docker exec morsl python scripts/reset-pin.py
"""

import json
from pathlib import Path

settings_path = Path("data/settings.json")
if settings_path.exists():
    settings = json.loads(settings_path.read_text())
else:
    settings = {}

settings["kiosk_pin"] = ""
settings["admin_pin_enabled"] = False
settings["kiosk_pin_enabled"] = False
settings_path.write_text(json.dumps(settings, indent=2))

print("PIN cleared. Admin access is now unrestricted.")
print("Restart the container, then set a new PIN from admin settings.")
