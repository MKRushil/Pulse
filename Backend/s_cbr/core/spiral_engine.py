# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import logging
import json
import asyncio

from s_cbr.config import cfg, SCBRConfig
from s_cbr.core.search_engine import SearchEngine
from s_cbr.llm.embedding import EmbedClient

log = logging.getLogger("s_cbr.SpiralEngine")


# ----------------------------- OpenAI 相容 LLM 客戶端 -----------------------------
class _OpenAICompatClient:
    """若 cfg 沒有 get_llm_client()，用這個以 cfg 的 url/key/model 呼叫 /v1/chat/completions。"""
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def chat_complete(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        try:
            import aiohttp
        except Exception:
            # 沒安裝 aiohttp 時，直接回退
            return "診斷結果：候選證型。\n建議：調整作息與情志管理。"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                data = await resp.json()
                # 盡量相容 openai 與一些代理
                try:
                    return data["choices"][0]["message"]["content"]
                except Exception:
                    return json.dumps(data, ensure_ascii=False)


# --------------------------------- 主引擎 ---------------------------------
class SpiralEngine:
    def __init__(
        self,
        config: SCBRConfig = cfg,
        search_engine: Optional[SearchEngine] = None,
        embed_client: Optional[EmbedClient] = None,
    ) -> None:
        self.cfg: SCBRConfig = config
        self.SE: SearchEngine = search_engine or SearchEngine(self.cfg)
        self.embedder: EmbedClient = embed_client or EmbedClient(self.cfg)

        self.alpha: float = getattr(self.cfg, "HYBRID_ALPHA", 0.5)
        self.k: int = getattr(self.cfg, "TOP_K", 10)

        self.case_fields = ["bm25_cjk"]
        self.pulse_fields = ["bm25_cjk"]
        self.rpcase_fields = ["bm25_text"]

        self.case_props = ["case_id", "chiefComplaint", "presentIllness", "pulse_text", "search_text"]
        self.pulse_props = ["pid", "name", "category", "category_id", "symptoms", "main_disease", "search_text"]
        self.rpcase_props = ["symptom_tags", "pulse_tags", "final_diagnosis"]

        # LLM 客戶端：優先 cfg.get_llm_client()；否則以 (url/key) 自建
        self._llm_client = None
        if hasattr(self.cfg, "get_llm_client"):
            try:
                self._llm_client = self.cfg.get_llm_client()
            except Exception as e:
                log.warning("[LLM] cfg.get_llm_client() 失敗：%s，改用 OpenAI 相容客戶端", e)
        if self._llm_client is None and hasattr(self.cfg, "LLM_URL") and hasattr(self.cfg, "LLM_API_KEY"):
            self._llm_client = _OpenAICompatClient(self.cfg.LLM_URL, self.cfg.LLM_API_KEY)

        self._llm_model = getattr(self.cfg, "LLM_MODEL", "gpt-4o-mini")

    # ------------------------- 外部調用的單輪流程 -------------------------
    async def execute_spiral_cycle(self, question: str, session_id: str) -> Dict[str, Any]:
        # 1) 向量
        qvec: Optional[List[float]] = None
        try:
            qvec = await self.embedder.embed(question)
            log.info("🧭 q_vector: dim=%s", len(qvec) if qvec else 0)
        except Exception as e:
            log.warning("[Spiral] 產生向量失敗，改 BM25-only：%s", e)

        # 2) 三庫檢索（await）
        case_hits, pulse_hits, rpcase_hits = await asyncio.gather(
            self._search_case(question, qvec),
            self._search_pulse(question, qvec),
            self._search_rpcase(question, qvec),
        )

        log.info("📊 Case: %s | RPCase: %s | PulsePJ: %s", len(case_hits), len(rpcase_hits), len(pulse_hits))
        self._log_hits("Case RAW", case_hits[:3])
        self._log_hits("PulsePJ RAW", pulse_hits[:3])
        if rpcase_hits:
            self._log_hits("RPCase RAW", rpcase_hits[:3])
        else:
            log.info("[RPCase RAW] (no hits)")

        # 3) Top-1
        case_top = case_hits[0] if case_hits else None
        pulse_top = pulse_hits[0] if pulse_hits else None
        rpcase_top = rpcase_hits[0] if rpcase_hits else None

        log.info("[TOP1] Case:\n%s", self._pretty(case_top))
        log.info("[TOP1] RPCase:\n%s", self._pretty(rpcase_top))
        log.info("[TOP1] PulsePJ:\n%s", self._pretty(pulse_top))

        # 4) 融合（主=Case；輔=Pulse）
        fused_primary = self._fuse_primary(case_top)
        fused_supp = self._fuse_pulse(pulse_top)
        log.info("[FUSE] Case top fused:\n%s", self._pretty(fused_primary))
        log.info("[FUSE] RPCase top fused:\n%s", self._pretty(self._fuse_rpcase(rpcase_top)))
        log.info("[FUSE] Pulse top fused:\n%s", self._pretty(fused_supp))

        primary = fused_primary
        supplement = fused_supp
        log.info("[FUSE] Primary selected:\n%s", self._pretty(primary))
        log.info("[FUSE] Supplement selected:\n%s", self._pretty(supplement))

        fused_sentence = self._build_fused_sentence(primary, supplement)
        log.info("[FUSED_SENTENCE] %s", fused_sentence)

        # 5) 產出你要的版面
        final_text = await self._call_llm_and_format(question, primary, supplement, fused_sentence)
        log.info("[LLM] final_text:\n%s", final_text)

        # 6) 回傳（同時提供多個鍵名，避免前端取不到）
        return {
            "ok": True,
            "question": question,
            "primary": primary,
            "supplement": supplement,
            "fused_sentence": fused_sentence,
            "text": final_text,         # 給前端 data.text
            "answer": final_text,       # 給前端 data.answer
            "final_text": final_text,   # 給前端 data.final_text
        }

    # ------------------------------ 檢索 ------------------------------
    async def _search_case(self, text: str, vec: Optional[List[float]]) -> List[Dict[str, Any]]:
        return await self.SE.hybrid_search(
            index="Case",
            text=text,
            vector=vec,
            alpha=self.alpha,
            limit=self.k,
            search_fields=self.case_fields,
            return_props=self.case_props,
        )

    async def _search_pulse(self, text: str, vec: Optional[List[float]]) -> List[Dict[str, Any]]:
        return await self.SE.hybrid_search(
            index="PulsePJ",
            text=text,
            vector=vec,
            alpha=self.alpha,
            limit=self.k,
            search_fields=self.pulse_fields,
            return_props=self.pulse_props,
        )

    async def _search_rpcase(self, text: str, vec: Optional[List[float]]) -> List[Dict[str, Any]]:
        return await self.SE.hybrid_search(
            index="RPCase",
            text=text,
            vector=vec,
            alpha=self.alpha,
            limit=self.k,
            search_fields=self.rpcase_fields,
            return_props=self.rpcase_props,
        )

    # ------------------------------ 融合 ------------------------------
    def _score_from_hit(self, hit: Optional[Dict[str, Any]]) -> float:
        if not hit:
            return 0.0
        addi = hit.get("_additional") or {}
        if "score" in addi and addi["score"] is not None:
            try:
                return float(addi["score"])
            except Exception:
                return 0.0
        if "distance" in addi and addi["distance"] is not None:
            try:
                d = float(addi["distance"])
                return max(0.0, 1.0 - d)
            except Exception:
                return 0.0
        return 0.0

    def _extract_lex_hits(self, raw_text: str) -> List[str]:
        if not raw_text:
            return []
        keys = ["失眠", "多夢", "心悸", "口乾", "左寸", "白天", "夜醒", "情志"]
        return [k for k in keys if k in raw_text][:5]

    def _fuse_primary(self, top_hit: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not top_hit:
            return None
        case_id = top_hit.get("case_id") or top_hit.get("id") or ""
        cc = top_hit.get("chiefComplaint") or ""
        pi = top_hit.get("presentIllness") or ""
        pulse = top_hit.get("pulse_text") or ""
        stext = top_hit.get("search_text") or ""

        v = self._score_from_hit(top_hit)
        lex_list = self._extract_lex_hits(stext)
        lex = len(lex_list) / 37.0
        final = 0.8 * v + 0.2 * lex

        return {
            "source": "Case",
            "id": str(case_id),
            "diagnosis": "",
            "pulse": pulse,
            "symptoms": f"{cc} {pi}".strip(),
            "_v": v,
            "raw": {**top_hit, "_confidence": v, "_attr_score": 0.0, "_final_score": v},
            "_lex": lex,
            "_final": final,
            "_hits": lex_list,
        }

    def _fuse_pulse(self, top_hit: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not top_hit:
            return None
        pid = top_hit.get("pid") or top_hit.get("id") or ""
        name = top_hit.get("name") or ""
        symptoms = top_hit.get("symptoms")
        sym_txt = "、".join(symptoms) if isinstance(symptoms, list) else (symptoms or "")
        stext = top_hit.get("search_text") or ""

        v = self._score_from_hit(top_hit)
        lex_list = self._extract_lex_hits(stext)
        lex = len(lex_list) / 37.0
        final = 0.6 * v + 0.4 * lex

        return {
            "source": "PulsePJ",
            "id": str(pid),
            "diagnosis": name,
            "pulse": "",
            "symptoms": sym_txt,
            "_v": v,
            "raw": {**top_hit, "_confidence": v, "_attr_score": 0.0, "_final_score": v},
            "_lex": lex,
            "_final": final,
            "_hits": lex_list,
        }

    def _fuse_rpcase(self, top_hit: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return top_hit

    def _build_fused_sentence(self, primary: Optional[Dict[str, Any]], supplement: Optional[Dict[str, Any]]) -> str:
        if not primary:
            return ""
        parts = []
        parts.append(f"參考案例（主體 Case {primary.get('id','')}，輔助 PulsePJ {supplement.get('id','') if supplement else 'NA'}）：")
        if primary.get("symptoms"):
            parts.append(f"症狀表現：{primary['symptoms']}；")
        if primary.get("pulse"):
            parts.append(f"脈象：{primary['pulse']}；")
        if supplement and supplement.get("symptoms"):
            parts.append(f"輔助條文：{supplement['symptoms']}；")
        parts.append(f"融合分：{primary.get('_final', 0.0):.2f}")
        return " ".join(parts)

    # ------------------------------ LLM 與版面 ------------------------------
    async def _call_llm_and_format(
        self,
        question: str,
        primary: Optional[Dict[str, Any]],
        supplement: Optional[Dict[str, Any]],
        fused_sentence: str,
    ) -> str:
        case_id = primary.get("id", "") if primary else ""
        pulse_sym = supplement.get("symptoms", "") if supplement else ""

        # prompt：不要求任何舌診，避免 LLM 生成舌/苔
        prompt = f"""你是一位中醫輔助決策系統，只輸出兩段：診斷結果、建議（非治療）。
題目是病人的當前描述，另外提供一則融合參考案例（主體為 Case，Pulse 為輔助）。
注意：不要描述舌、舌苔、舌象等內容，不要提供處方。

[當前問題]
{question}

[融合參考案例]
{fused_sentence}

[請輸出（只寫內容，不要重複標題）]
1) 診斷結果：一句話給出證型（如「心脾兩虛，兼陰虛內熱」）
2) 建議：兩到三行，聚焦作息/情志/飲食；不要寫任何舌診或處方。
"""

        llm_text = ""
        if self._llm_client is not None:
            try:
                llm_text = await self._llm_client.chat_complete(
                    model=self._llm_model,
                    messages=[
                        {"role": "system", "content": "你是嚴謹的中醫輔助決策助手。"},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                )
            except Exception as e:
                log.warning("[LLM] 調用失敗，fallback：%s", e)

        if not llm_text:
            llm_text = "診斷結果：候選證型。\n建議：調整作息、管理情志，減少咖啡因與刺激性飲食。"

        diag, adv = self._split_diag_and_advice(llm_text)

        # 過濾「舌/苔」相關句子
        diag = self._filter_tongue(diag)
        adv = self._filter_tongue(adv)

        lines: List[str] = []
        #lines.append("模擬案例輸出")
        lines.append("")
        lines.append(f"使用案例編號：{case_id}")
        lines.append("")
        lines.append("當前問題：")
        lines.append(question.strip())
        lines.append("")
        lines.append("依據過往案例線索 : ")
        if primary:
            if primary.get("_hits"):
                lines.append(f"- 關鍵線索：{'、'.join(primary['_hits'])}")
            if primary.get("pulse"):
                lines.append(f"- 脈象：{primary['pulse']}")
            if primary.get("symptoms"):
                lines.append(f"- 症狀：{primary['symptoms']}")
        if pulse_sym:
            lines.append(f"- 輔助條文：{pulse_sym}")
        lines.append("")
        lines.append("診斷結果：")
        lines.append(diag if diag else "（無）")
        lines.append("")
        lines.append("建議：")
        lines.append(adv if adv else "（無）")
        return "\n".join(lines)

    def _split_diag_and_advice(self, llm_text: str) -> Tuple[str, str]:
        text = (llm_text or "").strip()
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        diag, adv = "", ""
        for i, ln in enumerate(lines):
            if "診斷" in ln or ln.startswith("1)"):
                seg = [ln]
                for j in range(i + 1, len(lines)):
                    if "建議" in lines[j] or lines[j].startswith("2)"):
                        break
                    seg.append(lines[j])
                diag = " ".join(seg)
                break
        for i, ln in enumerate(lines):
            if "建議" in ln or ln.startswith("2)"):
                adv = " ".join(lines[i:])
                break
        # 清標頭
        for p in ("1)", "2)", "診斷結果：", "診斷結果:", "建議：", "建議:"):
            if diag.startswith(p):
                diag = diag[len(p):].strip()
            if adv.startswith(p):
                adv = adv[len(p):].strip()
        return diag, adv

    def _filter_tongue(self, s: str) -> str:
        """去掉含『舌』『苔』的句子。"""
        if not s:
            return s
        seps = ["。", "；", ";", ".", "\n"]
        tmp = [s]
        for sp in seps:
            tmp = [p for chunk in tmp for p in chunk.split(sp)]
        kept = [p for p in tmp if p and ("舌" not in p and "苔" not in p)]
        return "；".join(kept)

    # ------------------------------ 小工具 ------------------------------
    def _pretty(self, obj: Any) -> str:
        try:
            return json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            return str(obj)

    def _log_hits(self, title: str, hits: List[Dict[str, Any]]) -> None:
        if not hits:
            log.info("[%s] (no hits)", title)
            return
        for i, h in enumerate(hits, 1):
            log.info("[%s] #%d\n%s", title, i, self._pretty(h))
