# scbr/models/schemas.py
from pydantic import BaseModel
from typing import Optional, Dict, Any

class TurnInput(BaseModel):
    session_id: str
    user_query: str
    meta: Optional[Dict[str, Any]] = None

class TurnOutput(BaseModel):
    session_id: str
    turn_index: int
    diagnosis: str
    suggestions: str
    chosen_case_id: Optional[str] = None
    confidence: float
    scores: Dict[str, float]
    metrics: Dict[str, float]
    trace: Dict[str, Any]

class SaveCaseInput(BaseModel):
    session_id: str
    satisfied: bool
    final_problem: str
    final_diagnosis: str
    final_suggestions: str
