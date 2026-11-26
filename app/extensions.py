"""
Shared Flask extension instances (initialised inside create_app()).
"""
import sqlite3

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .matching.cache import MatchCache

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def _set_sqlite_foreign_keys(dbapi_connection, _connection_record):
    """Make SQLite enforce FOREIGN KEY rules (ON DELETE CASCADE / SET NULL).

    SQLite disables foreign keys by default, so without this pragma the
    cascading deletes configured on the models would silently do nothing.
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Shared in-memory cache for match results (versioned + TTL)
match_cache = MatchCache(ttl_seconds=300)

# Redirect unauthenticated users to the login page
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"
