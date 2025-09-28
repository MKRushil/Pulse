# -*- coding: utf-8 -*-
"""
診斷結果數據模型
"""

from typing import List, Dict, Any

class Diagnosis:
    def __init__(self, diag: str, conf: float, reasoning: str,
                 pulse_support: List[Any], rpcase_support: List[Any]):
        self.diagnosis = diag
        self.confidence = conf
        self.reasoning = reasoning
        self.pulse_support = pulse_support
        self.rpcase_support = rpcase_support
