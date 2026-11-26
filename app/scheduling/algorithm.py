"""
Schedule suggestion algorithm (Weeks 13-14 task).

Given a list of users, compute the time slots that EVERY member has free —
i.e. the intersection of all availability lists — so a group can meet.
"""
from ..utils.time_slots import intersect_many


def suggest_common_slots(users, top_n: int = 6) -> list[dict]:
    """Return up to `top_n` common slots (longest first) for all users."""
    slot_lists = [u.slots for u in users]
    slot_lists = [s for s in slot_lists if s]
    if len(slot_lists) < 2:
        return []

    common = intersect_many(slot_lists)
    if not common:
        return []

    # Suggest the most useful slots: longest overlap first.
    common.sort(key=lambda s: (-s["minutes"], s["day"], s["start"]))
    return common[:top_n]
