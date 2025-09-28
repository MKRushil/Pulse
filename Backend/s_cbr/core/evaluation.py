# -*- coding: utf-8 -*-
"""
CMS 評估指標計算
案例匹配相似性 (Case Matching Similarity)
"""

from typing import Dict, Any, Optional
from ..config import SCBRConfig


class CMSEvaluator:
    def __init__(self, config: SCBRConfig):
        self.config = config


    def calculate_cms_score(self, case_result: Optional[Dict[str, Any]], question: str) -> float:
        """
        CMS（Case Matching Similarity）
        = 0.5 * 語義相似(_confidence) + 0.3 * 屬性相似(_attr_score) + 0.2 * 證據強度
        證據強度：pulse_support 與 rpcase_support 的命中數正規化後合併（上限 1）
        """
        if not case_result:
            return 0.0

        def _to_float(v, d=0.0):
            try:
                if v is None: return float(d)
                if isinstance(v,(int,float)): return float(v)
                if isinstance(v,str): return float(v.strip())
            except: pass
            return float(d)

        semantic = _to_float(case_result.get("_confidence"), 0.0)       # 0~1
        attr_sim = _to_float(case_result.get("_attr_score"), 0.0)       # 0~1

        # 證據強度：最多以 3 個脈證據、2 個回饋案例計分
        pulse_support = case_result.get("pulse_support") or []
        rpcase_support = case_result.get("rpcase_support") or []
        ev_pulse = min(len(pulse_support), 3) / 3.0
        ev_rp    = min(len(rpcase_support), 2) / 2.0
        evidence = min(1.0, 0.5*ev_pulse + 0.5*ev_rp)

        raw = 0.5*semantic + 0.3*attr_sim + 0.2*evidence
        return round(max(0.0, min(1.0, raw)) * 10, 1)

