"""
Profile blueprint — view/update profile, change password, delete account.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db, match_cache
from ..models import (
    Availability,
    GroupMember,
    GroupSchedule,
    MatchResult,
    StudyRequest,
    User,
)

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile", methods=["GET"])
@login_required
def view_profile():
    return render_template(
        "profile/profile.html",
        modules_count=len(current_user.user_modules),
        slots_count=Availability.query.filter_by(user_id=current_user.user_id).count(),
        matches_count=MatchResult.query.filter_by(user_id=current_user.user_id).count(),
        groups_count=GroupMember.query.filter_by(user_id=current_user.user_id).count(),
    )


@profile_bp.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    course = request.form.get("course", "").strip()

    if len(name) < 2:
        flash("Please enter your full name.", "danger")
        return redirect(url_for("profile.view_profile"))
    if "@" not in email or "." not in email:
        flash("Please enter a valid email address.", "danger")
        return redirect(url_for("profile.view_profile"))
    if not course:
        flash("Please enter your course / programme.", "danger")
        return redirect(url_for("profile.view_profile"))

    existing = User.query.filter(User.email == email, User.user_id != current_user.user_id).first()
    if existing:
        flash("That email is already used by another account.", "danger")
        return redirect(url_for("profile.view_profile"))

    current_user.name = name
    current_user.email = email
    current_user.course = course
    db.session.commit()

    match_cache.invalidate()
    flash("Profile updated.", "success")
    return redirect(url_for("profile.view_profile"))


@profile_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not current_user.check_password(current_password):
        flash("Your current password is incorrect.", "danger")
        return redirect(url_for("profile.view_profile"))
    if len(new_password) < 8:
        flash("New password must be at least 8 characters long.", "danger")
        return redirect(url_for("profile.view_profile"))
    if new_password != confirm:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("profile.view_profile"))

    current_user.set_password(new_password)
    db.session.commit()
    flash("Password changed successfully.", "success")
    return redirect(url_for("profile.view_profile"))


@profile_bp.route("/profile/delete", methods=["POST"])
@login_required
def delete_account():
    me = current_user._get_current_object()

    # Groups: transfer ownership or delete empty creator groups
    for membership in list(me.group_memberships):
        group = membership.group
        if group.creator_id == me.user_id:
            others = sorted(
                (m for m in group.members if m.user_id != me.user_id),
                key=lambda m: m.joined_at,
            )
            if others:
                group.creator_id = others[0].user_id
                db.session.delete(membership)
            else:
                db.session.delete(group)
        else:
            db.session.delete(membership)

    # Schedules I proposed
    GroupSchedule.query.filter_by(proposed_by_id=me.user_id).delete()

    # Match results and study requests involving me
    MatchResult.query.filter(
        (MatchResult.user_id == me.user_id) | (MatchResult.matched_user_id == me.user_id)
    ).delete(synchronize_session=False)
    StudyRequest.query.filter(
        (StudyRequest.sender_id == me.user_id) | (StudyRequest.receiver_id == me.user_id)
    ).delete(synchronize_session=False)

    # Finally delete the user (cascades availability + user_modules)
    db.session.delete(me)
    db.session.commit()

    match_cache.invalidate()
    logout_user()
    flash("Your account has been permanently deleted. Goodbye!", "info")
    return redirect(url_for("main.index"))
