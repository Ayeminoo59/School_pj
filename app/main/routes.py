"""
Main blueprint — landing page and dashboard.
"""
from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..extensions import db
from ..models import GroupMember, GroupSchedule, MatchResult, StudyGroup, StudyRequest

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    me = current_user

    my_modules = [um.module for um in me.user_modules]
    my_slots = sorted(me.availabilities, key=lambda a: (a.day_of_week, a.start_time))

    matches_count = MatchResult.query.filter_by(user_id=me.user_id).count()
    pending_requests = StudyRequest.query.filter_by(
        receiver_id=me.user_id, status="pending"
    ).count()

    groups_count = GroupMember.query.filter_by(user_id=me.user_id).count()

    upcoming = (
        db.session.query(GroupSchedule, StudyGroup)
        .join(StudyGroup, StudyGroup.group_id == GroupSchedule.group_id)
        .join(GroupMember, GroupMember.group_id == StudyGroup.group_id)
        .filter(GroupMember.user_id == me.user_id)
        .order_by(GroupSchedule.day_of_week, GroupSchedule.start_time)
        .limit(5)
        .all()
    )

    return render_template(
        "main/dashboard.html",
        my_modules=my_modules,
        my_slots=my_slots,
        matches_count=matches_count,
        pending_requests=pending_requests,
        groups_count=groups_count,
        upcoming_schedules=upcoming,
    )
