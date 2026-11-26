"""
Requests blueprint — accept / decline / cancel study requests.
Accepting a request creates (or reuses) a study group for the shared module.
"""
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import GroupMember, GroupSchedule, StudyGroup, StudyRequest

requests_bp = Blueprint("requests", __name__)


@requests_bp.route("/requests", methods=["GET"])
@login_required
def list_requests():
    incoming = (
        StudyRequest.query.filter_by(receiver_id=current_user.user_id)
        .order_by(StudyRequest.created_at.desc())
        .all()
    )
    outgoing = (
        StudyRequest.query.filter_by(sender_id=current_user.user_id)
        .order_by(StudyRequest.created_at.desc())
        .all()
    )
    return render_template("requests/list.html", incoming=incoming, outgoing=outgoing)


@requests_bp.route("/requests/<int:request_id>/accept", methods=["POST"])
@login_required
def accept_request(request_id: int):
    req = db.session.get(StudyRequest, request_id)
    if req is None or req.receiver_id != current_user.user_id:
        flash("Request not found.", "danger")
        return redirect(url_for("requests.list_requests"))
    if req.status != "pending":
        flash("This request has already been handled.", "warning")
        return redirect(url_for("requests.list_requests"))

    req.status = "accepted"
    sender = req.sender_obj
    module = req.module_obj

    # Reuse the pair's group for this module, or create a new one
    group_name = f"{sender.name} & {current_user.name} — {module.module_name}"
    group = StudyGroup.query.filter_by(name=group_name).first()
    if group is None:
        group = StudyGroup(
            name=group_name,
            description=f"Study group created from an accepted study request for {module.module_name}.",
            module_id=module.module_id,
            creator_id=current_user.user_id,
        )
        db.session.add(group)
        db.session.flush()

    member_ids = {m.user_id for m in group.members}
    for user_id in (sender.user_id, current_user.user_id):
        if user_id not in member_ids:
            db.session.add(GroupMember(group_id=group.group_id, user_id=user_id))

    # Carry over the suggested common slot as a schedule proposal
    if req.day_of_week is not None and req.start_time and req.end_time:
        db.session.add(
            GroupSchedule(
                group_id=group.group_id,
                proposed_by_id=current_user.user_id,
                day_of_week=req.day_of_week,
                start_time=req.start_time,
                end_time=req.end_time,
                status="proposed",
            )
        )

    db.session.commit()
    flash(f"Request accepted — study group “{group.name}” is ready! 👥", "success")
    return redirect(url_for("groups.group_detail", group_id=group.group_id))


@requests_bp.route("/requests/<int:request_id>/decline", methods=["POST"])
@login_required
def decline_request(request_id: int):
    req = db.session.get(StudyRequest, request_id)
    if req is None or req.receiver_id != current_user.user_id:
        flash("Request not found.", "danger")
        return redirect(url_for("requests.list_requests"))
    if req.status != "pending":
        flash("This request has already been handled.", "warning")
        return redirect(url_for("requests.list_requests"))

    req.status = "declined"
    db.session.commit()
    flash("Request declined.", "info")
    return redirect(url_for("requests.list_requests"))


@requests_bp.route("/requests/<int:request_id>/cancel", methods=["POST"])
@login_required
def cancel_request(request_id: int):
    req = db.session.get(StudyRequest, request_id)
    if req is None or req.sender_id != current_user.user_id:
        flash("Request not found.", "danger")
        return redirect(url_for("requests.list_requests"))
    if req.status != "pending":
        flash("Only pending requests can be cancelled.", "warning")
        return redirect(url_for("requests.list_requests"))

    db.session.delete(req)
    db.session.commit()
    flash("Study request cancelled.", "info")
    return redirect(url_for("requests.list_requests"))
