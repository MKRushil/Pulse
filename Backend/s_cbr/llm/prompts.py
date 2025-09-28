# -*- coding: utf-8 -*-
"""
提示模板管理
"""

def build_diagnosis_prompt(question: str, case_summary: str) -> str:
    return (
        "你是一位經驗豐富的中醫師，"
        f"請根據以下案例摘要進行診斷：\n案例：{case_summary}\n"
        f"問題：{question}\n"
        "請返回 JSON 格式：{\"diagnosis\":...,\"reasoning\":...,\"confidence\":...}"
    )
