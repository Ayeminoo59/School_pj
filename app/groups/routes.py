"""
Groups blueprint — create/browse/join groups, propose & confirm schedules.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import GroupMember, GroupSchedule, StudyGroup
from ..scheduling.algorithm import suggest_common_slots
from ..utils.time_slots import DAY_NAMES

groups_bp = Blueprint("groups", __name__)


@groups_bp.route("/groups", methods=["GET"])
@login_required
def list_groups():
    my_groups = (
        StudyGroup.query.join(GroupMember, GroupMember.group_id == StudyGroup.group_id)
        .filter(GroupMember.user_id == current_user.user_id)
        .order_by(StudyGroup.created_at.desc())
        .all()
    )

    my_module_ids = current_user.module_ids
    discover_groups = []
    if my_module_ids:
        discover_groups = (
            StudyGroup.query.filter(
                StudyGroup.module_id.in_(my_module_ids),
                ~StudyGroup.members.any(GroupMember.user_id == current_user.user_id),
            )
            .order_by(StudyGroup.created_at.desc())
            .all()
        )

    my_modules = [um.module for um in current_user.user_modules]
    return render_template(
        "groups/list.html",
        my_groups=my_groups,
        discover_groups=discover_groups,
        my_modules=my_modules,
    )


@groups_bp.route("/groups/create", methods=["POST"])
@login_required
def create_group():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip() or None
    try:
        module_id = int(request.form.get("module_id", 0))
    except ValueError:
        module_id = 0

    if len(name) < 3:
        flash("Group name must be at least 3 characters long.", "danger")
        return redirect(url_for("groups.list_groups"))
    if module_id not in current_user.module_ids:
        flash("You can only create a group for a module you study.", "danger")
        return redirect(url_for("groups.list_groups"))

    group = StudyGroup(
        name=name,
        description=description,
        module_id=module_id,
        creator_id=current_user.user_id,
    )
    db.session.add(group)
    db.session.flush()
    db.session.add(GroupMember(group_id=group.group_id, user_id=current_user.user_id))
    db.session.commit()

    flash(f"Study group “{name}” created! 🎉", "success")
    return redirect(url_for("groups.group_detail", group_id=group.group_id))


def _get_group_or_redirect(group_id: int):
    group = db.session.get(StudyGroup, group_id)
    if group is None:
        flash("Group not found.", "danger")
        return None, redirect(url_for("groups.list_groups"))

    is_member = any(m.user_id == current_user.user_id for m in group.members)
    if not is_member:
        flash("You must be a member of this group to view it.", "warning")
        return None, redirect(url_for("groups.list_groups"))

    return group, None


@groups_bp.route("/groups/<int:group_id>", methods=["GET"])
@login_required
def group_detail(group_id: int):
    group, error = _get_group_or_redirect(group_id)
    if error:
        return error

    members = sorted(group.members, key=lambda m: m.joined_at)
    member_users = [m.user_obj for m in members]
    suggested_slots = suggest_common_slots(member_users)
    schedules = sorted(
        group.schedules,
        key=lambda s: (s.status != "confirmed", s.day_of_week, s.start_time),
    )

    return render_template(
        "groups/detail.html",
        group=group,
        members=members,
        suggested_slots=suggested_slots,
        schedules=schedules,
        day_names=DAY_NAMES,
    )


@groups_bp.route("/groups/<int:group_id>/join", methods=["POST"])
@login_required
def join_group(group_id: int):
    group = db.session.get(StudyGroup, group_id)
    if group is None:
        flash("Group not found.", "danger")
        return redirect(url_for("groups.list_groups"))
    if group.module_id not in current_user.module_ids:
        flash("You can only join groups for modules you study.", "warning")
        return redirect(url_for("groups.list_groups"))

    exists = GroupMember.query.filter_by(group_id=group.group_id, user_id=current_user.user_id).first()
    if exists:
        flash("You are already a member of this group.", "info")
        return redirect(url_for("groups.group_detail", group_id=group.group_id))

    db.session.add(GroupMember(group_id=group.group_id, user_id=current_user.user_id))
    db.session.commit()
    flash(f"You joined “{group.name}”! 👋", "success")
    return redirect(url_for("groups.group_detail", group_id=group.group_id))


@groups_bp.route("/groups/<int:group_id>/leave", methods=["POST"])
@login_required
def leave_group(group_id: int):
    group, error = _get_group_or_redirect(group_id)
    if error:
        return error
    if group.creator_id == current_user.user_id:
        flash("Creators cannot leave — use “Delete Group” instead.", "warning")
        return redirect(url_for("groups.group_detail", group_id=group.group_id))

    membership = GroupMember.query.filter_by(
        group_id=group.group_id, user_id=current_user.user_id
    ).first()
    if membership:
        db.session.delete(membership)
        db.session.commit()
    flash(f"You left “{group.name}”.", "info")
    return redirect(url_for("groups.list_groups"))


@groups_bp.route("/groups/<int:group_id>/delete", methods=["POST"])
@login_required
def delete_group(group_id: int):
    group = db.session.get(StudyGroup, group_id)
    if group is None:
        flash("Group not found.", "danger")
        return redirect(url_for("groups.list_groups"))
    if group.creator_id != current_user.user_id:
        flash("Only the group creator can delete this group.", "danger")
        return redirect(url_for("groups.group_detail", group_id=group.group_id))

    name = group.name
    db.session.delete(group)  # cascades members + schedules
    db.session.commit()
    flash(f"Study group “{name}” has been deleted.", "info")
    return redirect(url_for("groups.list_groups"))


@groups_bp.route("/groups/<int:group_id>/propose", methods=["POST"])
@login_required
def propose_schedule(group_id: int):
    group, error = _get_group_or_redirect(group_id)
    if error:
        return error

    try:
        day = int(request.form.get("day_of_week", -1))
    except ValueError:
        day = -1
    start = request.form.get("start_time", "").strip()
    end = request.form.get("end_time", "").strip()

    if day not in range(len(DAY_NAMES)):
        flash("Please choose a valid day.", "danger")
        return redirect(url_for("groups.group_detail", group_id=group.group_id))
    if not start or not end or start >= end:
        flash("Please provide a valid start and end time.", "danger")
        return redirect(url_for("groups.group_detail", group_id=group.group_id))

    db.session.add(
        GroupSchedule(
            group_id=group.group_id,
            proposed_by_id=current_user.user_id,
            day_of_week=day,
            start_time=start,
            end_time=end,
        )
    )
    db.session.commit()
    flash(f"Schedule proposed: {DAY_NAMES[day]} {start}–{end}. 🗓️", "success")
    return redirect(url_for("groups.group_detail", group_id=group.group_id))


@groups_bp.route("/groups/<int:group_id>/schedules/<int:schedule_id>/confirm", methods=["POST"])
@login_required
def confirm_schedule(group_id: int, schedule_id: int):
    group, error = _get_group_or_redirect(group_id)
    if error:
        return error

    schedule = db.session.get(GroupSchedule, schedule_id)
    if schedule is None or schedule.group_id != group.group_id:
        flash("Schedule not found.", "danger")
        return redirect(url_for("groups.group_detail", group_id=group.group_id))

    schedule.status = "confirmed"
    db.session.commit()
    flash("Schedule confirmed! 🎉", "success")
    return redirect(url_for("groups.group_detail", group_id=group.group_id))


@groups_bp.route("/groups/<int:group_id>/schedules/<int:schedule_id>/delete", methods=["POST"])
@login_required
def delete_schedule(group_id: int, schedule_id: int):
    group, error = _get_group_or_redirect(group_id)
    if error:
        return error

    schedule = db.session.get(GroupSchedule, schedule_id)
    if schedule is None or schedule.group_id != group.group_id:
        flash("Schedule not found.", "danger")
        return redirect(url_for("groups.group_detail", group_id=group.group_id))
    if schedule.proposed_by_id != current_user.user_id and group.creator_id != current_user.user_id:
        flash("Only the proposer or the creator can remove this schedule.", "warning")
        return redirect(url_for("groups.group_detail", group_id=group.group_id))

    db.session.delete(schedule)
    db.session.commit()
    flash("Schedule removed.", "info")
    return redirect(url_for("groups.group_detail", group_id=group.group_id))
