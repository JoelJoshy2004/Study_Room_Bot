"""
Silent token refresh using Playwright.

- Reads your saved .secrets/storage_state.json (cookies + localStorage)
- Opens the Resource Booker app headlessly
- Lets the SPA perform its usual silent sign-in
- Captures the updated localStorage + cookies back to storage_state.json
"""

from pathlib import Path
import base64, json, time

from bot import config

# Import Playwright only when needed so the bot can still run without it
def _ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except Exception:
        return False

def _b64url_decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    import base64 as b64
    return b64.urlsafe_b64decode(s.encode())

def minutes_remaining_from_token(token: str) -> int:
    """
    Parse JWT (no signature verification) and return minutes until exp.
    If parsing fails, return a large positive number to avoid false negatives.
    """
    try:
        parts = token.split(".")
        payload = json.loads(_b64url_decode(parts[1]).decode())
        exp = int(payload.get("exp", 0))
        return max(0, int((exp - time.time()) / 60))
    except Exception:
        return 9999

def get_current_token() -> str | None:
    """Read access_token from storage_state.json localStorage."""
    p = config.STORAGE_STATE
    if not p.exists():
        return None
    state = json.loads(p.read_text())
    for o in state.get("origins", []):
        if o.get("origin") == "https://resourcebooker.rmit.edu.au":
            for ls in o.get("localStorage", []):
                if ls.get("name") == "scientia-session-authorization":
                    try:
                        return json.loads(ls["value"])["access_token"]
                    except Exception:
                        return None
    return None

def refresh_with_playwright(timeout_ms: int = 15000) -> bool:
    """
    Launch Chromium headless, load the app, and save updated storage to disk.
    Returns True if storage was saved (likely refreshed), False otherwise.
    """
    if not _ensure_playwright():
        raise RuntimeError("playwright is not installed. `pip install playwright && playwright install chromium`")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        # Load existing storage (cookies + localStorage)
        ctx = browser.new_context(storage_state=str(config.STORAGE_STATE))
        page = ctx.new_page()
        page.goto("https://resourcebooker.rmit.edu.au/app/booking-types", wait_until="networkidle", timeout=timeout_ms)

        # Give the SPA a moment to perform silent sign-in and populate localStorage
        page.wait_for_timeout(1500)

        # Optionally, fetch token from localStorage for logging/debug
        # token_json = page.evaluate("() => localStorage.getItem('scientia-session-authorization')")

        # Persist the new storage state (this updates localStorage + cookies on disk)
        ctx.storage_state(path=str(config.STORAGE_STATE))
        browser.close()
        return True
