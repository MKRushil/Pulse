# -*- coding: utf-8 -*-
"""
會話數據模型
"""

import uuid
from typing import List, Dict, Any

class Session:
    def __init__(self, initial_question: str, patient_ctx: Dict[str,Any]):
        self.session_id = uuid.uuid4().hex
        self.accumulated_question = initial_question
        self.patient_ctx = patient_ctx
        self.round_count = 0
        self.history: List[Dict[str,Any]] = []
