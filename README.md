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



## Discord Bot

### Dependencies

Install the runtime dependencies first:

```bash
pip install discord.py requests python-dateutil matplotlib
# Optional (load token from .env):
pip install python-dotenv
```

### Environment setup

Set your bot token and ensure you’ve created the Playwright storage state.

```bash
export DISCORD_BOT_TOKEN=your_bot_token_here   # Windows (PowerShell): setx DISCORD_BOT_TOKEN "your_bot_token_here"
```

Make sure `.secrets/storage_state.json` exists (see the Storage State section above).

### Run the bot

```bash
python -m bot.main
```

On startup the bot:

* Prints to the terminal whether the session is active (look for **“RMIT booking study room session active”**).
* Attempts an initial weekly scrape and posts a calendar image to the bound channel (or the first writable channel).

### Data files used by the bot

* `friends.json` — IDs to match and the fields to scan.
* `rooms.json` — list of rooms to query `{ id:"<uuid>", code:"010.05.68", name:"Swanston Group Study Room" }`.
* `ignore_rooms.json` — rooms to flag in red `{ "rooms": ["080.10.04"] }`.
* `data/bind.json` — created by `/bind`, stores the channel id.
* `data/bookings.json` — last scrape summaries.
* `data/calendar.png` — last rendered weekly calendar (08:00–20:00).

### Slash commands

* **`/ping`** — Quick liveness check (replies “Pong!”).
* **`/addfriend s1234567`** — Adds a friend’s student number. Validation: `s` + 7 digits (case-insensitive input, stored with lowercase `s`).
* **`/listfriends`** — Shows the current list of friend IDs.
* **`/fetchtime`** — Scrapes the current week, renders a calendar (08:00–20:00), uploads it, and warns about bookings in ignored rooms (big red blocks + warning lines).
* **`/ignorerooms add 010.05.68`** — Adds a room code to the ignore list. Validation: `ddd.dd.dd` (e.g., `080.10.04`).
* **`/ignorerooms remove 010.05.68`** — Removes a room code from the ignore list.
* **`/ignorerooms list`** — Displays the ignore list.
* **`/bind`** — Binds the bot to the current channel (requires **Manage Channels**). When bound, the bot only responds/prints here.
* **`/unbind`** — Unbinds the bot; it can respond in any channel again.

### Notes

* The bot **never stores raw tokens** in the repo; they live only inside `.secrets/storage_state.json`.
* Use this for your own account / with consent. Respect RMIT’s terms of use.
* The calendar image hides student numbers inside the blocks; warnings will still include the student id for clarity.
* Message Content Intent is **not required** for these slash commands.
* If you see `Startup failed: session likely expired`, re-run the Playwright login to refresh `.secrets/storage_state.json`.

## Troubleshooting

* **401/403** when fetching: your token likely expired. Re-run `login_and_save.py` to refresh `storage_state.json`.
* Ensure you launched `python -m playwright install chromium` at least once.
* If times look wrong, remember output is displayed in **Australia/Melbourne** time.



## Project Structure (reference)

```
STUDY_ROOM_BOT/
├─ bot/
│  ├─ main.py                   # Discord bot entrypoint (slash commands)
│  ├─ config.py                 # paths, filenames, constants
│  ├─ datastore.py              # tiny JSON loader/saver
│  ├─ calendar_render.py        # headless matplotlib weekly calendar
│  ├─ scraper.py                # pulls bookings + builds calendar events
│  ├─ session_check.py          # validates Playwright session freshness
│  └─ guard.py                  # channel binding check
├─ data/                        # generated at runtime (calendar, cache)
│  ├─ calendar.png
│  ├─ bookings.json
│  └─ bind.json
├─ playwright/
│  ├─ booking_api_headers.json              # redacted copy (safe)
│  └─ .booking_api_headers.runtime.json     # real headers (gitignored)
├─ Storage_Creation/
│  ├─ login_and_save.py         # opens browser and saves storage_state.json
│  └─ reuse_session_check.py    # verifies saved session
├─ tests/
│  └─ run_tests.py              # lightweight sanity tests
├─ .secrets/
│  └─ storage_state.json        # Playwright session (DO NOT COMMIT)
├─ friends.json                 # friend IDs + match fields
├─ ignore_rooms.json            # rooms to highlight in red
├─ rooms.json                   # list of room UUIDs + codes/names
├─ rmit_booker.py               # API auth + fetch + summary helpers
├─ cli_list_bookings.py         # CLI to list bookings for a room
├─ storage_to_headers.py        # pulls bearer token from storage_state.json
├─ README.md
└─ .gitignore
```

Add to `.gitignore`:

```
.secrets/
data/
playwright/.booking_api_headers.runtime.json
__pycache__/
*.pyc
venv/
.DS_Store
---