"""
Database models for SCOPE.

Core tables from the interim ERD (Appendix B):
    User, Module, UserModule, Availability, MatchResult

Final-application tables (Weeks 13-24 plan):
    StudyGroup, GroupMember, GroupSchedule, StudyRequest
"""
from datetime import datetime

import bcrypt
from flask_login import UserMixin

from .extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "user"

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    course = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)  # admin panel access
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    availabilities = db.relationship(
        "Availability", backref="user", cascade="all, delete-orphan", lazy=True
    )
    user_modules = db.relationship(
        "UserModule", backref="user", cascade="all, delete-orphan", lazy=True
    )
    group_memberships = db.relationship(
        "GroupMember", backref="user_obj", cascade="all, delete-orphan", lazy=True
    )

    # --- password handling (bcrypt hashing) -----------------------------
    def set_password(self, raw_password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            raw_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                raw_password.encode("utf-8"), self.password_hash.encode("utf-8")
            )
        except ValueError:
            return False

    # --- helpers ----------------------------------------------------------
    def get_id(self) -> str:  # Flask-Login
        return str(self.user_id)

    @property
    def modules(self):
        return [um.module for um in self.user_modules]

    @property
    def module_ids(self):
        return {um.module_id for um in self.user_modules}

    @property
    def slots(self):
        return [a.as_slot() for a in self.availabilities]

    def __repr__(self):
        return f"<User {self.email}>"


class Module(db.Model):
    __tablename__ = "module"

    module_id = db.Column(db.Integer, primary_key=True)
    module_code = db.Column(db.String(10), unique=True, nullable=False)
    module_name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Module {self.module_code}>"


class UserModule(db.Model):
    """Association: which student is enrolled in which module."""

    __tablename__ = "user_module"
    __table_args__ = (db.UniqueConstraint("user_id", "module_id", name="uq_user_module"),)

    user_module_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    module_id = db.Column(
        db.Integer, db.ForeignKey("module.module_id", ondelete="CASCADE"), nullable=False
    )
    selected_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    module = db.relationship(
        "Module",
        backref=db.backref("enrollments", lazy=True, passive_deletes=True),
    )


class Availability(db.Model):
    __tablename__ = "availability"

    availability_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday … 6=Sunday
    start_time = db.Column(db.String(5), nullable=False)  # 'HH:MM'
    end_time = db.Column(db.String(5), nullable=False)    # 'HH:MM'

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "day_of_week", "start_time", "end_time", name="uq_availability"
        ),
    )

    def as_slot(self):
        return {"day": self.day_of_week, "start": self.start_time, "end": self.end_time}


class MatchResult(db.Model):
    """Persisted output of the matching engine for the dashboard."""

    __tablename__ = "match_result"
    __table_args__ = (
        db.UniqueConstraint("user_id", "matched_user_id", name="uq_match_pair"),
    )

    match_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    matched_user_id = db.Column(
        db.Integer, db.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    module_id = db.Column(
        db.Integer, db.ForeignKey("module.module_id", ondelete="SET NULL"), nullable=True
    )
    match_score = db.Column(db.Float, nullable=False, default=0.0)
    common_modules_count = db.Column(db.Integer, nullable=False, default=0)
    overlap_minutes = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class StudyGroup(db.Model):
    __tablename__ = "study_group"

    group_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    module_id = db.Column(
        db.Integer, db.ForeignKey("module.module_id", ondelete="CASCADE"), nullable=False
    )
    creator_id = db.Column(
        db.Integer, db.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    module_obj = db.relationship("Module", backref="groups", lazy=True, passive_deletes=True)
    members = db.relationship(
        "GroupMember", backref="group", cascade="all, delete-orphan", lazy=True
    )
    schedules = db.relationship(
        "GroupSchedule", backref="group", cascade="all, delete-orphan", lazy=True
    )

    @property
    def creator_obj(self):
        return db.session.get(User, self.creator_id)


class GroupMember(db.Model):
    __tablename__ = "group_member"
    __table_args__ = (db.UniqueConstraint("group_id", "user_id", name="uq_group_member"),)

    group_member_id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer, db.ForeignKey("study_group.group_id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class GroupSchedule(db.Model):
    """A proposed/confirmed study session for a group."""

    __tablename__ = "group_schedule"

    schedule_id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer, db.ForeignKey("study_group.group_id", ondelete="CASCADE"), nullable=False
    )
    proposed_by_id = db.Column(
        db.Integer, db.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="proposed")  # proposed/confirmed
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def proposer_obj(self):
        return db.session.get(User, self.proposed_by_id)


class StudyRequest(db.Model):
    """A study invitation sent from one student to a match."""

    __tablename__ = "study_request"

    request_id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(
        db.Integer, db.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    receiver_id = db.Column(
        db.Integer, db.ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
    )
    module_id = db.Column(
        db.Integer, db.ForeignKey("module.module_id", ondelete="CASCADE"), nullable=False
    )
    day_of_week = db.Column(db.Integer, nullable=True)
    start_time = db.Column(db.String(5), nullable=True)
    end_time = db.Column(db.String(5), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending/accepted/declined
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sender_obj = db.relationship(
        "User", foreign_keys=[sender_id], lazy=True, passive_deletes=True
    )
    receiver_obj = db.relationship(
        "User", foreign_keys=[receiver_id], lazy=True, passive_deletes=True
    )
    module_obj = db.relationship("Module", lazy=True, passive_deletes=True)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))
