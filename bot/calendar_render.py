
"""
Headless weekly calendar renderer.

Now renders a *workweek* view only (Mon–Fri).
"""

import matplotlib
matplotlib.use("Agg")  # headless backend

import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict


def render_week(
    events: List[Dict],
    week_title: str,
    out_path: Path,
    min_hour: int = 8,
    max_hour: int = 20,
) -> None:
    """
    Render a Mon–Fri calendar.

    events: list of dicts with:
      day_index: 0..4 (Mon..Fri)   <-- weekend events should already be filtered
      start_hour/end_hour: float hours in local time
      label: e.g., "12:30–13:30" (no student number)
      room_code: "010.05.68"
      ignored: bool
    """
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]   # <- workweek only
    num_days = len(days)
    y_ticks = list(range(min_hour, max_hour + 1))

    fig = plt.figure(figsize=(10, 6), dpi=160)
    ax  = fig.add_subplot(111)

    # X: 0..5 columns (Mon..Fri)
    ax.set_xlim(0, num_days)
    # Y: time window (08:00–20:00 by default)
    ax.set_ylim(min_hour, max_hour)

    ax.set_xticks([i + 0.5 for i in range(num_days)], labels=days)
    ax.set_yticks(y_ticks, labels=[f"{h}:00" for h in y_ticks])
    ax.grid(True, which="both", axis="both", linewidth=0.5)

    for e in events:
        x = e["day_index"]  # must be 0..4
        y0 = max(min_hour, min(max_hour, float(e["start_hour"])))
        y1 = max(min_hour, min(max_hour, float(e["end_hour"])))
        if y1 <= y0:
            continue

        height = max(0.25, y1 - y0)
        is_ignored = bool(e.get("ignored"))
        fc = (1, 0.3, 0.3, 0.92) if is_ignored else (1, 0.8, 0.3, 0.85)
        ec = (0, 0, 0, 1)
        lw = 2.0 if is_ignored else 1.0

        rect = plt.Rectangle((x + 0.05, y0 + 0.05), 0.9, height - 0.1,
                             facecolor=fc, edgecolor=ec, linewidth=lw)
        ax.add_patch(rect)

        room  = e.get("room_code") or "?"
        label = e.get("label", "")
        ax.text(x + 0.55, y0 + height / 2, f"{room}\n{label}",
                ha="center", va="center", fontsize=8, wrap=True)

    ax.set_title(week_title, fontsize=14, pad=10)
    ax.invert_yaxis()
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
