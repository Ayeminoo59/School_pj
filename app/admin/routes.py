"""
Admin blueprint — the back-office of SCOPE.

Features (added in the final application):
  * platform dashboard with live statistics
  * user management  (promote / demote admins, delete accounts)
  * module management (add / delete modules)
  * study group oversight (view / delete any group)
  * study request oversight (view / remove any request)

Security: every route is wrapped in @admin_required, which combines
Flask-Login's @login_required with an extra ``is_admin`` check, so normal
students can never reach these pages.
"""
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db, match_cache
from ..models import (
    Availability,
    GroupMember,
    GroupSchedule,
    MatchResult,
    Module,
    StudyGroup,
    StudyRequest,
    User,
    UserModule,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    """Combine @login_required with an is_admin check in one decorator."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            flash("That page is for administrators only.", "danger")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@admin_bp.route("/")
@admin_required
def dashboard():
    stats = {
        "users": User.query.count(),
        "modules": Module.query.count(),
        "groups": StudyGroup.query.count(),
        "requests_pending": StudyRequest.query.filter_by(status="pending").count(),
        "requests_total": StudyRequest.query.count(),
        "matches": MatchResult.query.count(),
        "slots": Availability.query.count(),
        "enrollments": UserModule.query.count(),
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_requests = (
        StudyRequest.query.order_by(StudyRequest.created_at.desc()).limit(5).all()
    )
    upcoming = (
        db.session.query(GroupSchedule, StudyGroup)
        .join(StudyGroup, StudyGroup.group_id == GroupSchedule.group_id)
        .order_by(GroupSchedule.day_of_week, GroupSchedule.start_time)
        .limit(5)
        .all()
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_users=recent_users,
        recent_requests=recent_requests,
        upcoming=upcoming,
    )


# --------------------------------------------------------------------------
# User management
# --------------------------------------------------------------------------
@admin_bp.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(user_id):
    user = db.get_or_404(User, user_id)

    if user.user_id == current_user.user_id:
        flash("You cannot change your own admin status.", "warning")
        return redirect(url_for("admin.users"))

    user.is_admin = not user.is_admin
    db.session.commit()
    match_cache.invalidate()
    flash(
        f"{user.name} is now {'an admin' if user.is_admin else 'a student'}.",
        "success",
    )
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.get_or_404(User, user_id)

    if user.user_id == current_user.user_id:
        flash("You cannot delete your own account here.", "warning")
        return redirect(url_for("admin.users"))

    name = user.name
    # Related rows (modules, availability, requests, matches, groups they
    # created) are removed automatically by the ON DELETE CASCADE rules.
    db.session.delete(user)
    db.session.commit()
    match_cache.invalidate()
    flash(f"User {name} and all their data were deleted.", "success")
    return redirect(url_for("admin.users"))


# --------------------------------------------------------------------------
# Module management
# --------------------------------------------------------------------------
@admin_bp.route("/modules", methods=["GET", "POST"])
@admin_required
def modules():
    if request.method == "POST":
        code = request.form.get("module_code", "").strip().upper()
        name = request.form.get("module_name", "").strip()
        description = request.form.get("description", "").strip() or None

        errors = []
        if not code or len(code) > 10:
            errors.append("Module code is required (max 10 characters).")
        if not name:
            errors.append("Module name is required.")
        if not errors and Module.query.filter_by(module_code=code).first():
            errors.append(f"Module code {code} already exists.")

        if errors:
            for message in errors:
                flash(message, "danger")
        else:
            db.session.add(
                Module(module_code=code, module_name=name, description=description)
            )
            db.session.commit()
            match_cache.invalidate()
            flash(f"Module {code} was added.", "success")

        return redirect(url_for("admin.modules"))

    all_modules = Module.query.order_by(Module.module_code).all()
    return render_template("admin/modules.html", modules=all_modules)


@admin_bp.route("/modules/<int:module_id>/delete", methods=["POST"])
@admin_required
def delete_module(module_id):
    module = db.get_or_404(Module, module_id)
    code = module.module_code
    # Enrolments and groups for this module are removed by cascade rules.
    db.session.delete(module)
    db.session.commit()
    match_cache.invalidate()
    flash(f"Module {code} was deleted (enrolments and its groups removed).", "success")
    return redirect(url_for("admin.modules"))


# --------------------------------------------------------------------------
# Study group oversight
# --------------------------------------------------------------------------
@admin_bp.route("/groups")
@admin_required
def groups():
    all_groups = StudyGroup.query.order_by(StudyGroup.created_at.desc()).all()
    return render_template("admin/groups.html", groups=all_groups)


@admin_bp.route("/groups/<int:group_id>/delete", methods=["POST"])
@admin_required
def delete_group(group_id):
    group = db.get_or_404(StudyGroup, group_id)
    name = group.name
    db.session.delete(group)  # members + schedules cascade with it
    db.session.commit()
    flash(f"Study group '{name}' was deleted.", "success")
    return redirect(url_for("admin.groups"))


# --------------------------------------------------------------------------
# Study request oversight
# --------------------------------------------------------------------------
@admin_bp.route("/requests")
@admin_required
def requests_view():
    all_requests = StudyRequest.query.order_by(StudyRequest.created_at.desc()).all()
    return render_template("admin/requests.html", requests_list=all_requests)


@admin_bp.route("/requests/<int:request_id>/delete", methods=["POST"])
@admin_required
def delete_request(request_id):
    req = db.get_or_404(StudyRequest, request_id)
    db.session.delete(req)
    db.session.commit()
    flash("Study request removed.", "success")
    return redirect(url_for("admin.requests_view"))
