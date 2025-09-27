# scbr/spiral_engine.py
from typing import List, Dict, Any
from scbr.models.schemas import TurnInput, TurnOutput
from scbr import metrics, pulse_rules, dialog_manager
import logging, random

# 初始化向量資料庫客戶端（Chroma）與集合
import chromadb
chroma_client = chromadb.Client()
cases_collection = chroma_client.get_collection(name="Case")
pulse_collection = chroma_client.get_collection(name="PulsePJV")
# （如果還有 RPCase 資料集，亦可在此初始化）

# 初始化對話管理器
dialog_mgr = dialog_manager.DialogManager()

# 日誌
logger = logging.getLogger("scbr.spiral_engine")

class SpiralEngine:
    def __init__(self):
        # 可在此載入 Nvidia API 模型介面，如果有需要
        # 例如：self.llm_api = NvidiaLLM(api_key=..., model_name=...)
        #       self.embed_api = NvidiaEmbed(api_key=..., model_name=...)
        # 這裡用 None 或假實現佔位
        self.llm_api = None
        self.embed_api = None

    def _embed_text(self, text: str) -> List[float]:
        """將給定文字轉換為向量嵌入。這裡使用 NVIDIA Embedding API 或模擬。"""
        if self.embed_api:
            # 調用真實的嵌入模型 API
            # e.g., response = requests.post(..., json={ "model": EMBEDDING_MODEL_NAME, "input": text }, headers={...})
            # vector = response.json()["embedding"]
            # return vector
            pass
        # 模擬：返回固定長度的隨機向量作為佔位
        return [random.random() for _ in range(768)]

    def _ask_llm(self, prompt: str) -> str:
        """向 LLM 提問並獲得答案（模擬或調用 NVIDIA LLM API）。"""
        if self.llm_api:
            # 調用 NVIDIA LLM API 獲取回答，例如 chat/completions 接口
            # response = requests.post(..., json={ "model": LLM_MODEL_NAME, "messages": [{"role": "user", "content": prompt}] }, headers={...})
            # answer = response.json()["choices"][0]["message"]["content"]
            # return answer
            pass
        # 模擬：直接返回提示中可能的診斷關鍵字作為佔位回答
        if "診斷" in prompt:
            return "可能的診斷是心肝血虛，建議養血安神，處方可考慮甘麥大棗湯調理失眠。"
        return "根據提供的信息，建議進一步檢查確認診斷。"

    def query(self, turn_input: TurnInput) -> TurnOutput:
        """處理一次使用者查詢（可能為多輪對話之一），返回推理結果。"""
        session_id = turn_input.session_id
        user_query = turn_input.user_query.strip()
        logger.info(f"[SpiralEngine] 收到查詢 (session={session_id}): {user_query}")

        # 1. 取得累積的問題描述（將新輸入合併上下文）
        full_query = dialog_mgr.update_session(session_id, user_query)
        turn_index = dialog_mgr.get_turn_count(session_id)
        logger.info(f"[SpiralEngine] Session {session_id} | Turn {turn_index} | 合併查詢: {full_query}")

        # 2. 向量化查詢，檢索相似病例和脈象知識
        query_vec = self._embed_text(full_query)
        # 從 Case 資料集中檢索前3相似病例
        case_results = cases_collection.query(query_embeddings=[query_vec], n_results=3)
        case_ids: List[str] = case_results["ids"][0] if case_results and "ids" in case_results else []
        case_scores: List[float] = case_results["distances"][0] if case_results and "distances" in case_results else []
        # （注意：Chroma 返回 distance 越小越相似，如使用內積可轉換為相似度）

        # 從 PulsePJV 資料集中檢索前2相似脈象條目（若使用者有提供脈象相關資訊）
        pulse_results = pulse_collection.query(query_embeddings=[query_vec], n_results=2)
        pulse_ids: List[str] = pulse_results["ids"][0] if pulse_results and "ids" in pulse_results else []
        pulse_scores: List[float] = pulse_results["distances"][0] if pulse_results and "distances" in pulse_results else []

        logger.info(f"[SpiralEngine] 檢索到案例IDs: {case_ids} (scores={case_scores}), 脈象IDs: {pulse_ids}")

        # 取最相似病例的ID與相關資訊作為候選
        chosen_case_id = case_ids[0] if case_ids else None
        chosen_case_score = case_scores[0] if case_scores else 0.0

        # 3. 建立 LLM 提示，包含使用者描述及檢索結果摘要
        prompt = self._build_prompt(full_query, case_ids, pulse_ids)
        llm_answer = self._ask_llm(prompt)
        # 從 LLM 回答中解析診斷與建議（此處假定回答格式固定或以簡單方式擷取）
        diagnosis, suggestions = self._parse_llm_answer(llm_answer)

        # 如果 LLM 未明確給出診斷，則可退而求其次使用檢索案例的診斷
        if not diagnosis and chosen_case_id:
            # 假設可以從案例庫中取得該案例的診斷字段
            case_data = cases_collection.get(ids=[chosen_case_id])
            if case_data and "diagnosis" in case_data["metadatas"][0]:
                diagnosis = case_data["metadatas"][0]["diagnosis"]
        # 同理，若無建議且有處方資料，可從 RPCase 或案例中補充
        if not suggestions:
            suggestions = "請遵醫囑進一步診治。"

        # 4. 計算信心分數與指標
        confidence = float(1 - chosen_case_score) if case_scores else 0.0  # 例如用距離轉成相似度(1-距離)
        # 構造所有檢索案例的分數字典（轉換為相似度形式）
        scores_dict: Dict[str, float] = {}
        for cid, dist in zip(case_ids, case_scores):
            scores_dict[cid] = float(1 - dist)  # 以1-距離作為相似度（假定距離<=1）
        # 計算 CMS 和 RCI（使用 metrics 模組）
        metrics_dict = metrics.compute_metrics(scores_dict, pulse_ids=pulse_ids, diagnosis=diagnosis)

        # 準備 trace 訊息（可包含重要中間結果供前端或調試用）
        trace_info: Dict[str, Any] = {
            "full_query": full_query,
            "retrieved_case_ids": case_ids,
            "retrieved_pulse_ids": pulse_ids,
            "llm_prompt": prompt,
            "llm_answer": llm_answer
        }

        # 構造 TurnOutput 對象
        output = TurnOutput(
            session_id=session_id,
            turn_index=turn_index,
            diagnosis=diagnosis,
            suggestions=suggestions,
            chosen_case_id=chosen_case_id,
            confidence=confidence,
            scores=scores_dict,
            metrics=metrics_dict,
            trace=trace_info
        )
        logger.info(f"[SpiralEngine] 完成推理: 診斷='{diagnosis}', 建議='{suggestions}', 信心={confidence:.2f}, CMS/RCI={metrics_dict}")
        return output

    def _build_prompt(self, full_query: str, case_ids: List[str], pulse_ids: List[str]) -> str:
        """根據使用者完整問題和檢索結果構建提示給 LLM。"""
        prompt_parts = [f"使用者描述: {full_query}"]
        # 添加檢索到的案例簡述（示範從元資料中取出摘要）
        if case_ids:
            prompt_parts.append("相似病例資訊:")
            for cid in case_ids:
                case_data = cases_collection.get(ids=[cid])
                if case_data:
                    # 假設每個案例 metadata 包含 summary_text 字段作為摘要
                    summary = case_data["metadatas"][0].get("summary_text") or "(摘要不可用)"
                    prompt_parts.append(f"- 病例{cid}摘要: {summary}")
        # 添加脈象知識提示
        if pulse_ids:
            prompt_parts.append("可能相關的脈象特徵:")
            for pid in pulse_ids:
                pulse_data = pulse_collection.get(ids=[pid])
                if pulse_data:
                    desc = pulse_data["metadatas"][0].get("description") or "(描述不可用)"
                    prompt_parts.append(f"- {desc}")
        prompt_parts.append("根據以上資訊，請給出可能的中醫診斷和治療建議。")
        return "\n".join(prompt_parts)

    def _parse_llm_answer(self, answer: str) -> (str, str):
        """從 LLM 回答文字解析出診斷和建議。這裡簡單地拆分句子尋找。"""
        diagnosis = ""
        suggestions = ""
        # 簡單規則：以'診斷是'開頭的句子作為診斷，以'建議'開頭的句子作為建議
        for sent in answer.split('，'):
            if sent.strip().startswith("可能的診斷") or sent.strip().startswith("診斷"):
                diagnosis = sent.split("是")[-1].strip()
            if sent.strip().startswith("建議"):
                suggestions = sent.strip().lstrip("建議").lstrip("：:").strip()
        # 防止空字符串
        return diagnosis or "", suggestions or ""
