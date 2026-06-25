import os
from dotenv import load_dotenv

from sqlalchemy import create_engine

from sqlalchemy.orm import (
    sessionmaker,
    declarative_base
)

load_dotenv()


def _get_database_url():
    """
    Priority order, same pattern as the API key in ai_service.py:
    1. Streamlit secrets (set via the platform's Secrets UI once
       deployed - never committed to the repo)
    2. .env / environment variable (local development)
    3. Local Postgres fallback (only works on your own machine)
    """

    try:
        import streamlit as st
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass

    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:system123@localhost/hr_agent"
    )


DATABASE_URL = _get_database_url()

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()