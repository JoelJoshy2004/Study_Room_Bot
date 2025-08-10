
import os, re, asyncio, random
from datetime import datetime, timedelta, timezone
import discord
from discord import app_commands
from discord.ext import commands

from bot import config
from bot.guard import allowed_channel
from bot.datastore import load_json, save_json
from bot.session_check import token_is_fresh
from bot.scraper import scrape_week
from bot.calendar_render import render_week

from bot.session_refresh import get_current_token, minutes_remaining_from_token, refresh_with_playwright


TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # set in your environment

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------- Helpers -----------------

def assert_channel(inter: discord.Interaction) -> bool:
    """Return True if command is allowed in this channel; otherwise reply ephemeral."""
    if allowed_channel(inter):
        return True
    else:
        asyncio.create_task(inter.response.send_message(
            "This bot is bound to a different channel. Use `/unbind` or run commands in the bound channel.",
            ephemeral=True))
        return False

async def post_startup_status():
    # Print to terminal whether session looks fresh
    if token_is_fresh():
        print("✅ RMIT booking study room session active")
    else:
        print("❌ RMIT booking session appears expired (token not fresh)")

    # Choose a channel and post status as before...
    channel_id = load_json(config.BIND_JSON, {}).get("channel_id")
    channel = None
    if channel_id:
        c = bot.get_channel(int(channel_id))
        if isinstance(c, discord.TextChannel):
            channel = c
    if channel is None:
        for g in bot.guilds:
            for c in g.text_channels:
                if c.permissions_for(g.me).send_messages:
                    channel = c; break
            if channel: break
    if channel is None:
        return

    if not token_is_fresh():
        await channel.send("❌ **Startup failed**: session likely expired. Please re-run the storage login flow.")
        return

    try:
        summaries, events, warns, title = scrape_week()
        # Render 08:00–20:00
        render_week(events, title, config.CAL_IMG, min_hour=8, max_hour=20)
        await channel.send(content="✅ **Startup OK**. Scraped current week.",
                           file=discord.File(config.CAL_IMG))
        if warns:
            await channel.send("\n".join(warns))
    except Exception as e:
        await channel.send(f"❌ **Startup scrape failed**: {e}")

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} app commands.")
    except Exception as e:
        print("App command sync failed:", e)

    print(f"Logged in as {bot.user} (id={bot.user.id})")
    # Start the refresher loop (don’t await forever)
    bot.loop.create_task(refresher_loop())
    await post_startup_status()

async def refresher_loop():
    """
    Every 30 minutes:
      1) attempt silent refresh using Playwright
      2) perform a small 'probe' by scraping and focusing a random room for now→+2h
    """
    warned = False
    while not bot.is_closed():
        try:
            ok = await asyncio.to_thread(refresh_with_playwright)
            if ok:
                print("[session] periodic refresh OK")
                warned = False
            else:
                if not warned:
                    print("[session] periodic refresh failed; will retry in 30 min")
                    warned = True
        except Exception as e:
            print(f"[session] refresher error: {e}")
        try:
            # Make a benign query to keep things warm
            probe_random_room(window_hours=2)
        except Exception as e:
            print(f"[probe] error: {e}")
        # Sleep 30 min
        await asyncio.sleep(1800)


def _ensure_dt(obj):
    """
    Return a timezone-aware datetime for `obj`.
    Supports datetime objects or ISO strings. Falls back to naive->local.
    """
    if isinstance(obj, datetime):
        return obj if obj.tzinfo else obj.replace(tzinfo=timezone.utc).astimezone()
    # try ISO parse without external deps
    try:
        # Basic ISO-like formats: 'YYYY-MM-DDTHH:MM:SS' (optionally with 'Z' or offset)
        s = str(obj)
        # Handle trailing Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone()
    except Exception:
        # last resort: now
        return datetime.now().astimezone()


def probe_random_room(window_hours: int = 2):
    """
    Make a lightweight 'poke' to the booking site by scraping the week,
    picking a random room, and looking at events between now and now+window.
    """
    try:
        summaries, events, warns, title = scrape_week()
    except Exception as e:
        print(f"[probe] scrape_week failed: {e}")
        return

    # Collect room codes from events (best-effort: supports common key names)
    def _room_of(e):
        return (
            e.get("room")
            or e.get("Room")
            or e.get("room_code")
            or e.get("RoomCode")
            or e.get("location")
        )

    room_codes = { _room_of(e) for e in events if _room_of(e) }
    if not room_codes:
        print("[probe] no room codes discovered from events")
        return

    # Exclude ignored rooms if present
    ignored = set(load_json(config.IGNORE_ROOMS_JSON, {"rooms": []}).get("rooms", []))
    candidates = sorted(rc for rc in room_codes if rc not in ignored) or sorted(room_codes)
    if not candidates:
        print("[probe] all discovered rooms are in ignore list")
        return

    choice = random.choice(candidates)

    now = datetime.now().astimezone()
    end = now + timedelta(hours=window_hours)

    # Try to count events for the chosen room in [now, end]
    hits = 0
    for e in events:
        if _room_of(e) != choice:
            continue
        # Common keys for start time
        start = e.get("start") or e.get("Start") or e.get("start_time") or e.get("StartTime")
        if not start:
            continue
        dt = _ensure_dt(start)
        if now <= dt <= end:
            hits += 1

    print(f"[probe] room {choice}: {hits} events between {now:%Y-%m-%d %H:%M} and {end:%H:%M} (title='{title}')")



# ------------- Slash Commands -----------------

@bot.tree.command(name="ping", description="Ping the bot")
async def ping(inter: discord.Interaction):
    if not assert_channel(inter): return
    await inter.response.send_message("Pong! 🏓")

@bot.tree.command(name="addfriend", description="Add a friend's student number (e.g., s1234567)")
@app_commands.describe(student_number="Student number starting with s followed by 7 digits")
async def addfriend(inter: discord.Interaction, student_number: str):
    if not assert_channel(inter): return

    s = student_number.strip().lower()
    if not re.fullmatch(r"s\d{7}", s):
        await inter.response.send_message("❌ Invalid student number. Expected `s1234567`.", ephemeral=True)
        return

    friends = load_json(config.FRIENDS_JSON, {"ids": [], "match_fields": ["Owner","BookerEmailAddress","BookerName","Reference"]})
    ids = set(x.lower() for x in friends.get("ids", []))
    if s in ids:
        await inter.response.send_message(f"ℹ️ `{s}` already in friends list.", ephemeral=True)
        return
    ids.add(s)
    friends["ids"] = sorted(ids)
    save_json(config.FRIENDS_JSON, friends)
    await inter.response.send_message(f"✅ Added `{s}` to friends.", ephemeral=True)

@bot.tree.command(name="rooms", description="Scrape this week's bookings and render a calendar")
async def rooms(inter: discord.Interaction):
    if not assert_channel(inter): return
    await inter.response.defer()

    if not token_is_fresh():
        await inter.followup.send("❌ Session expired. Please refresh the storage state.")
        return
    try:
        summaries, events, warns, title = scrape_week()
        # Render 08:00–20:00 and save
        render_week(events, title, config.CAL_IMG, min_hour=8, max_hour=20)
        save_json(config.BOOKINGS_JSON, {"summaries": summaries, "generated": title})

        await inter.followup.send(f"🗓️ **{title}** — {len(summaries)} matching bookings.",
                                  files=[discord.File(config.CAL_IMG)])
        if warns:
            await inter.followup.send("\n".join(warns))
    except Exception as e:
        await inter.followup.send(f"❌ Scrape failed: {e}")

# ignoreRooms subcommands: add / remove / list
ignore_group = app_commands.Group(name="ignorerooms", description="Manage the ignore-rooms list")
bot.tree.add_command(ignore_group)

@ignore_group.command(name="add", description="Add a room code to the ignore list (e.g., 010.05.68)")
@app_commands.describe(code="Room code 3 digits . 2 digits . 2 digits (e.g., 080.10.04)")
async def ign_add(inter: discord.Interaction, code: str):
    if not assert_channel(inter): return
    code = code.strip()
    if not re.fullmatch(r"\d{3}\.\d{2}\.\d{2}", code):
        await inter.response.send_message("❌ Invalid code. Example: `080.10.04`", ephemeral=True)
        return
    data = load_json(config.IGNORE_ROOMS_JSON, {"rooms": []})
    rooms = set(data.get("rooms", []))
    if code in rooms:
        await inter.response.send_message(f"ℹ️ `{code}` already in ignore list.", ephemeral=True)
        return
    rooms.add(code)
    data["rooms"] = sorted(rooms)
    save_json(config.IGNORE_ROOMS_JSON, data)
    await inter.response.send_message(f"✅ Added `{code}` to ignore list.", ephemeral=True)

@ignore_group.command(name="remove", description="Remove a room code from the ignore list")
async def ign_remove(inter: discord.Interaction, code: str):
    if not assert_channel(inter): return
    data = load_json(config.IGNORE_ROOMS_JSON, {"rooms": []})
    rooms = set(data.get("rooms", []))
    if code not in rooms:
        await inter.response.send_message(f"ℹ️ `{code}` not in ignore list.", ephemeral=True)
        return
    rooms.remove(code)
    data["rooms"] = sorted(rooms)
    save_json(config.IGNORE_ROOMS_JSON, data)
    await inter.response.send_message(f"✅ Removed `{code}` from ignore list.", ephemeral=True)

@ignore_group.command(name="list", description="Show ignore list")
async def ign_list(inter: discord.Interaction):
    if not assert_channel(inter): return
    data = load_json(config.IGNORE_ROOMS_JSON, {"rooms": []})
    rooms = data.get("rooms", [])
    txt = ", ".join(rooms) if rooms else "_(empty)_"
    await inter.response.send_message(f"Ignore rooms: {txt}", ephemeral=True)

# Bind / Unbind
@bot.tree.command(name="bind", description="Bind this bot to the current channel")
async def bind(inter: discord.Interaction):
    if not inter.user.guild_permissions.manage_channels:
        await inter.response.send_message("You need Manage Channels permission to bind.", ephemeral=True)
        return
    save_json(config.BIND_JSON, {"channel_id": inter.channel_id})
    await inter.response.send_message(f"✅ Bound to <#{inter.channel_id}>")

@bot.tree.command(name="unbind", description="Unbind the bot from any channel")
async def unbind(inter: discord.Interaction):
    if not inter.user.guild_permissions.manage_channels:
        await inter.response.send_message("You need Manage Channels permission to unbind.", ephemeral=True)
        return
    save_json(config.BIND_JSON, {"channel_id": None})
    await inter.response.send_message("✅ Unbound. The bot can reply in any channel now.")


@bot.tree.command(name="refreshsession", description="Force a silent session refresh (headless)")
async def refreshsession(inter: discord.Interaction):
    if not assert_channel(inter): return
    await inter.response.defer(ephemeral=True)
    try:
        ok = await asyncio.to_thread(refresh_with_playwright)
        if ok:
            await inter.followup.send("✅ Session refreshed.", ephemeral=True)
        else:
            await inter.followup.send("⚠️ Refresh attempt failed. You may need to re-login.", ephemeral=True)
    except Exception as e:
        await inter.followup.send(f"❌ Refresh error: {e}", ephemeral=True)




async def post_startup_status():
    # Print to terminal whether session looks fresh
    if token_is_fresh():
        print("✅ RMIT booking study room session active")
    else:
        print("❌ RMIT booking session appears expired (token not fresh)")

    # Choose a channel and post status as before...
    channel_id = load_json(config.BIND_JSON, {}).get("channel_id")
    channel = None
    if channel_id:
        c = bot.get_channel(int(channel_id))
        if isinstance(c, discord.TextChannel):
            channel = c
    if channel is None:
        for g in bot.guilds:
            for c in g.text_channels:
                if c.permissions_for(g.me).send_messages:
                    channel = c; break
            if channel: break
    if channel is None:
        return

    if not token_is_fresh():
        await channel.send("❌ **Startup failed**: session likely expired. Please re-run the storage login flow.")
        return

    try:
        summaries, events, warns, title = scrape_week()
        # Render 08:00–20:00
        render_week(events, title, config.CAL_IMG, min_hour=8, max_hour=20)
        await channel.send(content="✅ **Startup OK**. Scraped current week.",
                           file=discord.File(config.CAL_IMG))
        if warns:
            await channel.send("\n".join(warns))
    except Exception as e:
        await channel.send(f"❌ **Startup scrape failed**: {e}")

@bot.tree.command(name="listfriends", description="Show current friend student numbers")
async def listfriends(inter: discord.Interaction):
    if not assert_channel(inter): return
    data = load_json(config.FRIENDS_JSON, {"ids": []})
    ids = data.get("ids", [])
    txt = ", ".join(ids) if ids else "_(none added yet)_"
    await inter.response.send_message(f"Friends: {txt}", ephemeral=True)


# ------------- Run -----------------
def main():
    if not TOKEN:
        raise SystemExit("Set DISCORD_BOT_TOKEN in your environment.")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
