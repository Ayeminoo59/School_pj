"""
Module selection blueprint — students pick the modules they study.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db, match_cache
from ..models import Module, UserModule

modules_bp = Blueprint("modules", __name__)


@modules_bp.route("/modules", methods=["GET"])
@login_required
def select_modules():
    all_modules = Module.query.order_by(Module.module_code).all()
    selected_ids = current_user.module_ids
    return render_template(
        "modules/select.html", all_modules=all_modules, selected_ids=selected_ids
    )


@modules_bp.route("/modules/save", methods=["POST"])
@login_required
def save_modules():
    raw_ids = request.form.getlist("modules")
    try:
        module_ids = {int(value) for value in raw_ids}
    except ValueError:
        module_ids = set()

    valid_modules = Module.query.filter(Module.module_id.in_(module_ids)).all()

    if not valid_modules:
        flash("Please select at least one module.", "warning")
        return redirect(url_for("modules.select_modules"))

    # Replace the previous selection (simplest correct strategy)
    UserModule.query.filter_by(user_id=current_user.user_id).delete()
    for module in valid_modules:
        db.session.add(UserModule(user_id=current_user.user_id, module_id=module.module_id))
    db.session.commit()

    match_cache.invalidate()  # module data changed → stale matches
    flash("Modules saved! Now add your weekly availability.", "success")
    return redirect(url_for("availability.manage_availability"))
