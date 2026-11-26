"""
SCOPE — Smart Collaborative Oriented Peer Education
Application configuration.
"""
import os

# --- Optional .env file support --------------------------------------------
# If a ".env" file exists next to this config.py, its values are loaded as
# environment variables (via python-dotenv). If the library is missing or
# the file does not exist, the app simply continues with the defaults
# below — nothing breaks either way.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared by all environments."""

    # Secret key used for session signing (change in production!)
    SECRET_KEY = os.environ.get("SCOPE_SECRET_KEY", "scope-dev-secret-key-change-me")

    # Database: SQLite file stored inside the project's db/ folder
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SCOPE_DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "db", "scope.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CSRF protection (Flask-WTF) — enabled on every POST form
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # ---- Matching engine settings --------------------------------------
    # Two-stage matching: Stage 1 = shared module (mandatory filter),
    # Stage 2 = weighted time-overlap score.
    MATCH_MODULE_WEIGHT = 0.6   # weight of the module-similarity score
    MATCH_TIME_WEIGHT = 0.4     # weight of the availability-overlap score
    MATCH_MAX_RESULTS = 15      # matches kept per search

    # ---- Match cache settings (Weeks 15-16 performance task) -----------
    # Results are cached in memory; the cache is version-bumped whenever
    # any user's modules / availability / account data changes.
    MATCH_CACHE_TTL_SECONDS = 300
