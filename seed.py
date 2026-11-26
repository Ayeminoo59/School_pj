"""
SCOPE — database seeding utility.

Creates the SQLite database (if missing), adds all tables and fills it
with the demo data (10 modules, 8 demo students, one demo group and one
pending study request). Seeding is idempotent — running it again when the
data already exists changes nothing, so it is always safe to run.

Usage:
    python seed.py
"""
from app import create_app
from app.seed import seed_if_empty


def main() -> None:
    app = create_app()
    with app.app_context():
        seed_if_empty()
    print()
    print("Database ready — tables created and demo data loaded (if missing).")
    print("Start the application with:  python run.py")


if __name__ == "__main__":
    main()
