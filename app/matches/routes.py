"""
Matches blueprint — run the matching engine and send study requests.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db, match_cache
from ..matching.engine import compute_matches_for_user
from ..models import MatchResult, StudyRequest, User

matches_bp = Blueprint("matches", __name__)


@matches_bp.route("/matches", methods=["GET"])
@login_required
def view_matches():
    if not current_user.user_modules:
        flash("Select at least one module first so SCOPE can find your study partners.", "info")
        return redirect(url_for("modules.select_modules"))

    matches = match_cache.get(current_user.user_id)
    if matches is None:  # cache miss → compute (two-stage engine)
        matches = compute_matches_for_user(current_user)
        match_cache.set(current_user.user_id, matches)

    _persist_matches(current_user, matches)

    return render_template("matches/view.html", matches=matches)


def _persist_matches(user, matches) -> None:
    """Store the latest match list for dashboard statistics (MatchResult table)."""
    MatchResult.query.filter_by(user_id=user.user_id).delete()
    for match in matches:
        db.session.add(
            MatchResult(
                user_id=user.user_id,
                matched_user_id=match["user_id"],
                module_id=match["common_modules"][0].module_id,
                match_score=match["score"],
                common_modules_count=len(match["common_modules"]),
                overlap_minutes=match["overlap_minutes"],
            )
        )
    db.session.commit()


@matches_bp.route("/matches/send-request", methods=["POST"])
@login_required
def send_request():
    from ..models import Module

    try:
        matched_user_id = int(request.form.get("matched_user_id", 0))
        module_id = int(request.form.get("module_id", 0))
    except ValueError:
        flash("Invalid study request.", "danger")
        return redirect(url_for("matches.view_matches"))

    target = db.session.get(User, matched_user_id)
    if target is None:
        flash("That student no longer exists.", "danger")
        return redirect(url_for("matches.view_matches"))

    # The module must be shared between both students
    if module_id not in current_user.module_ids or module_id not in target.module_ids:
        flash("You can only send a request for a module you both study.", "danger")
        return redirect(url_for("matches.view_matches"))

    duplicate = StudyRequest.query.filter(
        StudyRequest.module_id == module_id,
        StudyRequest.status == "pending",
        (
            (StudyRequest.sender_id == current_user.user_id)
            & (StudyRequest.receiver_id == target.user_id)
        )
        | (
            (StudyRequest.sender_id == target.user_id)
            & (StudyRequest.receiver_id == current_user.user_id)
        ),
    ).first()
    if duplicate:
        flash(f"A pending request between you and {target.name} already exists.", "warning")
        return redirect(url_for("matches.view_matches"))

    # Optional proposed common slot ("day|start|end")
    day = start = end = None
    slot = request.form.get("slot", "")
    if slot:
        try:
            raw_day, start, end = slot.split("|")
            day = int(raw_day)
        except (ValueError, TypeError):
            day = start = end = None

    db.session.add(
        StudyRequest(
            sender_id=current_user.user_id,
            receiver_id=target.user_id,
            module_id=module_id,
            day_of_week=day,
            start_time=start,
            end_time=end,
        )
    )
    db.session.commit()

    flash(f"Study request sent to {target.name}! 🎉", "success")
    return redirect(url_for("matches.view_matches"))
