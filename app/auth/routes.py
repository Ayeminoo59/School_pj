"""
Authentication blueprint — register, login, logout.

Security features (carried over from the interim prototype):
  * bcrypt password hashing
  * Flask-Login session management with @login_required
  * CSRF protection on every POST form (Flask-WTF)
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db, match_cache
from ..models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        course = request.form.get("course", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []
        if len(name) < 2:
            errors.append("Please enter your full name.")
        if "@" not in email or "." not in email:
            errors.append("Please enter a valid email address.")
        if not course:
            errors.append("Please enter your course / programme.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        elif password != confirm:
            errors.append("Passwords do not match.")
        if not errors and User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")

        if errors:
            for message in errors:
                flash(message, "danger")
        else:
            user = User(name=name, email=email, course=course)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            match_cache.invalidate()  # a new candidate joined
            login_user(user)
            flash("Welcome to SCOPE! Step 1 done — now select your modules.", "success")
            return redirect(url_for("modules.select_modules"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash("Invalid email or password.", "danger")
        else:
            login_user(user, remember=False)
            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out. See you soon!", "info")
    return redirect(url_for("main.index"))
