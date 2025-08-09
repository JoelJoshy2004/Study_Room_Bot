# bot/guard.py
"""
Channel binding guard for slash commands.
If a channel is bound (data/bind.json), only allow commands from that channel.
"""
from discord import Interaction
from bot import config
from bot.datastore import load_json

def allowed_channel(interaction: Interaction) -> bool:
    data = load_json(config.BIND_JSON, {})
    bound = data.get("channel_id")
    return (bound is None) or (int(bound) == interaction.channel_id)
