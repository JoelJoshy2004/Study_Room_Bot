"""
------------------
Very lightweight sanity checks. These are *not* full unit tests—just quick
confidence checks that:
- we can parse the token (if storage_state.json exists),
- the URL builder encodes correctly,
- friend matching + summarisation behave as expected on a synthetic booking.
"""

from pathlib import Path
from web_scraper.rmit_booker import (
    load_bearer_from_storage,
    build_booking_url,
    is_friend_booking,
    summarize_booking,
)

def test_token_extraction() -> None:
    """
    Try to pull the token out of .secrets/storage_state.json.
    Skips gracefully if the file doesn't exist (so CI won't fail).
    """
    p = Path(".secrets/storage_state.json")
    if not p.exists():
        print("SKIP: .secrets/storage_state.json not found. (Login with Playwright first.)")
        return
    try:
        token = load_bearer_from_storage(p)
        print("OK: extracted token (length):", len(token))
    except Exception as e:
        print("FAIL: token extraction ->", e)

def test_url_builder() -> None:
    """
    Ensure the URL builder encodes path and query parameters as expected.
    """
    url = build_booking_url(
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "2025-08-08T22:00:00.000Z",
        "2025-08-09T09:59:00.000Z"
    )
    assert "Resources/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/BookingRequests" in url
    assert "StartDate=2025-08-08T22%3A00%3A00.000Z" in url
    assert "EndDate=2025-08-09T09%3A59%3A00.000Z" in url
    print("OK: URL builder")

def test_friend_match_and_summary() -> None:
    """
    Run a synthetic booking through matching + summarisation.
    This doesn't hit the network.
    """
    booking = {
        "Name": "Study Room Booking",
        "Owner": "s4166573",  # one of our friend IDs
        "BookerEmailAddress": "s4166573@student.rmit.edu.au",
        "Resources": [{"Name": "Swanston Library Rm 3.12"}],
        "StartDateTime": "2025-08-08T22:00:00.000Z",
        "EndDateTime": "2025-08-08T23:00:00.000Z"
    }
    friends = {"s4166573", "s9999999"}
    fields = ["Owner", "BookerEmailAddress", "BookerName", "Reference"]

    assert is_friend_booking(booking, friends, fields) is True

    summary = summarize_booking(booking)
    assert "start_local" in summary and "end_local" in summary
    assert summary["room"] == "Swanston Library Rm 3.12"
    print("OK: friend match + summary")

if __name__ == "__main__":
    test_token_extraction()
    test_url_builder()
    test_friend_match_and_summary()
