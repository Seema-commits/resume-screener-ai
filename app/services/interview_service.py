from sqlalchemy import text
from app.database.db import engine


def mark_interview_invited(candidate_name):

    query = text("""
        UPDATE candidate_approvals
        SET interview_invite_sent = true,
            interview_invite_date = NOW()
        WHERE candidate_name = :candidate_name
    """)

    with engine.begin() as connection:

        connection.execute(
            query,
            {
                "candidate_name": candidate_name
            }
        )