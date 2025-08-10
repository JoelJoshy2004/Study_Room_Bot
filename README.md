# Study\_Room\_Bot

A Discord bot + tiny CLI that shows all RMIT study-room bookings made by your friends, rendered as a weekly calendar.

---

## Quick Start

### 1) Create a Playwright storage state (one-time)

```bash
python -m venv venv
source venv/bin/activate
pip install playwright
python -m playwright install chromium
mkdir -p .secrets
```

Log in and save your session:

```bash
python Storage_Creation/login_and_save.py
```

Verify the session works:

```bash
python Storage_Creation/reuse_session_check.py
```

### 2) Start the Discord bot

Install deps:

```bash
pip install discord.py requests python-dateutil matplotlib
pip install python-dotenv    # optional
```

Set your bot token:

```bash
export DISCORD_BOT_TOKEN=your_bot_token_here
```

Run the bot:

```bash
python -m bot.main
```

On startup the bot will:

* print to the terminal whether the session is active (look for “RMIT booking study room session active”),
* perform an initial scrape and post a calendar image to the bound channel (or the first writable channel).

---

## Discord Bot – Slash Commands

* **/ping** — Liveness check.
* **/addfriend s1234567** — Add a friend’s student number. Validation: `s` + 7 digits (case-insensitive input; stored with lowercase `s`).
* **/listfriends** — Show the current list of friend IDs.
* **/rooms** — Scrape the selected workweek (Mon–Fri), render a calendar (08:00–20:00), upload it, and warn about bookings in ignored rooms (rendered red and listed as warnings).
* **/ignorerooms add 010.05.68** — Add a room code to the ignore list. Validation: `ddd.dd.dd` (e.g., 080.10.04).
* **/ignorerooms remove 010.05.68** — Remove a room code from the ignore list.
* **/ignorerooms list** — Display the ignore list.
* **/bind** — Bind the bot to the current channel (requires Manage Channels). When bound, the bot only responds/prints here.
* **/unbind** — Unbind the bot; it can respond in any channel again.
* **/refreshsession** (optional) — Force a silent session refresh via Playwright if enabled.

**Calendar behavior**

* Shows Mon–Fri only.
* Time axis: 08:00 → 20:00 (local Australia/Melbourne time).
* Title shows the full week range, e.g. “Week of 11–15 Aug 2025”.
* If you run it on Sat/Sun, it will fetch next week.
* Student numbers are not shown on the calendar blocks; warnings may include them for clarity.

**Data files used by the bot**

* `friends.json` — IDs to match and the fields to scan.
* `rooms.json` — rooms to query, e.g. `{ "id": "<uuid>", "code": "010.05.68", "name": "Swanston Group Study Room" }`.
* `ignore_rooms.json` — rooms to flag red, e.g. `{ "rooms": ["080.10.04"] }`.
* `data/bind.json` — created by `/bind`, stores the channel id.
* `data/bookings.json` — last scrape summaries.
* `data/calendar.png` — last rendered weekly calendar.

---

## Web Scraping – CLI (for testing)

After creating the storage state and installing deps (`requests`, `python-dateutil`), you can test the fetch without the bot.

**If your CLI file is at the repo root** (cli\_list\_bookings.py):

```bash
python cli_list_bookings.py --room 00000000-0000-0000-0000-000000000000 --start 2025-08-03T14:00:00.000Z --end 2025-08-10T13:59:00.000Z
```

**If your CLI lives under web\_scraper/**:

```bash
python web_scraper/cli_list_bookings.py --room 00000000-0000-0000-0000-000000000000 --start 2025-08-03T14:00:00.000Z --end 2025-08-10T13:59:00.000Z
# or, if web_scraper has __init__.py
python -m web_scraper.cli_list_bookings --room ... --start ... --end ...
```

**friends.json schema**

```json
{
  "ids": [],
  "match_fields": ["Owner", "BookerEmailAddress", "BookerName", "Reference"]
}
```

* **ids**: student numbers or emails (case-insensitive). Keep this empty in public repos if needed.
* **match\_fields**: booking fields to scan for those IDs (adjust if the API changes).

---

## Project Structure (reference)

```
STUDY_ROOM_BOT/
├─ bot/
│  ├─ main.py                   # Discord bot entrypoint (slash commands)
│  ├─ config.py                 # paths, filenames, constants
│  ├─ datastore.py              # tiny JSON loader/saver
│  ├─ calendar_render.py        # headless matplotlib weekly calendar (Mon–Fri, 08:00–20:00)
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
├─ cli_list_bookings.py         # (optional) CLI at repo root
├─ web_scraper/                 # (optional) folder if you keep CLI here instead
│  └─ cli_list_bookings.py
├─ storage_to_headers.py        # pulls bearer token from storage_state.json
├─ README.md
└─ .gitignore
```

**.gitignore**

```
.secrets/
data/
playwright/.booking_api_headers.runtime.json
__pycache__/
*.pyc
venv/
.DS_Store
```

---

## Troubleshooting

**Bot won’t start – 401 Unauthorized / LoginFailure: Improper token has been passed.**
Your Discord bot token is missing or wrong. Reset/copy the Bot Token in the Developer Portal, export it again, and restart.

**401/403 when scraping Resource Booker**
Your RMIT access token expired. Re-run `Storage_Creation/login_and_save.py` (or use `/refreshsession` if enabled). Then retry `/rooms`.

**Matplotlib pops a “Python” window on macOS**
We force a headless backend (Agg), and close figures after saving. If you still see windows, ensure no `plt.show()` calls exist and you’re on the latest code.

**Slash commands not appearing**
Give it a minute after first run. Check the bot has the right scope (applications.commands). We sync commands at startup; watch the console for “Synced N app commands.”

**Imports fail when running the CLI from subfolders**
Run from the repo root or use the provided path shim (see `web_scraper/cli_list_bookings.py`). Alternatively: `python -m web_scraper.cli_list_bookings ...`.

---

## Notes

* The bot never stores raw tokens in the repo; they live only inside `.secrets/storage_state.json`.
* Use this for your own account / with consent. Respect RMIT’s terms of use.
* Output times are shown in Australia/Melbourne local time.
* Calendar blocks hide student numbers; warnings may include them.
* **AI assistance**: Parts of this project were produced with the aid of AI (ChatGPT 5) for tasks like boilerplate generation and documentation. Usage was ethical: no confidential credentials or student data were shared with the model, and all outputs were reviewed and tested by the maintainers.

---

## Collaborators

* **Joel** — Lead Developer (architecture & implementation)
* **Aryan** — Data Acquisition & Web Scraping
* **Johnny** — QA & Debugging
