# bot/calendar_render.py
"""
Render a simple week calendar image with bookings.

events item shape:
    {
      day_index: 0..6 (Mon..Sun),
      start_hour: float (e.g., 13.5),
      end_hour:   float,
      label:      str (time range only),
      room_code:  str (e.g., "010.05.68"),
      ignored:    bool
    }

Defaults to showing 08:00–20:00.
"""
# Force non-GUI backend so macOS doesn't spawn a Python app in the Dock
import matplotlib
matplotlib.use("Agg")  
from pathlib import Path
from typing import List, Dict
import matplotlib.pyplot as plt

def render_week(
    events: List[Dict],
    week_title: str,
    out_path: Path,
    min_hour: int = 8,
    max_hour: int = 20,
) -> None:
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    y_ticks = list(range(min_hour, max_hour + 1))

    fig = plt.figure(figsize=(12, 7), dpi=160)
    ax = fig.add_subplot(111)

    # Axes limits (08:00–20:00)
    ax.set_xlim(0, 7)
    ax.set_ylim(min_hour, max_hour)
    ax.set_xticks([i+0.5 for i in range(7)], labels=days)
    ax.set_yticks(y_ticks, labels=[f"{h}:00" for h in y_ticks])
    ax.grid(True, which="both", axis="both", linewidth=0.5)

    # Draw blocks
    for e in events:
        x = e["day_index"]
        y0 = max(min_hour, min(max_hour, e["start_hour"]))
        y1 = max(min_hour, min(max_hour, e["end_hour"]))
        if y1 <= y0:  # fully out of range
            continue

        height = max(0.25, y1 - y0)
        # Normal vs ignored (red + thicker border)
        fc = (1, 0.8, 0.3, 0.85) if not e.get("ignored") else (1, 0.3, 0.3, 0.92)
        ec = (0, 0, 0, 1)
        lw = 1.0 if not e.get("ignored") else 2.0

        rect = plt.Rectangle((x+0.05, y0+0.05), 0.9, height-0.1,
                             facecolor=fc, edgecolor=ec, linewidth=lw)
        ax.add_patch(rect)

        room = e.get("room_code") or "?"
        label = e.get("label", "")
        ax.text(x+0.55, y0 + height/2, f"{room}\n{label}",
                ha="center", va="center", fontsize=8, wrap=True)

    ax.set_title(week_title, fontsize=14, pad=12)
    # Make earlier times appear nearer the top (like many calendars)
    ax.invert_yaxis()
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
