from pydantic import BaseModel
from typing import List


class InterviewPreparationResponse(BaseModel):

    candidate_summary: str

    strengths: List[str]

    improvement_areas: List[str]

    technical_questions: List[str]

    behavioral_questions: List[str]

    topics_to_prepare: List[str]

    interview_tips: List[str]