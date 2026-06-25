from app.database.db import engine
from app.database.models import Base


def init_db():
    """
    Creates DB tables if they don't exist.

    Returns True on success, False if the database is unreachable.
    The rest of the app should keep working either way - only
    logging/audit/approval features actually depend on the
    database. The core screening pipeline (parsing, scoring,
    flags, weights) does not touch the database at all.
    """

    try:
        Base.metadata.create_all(bind=engine)
        return True

    except Exception as e:
        print(f"[init_db] Database unavailable, skipping: {e}")
        return False