from sqlalchemy import text

from app.database.db import engine

# ---------------------------------------------------
# FETCH APPROVALS
# ---------------------------------------------------


def get_candidate_approvals():

    query = text("""

        SELECT
            candidate_name,
            email,
            status,
            created_at,
            interview_invite_sent,
            interview_invite_date

        FROM candidate_approvals

        ORDER BY created_at DESC

    """)

    with engine.connect() as connection:

        result = connection.execute(query)

        rows = result.mappings().all()

        return [dict(row) for row in rows]

# ---------------------------------------------------
# FETCH LOGS
# ---------------------------------------------------


def get_logs():

    query = text("""

        SELECT
            session_id,
            agent_name,
            event_type,
            data,
            created_at

        FROM agent_logs

        ORDER BY created_at DESC

        LIMIT 100

    """)

    with engine.connect() as connection:

        result = connection.execute(query)

        rows = result.fetchall()

    logs = []

    for row in rows:

        logs.append(
            {
                "session_id": row[0],
                "agent_name": row[1],
                "event_type": row[2],
                "data": row[3],
                "created_at": str(row[4]),
            }
        )

    return logs


# ---------------------------------------------------
# DASHBOARD METRICS
# ---------------------------------------------------


def get_dashboard_metrics():

    query = text("""

        SELECT status, COUNT(*)

        FROM candidate_approvals

        GROUP BY status

    """)

    with engine.connect() as connection:

        result = connection.execute(query)

        rows = result.fetchall()

    metrics = {"approved": 0, "rejected": 0, "pending": 0}

    for row in rows:

        status = row[0]
        count = row[1]

        metrics[status] = count

    metrics["total"] = metrics["approved"] + metrics["rejected"] + metrics["pending"]

    return metrics
