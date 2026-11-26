"""
Two-stage peer matching engine (final version of the interim V1 algorithm).

Stage 1 (mandatory):  only students sharing at least one module are considered.
Stage 2 (weighted):   a compatibility score blends module similarity and
                      availability overlap:

        score = 100 * (W_MODULE * module_score + W_TIME * time_score)

    module_score = |common| / |union|                     (Jaccard similarity)
    time_score   = overlap_minutes / min(total_a, total_b)

Improvements over the interim V1:
    * weighted time compatibility instead of same-module-only results
    * deterministic tie-breaking (more common modules → more overlap hours →
      name) instead of random selection among equal peers
    * results served through a versioned cache for O(1) repeat views
"""
from flask import current_app

from ..extensions import db
from ..models import Module, User
from ..utils.time_slots import intersect_slot_lists, total_minutes


def compute_matches_for_user(user, max_results: int | None = None) -> list[dict]:
    """Return ranked match candidates for `user`."""
    w_module = current_app.config["MATCH_MODULE_WEIGHT"]
    w_time = current_app.config["MATCH_TIME_WEIGHT"]
    if max_results is None:
        max_results = current_app.config["MATCH_MAX_RESULTS"]

    my_module_ids = user.module_ids
    my_slots = user.slots
    my_total = total_minutes(my_slots)

    if not my_module_ids:
        return []

    candidates = (
        User.query.filter(User.user_id != user.user_id).order_by(User.name).all()
    )

    results = []
    for other in candidates:
        other_module_ids = other.module_ids

        # ---- Stage 1: shared module is mandatory -------------------------
        common_ids = my_module_ids & other_module_ids
        if not common_ids:
            continue

        # ---- Stage 2: weighted score --------------------------------------
        union_ids = my_module_ids | other_module_ids
        module_score = len(common_ids) / len(union_ids) if union_ids else 0.0

        overlaps = intersect_slot_lists(my_slots, other.slots)
        overlap_minutes = sum(s["minutes"] for s in overlaps)
        other_total = total_minutes(other.slots)
        denominator = min(my_total, other_total) if (my_total and other_total) else 0
        time_score = overlap_minutes / denominator if denominator else 0.0

        score = round(100 * (w_module * module_score + w_time * time_score), 1)

        results.append(
            {
                "user_id": other.user_id,
                "user": other,
                "common_modules": sorted(
                    db.session.query(Module)
                    .filter(Module.module_id.in_(common_ids))
                    .all(),
                    key=lambda m: m.module_code,
                ),
                "module_score": round(module_score, 3),
                "time_score": round(time_score, 3),
                "overlap_minutes": overlap_minutes,
                "common_slots": overlaps,
                "score": score,
            }
        )

    # deterministic ordering: score ↓, common modules ↓, overlap ↓, name ↑
    results.sort(
        key=lambda r: (
            -r["score"],
            -len(r["common_modules"]),
            -r["overlap_minutes"],
            r["user"].name.lower(),
        )
    )
    return results[:max_results]
