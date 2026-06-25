from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    Boolean
)

from datetime import datetime
from app.database.db import Base

Base = declarative_base()


# ---------------------------------------------------
# Candidate Approval Table
# ---------------------------------------------------

class CandidateApproval(Base):

    __tablename__ = "candidate_approvals"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String)

    candidate_name = Column(String)

    agent_name = Column(String)

    status = Column(String)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    email = Column(String)

    interview_invite_sent = Column(
        Boolean,
        default=False
    )

    interview_invite_date = Column(DateTime)

# ---------------------------------------------------
# Agent Logs Table
# ---------------------------------------------------

class AgentLog(Base):

    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True)

    session_id = Column(String)

    agent_name = Column(String)

    event_type = Column(String)

    data = Column(JSON)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )