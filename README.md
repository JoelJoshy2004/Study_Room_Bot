# Study\_Room\_Bot

A bot that displays all the study rooms that my friends have booked.

---

## Quick Start

Firstly, in order to run the bot please **create a storage state**.

### Create a storage state

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install playwright
python -m playwright install chromium
mkdir -p .secrets
```

This creates the `.secrets/` folder where your browser session will be saved.

Then run:

```bash
python Storage_Creation/login_and_save.py
```

Then, to confirm all is working, run:

```bash
python Storage_Creation/reuse_session_check.py
```

### Install runtime dependencies

If you plan to run the CLI and tests, install the Python deps:

```bash
pip install requests python-dateutil
```

---

## Running Tests

```bash
python tests/run_tests.py
```

---

## Configure your friends list

Create/edit `friends.json` in the project root to define who to match against.

```json
{
  "ids": ["s4166573", "s4019428"],
  "match_fields": ["Owner", "BookerEmailAddress", "BookerName", "Reference"]
}
```

* **ids**: student numbers or emails (matching is case-insensitive).
* **match\_fields**: booking fields to scan for those IDs (adjust if API changes).

---

## CLI usage (example)

After creating the storage state and installing deps, you can list bookings for a room:

```bash
python cli_list_bookings.py \
  --room 00000000-0000-0000-0000-000000000000 \
  --start 2025-08-03T14:00:00.000Z \
  --end   2025-08-10T13:59:00.000Z
```

Replace `--room` with the resource (room) UUID you want to query.

---

## Project Structure (reference)

```
studyroom-bot/
├─ rmit_booker.py                # auth + fetch + filter + formatting library
├─ cli_list_bookings.py          # CLI to list friends’ bookings
├─ friends.json                  # your friends + matching fields
├─ tests/
│  └─ run_tests.py               # quick sanity tests
├─ Storage_Creation/
│  ├─ login_and_save.py          # opens a browser to log in and saves storage_state.json
│  └─ reuse_session_check.py     # verifies the saved session still works
└─ .secrets/
   └─ storage_state.json         # Playwright session (DO NOT COMMIT)
```



---

## Troubleshooting

* **401/403** when fetching: your token likely expired. Re-run `login_and_save.py` to refresh `storage_state.json`.
* Ensure you launched `python -m playwright install chromium` at least once.
* If times look wrong, remember output is displayed in **Australia/Melbourne** time.

---

## Notes

* The bot **never stores raw tokens** in the repo; they live only inside `.secrets/storage_state.json`.
* Use this for your own account / with consent. Respect RMIT’s terms of use.
