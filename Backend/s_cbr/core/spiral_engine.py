# -*- coding: utf-8 -*-
"""
螺旋推理引擎 v2.1
實現「檢索 → 適配 → 監控 → 回饋」四步迭代
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from ..config import SCBRConfig
from ..knowledge.vector_client import VectorClient
from .search_engine import SearchEngine
from .dialog_manager import DialogManager
from .evaluation import CMSEvaluator
from ..utils.logger import get_logger

logger = get_logger("SpiralEngine")
logger.info(f"📦 SpiralEngine loaded from: {__file__}")


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


    async def execute_spiral_cycle(self, question: str, session_id: str | None = None) -> dict:
        """
        1) 編碼問題 -> q_vector（取不到則退化為 BM25）
        2) 對 Case / PulsePJV / RPCase 做 hybrid 檢索
        3) 以「語義分數 × 屬性加權」融合排序，選出最佳案例
        4) 組裝『診斷結果與建議』（不含任何治療方案）與結構化欄位，給前端直接顯示
        """
        log = logging.getLogger("s_cbr.SpiralEngine")

        # ---- 0) 取得搜尋器（相容兩種屬性名） ----
        srch = getattr(self, "searcher", None) or getattr(self, "search_engine", None)
        if srch is None:
            raise AttributeError("SearchEngine not attached (expected 'self.searcher' or 'self.search_engine').")

        # ---- 1) 向量化問題（容錯，不致命） ----
        q_vec = None
        try:
            if hasattr(self, "embedder"):
                if hasattr(self.embedder, "encode_async"):
                    q_vec = await self.embedder.encode_async(question)
                else:
                    q_vec = self.embedder.encode(question)
        except Exception:
            q_vec = None
        log.info(f"🧭 q_vector: dim={len(q_vec) if isinstance(q_vec, list) else 0}")

        # 供 BM25 的處理文字（若沒有預處理器就用原文）
        processed_text = question or ""
        try:
            tp = getattr(srch, "text_processor", None)
            if tp and hasattr(tp, "clean"):
                processed_text = tp.clean(question)
        except Exception:
            pass

        # ---- 2) 多庫檢索 ----
        top_k = int(getattr(self.config.search, "top_k", 20) or 20)
        case_res   = await srch.hybrid_search("Case",     processed_text, q_vec, top_k)
        pjp_res    = await srch.hybrid_search("PulsePJV", processed_text, q_vec, top_k)
        rpcase_res = await srch.hybrid_search("RPCase",   processed_text, q_vec, top_k)

        def _hits(res: dict, cls: str) -> list[dict]:
            try:
                return res["data"]["Get"].get(cls, []) or []
            except Exception:
                return []

        case_hits   = _hits(case_res,   "Case")
        pjp_hits    = _hits(pjp_res,    "PulsePJV")
        rpcase_hits = _hits(rpcase_res, "RPCase")

        log.info(f"📊 Case 搜索: {len(case_hits)} 個結果")
        log.info(f"📊 PulsePJV 搜索: {len(pjp_hits)} 個結果")
        log.info(f"📊 RPCase 搜索: {len(rpcase_hits)} 個結果")

        # ---- 3) 融合排序（語義 × 屬性） ----
        # 3.1 計算語義置信分數
        def _conf(item: dict) -> float:
            addi = item.get("_additional", {}) if isinstance(item, dict) else {}
            score = addi.get("score", None)
            dist  = addi.get("distance", None)
            if hasattr(srch, "_calculate_confidence"):
                return float(srch._calculate_confidence(score, dist))
            # fallback: 距離越小越好
            try:
                import math
                if isinstance(dist, (int, float)):
                    return 1.0 / (1.0 + max(float(dist), 1e-9))
            except Exception:
                pass
            return float(score) if isinstance(score, (int, float)) else 0.0

        # 3.2 取詢問文本屬性
        q_attrs = self._extract_query_attrs(question, None)

        # 3.3 對 Case 做屬性加權，若 Case 為空才用 RPCase 映射
        candidates: list[dict] = []
        source_used = "Case"

        def _norm_case(hit: dict) -> dict:
            it = dict(hit)  # 保留原始欄位
            it.setdefault("diagnosis_main", it.get("diagnosis_main", "") or "")
            it.setdefault("pulse_text", it.get("pulse_text", "") or "")
            it["_confidence"] = _conf(hit)
            it["_attr_score"] = self._attribute_affinity(q_attrs, it)
            # 權重可由 config 調，這裡語義 0.6、屬性 0.4
            it["_final_score"] = 0.6 * it["_confidence"] + 0.4 * it["_attr_score"]
            return it

        if case_hits:
            candidates = [_norm_case(h) for h in case_hits]
        else:
            # 將 RPCase 映射為通用欄位後再打分
            source_used = "RPCase"
            def _norm_rpcase(hit: dict) -> dict:
                it = dict(hit)
                # 映射 final_diagnosis -> diagnosis_main
                diag = it.get("final_diagnosis", "")
                it["diagnosis_main"] = diag or ""
                # 將 pulse_tags / symptom_tags 串成可讀字串
                ptxt = it.get("pulse_tags", "")
                if isinstance(ptxt, list):
                    ptxt = "、".join(map(str, ptxt))
                stxt = it.get("symptom_tags", "")
                if isinstance(stxt, list):
                    stxt = "、".join(map(str, stxt))
                it["pulse_text"] = ptxt or ""
                it["symptoms"] = stxt or ""
                it["_confidence"] = _conf(hit)
                it["_attr_score"]  = self._attribute_affinity(q_attrs, it)
                it["_final_score"] = 0.6 * it["_confidence"] + 0.4 * it["_attr_score"]
                return it

            candidates = [_norm_rpcase(h) for h in rpcase_hits]

        candidates.sort(key=lambda x: float(x.get("_final_score", 0.0)), reverse=True)
        best = candidates[0] if candidates else None
        log.info(f"best_case keys (sample): {list(best.keys())[:20] if isinstance(best, dict) else None}")

        # ---- 4) 組裝：診斷文字（不含任何治療） ----
        def _txt(v) -> str:
            return "" if v is None else str(v)

        diag_main   = _txt(best.get("diagnosis_main") if best else "")
        pulse_text  = _txt(best.get("pulse_text") if best else "")

        pjp_symptoms = _txt((pjp_hits[0] or {}).get("symptoms") if pjp_hits else "")
        rp_final     = _txt((rpcase_hits[0] or {}).get("final_diagnosis") if rpcase_hits else "")
        rp_pulse     = _txt((rpcase_hits[0] or {}).get("pulse_tags") if rpcase_hits else "")
        rp_sym_tags  = _txt((rpcase_hits[0] or {}).get("symptom_tags") if rpcase_hits else "")

        diagnosis_lines = []
        if diag_main:
            diagnosis_lines.append(f"初步診斷傾向：{diag_main}")
        elif rp_final:
            diagnosis_lines.append(f"初步診斷傾向（推測）：{rp_final}")
        else:
            diagnosis_lines.append("初步診斷傾向：依相似病例與脈象特徵推估，暫列失眠相關證型（待進一步確認）。")

        evidence_bits = []
        if pulse_text:
            evidence_bits.append(f"脈象特徵：{pulse_text}")
        if pjp_symptoms:
            evidence_bits.append(f"症狀要點：{pjp_symptoms}")
        if rp_pulse:
            evidence_bits.append(f"對照脈象標籤：{rp_pulse}")
        if rp_sym_tags:
            evidence_bits.append(f"對照症狀標籤：{rp_sym_tags}")
        if evidence_bits:
            diagnosis_lines.append("主要依據：\n- " + "\n- ".join(evidence_bits))

        advice_steps = [
            "補充問診：入睡困難/多夢頻率、是否易醒、醒後是否難以再入睡、白天精神與記憶力狀況。",
            "伴隨症觀察：心悸、胸悶、頭暈、口乾、盜汗、便溏/便秘、夜間頻尿等是否出現。",
            "客觀資料：近1–2週作息與壓力事件、是否飲用濃茶/咖啡/酒精、藥物或保健品使用史。",
            "脈舌補充：再次確認左寸、右關/尺脈變化；舌質舌苔（淡/紅、苔薄/少/白/黃）。",
            "短期追蹤：記錄1週睡眠日誌（入睡時間、覺醒次數、總睡時、主觀恢復感）。",
        ]
        advice_text = "建議步驟：\n- " + "\n- ".join(advice_steps)

        final_text = "\n\n".join([s for s in ( "\n".join(diagnosis_lines), advice_text ) if s])

        # ---- 5) 回傳 payload（多鍵名同時給，方便前端讀取） ----
        payload = {
            "status": "ok",
            "session_id": session_id,
            "query": question,

            # 主要文字（同內容、多別名）
            "diagnosis_text": final_text,
            "final_text": final_text,
            "result_text": final_text,
            "summary": final_text,

            # 結構化資訊
            "diagnosis": {
                "conclusion": diagnosis_lines[0] if diagnosis_lines else "",
                "evidence": evidence_bits,
                "confidence": float(best.get("_confidence", 0.0)) if best else 0.0,
                "semantic_score": float(best.get("_confidence", 0.0)) if best else 0.0,
                "attribute_score": float(best.get("_attr_score", 0.0)) if best else 0.0,
                "final_score": float(best.get("_final_score", 0.0)) if best else 0.0,
                "source": source_used,
            },
            "recommendation": {
                "steps": advice_steps,
                "note": "以上為診斷流程與資訊補全建議，不含任何治療方案。",
            },

            # 檢索命中（保留做紀錄/除錯）
            "hits": {
                "Case": case_hits,
                "PulsePJV": pjp_hits,
                "RPCase": rpcase_hits,
            },

            # 最佳案例（含分數）
            "best_case": best,
        }

        return payload


