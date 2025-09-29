# -*- coding: utf-8 -*-
"""
SpiralEngine：向量化 → 多索引檢索 → 加權融合 → LLM 潤筆 → 回前端
- 嵌入器：NVIDIA nv-embedqa-e5-v5（1024 維；優先讀 config.embedding.api_key）
- 檢索：Case / PulsePJ / RPCase（Hybrid 或 BM25-only）
- 融合：向量分 + 詞面分（缺向量時自動 vec_w=0）
- LLM：僅修飾文字品質與格式，不輸出治療方案
"""

import os
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

# 允許套件/單檔兩種匯入方式
try:
    from .search_engine import SearchEngine
except ImportError:
    from search_engine import SearchEngine

logger = logging.getLogger("s_cbr.SpiralEngine")
logger.setLevel(logging.INFO)


# ---------- NVIDIA 向量器 ----------
class NvidiaEmbedder:
    """
    以 NVIDIA integrate API 產生 1024 維向量
    - 模型：nvidia/nv-embedqa-e5-v5
    - input_type: "query"（查詢用）
    - 金鑰來源：優先用建構子傳入；否則讀環境變數 NVIDIA_API_KEY / NV_API_KEY
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "nvidia/nv-embedqa-e5-v5", timeout: int = 60):
        import requests  # 延遲匯入
        self._requests = requests
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY") or os.getenv("NV_API_KEY")
        if not self.api_key:
            raise RuntimeError("未設定 NVIDIA_API_KEY")
        self.model = model
        self.url = "https://integrate.api.nvidia.com/v1/embeddings"
        self.timeout = timeout
        self.dim = 1024

    def embed(self, text: str, input_type: str = "query") -> List[float]:
        r = self._requests.post(
            self.url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "input": [text], "input_type": input_type},
            timeout=self.timeout,
        )
        if not r.ok:
            raise RuntimeError(f"NVIDIA embeddings error: {r.status_code} {r.text[:200]}")
        vec = r.json()["data"][0]["embedding"]
        if len(vec) != self.dim:
            raise ValueError(f"Embedding 維度 {len(vec)} != {self.dim}")
        return vec


# ---------- 小工具 ----------
_PUNCT = r"[\s,;，。！？、()\[\]{}:：/\\\-]+"

def _as_text(x: Any) -> str:
    if x is None: return ""
    if isinstance(x, str): return x
    if isinstance(x, (list, tuple, set)): return "、".join(map(_as_text, x))
    return str(x)

def _rough_tokens(s: str) -> List[str]:
    s = (s or "").strip()
    if not s: return []
    toks = [t for t in re.split(_PUNCT, s) if t]
    out: List[str] = []
    for t in toks:
        out.append(t)
        if re.search(r"[\u4e00-\u9fff]", t) and len(t) >= 2:
            out.extend([t[i:i+2] for i in range(len(t)-1)])
    seen = set(); ded = []
    for t in out:
        if t not in seen:
            ded.append(t); seen.add(t)
    return ded

def _overlap_score(q: str, doc: str) -> Tuple[float, List[str]]:
    q_toks = _rough_tokens(q)
    if not q_toks: return (0.0, [])
    hits = []
    seen = set()
    for tok in q_toks:
        if tok and tok in doc and tok not in seen:
            hits.append(tok); seen.add(tok)
    score = min(1.0, len(hits) / max(4, len(q_toks)))
    return score, hits[:8]


class SpiralEngine:
    def __init__(self, config: Any = None, search_engine: Optional[SearchEngine] = None, embedder: Any = None, llm: Any = None):
        """
        重要：這裡會「優先讀 config.embedding.api_key」提供給 NvidiaEmbedder 使用。
        若外部已注入 embedder，則直接使用之。
        """
        self.config = config
        self.search_engine = search_engine or SearchEngine(config)
        # 嵌入器決策：優先外部 → 其後讀 config → 最後才用環境變數
        if embedder is not None:
            self.embedder = embedder
        else:
            key_from_cfg = getattr(getattr(config, "embedding", None), "api_key", None)
            if key_from_cfg:
                # 直接建立 NvidiaEmbedder，金鑰取自 config
                self.embedder = NvidiaEmbedder(api_key=key_from_cfg)
            else:
                # 暫不建立，執行時再嘗試從環境變數建立
                self.embedder = None
        # LLM 客戶端（可為 None）：只做語氣/格式潤筆
        self.llm = llm or getattr(getattr(config, "llm", None), "client", None) or getattr(config, "llm_client", None)

    async def execute_spiral_cycle(self, question: str, session_id: str, alpha: float = 0.5, limit: int = 10) -> Dict[str, Any]:
        # 1) 向量（可缺省）
        q_vec: List[float] = []
        try:
            if self.embedder is None:
                # 仍可從環境變數建立備援
                self.embedder = NvidiaEmbedder()
            if hasattr(self.embedder, "embed"):
                q_vec = self.embedder.embed(question, input_type="query")
        except Exception as e:
            logger.warning(f"[Spiral] 產生向量失敗，改 BM25-only：{e}")
            q_vec = []
        logger.info(f"🧭 q_vector: dim={len(q_vec)}")

        # 2) 三索引檢索
        se = self.search_engine
        case_hits  = await se.hybrid_search("Case",    text=question, vector=(q_vec or None), alpha=alpha, limit=limit)
        pulse_hits = await se.hybrid_search("PulsePJ", text=question, vector=(q_vec or None), alpha=alpha, limit=limit)
        rpc_hits   = await se.hybrid_search("RPCase",  text=question, vector=(q_vec or None), alpha=alpha, limit=max(2, limit//2))

        logger.info(f"📊 Case: {len(case_hits)} | PulsePJ: {len(pulse_hits)} | RPCase: {len(rpc_hits)}")

        if not (case_hits or pulse_hits or rpc_hits):
            return {
                "text": "【系統訊息】未檢索到相近內容。請補充舌脈、症狀時序與影響因子後重試。",
                "diagnosis": "",
                "evidence": [],
                "advice": ["補充舌色/苔象與寸關尺脈象", "描述發生時程與誘因（情志/飲食/作息）"],
                "meta": {"retrieval": {"Case":0,"PulsePJ":0,"RPCase":0}, "qdim": len(q_vec)},
            }

        # 3) 統一候選
        def _score(h: Dict[str, Any]) -> float:
            try:
                return float((h.get("_additional") or {}).get("score") or h.get("_confidence") or 0.0)
            except Exception:
                return 0.0

        def _case(h):
            return {
                "source": "Case",
                "id": h.get("src_casev_uuid") or h.get("case_id") or "",
                "diagnosis": _as_text(h.get("diagnosis_main")),
                "pulse": _as_text(h.get("pulse_text")),
                "symptoms": (_as_text(h.get("chiefComplaint")) + " " + _as_text(h.get("presentIllness"))).strip(),
                "_v": _score(h), "raw": h,
            }

        def _pulse(h):
            return {
                "source": "PulsePJ",
                "id": h.get("pid") or h.get("category_id") or "",
                "diagnosis": _as_text(h.get("name")),
                "pulse": "",
                "symptoms": _as_text(h.get("symptoms")),
                "_v": _score(h), "raw": h,
            }

        def _rpc(h):
            return {
                "source": "RPCase",
                "id": h.get("rid") or "",
                "diagnosis": _as_text(h.get("final_diagnosis")),
                "pulse": _as_text(h.get("pulse_tags")),
                "symptoms": _as_text(h.get("symptom_tags")),
                "_v": _score(h), "raw": h,
            }

        cands: List[Dict[str, Any]] = list(map(_case, case_hits)) + list(map(_pulse, pulse_hits)) + list(map(_rpc, rpc_hits))

        # 4) 融合（向量分 + 詞面分）
        vec_w = 0.55 if q_vec else 0.0
        lex_w = 1.0 - vec_w
        for c in cands:
            doc = " ".join([c.get("diagnosis",""), c.get("pulse",""), c.get("symptoms","")])
            lex, hits = _overlap_score(question, doc)
            final = vec_w * max(0.0, float(c.get("_v",0.0))) + lex_w * lex
            src_boost = {"Case": 1.00, "RPCase": 0.98, "PulsePJ": 0.95}.get(c["source"], 1.0)
            c["_lex"] = lex
            c["_final"] = final * src_boost
            c["_hits"] = hits
        cands.sort(key=lambda x: x["_final"], reverse=True)
        best = cands[0]

        # 5) 組裝輸出（交給 LLM 潤筆）
        conclusion = (
            best.get("diagnosis") or
            _as_text(best.get("raw", {}).get("diagnosis_main")) or
            _as_text(best.get("raw", {}).get("final_diagnosis")) or
            _as_text(best.get("raw", {}).get("name")) or
            "根據相近案例推測之候選證候"
        ).strip()

        evid = []
        if best.get("_hits"):
            evid.append("特徵對應：" + "、".join(best["_hits"]))
        if best["source"] == "Case":
            if best.get("pulse"):    evid.append(f"脈象：{best['pulse'][:240]}{'…' if len(best['pulse'])>240 else ''}")
            if best.get("symptoms"): evid.append(f"主訴/現病史：{best['symptoms'][:240]}{'…' if len(best['symptoms'])>240 else ''}")
        elif best["source"] == "RPCase":
            if best.get("pulse"):    evid.append(f"脈象要素：{best['pulse']}")
            if best.get("symptoms"): evid.append(f"症狀要素：{best['symptoms']}")
        else:
            if best.get("symptoms"): evid.append(f"條文/症狀：{best['symptoms']}")
        evid.append(f"融合分：向量 {best.get('_v',0.0):.2f} + 詞面 {best.get('_lex',0.0):.2f} → 最終 {best.get('_final',0.0):.2f}")

        advice = [
            "補齊寸關尺脈象的具體觀察。",
            "紀錄睡眠的入睡潛伏期、夜醒次數/時段、早醒與夢境性質。",
            "標註誘因：情志、咖啡因/酒精、作息變化、合併症或用藥史。",
            "1~2 週後更新資料可提高相似案例的準確度。",
        ]

        base = (
            f"【診斷結果（結論）】\n{conclusion}\n\n"
            f"【依據】\n- " + "\n- ".join(evid) + "\n\n"
            f"【建議（非治療）】\n- " + "\n- ".join(advice)
        )
        final_text = base
        if self.llm:
            try:
                prompt = (
                    "請以專業而精簡的中文，將下列臨床摘要潤筆，維持三段："
                    "【診斷結果（結論）】【依據】【建議（非治療）】；"
                    "不可加入任何治療方案、藥方或劑量；避免冗長與口語。\n====\n" + base
                )
                if hasattr(self.llm, "generate"):
                    final_text = self.llm.generate(prompt=prompt, model=getattr(getattr(self.config, "llm", None), "model", None))
                elif hasattr(self.llm, "chat"):
                    final_text = self.llm.chat(prompt=prompt, model=getattr(getattr(self.config, "llm", None), "model", None))
            except Exception as e:
                logger.warning(f"[Spiral] LLM 潤筆失敗，使用原文：{e}")
                final_text = base

        return {
            "text": final_text,
            "diagnosis": conclusion,
            "evidence": evid,
            "advice": advice,
            "meta": {
                "retrieval": {"Case": len(case_hits), "PulsePJ": len(pulse_hits), "RPCase": len(rpc_hits)},
                "qdim": len(q_vec),
                "best": {"source": best["source"], "id": best.get("id"),
                         "scores": {"vector": best.get("_v",0.0), "lexical": best.get("_lex",0.0), "final": best.get("_final",0.0)}}
            },
        }
