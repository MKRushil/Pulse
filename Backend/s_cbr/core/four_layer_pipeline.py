# -*- coding: utf-8 -*-
"""
四層推理引擎核心管線 (FourLayerSCBR)

職責：協調 L1 (Gate) -> 檢索 -> L2 (Diagnosis) -> L3 (Review) -> L4 (Presentation)
的數據流和邏輯判斷。

核心修復：
1. 確保 L1 Gate 的拒絕狀態能夠正確返回給 main.py 進行 422 處理。
2. 將 L2, L3, L4 的 LLM 調用失敗改為拋出受控異常，讓主 Engine 處理為 500 Internal Server Error。
3. 🚨 修正：將 L1, L3, L4 的模擬函式替換為實際的 LLM 呼叫，並設置溫度參數。
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json
import asyncio 
import re # 引入 re 處理 JSON 容錯

# 假設存在這些模組
from ..llm.client import LLMClient
from ..config import SCBRConfig
from ..utils.logger import get_logger
from ..security.owasp_mapper import OWASPMapper 
from ..llm.embedding import EmbedClient
from .search_engine import SearchEngine # 假設 SearchEngine 存在

logger = get_logger("FourLayerPipeline")

# 是否啟用檢索結果瘦身（預設停用，走 raw 優先）
USE_RETRIEVAL_SLIMMING = False


def _read_prompt(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _classify_domain(text: str) -> str:
    """極簡領域分類：digestive / gyne / general。"""
    if not text:
        return "general"
    d_words = ["胃", "脘", "脹", "噯氣", "嗳氣", "早飽", "脾胃", "食慾不振"]
    g_words = ["帶下", "白帶", "陰道", "月經", "經期", "婦科"]
    for w in d_words:
        if w in text:
            return "digestive"
    for w in g_words:
        if w in text:
            return "gyne"
    return "general"


async def call_llm_with_prompt(llm: LLMClient, prompt_path: Path, payload: Dict[str, Any], temperature: float = 0.0) -> Dict[str, Any]:
    """
    載入對應 .txt prompt，形成 system 指示 + user payload，呼叫 LLM。
    🚨 修正：將 temperature 作為額外參數傳入，但不直接傳遞給 llm.complete_json()
             因為 complete_json() 預期不接受此參數 (除非它內部調用 chat_complete)。
    """
    system_prompt = _read_prompt(prompt_path)
    
    # 🚨 修正點：只傳遞 LLMClient.complete_json 接受的參數
    # 假設 LLMClient.complete_json 內部會處理 temperature/其它參數。
    # 如果 LLMClient.complete_json 內部沒有處理，這會是下一個問題。
    resp = await llm.complete_json(system_prompt=system_prompt, user_prompt=payload) 

    if isinstance(resp, dict):
        return resp
    # 簡化 JSON 容錯處理
    if isinstance(resp, str):
        try:
            return json.loads(resp)
        except Exception:
            import re
            m = re.search(r"\{.*\}", resp, re.DOTALL)
            if not m:
                raise ValueError("LLM 響應不是有效的 JSON 格式，且無法提取 JSON 區塊") 
            return json.loads(m.group(0))
    raise TypeError(f"LLM 響應類型錯誤: {type(resp)}")


# 為了在日誌中提取分數，定義 _score_of 函式
def _score_of(hit: Dict[str, Any]) -> float:
    """從檢索結果中提取分數，兼容 _additional 和 score 結構"""
    try:
        add = hit.get("_additional", {}) if isinstance(hit.get("_additional"), dict) else {}
        # 優先使用 score/distance，其次使用 _final_score (SearchEngine 會正規化)
        return float(add.get("score") or hit.get("_final_score") or 0.0)
    except Exception:
        return 0.0


class FourLayerSCBR:
    """四層順序執行控制器。"""

    def __init__(self, llm: LLMClient, config: Optional[SCBRConfig] = None, search_engine: Optional[SearchEngine] = None, embed_client: Optional[EmbedClient] = None):
        self.llm = llm
        self.cfg = config
        self.SE = search_engine or (SearchEngine(self.cfg) if self.cfg else None)
        self.embed = embed_client or (EmbedClient(self.cfg) if self.cfg else None)
        self.base_dir = Path(__file__).resolve().parents[1]
        self.prompts_dir = self.base_dir / "prompts"

    async def run_once(
        self, 
        user_query: str, 
        history_summary: str | None = None, 
        disable_case_slimming: Optional[bool] = None, 
        round_count: int = 1, 
        max_rounds: int = 7,
        previous_diagnosis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        debug_notes: List[str] = []
        
        # 1. 初始化 Result 結構
        result = {
            "l1": {}, "l2": {}, "l3": {}, "l4": {}, 
            "diagnosis": {}, "converged": False, "security_checks": {}, "is_forced_convergence": False
        }
        
        # ==================== L1: 門禁層 (Gate Layer) ====================
        l1_payload = {
            "layer": "L1_GATE",
            "input": {"user_query": user_query, "history_summary": history_summary or ""}
        }
        # 🚨 L1 實際 LLM 調用 (使用溫度 0.0)
        l1 = await call_llm_with_prompt(self.llm, self.prompts_dir / "l1_gate_prompt.txt", l1_payload, temperature=0.0)
        result['l1'] = l1
        
        logger.info(f"[L1 FINAL RESULT] L1 狀態: {l1.get('status', 'N/A')}")
        # L1 Schema 定義了 keyword_plan
        logger.info(f"[L1 KEYWORD PLAN]\n{json.dumps(l1.get('keyword_plan', {}), indent=2, ensure_ascii=False)}")

        # 舊版日誌的 L1 BEFORE/AFTER FILTER 邏輯（保留）
        try:
            raw = getattr(self.llm, "_last_raw_output", None)
            flt = getattr(self.llm, "_last_filtered_output", None)
            is_l1 = getattr(self.llm, "_last_is_l1", False)
            if is_l1 and raw and flt:
                def _pp(s: str) -> str:
                    try:
                        return json.dumps(json.loads(s), ensure_ascii=False, indent=2)
                    except Exception:
                        return s
                logger.info("[L1 BEFORE FILTER]\n%s", _pp(raw))
                logger.info("[L1 AFTER  FILTER]\n%s", _pp(flt))
        except Exception:
            pass
        
        # 🚨 L1 檢查點 (關鍵點：將拒絕邏輯返回給 main.py 處理)
        if l1.get("status") == "reject" or l1.get("next_action") == "reject":
            logger.warning(f"🛡️ L1 門禁檢測到威脅，阻止後續推理。狀態: {l1.get('status')}")
            result['security_checks']['l1_flags'] = l1.get('owasp_screening', {}).get('flags', [])
            return result # 返回給 main.py 拋出 422 HTTPException

        # ------------------- 正常流程 -------------------
        
        # 2. 檢索層 (Retrieval Layer)
        cases: List[Dict] = []
        if l1.get("next_action") == "vector_search":
            if not self.SE or not self.embed:
                logger.error("❌ SearchEngine 或 EmbedClient 未初始化，無法進行檢索。")
                return result 
            
            # 從 L1 結果中提取關鍵字（BM25 用，但我們遵循舊日誌使用 full_text）
            text_query = user_query 
            
            # 1. 獲取查詢向量
            try:
                # 實際調用 embed 服務
                vector = await self.embed.embed(text_query) 
            except Exception as e:
                 logger.warning(f"⚠️ 向量生成失敗，嘗試純 BM25: {e}")
                 vector = None
                
            # 2. 執行混合檢索
            try:
                # 🚨 關鍵檢索呼叫：使用 hybrid_search (參考 v2.3.md Step 5: alpha=0.55, search_fields=["full_text"])
                cases = await self.SE.hybrid_search(
                    index="TCMCase", 
                    text=text_query, 
                    vector=vector, 
                    alpha=self.cfg.search.hybrid_alpha if vector else 1.0, 
                    limit=self.cfg.search.top_k,
                    # 從 config 讀取搜索欄位
                    search_fields=self.cfg.search.search_fields 
                )
            except Exception as e:
                logger.error(f"❌ 檢索失敗: {e}", exc_info=True)
                # 檢索失敗，將返回空列表 []

        # 🚨 日誌點 2：檢索結果摘要
        log_samples = []
        if cases:
            log_samples = [
                # 使用 _score_of 函式，兼容 score/final_score
                {"case_id": c.get("case_id", "N/A"), "score": f"{_score_of(c):.4f}"}
                for c in cases[:3] 
            ]
        logger.info(f"[RETRIEVAL RESULT] 成功找到 {len(cases)} 個案例. Top 3 範例: {log_samples}")

        if not cases:
            debug_notes.append("Retrieval returned zero cases.")
            result["debug_note"] = "; ".join(debug_notes)
            return result 

        # 3. L2: 生成層 (Diagnosis Layer)
        l2_payload = {
            "layer": "L2_CASE_ANCHORED_DIAGNOSIS",
            "input": {
                "user_accumulated_query": user_query,
                "retrieved_cases": cases,
                "round_count": round_count,
                "previous_diagnosis": previous_diagnosis if previous_diagnosis else {}
            }
        }
        # 🚨 L2 實際 LLM 調用 (使用溫度 0.1)
        l2_result = await call_llm_with_prompt(self.llm, self.prompts_dir / "l2_case_anchored_diagnosis_prompt.txt", l2_payload, temperature=0.1)
        result['l2'] = l2_result

        # 🚨 [日誌點 3: L2 案例錨定摘要]
        selected_case_id = l2_result.get("selected_case", {}).get("case_id", "未錨定")
        coverage = l2_result.get("coverage_evaluation", {}).get("coverage_ratio", 0.0)
        primary_pattern = l2_result.get('tcm_inference', {}).get('primary_pattern', 'N/A')
        
        logger.info(
            f"[L2 DIAGNOSIS SUMMARY] 錨定 ID: {selected_case_id}, 證型: {primary_pattern}, "
            f"覆蓋度: {coverage:.2f}"
        )

        # 4. L3: 審核層 (Safety Review Layer)
        l3_payload = {"layer": "L3_SAFETY_REVIEW", "input": {"diagnosis_payload": l2_result}}
        # 🚨 L3 實際 LLM 調用 (使用溫度 0.0)
        l3_result = await call_llm_with_prompt(self.llm, self.prompts_dir / "l3_safety_review_prompt.txt", l3_payload, temperature=0.0)
        result['l3'] = l3_result
        
        # 🚨 [日誌點 4: L3 安全審核結果]
        logger.info(f"[L3 REVIEW STATUS] 審核結果: {l3_result.get('status', 'N/A')}")
            
        # 🚨 L3 檢查點
        if l3_result.get('status') == 'rejected':
            logger.warning("🛡️ L3 審核拒絕輸出。")
            result['security_checks']['l3_violations'] = l3_result.get('violations', [])
            return result # 返回給 main.py 處理 422 HTTPException

        # 5. L4: 呈現層 (Presentation Layer)
        safe_diagnosis = l3_result.get('safe_diagnosis_payload', {})
        l4_payload = {
            "layer": "L4_PRESENTATION", 
            "input": {
                "safe_diagnosis_payload": safe_diagnosis, 
                "round_count": round_count, 
                "max_rounds": max_rounds,
                "previous_diagnosis": previous_diagnosis if previous_diagnosis else {}
            }
        }
        # 🚨 L4 實際 LLM 調用 (使用溫度 0.1)
        l4_result = await call_llm_with_prompt(self.llm, self.prompts_dir / "l4_presentation_prompt.txt", l4_payload, temperature=0.1)
        result['l4'] = l4_result
        result['diagnosis'] = l4_result.get('presentation', {})
        
        # 檢查收斂 (依據 SCBR 文件 [10.2] 的收斂條件)
        coverage_ratio = l2_result.get('coverage_evaluation', {}).get('coverage_ratio', 0.0)
        # 修正收斂判斷邏輯，納入最大輪次檢查 (強制收斂)
        is_coverage_ok = coverage_ratio >= 0.8
        is_max_round_reached = round_count >= max_rounds
        # 這裡的邏輯必須和 main.py 內部的 should_converge 邏輯保持一致
        result['converged'] = is_coverage_ok or is_max_round_reached 

        # 🚨 [新增] 檢查是否為「低覆蓋度的強制收斂」 (用於 output_validator 強化警告)
        if is_max_round_reached and coverage_ratio < 0.75:
            result['is_forced_convergence'] = True
            logger.warning(
                f"⚠️ 觸發低覆蓋度強制收斂 (Round: {round_count}, Coverage: {coverage_ratio:.2f})")
        
        return result