
"""
Headless weekly calendar renderer.

Now renders a *workweek* view only (Mon–Fri).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Iterable

import matplotlib.pyplot as plt


@dataclass
class Event:
    day_index: int     # 0..4 (Mon..Fri)
    start_hour: float  # e.g. 12.5 for 12:30
    end_hour: float
    room_code: str | None
    ignored: bool      # draw red if True


def _clamp_interval(start: float, end: float, lo: float, hi: float) -> Tuple[float, float] | None:
    """Clamp [start,end] into [lo,hi]; return None if fully outside."""
    s = max(start, lo)
    e = min(end, hi)
    if e <= lo or s >= hi or e <= s:
        return None
    return s, e


def _merge_same_room(events: List[Event], eps: float = 1e-6) -> List[Event]:
    """
    Merge overlapping/adjacent windows **for the same room on the same day**.
    Keeps 'ignored' True if any merged piece was ignored.
    """
    out: List[Event] = []
    # group by (day, room)
    by_key: Dict[Tuple[int, str | None], List[Event]] = {}
    for ev in events:
        by_key.setdefault((ev.day_index, ev.room_code), []).append(ev)

    for (day, room), lst in by_key.items():
        lst.sort(key=lambda e: (e.start_hour, e.end_hour))
        cur = None
        cur_ignored = False
        for e in lst:
            if cur is None:
                cur = [e.start_hour, e.end_hour]
                cur_ignored = e.ignored
            else:
                if e.start_hour <= cur[1] + eps:  # overlap or touches
                    cur[1] = max(cur[1], e.end_hour)
                    cur_ignored = cur_ignored or e.ignored
                else:
                    out.append(Event(day, cur[0], cur[1], room, cur_ignored))
                    cur = [e.start_hour, e.end_hour]
                    cur_ignored = e.ignored
        if cur is not None:
            out.append(Event(day, cur[0], cur[1], room, cur_ignored))
    return out


def _group_identical_windows(events: List[Event]) -> List[Dict]:
    """
    For events that share the *exact same* (day, start, end, ignored),
    combine them into one drawing block and accumulate all room codes.
    """
    buckets: Dict[Tuple[int, float, float, bool], List[str]] = {}
    for e in events:
        key = (e.day_index, round(e.start_hour, 4), round(e.end_hour, 4), e.ignored)
        buckets.setdefault(key, []).append(e.room_code or "?")
    blocks: List[Dict] = []
    for (day, s, e, ign), rooms in buckets.items():
        blocks.append(
            {"day_index": day, "start_hour": s, "end_hour": e, "rooms": rooms, "ignored": ign}
        )
    blocks.sort(key=lambda b: (b["day_index"], b["start_hour"], b["end_hour"]))
    return blocks


def _assign_lanes(blocks_for_day: List[Dict]) -> List[Tuple[Dict, int, int]]:
    """
    Greedy lane assignment so overlapping blocks render side-by-side.
    Returns list of (block, lane_index, lane_count_for_that_time_span).
    """
    # Simple interval graph coloring (greedy).
    lanes_end: List[float] = []  # per lane, the current end time
    placed: List[Tuple[Dict, int, int]] = []
    # Sort by start time
    blocks_for_day = sorted(blocks_for_day, key=lambda b: (b["start_hour"], b["end_hour"]))
    for b in blocks_for_day:
        placed_lane = None
        for li, last_end in enumerate(lanes_end):
            if b["start_hour"] >= last_end - 1e-9:
                placed_lane = li
                lanes_end[li] = b["end_hour"]
                break
        if placed_lane is None:
            placed_lane = len(lanes_end)
            lanes_end.append(b["end_hour"])
        # lane_count is dynamic; for simplicity use the max #lanes encountered so far
        placed.append((b, placed_lane, len(lanes_end)))
    return placed


def _fmt_time(h: float) -> str:
    hours = int(math.floor(h))
    mins = int(round((h - hours) * 60)) % 60
    return f"{hours:02d}:{mins:02d}"


def render_week_calendar(
    events: Iterable[Dict],
    title: str,
    out_path: str,
    *,
    min_hour: int = 8,
    max_hour: int = 20,
) -> str:
    """
    Draw a Mon–Fri weekly calendar.
    `events` items must have:
      - day_index (0..4), start_hour, end_hour (floats, hours)
      - room_code (str | None), ignored (bool)

    Returns the path to the saved PNG.
    """
    # Convert dicts -> Event objects and clamp to visible window
    tmp: List[Event] = []
    for e in events:
        clamped = _clamp_interval(e["start_hour"], e["end_hour"], min_hour, max_hour)
        if not clamped:
            continue
        s, en = clamped
        tmp.append(Event(int(e["day_index"]), s, en, e.get("room_code"), bool(e.get("ignored", False))))

    # Merge overlapping windows for the same room/day
    merged = _merge_same_room(tmp)
    # Group identical windows (same day & exact time) to combine room labels
    blocks = _group_identical_windows(merged)

    # Split by day for lane layout
    by_day: Dict[int, List[Dict]] = {d: [] for d in range(5)}
    for b in blocks:
        if 0 <= b["day_index"] <= 4:
            by_day[b["day_index"]].append(b)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(14, 8))

    # y-axis top->bottom (8 to 20)
    ax.set_ylim(max_hour, min_hour)
    ax.set_yticks(range(min_hour, max_hour + 1))
    ax.set_yticklabels([f"{h}:00" for h in range(min_hour, max_hour + 1)])

    # x-axis Mon..Fri centered at 0..4
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    ax.set_xlim(-0.5, 4.5)
    ax.set_xticks(range(5))
    ax.set_xticklabels(days)

    # Grid lines
    ax.grid(True, which="both", axis="y", linestyle="-", linewidth=0.5, alpha=0.25)
    ax.set_title(title, fontsize=20, pad=20)

    # draw blocks per day with lane offsets
    for day in range(5):
        day_blocks = by_day.get(day, [])
        if not day_blocks:
            continue
        placed = _assign_lanes(day_blocks)
        max_lanes = max(l for _, _, l in placed) if placed else 1
        # base column width
        col_width = 0.8
        lane_width = col_width / max_lanes
        left_base = day - col_width / 2 + 0.1  # a bit of gutter

        for b, lane_idx, _ in placed:
            y = b["start_hour"]
            h = b["end_hour"] - b["start_hour"]
            x = left_base + lane_idx * lane_width
            w = lane_width * 0.95  # small gutter between lanes

            # colors
            face = "tab:red" if b["ignored"] else "orange"
            alpha = 0.35 if b["ignored"] else 0.6
            edge = "black"

            rect = plt.Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, alpha=alpha)
            ax.add_patch(rect)

            # label: "ROOM1 / ROOM2" on first line, time on second
            rooms_line = " / ".join(sorted(rc for rc in b["rooms"] if rc))
            time_line = f"{_fmt_time(b['start_hour'])}–{_fmt_time(b['end_hour'])}"
            label = f"{rooms_line}\n{time_line}"

            ax.text(
                x + w / 2.0,
                y + h / 2.0,
                label,
                ha="center",
                va="center",
                fontsize=10,
                weight="bold" if not b["ignored"] else "normal",
                color="black",
                clip_on=True,
            )

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# Back-compat alias: older code may import render_week
def render_week(*args, **kwargs):
    """Alias that forwards to render_week_calendar (keeps old imports working)."""
    return render_week_calendar(*args, **kwargs)


__all__ = ["render_week_calendar", "render_week"]
