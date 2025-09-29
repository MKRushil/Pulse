# -*- coding: utf-8 -*-
"""
SpiralEngine：單輪推理編排
- 先產生向量（優先讀 config.embedding.api_key；失敗則 BM25-only）
- 針對 Case / RPCase / PulsePJ 各自取 Top-1
- 融合：向量分 + 詞面分（缺向量時 vec_w=0）
- 主體：比較 Case 與 RPCase 的融合分取較高者；若兩者都無，再以 PulsePJ 頂上
- 輔助：PulsePJ Top-1（若有）
- LLM 僅做語氣/格式潤筆（不提供治療方案）
- 內建 4 類關鍵 Log：原始命中、Top-1、融合後、LLM 最終文字
"""

import os
import re
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

# 允許套件/單檔兩種匯入方式
try:
    from .search_engine import SearchEngine
except ImportError:
    from search_engine import SearchEngine

logger = logging.getLogger("s_cbr.SpiralEngine")
logger.setLevel(logging.INFO)


# ---------- Log 工具：安全列印、截斷、精簡命中 ----------
def _short(s: str, n: int = 600) -> str:
    """避免 log 過長：多於 n 字就截斷"""
    if s is None:
        return ""
    return (s[:n] + " …(截斷)") if len(s) > n else s

def _pp(obj) -> str:
    """pretty json"""
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)

def _slim_hit(hit: dict, keep_props=None) -> dict:
    """
    壓縮 Weaviate 命中結果：保留常見欄位與 _additional 分數，避免 log 爆量
    """
    keep = set(keep_props or [])
    slim = {}
    addi = hit.get("_additional") or {}
    slim["_score"] = addi.get("score")
    slim["_distance"] = addi.get("distance")

    # 常見欄位（依你的 schema）
    for k in [
        # Case
        "case_id", "chiefComplaint", "presentIllness", "pulse_text",
        "diagnosis_main", "search_text", "src_casev_uuid",
        # PulsePJ
        "pid", "name", "category", "category_id", "main_disease", "symptoms",
        # RPCase
        "rid", "final_diagnosis", "pulse_tags", "symptom_tags",
    ]:
        if k in hit:
            v = hit[k]
            if isinstance(v, str):
                slim[k] = _short(v, 300)
            else:
                slim[k] = v

    # 額外保留
    for k in keep:
        if k in hit and k not in slim:
            slim[k] = hit[k]
    return slim


# ---------- NVIDIA 向量器 ----------
class NvidiaEmbedder:
    """
    使用 NVIDIA Integrate Embeddings API 產生 1024 維向量
    - 模型：nvidia/nv-embedqa-e5-v5
    - 金鑰來源：建構子 api_key > 環境 NVIDIA_API_KEY/NV_API_KEY
    """
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


# ---------- 字串處理小工具 ----------
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
        # 中文粗 bi-gram
        if re.search(r"[\u4e00-\u9fff]", t) and len(t) >= 2:
            out.extend([t[i:i+2] for i in range(len(t)-1)])
    seen = set(); ded = []
    for t in out:
        if t not in seen:
            ded.append(t); seen.add(t)
    return ded

def _overlap_score(q: str, doc: str) -> Tuple[float, List[str]]:
    """詞面重合（0~1）與命中詞"""
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
        嵌入器取得策略：
        - 優先使用外部注入的 embedder
        - 否則讀取 config.embedding.api_key 建立 NvidiaEmbedder
        - 若仍無法，執行時退回環境變數建立（失敗則 BM25-only）
        """
        self.config = config
        self.search_engine = search_engine or SearchEngine(config)

        # 嵌入器
        if embedder is not None:
            self.embedder = embedder
        else:
            key_from_cfg = getattr(getattr(config, "embedding", None), "api_key", None)
            if key_from_cfg:
                self.embedder = NvidiaEmbedder(api_key=key_from_cfg)
            else:
                self.embedder = None

        # LLM（可選）：只做文字潤筆，不提供治療方案
        self.llm = llm or getattr(getattr(config, "llm", None), "client", None) or getattr(config, "llm_client", None)

    # ---------------- 主流程 ----------------
    async def execute_spiral_cycle(self, question: str, session_id: str, alpha: float = 0.5, limit: int = 10) -> Dict[str, Any]:
        # 1) 向量（可缺省）
        q_vec: List[float] = []
        try:
            if self.embedder is None:
                self.embedder = NvidiaEmbedder()  # 讀環境變數備援
            if hasattr(self.embedder, "embed"):
                q_vec = self.embedder.embed(question, input_type="query")
        except Exception as e:
            logger.warning(f"[Spiral] 產生向量失敗，改 BM25-only：{e}")
            q_vec = []
        logger.info(f"🧭 q_vector: dim={len(q_vec)}")

        # 2) 各索引檢索（只取 Top-1）
        se = self.search_engine
        case_hits  = await se.hybrid_search("Case",    text=question, vector=(q_vec or None), alpha=alpha, limit=max(1, limit))
        pulse_hits = await se.hybrid_search("PulsePJ", text=question, vector=(q_vec or None), alpha=alpha, limit=max(1, limit))
        rpc_hits   = await se.hybrid_search("RPCase",  text=question, vector=(q_vec or None), alpha=alpha, limit=max(1, limit))

        logger.info(f"📊 Case: {len(case_hits)} | RPCase: {len(rpc_hits)} | PulsePJ: {len(pulse_hits)}")

        # 【1】各向量庫回傳資料（精簡後）
        try:
            logger.debug("[RET] Case raw hits (slim):\n"    + _pp([_slim_hit(h) for h in case_hits]))
            logger.debug("[RET] RPCase raw hits (slim):\n"  + _pp([_slim_hit(h) for h in rpc_hits]))
            logger.debug("[RET] PulsePJ raw hits (slim):\n" + _pp([_slim_hit(h) for h in pulse_hits]))
        except Exception as e:
            logger.warning(f"[Log] dump raw hits failed: {e}")

        if not (case_hits or rpc_hits or pulse_hits):
            return {
                "text": "【系統訊息】未檢索到相近內容。請補充舌脈、症狀時序與影響因子後重試。",
                "diagnosis": "",
                "evidence": [],
                "advice": ["補充舌色/苔象與寸關尺脈象", "描述發生時程與誘因（情志/飲食/作息）"],
                "meta": {"retrieval": {"Case":0,"RPCase":0,"PulsePJ":0}, "qdim": len(q_vec)},
            }

        # 3) 轉為統一候選（只取 Top-1）
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

        # 【2】各庫 Top-1
        try:
            logger.info("[TOP1] Case:\n"   + _pp(top_case))
            logger.info("[TOP1] RPCase:\n" + _pp(top_rpc))
            logger.info("[TOP1] PulsePJ:\n"+ _pp(top_pulse))
        except Exception as e:
            logger.warning(f"[Log] dump top-1 failed: {e}")

        # 4) 為每一個 top 候選計算「向量分 + 詞面分」融合分
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
            primary = top_pulse  # 兩者都沒有時，用 PulsePJ 頂上

        supplement = top_pulse if (top_pulse and (primary is not top_pulse)) else None

        # 【3】融合後資料與主體/輔助
        try:
            logger.info("[FUSE] Case top fused:\n"   + _pp(top_case))
            logger.info("[FUSE] RPCase top fused:\n" + _pp(top_rpc))
            logger.info("[FUSE] Pulse top fused:\n"  + _pp(top_pulse))
            logger.info("[FUSE] Primary selected:\n" + _pp(primary))
            logger.info("[FUSE] Supplement selected:\n" + _pp(supplement))
        except Exception as e:
            logger.warning(f"[Log] dump fused failed: {e}")

        if primary is None:
            # 保底
            return {
                "text": "【系統訊息】未檢索到相近內容。",
                "diagnosis": "",
                "evidence": [],
                "advice": [],
                "meta": {"retrieval": {"Case": len(case_hits), "RPCase": len(rpc_hits), "PulsePJ": len(pulse_hits)}, "qdim": len(q_vec)},
            }

        # 6) 組裝主體/補充供 LLM 使用
        source_title = {"Case": "案例（Case）", "RPCase": "案例（RPCase）", "PulsePJ": "脈學補充（PulsePJ）"}
        primary_title = source_title.get(primary["source"], primary["source"])
        primary_id = primary.get("id", "")
        primary_block = [
            f"【主體：{primary_title}】",
            f"- 使用案例編號：{primary_id}",
            f"- 診斷/名稱：{primary.get('diagnosis','') or '（無）'}",
        ]
        if primary.get("pulse"):    primary_block.append(f"- 脈象：{primary['pulse']}")
        if primary.get("symptoms"): primary_block.append(f"- 症狀文本：{primary['symptoms']}")
        primary_block.append(f"- 分數：向量 {primary.get('_v',0.0):.2f} + 詞面 {primary.get('_lex',0.0):.2f} → 融合 {primary.get('_final',0.0):.2f}")

        supplement_block = []
        if supplement:
            supplement_block = [
                "【輔助：脈學補充（PulsePJ）】",
                f"- ID/類別：{supplement.get('id','')} / {supplement.get('source','')}",
                f"- 名稱/主病：{supplement.get('diagnosis','')} / {supplement.get('raw',{}).get('main_disease','')}",
            ]
            if supplement.get("symptoms"): supplement_block.append(f"- 條文/症狀：{supplement['symptoms']}")
            supplement_block.append(f"- 分數：向量 {supplement.get('_v',0.0):.2f} + 詞面 {supplement.get('_lex',0.0):.2f} → 融合 {supplement.get('_final',0.0):.2f}")

        # 7) 產出給 LLM 的 Prompt
        prompt = (
            "你是一位中醫臨床助理。根據【主體】以及【輔助】（若有），"
            "請以專業而精簡的中文，輸出三個段落：\n"
            "1) 【診斷結果（結論）】：概述辨證判斷（不提供任何治療方案/藥方/劑量）。\n"
            "2) 【依據】：條列影響結論的關鍵症狀/脈象/特徵（不可臆測未提供的資訊）。\n"
            "3) 【建議（非治療）】：提出病情觀察與資料補充的方向（不含任何治療建議）。\n"
            "最後獨立一行輸出【使用案例編號】：填入主體案例的編號。\n"
            "----\n"
            f"【使用者問題】\n{question}\n\n"
            + "\n".join(primary_block) + "\n\n"
            + ("\n".join(supplement_block) if supplement_block else "")
        )

        # 8) 產生回傳文字（可無 LLM）
        base_text = (
            "【診斷結果（結論）】\n"
            f"{primary.get('diagnosis') or '根據相近案例推測之候選證候'}\n\n"
            "【依據】\n- "
            + "\n- ".join(filter(None, [
                (primary.get("_hits") and ("特徵對應：" + "、".join(primary["_hits"]))) or "",
                (primary.get("pulse") and f"脈象：{primary['pulse'][:240]}{'…' if len(primary['pulse'])>240 else ''}") or "",
                (primary.get("symptoms") and f"主訴/現病史：{primary['symptoms'][:240]}{'…' if len(primary['symptoms'])>240 else ''}") or "",
                (supplement and supplement.get("symptoms") and f"輔助條文/症狀：{supplement['symptoms']}") or "",
                f"融合分：向量 {primary.get('_v',0.0):.2f} + 詞面 {primary.get('_lex',0.0):.2f} → 最終 {primary.get('_final',0.0):.2f}"
            ])) + "\n\n"
            "【建議（非治療）】\n- "
            + "\n- ".join([
                "補齊舌色與苔象（色/厚薄/潤燥）與寸關尺脈象的具體觀察。",
                "紀錄睡眠的入睡潛伏期、夜醒次數/時段、早醒與夢境性質。",
                "標註誘因：情志、咖啡因/酒精、作息變化、合併症或用藥史。",
                "1~2 週後更新資料可提高相似案例的準確度。",
            ])
            + f"\n\n【使用案例編號】\n{primary_id}"
        )

        final_text = base_text
        try:
            if self.llm:
                if hasattr(self.llm, "generate"):
                    final_text = self.llm.generate(prompt=prompt, model=getattr(getattr(self.config, "llm", None), "model", None))
                elif hasattr(self.llm, "chat"):
                    final_text = self.llm.chat(prompt=prompt, model=getattr(getattr(self.config, "llm", None), "model", None))
        except Exception as e:
            logger.warning(f"[Spiral] LLM 潤筆失敗，使用原文：{e}")
            final_text = base_text

        # 【4】LLM 最終輸出（或基準稿）
        try:
            logger.info("[LLM] final_text:\n" + _short(final_text, 4000))
        except Exception as e:
            logger.warning(f"[Log] dump final_text failed: {e}")

        # 9) 回傳給前端
        return {
            "text": final_text,                          # 顯示文字（已潤筆或基準稿）
            "diagnosis": primary.get("diagnosis") or "", # 提取的結論（方便前端單獨顯示）
            "evidence": [
                *(primary.get("_hits") and [ "特徵對應：" + "、".join(primary["_hits"]) ] or []),
                *(primary.get("pulse") and [ f"脈象：{primary['pulse']}" ] or []),
                *(primary.get("symptoms") and [ f"主訴/現病史：{primary['symptoms']}" ] or []),
                *(supplement and supplement.get("symptoms") and [ f"輔助條文/症狀：{supplement['symptoms']}" ] or []),
            ],
            "advice": [
                "補齊舌脈與症狀時序資料，以利提高辨證可靠度。",
                "留意情志、飲食、作息等影響因子，持續觀察並回填。",
            ],
            "primary_source": primary["source"],         # 主體來源（Case / RPCase / PulsePJ）
            "primary_id": primary_id,                    # 使用案例編號（主體）
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
                }
            },
        }
