"""
SCOPE — Smart Collaborative Oriented Peer Education
Application factory.

Final application of the Information Systems Project (ISP) by
AYE MIN OO (201941) — BSc (Hons) Business Computing and Information Systems.
"""
import os

from flask import Flask, redirect, url_for, flash, render_template
from flask_wtf.csrf import CSRFError

from config import Config
from .extensions import db, login_manager, csrf
from .utils.time_slots import DAY_NAMES


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Make sure the database folder exists before SQLite connects
    os.makedirs(os.path.join(app.root_path, "..", "db"), exist_ok=True)

    # --- Extensions -----------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # --- Blueprints (modular design, one blueprint per feature) ---------
    from .auth.routes import auth_bp
    from .main.routes import main_bp
    from .modules.routes import modules_bp
    from .availability.routes import availability_bp
    from .matches.routes import matches_bp
    from .requests.routes import requests_bp
    from .groups.routes import groups_bp
    from .profile.routes import profile_bp
    from .admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(modules_bp)
    app.register_blueprint(availability_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)

    # --- Template globals & filters --------------------------------------
    from .models import StudyRequest
    from flask_login import current_user

    @app.context_processor
    def inject_nav_data():
        """Expose the number of pending study requests to the navbar."""
        pending = 0
        if current_user.is_authenticated:
            pending = StudyRequest.query.filter_by(
                receiver_id=current_user.user_id, status="pending"
            ).count()
        return dict(pending_requests=pending, day_names=DAY_NAMES)

    app.jinja_env.filters["day_name"] = lambda d: DAY_NAMES[d] if isinstance(d, int) and 0 <= d < len(DAY_NAMES) else "—"

    # --- Error handling ---------------------------------------------------
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        from flask import request

        flash("Your session expired. Please try again.", "danger")
        return redirect(request.referrer or url_for("main.index"))

    @app.errorhandler(404)
    def handle_404(error):
        return render_template("errors/404.html"), 404

    # --- Database -----------------------------------------------------------
    with app.app_context():
        from . import seed  # noqa: F401  (imported for side-effect availability)

        db.create_all()
        seed.ensure_schema()   # lightweight migration for older scope.db files
        seed.seed_if_empty()

    return app
