# -*- coding: utf-8 -*-
"""
Pulse 脈診數據模型
"""

class PulsePattern:
    def __init__(self, pulse_id: str, name: str, category: str, symptoms: list):
        self.pulse_id = pulse_id
        self.name = name
        self.category = category
        self.symptoms = symptoms
