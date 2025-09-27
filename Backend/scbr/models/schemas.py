# scbr/models/schemas.py (片段)
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

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

# 新增資料模型 Schema
class Case(BaseModel):
    case_id: str
    chief_complaint: str
    present_illness: str
    tentative_diagnosis: str
    # 可以加入其他欄位：症狀列表、脈象、舌象等。為簡化，此處略去。

class PulsePJV(BaseModel):
    name: str            # 脈象名稱，例如 "沉脈"
    description: str     # 描述該脈象的文字
    related_diagnoses: Optional[List[str]] = None  # 可選，相關的證型列表

class RPCase(BaseModel):
    pattern: str         # 證型名稱，例如 "心肝血虛"
    prescription: str    # 推薦處方或方案，例如 "甘麥大棗湯"
    info: Optional[str] = None  # 可選，附加說明，如處方組成
