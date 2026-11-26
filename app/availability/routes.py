"""
Availability blueprint — manage weekly free-time slots.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db, match_cache
from ..models import Availability
from ..utils.time_slots import DAY_NAMES

availability_bp = Blueprint("availability", __name__)


@availability_bp.route("/availability", methods=["GET"])
@login_required
def manage_availability():
    my_slots = Availability.query.filter_by(user_id=current_user.user_id).all()
    return render_template("availability/manage.html", my_slots=my_slots, day_names=DAY_NAMES)


@availability_bp.route("/availability/add", methods=["POST"])
@login_required
def add_slot():
    try:
        day = int(request.form.get("day_of_week", -1))
    except ValueError:
        day = -1
    start = request.form.get("start_time", "").strip()
    end = request.form.get("end_time", "").strip()

    if day not in range(len(DAY_NAMES)):
        flash("Please choose a valid day.", "danger")
        return redirect(url_for("availability.manage_availability"))
    if not start or not end:
        flash("Please provide both a start time and an end time.", "danger")
        return redirect(url_for("availability.manage_availability"))
    if start >= end:
        flash("End time must be after start time.", "danger")
        return redirect(url_for("availability.manage_availability"))

    duplicate = Availability.query.filter_by(
        user_id=current_user.user_id,
        day_of_week=day,
        start_time=start,
        end_time=end,
    ).first()
    if duplicate:
        flash("That time slot is already in your availability.", "warning")
        return redirect(url_for("availability.manage_availability"))

    db.session.add(
        Availability(user_id=current_user.user_id, day_of_week=day, start_time=start, end_time=end)
    )
    db.session.commit()

    match_cache.invalidate()  # availability changed → stale matches
    flash(f"{DAY_NAMES[day]} {start}–{end} added to your availability.", "success")
    return redirect(url_for("availability.manage_availability"))


@availability_bp.route("/availability/<int:slot_id>/delete", methods=["POST"])
@login_required
def delete_slot(slot_id: int):
    slot = db.session.get(Availability, slot_id)
    if slot is None or slot.user_id != current_user.user_id:
        flash("Time slot not found.", "danger")
        return redirect(url_for("availability.manage_availability"))

    db.session.delete(slot)
    db.session.commit()

    match_cache.invalidate()
    flash("Time slot removed.", "info")
    return redirect(url_for("availability.manage_availability"))
