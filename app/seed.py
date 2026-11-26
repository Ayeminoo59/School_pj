"""
Idempotent database seeding + lightweight schema migration:
  - schema migration: adds columns introduced in later versions to older
    scope.db files (db.create_all() only creates MISSING tables)
  - admin account: admin@university.com / admin123 (admin panel access)
  - 10 preset modules (as used in the prototype)
  - 8 demo students with overlapping modules/availability
    (password for every demo account: password123)
  - one demo group with a proposed schedule
  - one pending study request (Emma → Sarah)

Seeding runs only when the target data is missing, so restarts are safe.
"""
from datetime import datetime

from sqlalchemy import text

from .extensions import db
from .models import User, Module, UserModule, Availability, StudyGroup, GroupMember, GroupSchedule, StudyRequest

DEMO_PASSWORD = "password123"

ADMIN_EMAIL = "admin@university.com"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "SCOPE Admin"

MODULES = [
    ("CS401", "Web Development", "Modern front-end and back-end web technologies."),
    ("CS402", "Database Systems", "Relational modelling, SQL and normalisation."),
    ("CS403", "Software Engineering", "SDLC, requirements, design patterns and testing."),
    ("CS404", "Cloud Computing", "Virtualisation, IaaS/PaaS/SaaS and deployment."),
    ("CS405", "Cybersecurity", "Threats, cryptography and secure system design."),
    ("CS406", "Data Science", "Statistics, data wrangling and visualisation."),
    ("CS407", "Machine Learning", "Supervised/unsupervised learning fundamentals."),
    ("CS408", "Computer Networks", "TCP/IP, routing and network administration."),
    ("CS409", "Human-Computer Interaction", "Usability, UX principles and evaluation."),
    ("CS410", "IT Project Management", "WBS, Gantt charts, risk and project planning."),
]

DEMO_USERS = [
    # (name, email, course, [module codes], [(day, start, end), ...])
    ("Sarah Chen", "sarah.chen@university.com", "BSc Computer Science",
     ["CS401", "CS402", "CS403"],
     [(0, "10:00", "12:00"), (2, "14:00", "16:00"), (4, "09:00", "11:00")]),
    ("Michael Brown", "michael.brown@university.com", "BSc Software Engineering",
     ["CS402", "CS403", "CS405"],
     [(2, "14:00", "16:00"), (4, "13:00", "15:00"), (5, "10:00", "12:00")]),
    ("Emma Wilson", "emma.wilson@university.com", "BSc Computer Science",
     ["CS401", "CS403", "CS406"],
     [(4, "09:00", "11:00"), (0, "14:00", "16:00"), (3, "10:00", "12:00")]),
    ("David Lee", "david.lee@university.com", "BSc Business Computing",
     ["CS401", "CS404"],
     [(0, "10:00", "12:00"), (1, "13:00", "15:00")]),
    ("Thiri Aung", "thiri.aung@university.com", "BSc Computer Science",
     ["CS402", "CS406", "CS407"],
     [(2, "14:00", "16:00"), (3, "09:00", "11:00"), (5, "14:00", "17:00")]),
    ("Zaw Min", "zaw.min@university.com", "BSc Software Engineering",
     ["CS403", "CS405", "CS407"],
     [(4, "09:00", "11:00"), (0, "10:00", "12:00")]),
    ("Hnin Yu", "hnin.yu@university.com", "BSc Business Computing",
     ["CS401", "CS402", "CS403", "CS406"],
     [(0, "10:00", "12:00"), (2, "14:00", "16:00"), (4, "09:00", "11:00")]),
    ("Pyae Sone", "pyae.sone@university.com", "BSc Business Computing",
     ["CS404", "CS405", "CS408"],
     [(1, "13:00", "15:00"), (6, "10:00", "12:00")]),
]


def ensure_schema() -> None:
    """Lightweight migration for databases created by older versions.

    db.create_all() never modifies existing tables, so when an older
    scope.db file lacks a column the current models expect, we add it
    here with ALTER TABLE. (Fresh databases already have the column,
    so the check simply passes.)
    """
    with db.engine.connect() as conn:
        columns = [row[1] for row in conn.execute(text("PRAGMA table_info(user)"))]
        if columns and "is_admin" not in columns:
            conn.execute(
                text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
            )
            conn.commit()
            print("[scope] migrated: added 'is_admin' column to user table")


def ensure_admin() -> None:
    """Guarantee the admin account exists (also on pre-admin databases)."""
    if User.query.filter_by(email=ADMIN_EMAIL).first() is not None:
        return
    admin = User(name=ADMIN_NAME, email=ADMIN_EMAIL, course="Staff", is_admin=True)
    admin.set_password(ADMIN_PASSWORD)
    db.session.add(admin)
    db.session.commit()
    print("[scope] admin account created:", ADMIN_EMAIL)


def seed_if_empty() -> None:
    ensure_admin()   # runs even when demo data already exists
    _seed_modules()
    _seed_demo_users()
    _seed_demo_group()
    _seed_demo_request()


def _seed_modules() -> None:
    if Module.query.first() is not None:
        return
    for code, name, description in MODULES:
        db.session.add(Module(module_code=code, module_name=name, description=description))
    db.session.commit()


def _seed_demo_users() -> None:
    emails = [email for _, email, *_ in DEMO_USERS]
    if User.query.filter(User.email.in_(emails)).first() is not None:
        return

    modules_by_code = {m.module_code: m for m in Module.query.all()}
    users = []

    for name, email, course, module_codes, slots in DEMO_USERS:
        user = User(name=name, email=email, course=course)
        user.set_password(DEMO_PASSWORD)
        db.session.add(user)
        users.append((user, module_codes, slots))

    db.session.flush()  # assign user_id values

    for user, module_codes, slots in users:
        for code in module_codes:
            module = modules_by_code.get(code)
            if module:
                db.session.add(UserModule(user_id=user.user_id, module_id=module.module_id))
        for day, start, end in slots:
            db.session.add(
                Availability(user_id=user.user_id, day_of_week=day, start_time=start, end_time=end)
            )

    db.session.commit()


def _seed_demo_group() -> None:
    if StudyGroup.query.first() is not None:
        return

    sarah = User.query.filter_by(email="sarah.chen@university.com").first()
    michael = User.query.filter_by(email="michael.brown@university.com").first()
    thiri = User.query.filter_by(email="thiri.aung@university.com").first()
    cs402 = Module.query.filter_by(module_code="CS402").first()
    if not (sarah and michael and thiri and cs402):
        return

    group = StudyGroup(
        name="CS402 Database Crew",
        description="Weekly SQL practice and assignment discussion.",
        module_id=cs402.module_id,
        creator_id=sarah.user_id,
    )
    db.session.add(group)
    db.session.flush()

    for member in (sarah, michael, thiri):
        db.session.add(GroupMember(group_id=group.group_id, user_id=member.user_id))

    db.session.add(
        GroupSchedule(
            group_id=group.group_id,
            proposed_by_id=michael.user_id,
            day_of_week=2,
            start_time="14:00",
            end_time="16:00",
            status="proposed",
        )
    )
    db.session.commit()


def _seed_demo_request() -> None:
    if StudyRequest.query.first() is not None:
        return

    emma = User.query.filter_by(email="emma.wilson@university.com").first()
    sarah = User.query.filter_by(email="sarah.chen@university.com").first()
    cs403 = Module.query.filter_by(module_code="CS403").first()
    if not (emma and sarah and cs403):
        return

    db.session.add(
        StudyRequest(
            sender_id=emma.user_id,
            receiver_id=sarah.user_id,
            module_id=cs403.module_id,
            day_of_week=4,
            start_time="09:00",
            end_time="11:00",
            status="pending",
            created_at=datetime.utcnow(),
        )
    )
    db.session.commit()
