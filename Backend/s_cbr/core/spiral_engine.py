# -*- coding: utf-8 -*-
"""
螺旋推理引擎 v2.1
實現「檢索 → 適配 → 監控 → 回饋」四步迭代
"""

import asyncio
from typing import Dict, Any, List, Optional
from ..config import SCBRConfig
from ..knowledge.vector_client import VectorClient
from .search_engine import SearchEngine
from .dialog_manager import DialogManager
from .evaluation import CMSEvaluator
from ..utils.logger import get_logger

logger = get_logger("SpiralEngine")


class SpiralEngine:
    def __init__(self, config: SCBRConfig):
        self.config = config
        self.searcher = SearchEngine(config)
        self.dialog = DialogManager(config)
        self.evaluator = CMSEvaluator(config)
        self.version = "2.1.0"
        logger.info(f"螺旋推理引擎 v{self.version} 初始化完成")

    def _extract_query_attrs(self, question: str, patient_ctx: dict | None) -> dict:
        import re
        text = (question or "") + " " + (" ".join(patient_ctx.get("symptoms", [])) if isinstance(patient_ctx, dict) else "")
        attrs = {"gender": None, "age": None, "pulses": [], "symptoms": []}
        if "女" in text: attrs["gender"] = "女"
        elif "男" in text: attrs["gender"] = "男"
        m = re.search(r"(\d{1,3})\s*歲", text)
        if m:
            try: attrs["age"] = int(m.group(1))
            except: pass
        pulse_positions = ["左寸","左關","左尺","右寸","右關","右尺"]
        pulse_kws = ["遲","數","滑","弦","細","沉","浮","虛","實","緩","促","結","代"]
        for pos in pulse_positions:
            for kw in pulse_kws:
                if pos in text and kw in text:
                    attrs["pulses"].append(f"{pos}:{kw}")
        sym_kws = ["失眠","多夢","心悸","健忘","胸悶","口乾","口苦","焦慮","煩躁","畏寒","手足心熱","盜汗"]
        attrs["symptoms"] = [k for k in sym_kws if k in text]
        return attrs

    def _attribute_affinity(self, q: dict, item: dict) -> float:
        # 欄位取值（防呆）
        gender = (item.get("gender") or item.get("sex") or "").strip()
        age = item.get("age")
        case_pulse_text = (item.get("pulse") or item.get("pulse_text") or item.get("maixiang") or "")
        case_symp_text  = (item.get("symptoms") or item.get("chief_complaint") or item.get("subjective") or "")
        # 權重
        w_gender, w_age, w_pulse, w_sym = 0.1, 0.2, 0.5, 0.2

        # 性別
        s_gender = 1.0 if (q.get("gender") and q["gender"] in gender) else (0.5 if q.get("gender") else 0.0)
        # 年齡
        s_age = 0.0
        try:
            qa, ca = int(q.get("age") or -1), int(age if isinstance(age,(int,float,str)) else -999)
            if qa>0 and ca>0:
                diff = abs(qa - ca)
                s_age = 1.0 if diff <= 5 else (0.7 if diff <= 10 else (0.4 if diff <= 20 else 0.1))
        except: pass
        # 脈象
        s_pulse = 0.0
        if q.get("pulses"):
            hits = 0
            for tag in q["pulses"]:
                pos, typ = tag.split(":")
                if pos in case_pulse_text and typ in case_pulse_text: hits += 1
                elif typ in case_pulse_text: hits += 0.5
            s_pulse = min(1.0, hits / max(1.0, len(q["pulses"])))
        # 症狀
        s_sym = 0.0
        if q.get("symptoms"):
            hit = sum(1 for k in q["symptoms"] if k in case_symp_text)
            s_sym = hit / max(1.0, len(q["symptoms"]))
        return w_gender*s_gender + w_age*s_age + w_pulse*s_pulse + w_sym*s_sym

    def _fuse_and_rank(self, question: str, patient_ctx: dict | None,
                    case_results: list[dict], pulse_results: list[dict], rpcase_results: list[dict],
                    weights: dict | None = None) -> dict:
        # 語義×屬性融合排序
        def _to_float(v, d=0.0):
            try:
                if v is None: return float(d)
                if isinstance(v,(int,float)): return float(v)
                if isinstance(v,str): return float(v.strip())
            except: pass
            return float(d)

        w = {"semantic": 0.6, "attribute": 0.4}
        if isinstance(weights, dict):
            w.update({k:v for k,v in weights.items() if k in w})

        qattrs = self._extract_query_attrs(question, patient_ctx or {})
        ranked = []
        for it in (case_results or []):
            sem = _to_float(it.get("_confidence"), 0.0)
            attr = self._attribute_affinity(qattrs, it)
            it["_attr_score"]  = attr
            it["_final_score"] = w["semantic"]*sem + w["attribute"]*attr
            ranked.append(it)
        ranked.sort(key=lambda x: _to_float(x.get("_final_score"),0.0), reverse=True)
        return {
            "best_case": ranked[0] if ranked else None,
            "ranked_cases": ranked,
            "pulse_support": (pulse_results or [])[:3],
            "rpcase_support": (rpcase_results or [])[:2],
            "query_attrs": qattrs
        }


    async def execute_spiral_cycle(
        self,
        question: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        執行一輪螺旋推理：檢索 → 適配 → 監控 → 回饋
        """
        # 0) 先確保會話存在
        self.dialog.continue_session(session_id=session_id, initial_question=question, patient_ctx={})

        # 1) 生成查詢向量並做三庫混合檢索
        from ..llm.embedding import EmbedClient
        embed_client = EmbedClient(self.config)
        q_vector = await embed_client.embed(question)
        tasks = [
            self.searcher.hybrid_search("Case",     question, q_vector, limit=self.config.search.vector_limit),
            self.searcher.hybrid_search("PulsePJV", question, q_vector, limit=self.config.search.vector_limit),
            self.searcher.hybrid_search("RPCase",   question, q_vector, limit=self.config.search.vector_limit),
        ]
        case_results, pulse_results, rpcase_results = await asyncio.gather(*tasks)

        # 2) 語義×屬性 融合排序，取得最相近案例
        fusion = self._fuse_and_rank(
            question=question,
            patient_ctx={},
            case_results=case_results,
            pulse_results=pulse_results,
            rpcase_results=rpcase_results,
            weights={"semantic":0.6, "attribute":0.4},
        )
        best_case = fusion["best_case"]

        # 3) 監控：CMS（會用到 _confidence/_attr_score 與證據數）
        cms_score = self.evaluator.calculate_cms_score(best_case, question)

        # 4) 回饋：只輸出診斷結果與建議（不含任何治療方案）
        qa = fusion["query_attrs"]
        bits = []
        if qa.get("gender"):   bits.append(f"性別匹配：{qa['gender']}")
        if qa.get("age"):      bits.append(f"年齡相近：{qa['age']} 歲")
        if qa.get("pulses"):   bits.append("脈象命中：" + "、".join(qa["pulses"]))
        if qa.get("symptoms"): bits.append("症狀關鍵詞：" + "、".join(qa["symptoms"]))

        advice = [
            "建議補充問診：入睡潛伏期、夜醒次數/時段、是否早醒、日間嗜睡程度、情志壓力與生活作息。",
            "建議觀察：近一週脈象是否持續偏慢（遲脈）及有無寒熱虛實相關表現。",
            "建議檢視睡眠衛生與刺激物（咖啡因/酒精/藥物）暴露，先排除干擾因子。"
        ]
        logger.debug(f"best_case keys: {list(best_case.keys())}")
        def _pick_case_diagnosis(case: dict) -> str:
            # 依序嘗試多種欄位名稱，抓到第一個非空字串就用
            candidates = ["diagnosis_main","diagnosis","辨證","syndrome","主診斷","pattern","證型",
              "證候","證名","final_dx"]
            for k in candidates:
                val = case.get(k)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            return "未能確定"

        diag_text = _pick_case_diagnosis(best_case) if best_case else "未能確定"


        diagnosis = {
            "diagnosis": diag_text,
            "confidence": min(1.0, cms_score/10.0),
            "reasoning": "；".join(bits) or f"依語義與屬性融合排序的最高匹配案例（CMS={cms_score}）",
            "advice": advice,
            "support_case_id": (best_case.get("case_id") if best_case else None),
            "pulse_support": fusion["pulse_support"],
            "rpcase_support": fusion["rpcase_support"],
            "cms_score": cms_score,
            "round": self.dialog.increment_round(session_id),
            "continue_available": cms_score < self.config.spiral.convergence_threshold
        }

        self.dialog.record_step(session_id, diagnosis)
        return diagnosis