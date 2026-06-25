import streamlit as st
import pandas as pd
from sqlalchemy import text

from app.database.db import engine
from app.database.init_db import init_db

st.set_page_config(
    page_title="Logs",
    page_icon="🪵",
    layout="wide"
)

db_available = init_db()

st.title("🪵 Application Logs")

if not db_available:

    st.warning(
        "⚠️ Database is currently unavailable, so logs can't be "
        "shown here right now. This doesn't affect screening - "
        "parsing, scoring, and flags all work fine without the "
        "database; only this log view depends on it."
    )

    st.stop()

st.caption(
    "Parsing/scoring errors and unexpected failures are logged "
    "here automatically instead of crashing the app. If a "
    "screening run behaved unexpectedly, check here first."
)

ERROR_EVENT_TYPES = (
    "error", "parse_error", "parse_batch_error",
    "batch_error", "ui_error"
)


def fetch_logs(error_only=True, limit=200):

    if error_only:

        placeholders = ", ".join(
            f"'{t}'" for t in ERROR_EVENT_TYPES
        )

        query = text(f"""
            SELECT session_id, agent_name, event_type, data, created_at
            FROM agent_logs
            WHERE event_type IN ({placeholders})
            ORDER BY created_at DESC
            LIMIT :limit
        """)

    else:

        query = text("""
            SELECT session_id, agent_name, event_type, data, created_at
            FROM agent_logs
            ORDER BY created_at DESC
            LIMIT :limit
        """)

    try:

        with engine.connect() as connection:
            result = connection.execute(query, {"limit": limit})
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    except Exception as e:

        st.error(f"Could not load logs from the database: {e}")
        return []


show_all = st.toggle("Show all events (not just errors)", value=False)

logs = fetch_logs(error_only=not show_all)

if not logs:

    st.info(
        "No errors logged yet."
        if not show_all
        else "No log events found."
    )

else:

    for log in logs:

        is_error = log["event_type"] in ERROR_EVENT_TYPES

        icon = "🔴" if is_error else "🔵"

        with st.expander(
            f"{icon} {log['event_type']} — {log['agent_name']} "
            f"— {log['created_at']}"
        ):

            st.write(f"**Session:** {log['session_id']}")
            st.json(log["data"])

st.divider()
st.caption(
    f"Showing up to 200 most recent "
    f"{'events' if show_all else 'errors'}."
)