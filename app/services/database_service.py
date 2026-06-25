from app.database.db import SessionLocal
from app.database.models import (
    CandidateApproval
)


def save_candidate_approval(
    session_id,
    candidate_name,
    email,
    agent_name,
    status
):

    db = SessionLocal()

    approval = CandidateApproval(
        session_id=session_id,
        candidate_name=candidate_name,
        agent_name=agent_name,
        status=status,
        email=email
    )

    db.add(approval)

    db.commit()

    db.close()