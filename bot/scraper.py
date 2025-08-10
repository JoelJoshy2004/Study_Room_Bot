
"""
Scraper that now:
- Picks the *current* workweek if today is Mon–Fri,
  otherwise the *next* workweek if run on Sat/Sun.
- Queries only Mon 00:00:00 -> Fri 23:59:59 (UTC).
- Builds events with day_index 0..4 (Mon..Fri) and skips weekends.
- Labels are time-only (no student number).
"""

from __future__ import annotations
import datetime as dt
from typing import List, Dict, Tuple

from web_scraper.rmit_booker import list_friend_bookings
from bot import config
from bot.datastore import load_json, save_json
from datetime import datetime, timedelta


def workweek_bounds_utc(anchor: dt.datetime | None = None) -> Tuple[str, str, dt.date]:
    """
    Return (start_iso_Z, end_iso_Z, monday_date) for the workweek.

    - If anchor is Mon–Fri -> that week's Monday–Friday.
    - If anchor is Sat/Sun -> *next* week's Monday–Friday.

    All times are UTC ISO strings with 'Z'.
    """
    if anchor is None:
        anchor = dt.datetime.utcnow()

    wd = anchor.weekday()  # Mon=0 .. Sun=6
    if wd >= 5:
        # Weekend -> jump to *next* Monday
        days_to_next_mon = 7 - wd
        monday = (anchor + dt.timedelta(days=days_to_next_mon)).date()
    else:
        # Weekday -> this week's Monday
        monday = (anchor - dt.timedelta(days=wd)).date()

    start = dt.datetime.combine(monday, dt.time.min, tzinfo=dt.timezone.utc)          # Mon 00:00:00
    end   = start + dt.timedelta(days=5) - dt.timedelta(seconds=1)                    # Fri 23:59:59
    return start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z"), monday


def _format_week_range(monday_date: dt.date) -> str:
    """
    Pretty range like:
      same month/year:        11–15 Aug 2025
      different month:        29 Aug – 02 Sep 2025
      different year (NY wk): 30 Dec 2025 – 03 Jan 2026
    """
    fri = monday_date + dt.timedelta(days=4)

    def d(dte):  # day without leading zero
        return dte.strftime("%-d") if hasattr(dte, "strftime") else str(dte.day)

    # Windows doesn't support %-d; fallback:
    try:
        d_start = monday_date.strftime("%-d")
        d_end   = fri.strftime("%-d")
    except ValueError:
        d_start = monday_date.strftime("%#d")
        d_end   = fri.strftime("%#d")

    if monday_date.year == fri.year:
        if monday_date.month == fri.month:
            # 11–15 Aug 2025
            return f"{d_start}–{d_end} {fri.strftime('%b %Y')}"
        else:
            # 29 Aug – 02 Sep 2025
            return f"{d_start} {monday_date.strftime('%b')} – {d_end} {fri.strftime('%b %Y')}"
    else:
        # 30 Dec 2025 – 03 Jan 2026
        return f"{d_start} {monday_date.strftime('%b %Y')} – {d_end} {fri.strftime('%b %Y')}"


def scrape_week() -> Tuple[List[Dict], List[Dict], List[str], str]:
    """
    Scrape the chosen workweek and return:
      summaries  : list of friend bookings (summaries)
      events     : list for calendar rendering (Mon–Fri only)
      warnings   : any red-flag ignore-room warnings
      title      : e.g., "Week of 04 Aug 2025"

    Side effect:
      writes data/bookings.json cache.
    """
    rooms = load_json(config.ROOMS_JSON, [])
    ignore = set(load_json(config.IGNORE_ROOMS_JSON, {"rooms": []}).get("rooms", []))
    if not rooms:
        raise RuntimeError("rooms.json is empty. Add room UUIDs + codes first.")

    start_iso, end_iso, monday = workweek_bounds_utc()

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
        # attach room metadata
        for s in summaries:
            s.setdefault("room", r.get("name") or r.get("code") or "?")
            s.setdefault("room_code", r.get("code"))
            all_summaries.append(s)

    # Build events (Mon–Fri only) + warnings
    events: List[Dict] = []
    warns: List[str] = []
    from datetime import datetime

    for s in all_summaries:
        start_local = datetime.strptime(s["start_local"], "%a %d %b %Y %H:%M")
        end_local   = datetime.strptime(s["end_local"], "%a %d %b %Y %H:%M")

        day_idx = start_local.weekday()  # Mon=0..Sun=6
        if day_idx >= 5:
            # Weekend -> skip from the calendar
            continue

        start_hour = start_local.hour + start_local.minute / 60
        end_hour   = end_local.hour + end_local.minute / 60

        ignored = (s.get("room_code") in ignore)
        label   = f"{start_local.strftime('%H:%M')}–{end_local.strftime('%H:%M')}"  # time-only

        events.append({
            "day_index": day_idx,  # 0..4 only now
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

    # Save cache + title
    save_json(config.BOOKINGS_JSON, {"summaries": all_summaries, "week": str(monday)})
    pretty_range = _format_week_range(monday)
    title = f"Week of {pretty_range}"
    return all_summaries, events, warns, title
