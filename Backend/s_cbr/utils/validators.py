# -*- coding: utf-8 -*-
"""
數據驗證
"""

def validate_question(q: str):
    if not q or not q.strip():
        raise ValueError("問題不可為空")
