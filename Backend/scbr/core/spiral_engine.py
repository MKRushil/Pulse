# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import logging, random
import chromadb

from scbr.models.schemas import TurnInput, TurnOutput
from scbr.metrics import compute_metrics
from scbr.dialog_manager import DialogManager
from scbr.scbr_config import settings

logger = logging.getLogger("scbr.spiral_engine")

class SpiralEngine:
    def __init__(self, dialog_mgr: DialogManager = None, embed_client=None, llm_client=None):
        self._dm = dialog_mgr or DialogManager()
        self._embed = embed_client   # scbr.llm.client.EmbeddingClient
        self._llm = llm_client       # scbr.llm.client.LLMClient

        # 僅在此建立 client / collections（PersistentClient + get_or_create）
        self._client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self._cases  = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_CASE,  metadata={"hnsw:space": "cosine"}
        )
        self._pulse  = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_PULSE, metadata={"hnsw:space": "cosine"}
        )
        # self._rpc = self._client.get_or_create_collection(
        #     name=settings.CHROMA_COLLECTION_RPCASE, metadata={"hnsw:space":"cosine"}
        # )

    # ---- 內部工具 ----
    def _embed_text(self, text: str, input_type: str = "query") -> List[float]:
        if self._embed:
            return self._embed.embed([text], input_type=input_type)[0]
        # 無嵌入客戶端時的退化（保證流程可跑）
        return [random.random() for _ in range(768)]

    def _ask_llm(self, prompt: str) -> str:
        if self._llm:
            return self._llm.chat(
                messages=[{"role":"system","content":"你是中醫輔助診斷助手。"},
                          {"role":"user","content":prompt}],
                temperature=0.2, max_tokens=512
            )
        # 無 LLM 時的退化
        return "可能的診斷是心肝血虛，建議養血安神，可考慮甘麥大棗湯；如有失眠心悸，兼參酸棗仁湯化裁。"

    def _parse_llm_answer(self, answer: str) -> Tuple[str, str]:
        diagnosis, suggestions = "", ""
        for sent in answer.replace("：", ":").split("，"):
            s = sent.strip()
            if s.startswith("可能的診斷") or s.startswith("診斷"):
                parts = s.split("是")
                diagnosis = (parts[-1] if parts else s).strip()
            if s.startswith("建議") or s.lower().startswith("suggestion"):
                suggestions = s.split(":")[-1].strip()
        if not suggestions:
            # 嘗試再切行
            for line in answer.splitlines():
                if line.strip().startswith(("建議", "建議：", "建議:")):
                    suggestions = line.split(":",1)[-1].replace("：","").strip()
                    break
        return diagnosis or "", suggestions or ""

    def _build_prompt(self, full_query: str, case_ids: List[str], pulse_ids: List[str]) -> str:
        parts = [f"使用者描述: {full_query}"]
        if case_ids:
            parts.append("相似病例資訊:")
            for cid in case_ids:
                d = self._cases.get(ids=[cid])
                if d and d.get("metadatas"):
                    summary = d["metadatas"][0].get("summary_text") or "(摘要不可用)"
                    parts.append(f"- 病例{cid}摘要: {summary}")
        if pulse_ids:
            parts.append("可能相關的脈象特徵:")
            for pid in pulse_ids:
                d = self._pulse.get(ids=[pid])
                if d and d.get("metadatas"):
                    desc = d["metadatas"][0].get("description") or "(描述不可用)"
                    parts.append(f"- {desc}")
        parts.append("請給出可能的中醫診斷（證型）與治療建議。")
        return "\n".join(parts)

    # ---- 核心入口 ----
    def query(self, turn_input: TurnInput) -> TurnOutput:
        session_id = turn_input.session_id
        user_query = (turn_input.user_query or "").strip()
        logger.info(f"[SpiralEngine] session={session_id} input={user_query}")

        # (1) 會話累積
        full_query = self._dm.update_session(session_id, user_query)
        turn_index = self._dm.get_turn_count(session_id)

        # (2) 向量檢索（Case / Pulse）
        qv = self._embed_text(full_query, input_type="query")

        case_res = self._cases.query(query_embeddings=[qv], n_results=3)
        case_ids    = case_res.get("ids", [[]])[0] if case_res else []
        case_dists  = case_res.get("distances", [[]])[0] if case_res else []

        pulse_res = self._pulse.query(query_embeddings=[qv], n_results=2)
        pulse_ids   = pulse_res.get("ids", [[]])[0] if pulse_res else []
        pulse_dists = pulse_res.get("distances", [[]])[0] if pulse_res else []

        chosen_case_id   = case_ids[0] if case_ids else None
        chosen_case_dist = float(case_dists[0]) if case_ids else 1.0

        # (3) LLM 推理
        prompt = self._build_prompt(full_query, case_ids, pulse_ids)
        llm_answer = self._ask_llm(prompt)
        diagnosis, suggestions = self._parse_llm_answer(llm_answer)

        # 缺診斷時，嘗試從案例 metadata 補
        if not diagnosis and chosen_case_id:
            d = self._cases.get(ids=[chosen_case_id])
            if d and d.get("metadatas") and d["metadatas"][0].get("diagnosis"):
                diagnosis = d["metadatas"][0]["diagnosis"]
        if not suggestions:
            suggestions = "請遵醫囑進一步辨證論治，必要時補充舌脈與伴隨症狀。"

        # (4) 分數與指標（距離→相似度：sim=1-dist，假設dist∈[0,1]）
        sim_scores: Dict[str, float] = {cid: float(1.0 - dist) for cid, dist in zip(case_ids, case_dists)}
        confidence = sim_scores.get(chosen_case_id, 0.0) if chosen_case_id else 0.0
        metrics_dict = compute_metrics(sim_scores, pulse_ids=pulse_ids, diagnosis=diagnosis)

        trace = {
            "full_query": full_query,
            "retrieved_case_ids": case_ids,
            "retrieved_pulse_ids": pulse_ids,
            "llm_prompt": prompt,
            "llm_answer": llm_answer
        }

        return TurnOutput(
            session_id=session_id,
            turn_index=turn_index,
            diagnosis=diagnosis,
            suggestions=suggestions,
            chosen_case_id=chosen_case_id,
            confidence=confidence,
            scores=sim_scores,
            metrics=metrics_dict,
            trace=trace
        )
