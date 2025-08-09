"""
--------------------
Simple command-line entrypoint to list friends' bookings for one room
within a given UTC time window.

Usage example:
    python cli_list_bookings.py \
      --room 5cc281bb-488c-445a-8893-cfd8d37add6a \
      --start 2025-08-03T14:00:00.000Z \
      --end   2025-08-10T13:59:00.000Z
"""

import argparse
from pathlib import Path
from rmit_booker import list_friend_bookings

def main() -> None:
    ap = argparse.ArgumentParser(description="List RMIT study room bookings for friends.")
    ap.add_argument(
        "--storage",
        default=".secrets/storage_state.json",
        help="Path to Playwright storage_state.json (contains your session; NOT committed)."
    )
    ap.add_argument(
        "--friends",
        default="friends.json",
        help="Path to friends.json (IDs + which booking fields to scan)."
    )
    ap.add_argument("--room", required=True, help="Resource (room) UUID")
    ap.add_argument("--start", required=True, help="UTC ISO start (e.g. 2025-08-08T22:00:00.000Z)")
    ap.add_argument("--end",   required=True, help="UTC ISO end   (e.g. 2025-08-09T09:59:00.000Z)")
    args = ap.parse_args()

    storage_path = Path(args.storage)
    friends_path = Path(args.friends)

    summaries, total = list_friend_bookings(
        storage_path=storage_path,
        friends_path=friends_path,
        resource_id=args.room,
        start_iso=args.start,
        end_iso=args.end,
    )

    # Pretty-print each match in local time (AU/Melbourne)
    for s in summaries:
        print(f"{s['start_local']} → {s['end_local']} | {s['title']} | {s['room']} | Owner:{s['owner']} | {s['email']}")
    print(f"\nMatched {len(summaries)} of {total} bookings in that window.")

if __name__ == "__main__":
    main()
