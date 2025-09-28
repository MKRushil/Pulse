# -*- coding: utf-8 -*-
"""
Case 案例數據模型
"""

from typing import List

class Case:
    def __init__(self, case_id: str, summary: str, symptoms: List[str]):
        self.case_id = case_id
        self.summary = summary
        self.symptoms = symptoms
