"""
---------------
Tiny library to authenticate against RMIT Resource Booker using a *browser*
session exported by Playwright (storage_state.json), call the hidden bookings
API, then filter + summarise bookings for a set of friends.

Security notes:
- We never store the raw Bearer token on disk; we read it on demand from
  `.secrets/storage_state.json` and keep it in memory for the single request.
- If the API returns 401, your session token has expired; refresh it by
  re-running your Playwright login capture.

Assumptions:
- Your storage_state.json contains localStorage key
  "scientia-session-authorization" with {"access_token": "..."}.
- The bookings endpoint returns either a list[...] or {"items":[...]}.
- Booking objects contain start/end and some fields that can identify the user
  (Owner, BookerEmailAddress, etc.). You can control which fields to match
  in friends.json -> "match_fields".
"""

from __future__ import annotations

import json
import requests
import datetime as dt
from dateutil import tz
from pathlib import Path
from urllib.parse import urlencode, urlunparse
from typing import Iterable, Tuple, Dict, Any, List

# ---- Constants ---------------------------------------------------------------

# Convert times to Melbourne local time for printing
MELB_TZ = tz.gettz("Australia/Melbourne")

# API base (host lives here; path/query are built per request)
API_HOST = "cyon-syd-v4-api-d1-03.azurewebsites.net"


# ---- Auth / headers (from storage_state.json) --------------------------------

def load_bearer_from_storage(storage_path: Path) -> str:
    """
    Extract the short-lived Bearer token from Playwright's storage_state.json.

    storage_path: Path to .secrets/storage_state.json produced by Playwright.
    returns: raw access_token string (NOT persisted anywhere else).

    Raises RuntimeError with helpful messages if the structure isn't found.
    """
    state = json.loads(storage_path.read_text(encoding="utf-8"))

    # Find the origin block that corresponds to the Resource Booker single-page app
    rb_origin = "https://resourcebooker.rmit.edu.au"
    origin_obj = next((o for o in state.get("origins", []) if o.get("origin") == rb_origin), None)
    if not origin_obj:
        raise RuntimeError(f"Origin {rb_origin} not found in storage state.")

    # In that origin, localStorage should hold a JSON blob with the token
    ls = origin_obj.get("localStorage", [])
    auth_item = next((x for x in ls if x.get("name") == "scientia-session-authorization"), None)
    if not auth_item:
        raise RuntimeError("localStorage key 'scientia-session-authorization' not found.")

    # Parse the JSON and pull out the token
    try:
        auth_json = json.loads(auth_item["value"])
        token = auth_json["access_token"]
        if not token:
            raise KeyError("access_token empty")
        return token
    except Exception as e:
        raise RuntimeError(f"Failed to parse access_token from storage_state.json: {e}")


def build_headers_from_storage(storage_path: Path) -> Dict[str, str]:
    """
    Build minimal request headers needed to call the API from server-side code.
    We keep this minimal to avoid leaking browser-specific headers.

    returns: {"Authorization": "Bearer ...", "Accept": "application/json"}
    """
    token = load_bearer_from_storage(storage_path)
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


# ---- URL builder -------------------------------------------------------------

def build_booking_url(resource_id: str, start_iso: str, end_iso: str) -> str:
    """
    Build the full BookingRequests URL for one resource in a date range.

    resource_id: room UUID (string from DevTools -> the /Resources/<UUID>/ call)
    start_iso / end_iso: UTC ISO strings with 'Z', e.g. "2025-08-08T22:00:00.000Z"

    returns: fully qualified URL (https://.../api/Resources/<id>/BookingRequests?...).
    """
    query = urlencode({
        "StartDate": start_iso,
        "EndDate": end_iso,
        "CheckSplitPermissions": "true",
    })
    path = f"/api/Resources/{resource_id}/BookingRequests"
    return urlunparse(("https", API_HOST, path, "", query, ""))


# ---- Fetch -------------------------------------------------------------------

def fetch_bookings(headers: Dict[str, str], url: str) -> List[Dict[str, Any]]:
    """
    Call the BookingRequests endpoint and normalise the response to a list.

    headers: dict from build_headers_from_storage(...)
    url    : string from build_booking_url(...)

    returns: list of booking dicts (possibly empty).
    raises : RuntimeError on non-200 with the first 500 chars of the response.
    """
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        preview = r.text[:500]
        raise RuntimeError(f"HTTP {r.status_code}: {preview}")
    payload = r.json()
    # Some endpoints return { items: [...] }, others return [...]. Handle both.
    return payload if isinstance(payload, list) else payload.get("items", [])


# ---- Friends / matching ------------------------------------------------------

def load_friends(friends_path: Path) -> Tuple[set[str], List[str]]:
    """
    Load matching config from friends.json.

    Expected schema:
    {
      "ids": ["s4166573", "friend@example.com"],
      "match_fields": ["Owner", "BookerEmailAddress", "BookerName", "Reference"]
    }

    returns:
      (friend_ids_lowercased, match_fields_list)
    """
    data = json.loads(friends_path.read_text(encoding="utf-8"))
    ids = set(x.lower() for x in data.get("ids", []))
    # Which fields to concatenate and search for friend IDs (case-insensitive)
    fields = data.get("match_fields", ["Owner", "BookerEmailAddress", "BookerName", "Reference"])
    return ids, fields


def is_friend_booking(booking: Dict[str, Any], friend_ids: set[str], match_fields: List[str]) -> bool:
    """
    Decide whether a booking belongs to any of our friends.

    Strategy:
    1) Build a small "haystack" string from configured fields.
    2) If that misses (API changed?), fall back to scanning the full JSON string.

    returns: True if any friend id is found, else False.
    """
    # Build a quick string from the primary fields
    hay = " ".join(str(booking.get(f, "")) for f in match_fields).lower()
    if any(fid in hay for fid in friend_ids):
        return True

    # Fallback: slow path, scan the entire object as JSON
    hay_all = json.dumps(booking).lower()
    return any(fid in hay_all for fid in friend_ids)


# ---- Formatting helpers ------------------------------------------------------

def parse_dt_any(booking: Dict[str, Any], key_candidates: List[str]) -> dt.datetime:
    """
    Find and parse the first present ISO datetime field in `booking`.

    key_candidates: ordered preference, e.g. ["StartDateTime", "startDate", "StartDate"]

    returns: timezone-aware datetime (Python) for the first matching key.
    raises : KeyError if none of the keys are present.
    """
    for k in key_candidates:
        if k in booking and booking[k]:
            val = booking[k]
            # Normalise 'Z' (Zulu/UTC) to +00:00 for Python's fromisoformat
            iso = val.replace("Z", "+00:00") if isinstance(val, str) else str(val)
            try:
                return dt.datetime.fromisoformat(iso)
            except Exception:
                # Try the next candidate if parsing failed
                pass
    raise KeyError(f"None of the datetime keys present: {key_candidates}")


def fmt_local(aware_dt: dt.datetime) -> str:
    """Format an aware UTC datetime into AU/Melbourne local time for display."""
    return aware_dt.astimezone(MELB_TZ).strftime("%a %d %b %Y %H:%M")


def extract_room_name(booking: Dict[str, Any]) -> str:
    """
    Try a few common places bookings store the room name.
    """
    resources = booking.get("Resources") or []
    if resources and isinstance(resources, list):
        return (resources[0].get("Name")
                or resources[0].get("name")
                or "?")
    return booking.get("ResourceName") or "?"


def summarize_booking(booking: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a compact, safe-to-print summary from a raw booking object.
    """
    start = parse_dt_any(booking, ["StartDateTime", "startDate", "StartDate"])
    end   = parse_dt_any(booking, ["EndDateTime", "endDate", "EndDate"])
    return {
        "title": booking.get("Name") or booking.get("Title") or "Booking",
        "room": extract_room_name(booking),
        "start_local": fmt_local(start),
        "end_local": fmt_local(end),
        "owner": booking.get("Owner"),
        "email": booking.get("BookerEmailAddress"),
    }


# ---- High-level utility ------------------------------------------------------

def list_friend_bookings(
    storage_path: Path,
    friends_path: Path,
    resource_id: str,
    start_iso: str,
    end_iso: str,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    One-shot helper: authenticate (via storage), fetch, filter, and summarise.

    returns:
      (summaries, total_count)
      - summaries: list of dicts safe to print/post
      - total_count: total bookings returned by the API (before filtering)
    """
    # Build minimal headers from saved browser session
    headers = build_headers_from_storage(storage_path)

    # Construct the endpoint URL for the given room + time window
    url = build_booking_url(resource_id, start_iso, end_iso)

    # Call API
    bookings = fetch_bookings(headers, url)

    # Load matching config and filter
    friend_ids, match_fields = load_friends(friends_path)
    matches = [b for b in bookings if is_friend_booking(b, friend_ids, match_fields)]

    # Return human-friendly summaries + stats
    return [summarize_booking(b) for b in matches], len(bookings)
