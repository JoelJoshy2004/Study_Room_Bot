
"""
Tiny CLI to list RMIT study room bookings for your friends.

Why this file exists:
- Helpful when developing/testing scraping without running the Discord bot.

How it finds project modules:
- This script lives in web_scraper/, not the repo root.
- We insert the repo root onto sys.path so `from bot import config`
  and `from rmit_booker import list_friend_bookings` work when you run:
      python web_scraper/cli_list_bookings.py ...

Typical usage:
    python web_scraper/cli_list_bookings.py \
        --room 5cc281bb-488c-445a-8893-cfd8d37add6a \
        --start 2025-08-03T14:00:00.000Z \
        --end   2025-08-10T13:59:00.000Z

Notes:
- `--storage` and `--friends` default to the paths defined in bot/config.py,
  so you usually don’t need to pass them explicitly.
"""

import argparse
import sys
import pathlib

# --- Make the repo root importable -------------------------------------------
# Resolve this file's absolute path → go up one directory to the repo root.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# If the root isn't already on sys.path, add it at position 0 (highest priority).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Now we can import our project modules as if we were running from the root.
from bot import config
from rmit_booker import list_friend_bookings  # main library function

def main() -> None:
    """
    Parse CLI args, fetch bookings for the specified room + time window,
    and print any matches (filtered by friends.json) in a readable format.
    """
    ap = argparse.ArgumentParser(
        description="List RMIT study room bookings for friends."
    )

    # Path to Playwright's saved browser session (cookies + localStorage).
    ap.add_argument(
        "--storage",
        default=str(config.STORAGE_STATE),
        help="Path to Playwright storage_state.json (default from bot/config.py)",
    )

    # Path to friends.json (contains IDs to match + field names to scan).
    ap.add_argument(
        "--friends",
        default=str(config.FRIENDS_JSON),
        help="Path to friends.json (default from bot/config.py)",
    )

    # UUID of the room/resource to query (see rooms.json for your list).
    ap.add_argument(
        "--room",
        required=True,
        help="Resource (room) UUID, e.g. 5cc2...add6a",
    )

    # UTC ISO start/end of the window to query (Z suffix required).
    ap.add_argument(
        "--start",
        required=True,
        help="UTC ISO start, e.g. 2025-08-03T14:00:00.000Z",
    )
    ap.add_argument(
        "--end",
        required=True,
        help="UTC ISO end, e.g. 2025-08-10T13:59:00.000Z",
    )

    args = ap.parse_args()

    from pathlib import Path

    # Call the high-level helper:
    # - reads the bearer token from storage_state.json
    # - calls the BookingRequests API for the given room + window
    # - filters by friends.json and returns human-friendly summaries
    summaries, total = list_friend_bookings(
        storage_path=Path(args.storage),
        friends_path=Path(args.friends),
        resource_id=args.room,
        start_iso=args.start,
        end_iso=args.end,
    )

    # Print each match in local (Australia/Melbourne) time.
    for s in summaries:
        print(
            f"{s['start_local']} → {s['end_local']} | "
            f"{s['title']} | {s['room']} | Owner:{s['owner']} | {s['email']}"
        )

    # A tiny footer so you know how many matches you got vs total bookings found.
    print(f"\nMatched {len(summaries)} of {total} bookings in that window.")

if __name__ == "__main__":
    main()
