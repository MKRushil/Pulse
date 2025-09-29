# -*- coding: utf-8 -*-
"""
SpiralEngine：單輪推理編排（融合一句版）
流程：
1) 產生向量（NVIDIA；失敗則 BM25-only）
2) Case / RPCase / PulsePJ 混合檢索，各自取 Top-1
3) 對 Top-1 做「向量分 + 詞面分」融合（可在無向量時自動降權）
4) 主體：Case 與 RPCase 比較，取分高者；都沒有時用 PulsePJ 頂上
5) 輔助：PulsePJ Top-1（若存在且不同於主體）
6) 以主體+輔助生成「單一句 融合參考案例（fused_case_text）」→ 餵 LLM
7) 回傳 text / diagnosis_text / diagnosis（同文，避免前端空白）
8) Logger：原始命中、Top-1、融合後、LLM 最終文字、以及 fused_case_text

注意：此檔案不涉及任何治療方案輸出。
"""

import os
import re
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

# 嘗試兩種相對/絕對匯入
try:
    from .search_engine import SearchEngine
except ImportError:
    from search_engine import SearchEngine

logger = logging.getLogger("s_cbr.SpiralEngine")
logger.setLevel(logging.INFO)

# ---------------- 小工具 ----------------
_PUNCT = r"[\s,;，。！？、()\[\]{}:：/\\\-]+"

def _short(s: str, n: int = 1000) -> str:
    if s is None: return ""
    return (s[:n] + " …(截斷)") if len(s) > n else s

def _pp(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)

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
    hits, seen = [], set()
    for tok in q_toks:
        if tok and tok in doc and tok not in seen:
            hits.append(tok); seen.add(tok)
    score = min(1.0, len(hits) / max(4, len(q_toks)))
    return score, hits[:8]

def _slim_hit(hit: dict, keep_props=None) -> dict:
    keep = set(keep_props or [])
    slim = {}
    addi = hit.get("_additional") or {}
    slim["_score"] = addi.get("score")
    slim["_distance"] = addi.get("distance")
    for k in [
        # Case
        "case_id","chiefComplaint","presentIllness","pulse_text","search_text",
        # PulsePJ
        "pid","name","category","main_disease","symptoms",
        # RPCase
        "rid","final_diagnosis","pulse_tags","symptom_tags",
    ]:
        if k in hit:
            v = hit[k]
            slim[k] = _short(v, 300) if isinstance(v, str) else v
    for k in keep:
        if k in hit and k not in slim:
            slim[k] = hit[k]
    return slim

# ---------------- NVIDIA 向量器 ----------------
class NvidiaEmbedder:
    """NVIDIA Integrate Embeddings API（nvidia/nv-embedqa-e5-v5, 1024 維）"""
    def __init__(self, api_key: Optional[str] = None, model: str = "nvidia/nv-embedqa-e5-v5", timeout: int = 60):
        import requests
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

# ---------------- 主引擎 ----------------
class SpiralEngine:
    def __init__(self, config: Any = None, search_engine: Optional[SearchEngine] = None, embedder: Any = None, llm: Any = None):
        self.config = config
        self.search_engine = search_engine or SearchEngine(config)

        if embedder is not None:
            self.embedder = embedder
        else:
            key_from_cfg = getattr(getattr(config, "embedding", None), "api_key", None)
            self.embedder = NvidiaEmbedder(api_key=key_from_cfg) if key_from_cfg else None

        # LLM 客戶端（可為 None；則走內建基準稿）
        self.llm = llm or getattr(getattr(config, "llm", None), "client", None) or getattr(config, "llm_client", None)

    async def execute_spiral_cycle(self, question: str, session_id: str, alpha: float = 0.5, limit: int = 10) -> Dict[str, Any]:
        # 1) 向量（可降級）
        q_vec: List[float] = []
        try:
            if self.embedder is None:
                self.embedder = NvidiaEmbedder()
            if hasattr(self.embedder, "embed"):
                q_vec = self.embedder.embed(question, input_type="query")
        except Exception as e:
            logger.warning(f"[Spiral] 產生向量失敗，改 BM25-only：{e}")
            q_vec = []
        logger.info(f"🧭 q_vector: dim={len(q_vec)}")

        # 2) 檢索
        se = self.search_engine
        case_hits  = await se.hybrid_search("Case",    text=question, vector=(q_vec or None), alpha=alpha, limit=max(1, limit))
        pulse_hits = await se.hybrid_search("PulsePJ", text=question, vector=(q_vec or None), alpha=alpha, limit=max(1, limit))
        rpc_hits   = await se.hybrid_search("RPCase",  text=question, vector=(q_vec or None), alpha=alpha, limit=max(1, limit))
        logger.info(f"📊 Case: {len(case_hits)} | RPCase: {len(rpc_hits)} | PulsePJ: {len(pulse_hits)}")

        # 【1】原始命中（精簡展示）
        try:
            logger.debug("[RET] Case hits (slim):\n"    + _pp([_slim_hit(h) for h in case_hits]))
            logger.debug("[RET] RPCase hits (slim):\n"  + _pp([_slim_hit(h) for h in rpc_hits]))
            logger.debug("[RET] PulsePJ hits (slim):\n" + _pp([_slim_hit(h) for h in pulse_hits]))
        except Exception as e:
            logger.warning(f"[Log] dump raw hits failed: {e}")

        if not (case_hits or rpc_hits or pulse_hits):
            empty_msg = "【系統訊息】未檢索到相近內容。請補充舌脈、症狀時序與影響因子後重試。"
            return {
                "text": empty_msg,
                "diagnosis_text": empty_msg,
                "diagnosis": empty_msg,
                "evidence": [],
                "advice": ["補充舌色/苔象與寸關尺脈象", "描述發生時程與誘因（情志/飲食/作息）"],
                "primary_source": None,
                "primary_id": None,
                "supplement": None,
                "meta": {"retrieval": {"Case":0,"RPCase":0,"PulsePJ":0}, "qdim": len(q_vec)},
            }

        # 3) 轉為統一候選（Top-1）
        def _score(h: Dict[str, Any]) -> float:
            try:
                return float((h.get("_additional") or {}).get("score") or h.get("_confidence") or 0.0)
            except Exception:
                return 0.0

        def _to_case(h: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "source": "Case",
                "id": h.get("src_casev_uuid") or h.get("case_id") or "",
                "diagnosis": _as_text(h.get("diagnosis_main")),
                "pulse": _as_text(h.get("pulse_text")),
                "symptoms": (_as_text(h.get("chiefComplaint")) + " " + _as_text(h.get("presentIllness"))).strip(),
                "_v": _score(h), "raw": {**h, "_additional": h.get("_additional", {})},
            }

        def _to_rpc(h: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "source": "RPCase",
                "id": h.get("rid") or "",
                "diagnosis": _as_text(h.get("final_diagnosis")),
                "pulse": _as_text(h.get("pulse_tags")),
                "symptoms": _as_text(h.get("symptom_tags")),
                "_v": _score(h), "raw": {**h, "_additional": h.get("_additional", {})},
            }

        def _to_pulse(h: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "source": "PulsePJ",
                "id": h.get("pid") or h.get("category_id") or "",
                "diagnosis": _as_text(h.get("name")),
                "pulse": "",
                "symptoms": _as_text(h.get("symptoms")),
                "_v": _score(h), "raw": {**h, "_additional": h.get("_additional", {})},
            }

        top_case  = _to_case(case_hits[0])   if case_hits  else None
        top_rpc   = _to_rpc(rpc_hits[0])     if rpc_hits   else None
        top_pulse = _to_pulse(pulse_hits[0]) if pulse_hits else None

        # 【2】Top-1
        try:
            logger.info("[TOP1] Case:\n"   + _pp(top_case))
            logger.info("[TOP1] RPCase:\n" + _pp(top_rpc))
            logger.info("[TOP1] PulsePJ:\n"+ _pp(top_pulse))
        except Exception as e:
            logger.warning(f"[Log] dump top-1 failed: {e}")

        # 4) 融合分（向量+詞面）
        def _fuse(cand: Dict[str, Any]) -> Dict[str, Any]:
            doc = " ".join([cand.get("diagnosis",""), cand.get("pulse",""), cand.get("symptoms","")])
            lex, hits = _overlap_score(question, doc)
            vec = max(0.0, float(cand.get("_v", 0.0)))
            vec_w = 0.55 if q_vec else 0.0
            lex_w = 1.0 - vec_w
            final = vec_w * vec + lex_w * lex
            return {**cand, "_lex": lex, "_final": final, "_hits": hits}

        if top_case:  top_case  = _fuse(top_case)
        if top_rpc:   top_rpc   = _fuse(top_rpc)
        if top_pulse: top_pulse = _fuse(top_pulse)

        # 5) 主體/輔助決策
        if top_case and top_rpc:
            primary = top_case if top_case["_final"] >= top_rpc["_final"] else top_rpc
        elif top_case or top_rpc:
            primary = top_case or top_rpc
        else:
            primary = top_pulse

        supplement = top_pulse if (top_pulse and (primary is not top_pulse)) else None

        # 【3】融合後 & 選擇
        try:
            logger.info("[FUSE] Case top fused:\n"   + _pp(top_case))
            logger.info("[FUSE] RPCase top fused:\n" + _pp(top_rpc))
            logger.info("[FUSE] Pulse top fused:\n"  + _pp(top_pulse))
            logger.info("[FUSE] Primary selected:\n" + _pp(primary))
            logger.info("[FUSE] Supplement selected:\n" + _pp(supplement))
        except Exception as e:
            logger.warning(f"[Log] dump fused failed: {e}")

        if primary is None:
            empty_msg = "【系統訊息】未檢索到相近內容。"
            return {
                "text": empty_msg,
                "diagnosis_text": empty_msg,
                "diagnosis": empty_msg,
                "evidence": [],
                "advice": [],
                "primary_source": None,
                "primary_id": None,
                "supplement": None,
                "meta": {"retrieval": {"Case": len(case_hits), "RPCase": len(rpc_hits), "PulsePJ": len(pulse_hits)}, "qdim": len(q_vec)},
            }

        # 6) 生成「一句融合參考案例」
        primary_id = primary.get("id", "")
        def _one_line(s: str) -> str:
            return re.sub(r"\s+", " ", (s or "").strip())

        fused_parts = []
        # 症狀：以主體為底
        if primary.get("symptoms"):
            fused_parts.append(f"症狀表現：{_one_line(primary['symptoms'])}")
        # 脈象（若有）
        if primary.get("pulse"):
            fused_parts.append(f"脈象：{_one_line(primary['pulse'])}")
        # 補充條文（Pulse）
        if supplement and supplement.get("symptoms"):
            fused_parts.append(f"輔助條文：{_one_line(_as_text(supplement['symptoms']))}")
        # 簡要分數
        fused_score = f"融合分：{primary.get('_final',0.0):.2f}"
        fused_case_text = f"參考案例（主體 {primary['source']} {primary_id}" + (f"，輔助 {supplement['source']} {supplement.get('id','')}" if supplement else "") + "）： " + "；".join(fused_parts) + f"；{fused_score}"

        # 額外 Log
        logger.info("[FUSED_SENTENCE] %s", _short(fused_case_text, 1200))

        # 7) LLM Prompt（只提供「一句融合案例 + 使用者問題」）
        llm_prompt = (
            "你是一位中醫臨床助理。僅以『融合參考案例』作為背景參考，"
            "並結合使用者當前的描述，請輸出三段短文（嚴禁提供任何治療/方藥）：\n"
            "1) 【診斷結果（結論）】：一句到兩句的辨證結論（勿贅述來源）。\n"
            "2) 【依據】：精煉列出 2-4 條與結論最相關的線索（避免逐字轉貼原文）。\n"
            "3) 【建議（非治療）】：觀察與紀錄方向（不可包含任何治療建議）。\n"
            "最後獨立一行輸出【使用案例編號】：填入主體案例 ID。\n"
            "-----\n"
            f"【使用者問題】\n{question}\n"
            "-----\n"
            f"【融合參考案例】\n{fused_case_text}\n"
        )

        # 8) 產生回傳文字（無 LLM 時也可落地）
        base_text = (
            "【診斷結果（結論）】\n"
            "根據當前描述與融合參考案例，給出候選辨證結論。\n\n"
            "【依據】\n- " +
            "\n- ".join(filter(None, [
                (primary.get("_hits") and ("關鍵線索：" + "、".join(primary["_hits"]))) or "",
                (primary.get("pulse") and f"脈象：{_short(primary['pulse'], 180)}") or "",
                (primary.get("symptoms") and f"症狀：{_short(primary['symptoms'], 180)}") or "",
                (supplement and supplement.get("symptoms") and f"輔助條文：{_short(_as_text(supplement['symptoms']), 100)}") or "",
                f"融合分：{primary.get('_final',0.0):.2f}",
            ])) +
            f"\n\n【建議（非治療）】\n- 補齊舌色/苔象與更具體的寸關尺描述\n- 紀錄症狀時序、誘因（情志/飲食/作息）與影響\n\n【使用案例編號】\n{primary_id}"
        )

        final_text = base_text
        try:
            if self.llm:
                if hasattr(self.llm, "generate"):
                    final_text = self.llm.generate(
                        prompt=llm_prompt,
                        model=getattr(getattr(self.config, "llm", None), "model", None)
                    )
                elif hasattr(self.llm, "chat"):
                    final_text = self.llm.chat(
                        prompt=llm_prompt,
                        model=getattr(getattr(self.config, "llm", None), "model", None)
                    )
        except Exception as e:
            logger.warning(f"[Spiral] LLM 潤筆失敗，使用基準稿：{e}")
            final_text = base_text

        # 【4】LLM 最終輸出
        logger.info("[LLM] final_text:\n%s", _short(final_text, 4000))

        # 9) 回傳（text / diagnosis_text / diagnosis 同文，避免前端空白）
        return {
            "text": final_text,
            "diagnosis_text": final_text,
            "diagnosis": final_text,
            "evidence": [
                *(primary.get("_hits") and [ "關鍵線索：" + "、".join(primary["_hits"]) ] or []),
                *(primary.get("pulse") and [ f"脈象：{primary['pulse']}" ] or []),
                *(primary.get("symptoms") and [ f"症狀：{primary['symptoms']}" ] or []),
                *(supplement and supplement.get("symptoms") and [ f"輔助條文：{_as_text(supplement['symptoms'])}" ] or []),
            ],
            "advice": [
                "補齊舌脈與症狀時序資料，以利提高辨證可靠度。",
                "留意情志、飲食、作息等影響因子，持續觀察並回填。",
            ],
            "primary_source": primary["source"],
            "primary_id": primary_id,
            "supplement": {
                "source": (supplement or {}).get("source"),
                "id": (supplement or {}).get("id"),
                "name": (supplement or {}).get("diagnosis"),
            } if supplement else None,
            "meta": {
                "retrieval": {"Case": len(case_hits), "RPCase": len(rpc_hits), "PulsePJ": len(pulse_hits)},
                "qdim": len(q_vec),
                "scores": {
                    "primary": {"vector": primary.get("_v",0.0), "lexical": primary.get("_lex",0.0), "final": primary.get("_final",0.0)},
                    "supplement": (supplement and {"vector": supplement.get("_v",0.0), "lexical": supplement.get("_lex",0.0), "final": supplement.get("_final",0.0)}) or None
                },
                "fused_case_text": fused_case_text,
            },
        }
