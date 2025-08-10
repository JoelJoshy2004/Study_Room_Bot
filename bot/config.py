
from pathlib import Path

# Folders
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SECRETS = ROOT / ".secrets"
JSONS = ROOT / "jsons"  
DATA.mkdir(exist_ok=True)
SECRETS.mkdir(exist_ok=True)

# Files
STORAGE_STATE = SECRETS / "storage_state.json"       # created by Playwright
FRIENDS_JSON = JSONS / "friends.json"             # {"ids":[...], "match_fields":[...]}
IGNORE_ROOMS_JSON = JSONS / "ignore_rooms.json"       # {"rooms":[ "080.10.04", ... ]}
ROOMS_JSON = JSONS / "rooms.json"                   # [{"id":"<uuid>", "code":"010.05.68", "name":"Swanston Group Study Room"}, ...]
BIND_JSON = DATA / "bind.json"                       # {"channel_id": 12345}
BOOKINGS_JSON = DATA / "bookings.json"               # last scrape cache
CAL_IMG = DATA / "calendar.png"                      # last calendar render

# API defaults
DEFAULT_WINDOW_DAYS = 7
