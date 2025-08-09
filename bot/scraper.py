# bot/scraper.py
from __future__ import annotations
import datetime as dt
from typing import List, Dict, Tuple
from pathlib import Path

from rmit_booker import list_friend_bookings
from bot import config
from bot.datastore import load_json, save_json

def week_bounds_utc(anchor: dt.datetime | None = None) -> Tuple[str, str, dt.date]:
    if anchor is None:
        anchor = dt.datetime.utcnow()
    monday = (anchor - dt.timedelta(days=anchor.weekday())).date()
    start = dt.datetime.combine(monday, dt.time.min, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=7) - dt.timedelta(seconds=1)
    return start.isoformat().replace("+00:00","Z"), end.isoformat().replace("+00:00","Z"), monday

def scrape_week() -> Tuple[List[Dict], List[Dict], List[str], str]:
    rooms = load_json(config.ROOMS_JSON, [])
    ignore = set(load_json(config.IGNORE_ROOMS_JSON, {"rooms": []}).get("rooms", []))
    if not rooms:
        raise RuntimeError("rooms.json is empty. Add room UUIDs + codes first.")

    start_iso, end_iso, monday = week_bounds_utc()
    all_summaries: List[Dict] = []

    for r in rooms:
        rid = r["id"]
        summaries, _ = list_friend_bookings(
            storage_path=config.STORAGE_STATE,
            friends_path=config.FRIENDS_JSON,
            resource_id=rid,
            start_iso=start_iso,
            end_iso=end_iso,
        )
        for s in summaries:
            s.setdefault("room", r.get("name") or r.get("code") or "?")
            s.setdefault("room_code", r.get("code"))
            all_summaries.append(s)

    # Build events + warnings
    events: List[Dict] = []
    warns: List[str] = []
    from datetime import datetime

    for s in all_summaries:
        start_local = datetime.strptime(s["start_local"], "%a %d %b %Y %H:%M")
        end_local   = datetime.strptime(s["end_local"], "%a %d %b %Y %H:%M")

        day_idx = start_local.weekday()
        start_hour = start_local.hour + start_local.minute/60
        end_hour   = end_local.hour + end_local.minute/60

        ignored = (s.get("room_code") in ignore)
        # Label should be time-only for the calendar rendering
        label = f"{start_local.strftime('%H:%M')}–{end_local.strftime('%H:%M')}"

        events.append({
            "day_index": day_idx,
            "start_hour": start_hour,
            "end_hour": end_hour,
            "label": label,
            "room_code": s.get("room_code"),
            "ignored": ignored,
        })

        if ignored:
            warns.append(
                f"⚠️ IGNORE-ROOM: {s.get('owner')} booked {s.get('room_code')} ({s['room']}) "
                f"{start_local.strftime('%a %d %b %H:%M')}–{end_local.strftime('%H:%M')}"
            )

    save_json(config.BOOKINGS_JSON, {"summaries": all_summaries, "week": str(monday)})
    title = f"Week of {monday.strftime('%d %b %Y')}"
    return all_summaries, events, warns, title
