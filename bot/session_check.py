# bot/session_check.py
"""
Validate the saved session is still good by:
- extracting bearer token from storage_state.json
- checking the JWT exp time (no verification) to avoid obviously-dead tokens
"""
import base64, json, time
from bot import config
from rmit_booker import load_bearer_from_storage

def _b64url_decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())

def token_is_fresh() -> bool:
    try:
        token = load_bearer_from_storage(config.STORAGE_STATE)
    except Exception:
        return False
    try:
        parts = token.split(".")
        payload = json.loads(_b64url_decode(parts[1]).decode())
        exp = int(payload.get("exp", 0))
        # consider fresh if > 5 minutes from now
        return exp > int(time.time()) + 300
    except Exception:
        # if we can't parse, let scrape be the judge later
        return True
