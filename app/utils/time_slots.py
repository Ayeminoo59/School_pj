"""
Shared time-slot helpers used by the matching engine and the
schedule suggestion algorithm.

A "slot" is a dict: {'day': int 0-6, 'start': 'HH:MM', 'end': 'HH:MM'}
"""
from functools import reduce

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def to_minutes(hhmm: str) -> int:
    """Convert 'HH:MM' to minutes since midnight."""
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def from_minutes(total: int) -> str:
    """Convert minutes since midnight back to 'HH:MM'."""
    total = max(0, total)
    return f"{total // 60:02d}:{total % 60:02d}"


def slot_minutes(slot: dict) -> int:
    """Duration of a slot in minutes."""
    return max(0, to_minutes(slot["end"]) - to_minutes(slot["start"]))


def total_minutes(slots) -> int:
    """Total free minutes across all slots."""
    return sum(slot_minutes(s) for s in slots)


def intersect_slot_lists(slots_a, slots_b):
    """Return the overlapping slots between two availability lists.

    Time slot overlap detection (Weeks 13-14 task). Returns a list of
    {'day', 'start', 'end', 'minutes'} dicts sorted by day then start.
    """
    overlaps = []
    for a in slots_a:
        for b in slots_b:
            if a["day"] != b["day"]:
                continue
            start = max(to_minutes(a["start"]), to_minutes(b["start"]))
            end = min(to_minutes(a["end"]), to_minutes(b["end"]))
            if end > start:
                overlaps.append(
                    {
                        "day": a["day"],
                        "start": from_minutes(start),
                        "end": from_minutes(end),
                        "minutes": end - start,
                    }
                )
    overlaps.sort(key=lambda s: (s["day"], s["start"]))
    return overlaps


def intersect_many(slot_lists):
    """Intersect N availability lists (used for whole-group suggestions)."""
    if not slot_lists:
        return []
    return reduce(intersect_slot_lists, slot_lists)
