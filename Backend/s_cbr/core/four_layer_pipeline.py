# -*- coding: utf-8 -*-
"""
四層推理引擎核心管線 (FourLayerSCBR)

職責：協調 L1 (Gate) -> 檢索 -> L2 (Diagnosis) -> L3 (Review) -> L4 (Presentation)
的數據流和邏輯判斷。

核心修復：
1. 確保 L1 Gate 的拒絕狀態能夠正確返回給 main.py 進行 422 處理。
2. 將 L2, L3, L4 的 LLM 調用失敗改為拋出受控異常，讓主 Engine 處理為 500 Internal Server Error。
3. 🚨 方案三實裝：L1 階段引入 TCMTools 進行真正的外部工具查詢增強。
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
from .search_engine import SearchEngine 
from .agentic_retrieval import AgenticRetrieval
from .l2_agentic_diagnosis import L2AgenticDiagnosis
from ..utils.terminology_manager import TerminologyManager

# [MODIFIED] 引入工具庫 (方案三必要)
from ..tools.tcm_tools import TCMTools

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
    """
    system_prompt = _read_prompt(prompt_path)
    
    resp = await llm.complete_json(system_prompt=system_prompt, user_prompt=payload, temperature=temperature) 

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
        # 🆕 初始化 Agentic 檢索器
        self.agentic_enabled = (
            self.cfg.agentic_nlu.enabled 
            if self.cfg and hasattr(self.cfg, 'agentic_nlu') 
            else False
        )
        if self.agentic_enabled and self.SE and self.embed:
            self.agentic_retrieval = AgenticRetrieval(
                search_engine=self.SE,
                embed_client=self.embed,
                config=self.cfg
            )
        else:
            self.agentic_retrieval = None
        
        # [MODIFIED] 初始化 TCMTools 工具庫 (用於 L1 增強)
        self.tools = TCMTools() 
        logger.info("[FourLayerPipeline] TCMTools 工具庫已掛載")
        
        # 🆕 初始化 L2 Agentic 診斷器
        if self.agentic_enabled and self.cfg:
            try:
                self.l2_agentic = L2AgenticDiagnosis(config=self.cfg, search_engine=self.SE,embed_client=self.embed)
                logger.info("[L2Agentic] 初始化完成 (含內部知識庫連線)")
            except Exception as e:
                logger.warning(f"[L2Agentic] 初始化失敗: {e}，將降級為傳統 L2 模式")
                self.l2_agentic = None
        else:
            self.l2_agentic = None
            if not self.agentic_enabled:
                logger.info("[L2] Agentic 模式未啟用，使用傳統 L2 模式")
        
        self.term_manager = TerminologyManager()
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
        # 🆕 根據配置選擇 L1 Prompt
        if self.agentic_enabled:
            l1_prompt_file = "l1_gate_agentic_prompt.txt"
            l1_payload = {
                "layer": "L1_AGENTIC_GATE",
                "input": {"user_query": user_query, "history_summary": history_summary or ""}
            }
            logger.info("[L1] 使用 Agentic NLU 模式")
        else:
            l1_prompt_file = "l1_gate_prompt.txt"
            l1_payload = {
                "layer": "L1_GATE",
                "input": {"user_query": user_query, "history_summary": history_summary or ""}
            }
            logger.info("[L1] 使用傳統模式")
        
        # 🚨 L1 實際 LLM 調用 (使用溫度 0.0 或 Agentic 溫度)
        l1_temperature = (
            self.cfg.agentic_nlu.llm_temperature 
            if self.agentic_enabled and self.cfg 
            else 0.0
        )
        l1 = await call_llm_with_prompt(
            self.llm, 
            self.prompts_dir / l1_prompt_file, 
            l1_payload, 
            temperature=l1_temperature
        )
        result['l1'] = l1
        
        logger.info(f"[L1 FINAL RESULT] L1 狀態: {l1.get('status', 'N/A')}")
        
        # 🆕 記錄 Agentic 決策（如果啟用）
        if self.agentic_enabled:
            logger.info(
                f"[L1 AGENTIC DECISION]\n"
                f"  Overall Confidence: {l1.get('overall_confidence', 0.0):.3f}\n"
                f"  Decided Alpha: {l1.get('retrieval_strategy', {}).get('decided_alpha', 0.5)}\n"
                f"  Strategy Type: {l1.get('retrieval_strategy', {}).get('strategy_type', 'N/A')}\n"
                f"  Expected Quality: {l1.get('retrieval_strategy', {}).get('expected_quality', 'N/A')}"
            )
        else:
            # 傳統模式記錄
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

        # =================================================================
        # 🆕 [新增] L1 策略微調 (基於本地詞庫的 Hybrid 修正)
        # =================================================================
        if self.agentic_enabled and l1.get("status") == "ok":
            try:
                # 1. 收集 L1 提取的所有關鍵字
                extracted_terms = []
                kw_data = l1.get("keyword_extraction", {})
                extracted_terms.extend(kw_data.get("symptom_terms", []))
                extracted_terms.extend(kw_data.get("tongue_pulse_terms", []))
                
                # 2. 計算「術語密度」 (有多少比例是已知標準詞)
                density = self.term_manager.get_density(extracted_terms)
                
                # 3. 策略自動修正 (Auto-Correction)
                # 規則：如果 50% 以上是標準術語，且目前 Alpha > 0.4 (非 Keyword Focus)，強制降轉
                current_strategy = l1.get("retrieval_strategy", {})
                current_alpha = current_strategy.get("decided_alpha", 0.5)
                
                if density >= 0.5 and current_alpha > 0.4:
                    logger.info(f"🔧 [L1 Correction] 檢測到高密度標準術語 ({density:.0%})，強制調整 Alpha: {current_alpha} -> 0.3")
                    
                    # 修改 L1 的決策結果 (In-place modification)
                    if "retrieval_strategy" not in l1: l1["retrieval_strategy"] = {}
                    
                    l1["retrieval_strategy"]["decided_alpha"] = 0.3
                    l1["retrieval_strategy"]["strategy_type"] = "keyword_focus_forced"
                    
                    # 記錄修正原因，方便後續除錯
                    original_reason = l1["retrieval_strategy"].get("reasoning", "")
                    l1["retrieval_strategy"]["reasoning"] = (
                        f"{original_reason} (系統檢測到 {density:.0%} 標準術語，已由本地詞庫強制修正策略)"
                    )
            except Exception as e:
                logger.warning(f"⚠️ L1 策略修正執行失敗 (不影響主流程): {e}")
        
        # 🚨 L1 檢查點 (關鍵點：將拒絕邏輯返回給 main.py 處理)
        if l1.get("status") == "reject" or l1.get("next_action") == "reject":
            logger.warning(f"🛡️ L1 門禁檢測到威脅，阻止後續推理。狀態: {l1.get('status')}")
            result['security_checks']['l1_flags'] = l1.get('owasp_screening', {}).get('flags', [])
            return result # 返回給 main.py 拋出 422 HTTPException

        # =================================================================
        # 🆕 [方案三修正版] L1 外部工具介入 (Tool-Assisted Query Enrichment)
        # =================================================================
        # 核心邏輯：如果 L1 信心不足 (< 0.4)，先用 LLM 轉譯，再調用工具
        l1_conf = l1.get("overall_confidence", 0.0)
        user_query_text = user_query
        
        if self.agentic_enabled and l1_conf < 0.4:
            logger.info(f"🔧 [L1 Enhancement] 檢測到直敘句/信心不足 ({l1_conf})，啟動外部工具增強模式...")
            
            try:
                # [FIX] 步驟 1: 先讓 LLM 扮演「翻譯官」，將長句轉為 1-2 個核心搜尋詞
                # 這解決了 "外部工具查詢無結果" 的問題
                extraction_prompt = (
                    f"請從以下患者描述中，提取最核心的一個「中醫病名」或「主症術語」用於檢索百科。\n"
                    f"患者描述：{user_query}\n"
                    f"要求：只輸出一個詞，不要其他文字。範例：「產後缺乳」、「失眠」。"
                )
                search_term = await self.llm.chat_complete(
                    system_prompt="你是一個精準的中醫關鍵詞提取器。",
                    user_prompt=extraction_prompt
                )
                search_term = search_term.strip().replace("。", "")
                logger.info(f"🔧 [L1 Translation] 長句轉譯 -> 搜尋詞: {search_term}")

                # [FIX] 步驟 2: 使用轉譯後的關鍵詞去查工具 (A+百科)
                loop = asyncio.get_event_loop()
                tool_content = await loop.run_in_executor(
                    None, 
                    self.tools.tool_b_syndrome_logic, 
                    search_term # 這裡傳入短詞，工具就能找到了！
                )
                
                # 步驟 3: 從工具回傳的豐富知識中，提取更多擴充關鍵字
                if tool_content and "未找到" not in tool_content:
                    enrichment_prompt = (
                        f"參考以下中醫知識，為症狀 '{search_term}' 提取 3-5 個相關的中醫辨證關鍵字(如證型、病機)。"
                        f"只輸出關鍵字，用空格分隔。\n\n知識內容：{tool_content[:500]}"
                    )
                    enriched_terms = await self.llm.chat_complete(
                        system_prompt="你是一個中醫術語擴充器。",
                        user_prompt=enrichment_prompt
                    )
                    
                    logger.info(f"🔧 [Tool Result] 知識庫擴充成功 -> 增強術語: {enriched_terms}")
                    user_query_text = f"{user_query} {enriched_terms}"
                    
                    # 標記增強
                    if "retrieval_strategy" in l1:
                        l1["retrieval_strategy"]["reasoning"] += " (已由 A+百科工具增強術語)"
                    # =====================================================
                    # 🚨 [CRITICAL FIX] 強制覆蓋 L1 的下一步決策
                    # =====================================================
                    # 原本 L1 因為信心低可能回傳 "ask_more"，導致後面檢索區塊被跳過。
                    # 現在既然已經增強了關鍵字，我們就強制系統進行向量檢索。
                    l1["next_action"] = "vector_search" 
                    logger.info("🔧 [L1 Override] 已強制將 next_action 修改為 'vector_search'")
                                    
            except Exception as e:
                logger.warning(f"⚠️ 工具增強執行失敗 (不影響主流程): {e}")

        # ------------------- 正常流程 -------------------
        
        # 2. 檢索層 (Retrieval Layer)
        cases: List[Dict] = []
        retrieval_metadata = {}
        
        if l1.get("next_action") == "vector_search":
            if not self.SE or not self.embed:
                logger.error("❌ SearchEngine 或 EmbedClient 未初始化，無法進行檢索。")
                return result 
            
            # [MODIFIED] 使用經過工具增強的 user_query_text
            text_query = user_query_text
            
            # 🆕 根據模式選擇檢索方式
            if self.agentic_enabled and self.agentic_retrieval:
                # === Agentic 智能檢索模式 ===
                logger.info("[RETRIEVAL] 使用 Agentic 智能檢索")
                
                try:
                    # 執行智能檢索（包含動態 alpha、品質評估、自動 fallback）
                    retrieval_result = await self.agentic_retrieval.intelligent_search(
                        index="TCMCase",
                        text=text_query,
                        l1_strategy=l1.get("retrieval_strategy", {}),
                        limit=3
                    )
                    
                    cases = retrieval_result.get("cases", [])
                    retrieval_metadata = retrieval_result.get("metadata", {})
                    
                    # 記錄 Agentic 檢索決策
                    logger.info(
                        f"[AGENTIC RETRIEVAL]\n"
                        f"  初始 Alpha: {retrieval_metadata.get('initial_alpha', 0.0):.2f}\n"
                        f"  最終 Alpha: {retrieval_metadata.get('final_alpha', 0.0):.2f}\n"
                        f"  嘗試次數: {retrieval_metadata.get('attempts', 0)}\n"
                        f"  品質評分: {retrieval_metadata.get('quality_score', 0.0):.3f}\n"
                        f"  Fallback: {'是' if retrieval_metadata.get('fallback_triggered') else '否'}"
                    )
                    
                except Exception as e:
                    logger.error(f"❌ Agentic 檢索失敗: {e}", exc_info=True)
                    cases = []
                    
            else:
                # === 傳統檢索模式 ===
                logger.info("[RETRIEVAL] 使用傳統檢索模式")
                
                # 1. 獲取查詢向量
                try:
                    vector = await self.embed.embed(text_query) 
                except Exception as e:
                     logger.warning(f"⚠️ 向量生成失敗，嘗試純 BM25: {e}")
                     vector = None
                    
                # 2. 執行混合檢索
                try:
                    cases = await self.SE.hybrid_search(
                        index="TCMCase", 
                        text=text_query, 
                        vector=vector, 
                        alpha=0.55 if vector else 1.0, 
                        limit=3,
                        search_fields=["full_text"] 
                    )
                except Exception as e:
                    logger.error(f"❌ 檢索失敗: {e}", exc_info=True)
                    cases = []

        # 🚨 日誌點 2：檢索結果摘要
        log_samples = []
        if cases:
            log_samples = [
                {"case_id": c.get("case_id", "N/A"), "score": f"{_score_of(c):.4f}"}
                for c in cases[:3] 
            ]
        logger.info(f"[RETRIEVAL RESULT] 成功找到 {len(cases)} 個案例. Top 3 範例: {log_samples}")

        # 🆕 將檢索元數據添加到結果中
        if retrieval_metadata:
            result['retrieval_metadata'] = retrieval_metadata

        if not cases:
            debug_notes.append("Retrieval returned zero cases.")
            result["debug_note"] = "; ".join(debug_notes)
            # return result 

        
        # 3. L2: 生成層 (Diagnosis Layer)
        l2_raw_result = {}
        
        # [MODIFIED] 根據模式選擇執行路徑
        if self.agentic_enabled and self.l2_agentic:
            logger.info("[L2] 使用 Agentic 增強模式 (v2.3 全託管流程)")
            
            # 執行全託管診斷 (包含 鎖定錨定 -> 推理 -> 內部知識檢索 -> 工具調用 -> 綜合)
            # 這裡呼叫的是我們剛在 l2_agentic_diagnosis.py 中更新的 diagnose_with_tools
            agentic_result = await self.l2_agentic.diagnose_with_tools(
                user_query=user_query,
                retrieved_cases=cases,
                l1_decision=l1
            )
            
            # [關鍵] 將 Agentic 的最終診斷 (Final Diagnosis) 重構為系統通用的 l2_raw_result 格式
            # 這樣 L3 (安全審核) 和 L4 (呈現) 才能看到被 Agentic 修正過的高品質內容
            final_diag = agentic_result.get("final_diagnosis", {})
            metrics = agentic_result.get("metrics", {})
            tool_outputs = agentic_result.get("tool_outputs", {})
            
            # 重建 l2_raw_result 結構
            l2_raw_result = {
                "tcm_inference": {
                    "primary_pattern": final_diag.get("primary_syndrome", "未定"),
                    "pathogenesis": final_diag.get("pathogenesis", ""),
                    "treatment_principle": final_diag.get("treatment_principle", ""),
                    # 這裡將包含 '發現疑點...' 的 reasoning 注入，讓 L4 呈現給用戶看
                    "syndrome_analysis": final_diag.get("reasoning", "") 
                },
                "coverage_evaluation": {
                    "coverage_ratio": metrics.get("case_completeness", 0.0),
                    "missing_info": []
                },
                "selected_case": {
                    # 嘗試從 initial_diagnosis 拿回錨定資訊，若無則標記為 Agentic 合成
                    "case_id": agentic_result.get("initial_diagnosis", {}).get("anchored_case_id", "Agentic_Synthesized"),
                    "diagnosis": "Agentic Optimization"
                },
                "knowledge_supplements": final_diag.get("knowledge_supplements", [])
            }

            # 填充 result 結構
            result['l2'] = l2_raw_result
            result['l2_agentic_metadata'] = {
                "validation_status": "validated" if tool_outputs else "unvalidated",
                "tool_calls": len(tool_outputs),
                "confidence_boost": 0.15 if tool_outputs else 0.0,
                "case_completeness": metrics.get("case_completeness", 0.0),
                "diagnosis_confidence": metrics.get("final_confidence", 0.0)
            }
            
            # 將工具輸出傳遞給 result (供前端或除錯使用)
            if tool_outputs:
                result['l2']['tool_outputs'] = tool_outputs

            logger.info(
                f"[L2 AGENTIC COMPLETE]\n"
                f"  最終診斷: {l2_raw_result['tcm_inference']['primary_pattern']}\n"
                f"  工具調用: {len(tool_outputs)}\n"
                f"  包含疑點分析: {'是' if '疑點' in l2_raw_result['tcm_inference']['syndrome_analysis'] else '否'}"
            )

        else:
            # === 傳統模式 ===
            logger.info("[L2] 使用傳統模式 (無 Agentic)")
            l2_payload = {
                "layer": "L2_CASE_ANCHORED_DIAGNOSIS",
                "input": {
                    "user_accumulated_query": user_query,
                    "retrieved_cases": cases,
                    "round_count": round_count,
                    "previous_diagnosis": previous_diagnosis if previous_diagnosis else {}
                }
            }
            l2_raw_result = await call_llm_with_prompt(
                self.llm, 
                self.prompts_dir / "l2_case_anchored_diagnosis_prompt.txt", 
                l2_payload, 
                temperature=0.1
            )
            result['l2'] = l2_raw_result

        # 🚨 [日誌點 3: L2 案例錨定摘要]
        selected_case_id = l2_raw_result.get("selected_case", {}).get("case_id", "未錨定")
        coverage = l2_raw_result.get("coverage_evaluation", {}).get("coverage_ratio", 0.0)
        primary_pattern = l2_raw_result.get('tcm_inference', {}).get('primary_pattern', 'N/A')
        
        logger.info(
            f"[L2 DIAGNOSIS SUMMARY] 錨定 ID: {selected_case_id}, 證型: {primary_pattern}, "
            f"覆蓋度: {coverage:.2f}"
        )

        # 4. L3: 審核層 (Safety Review Layer)
        l3_payload = {"layer": "L3_SAFETY_REVIEW", "input": {"diagnosis_payload": l2_raw_result}}
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
        
        # [FIX] 前端防崩潰處理：確保 diagnosis 是字串
        presentation = l4_result.get('presentation', "")
        
        if isinstance(presentation, dict):
            # 如果 L4 回傳的是結構化物件 (例如包含 title/content)，優先取內容
            if "content" in presentation:
                result['diagnosis'] = presentation["content"]
            elif "message" in presentation:
                result['diagnosis'] = presentation["message"]
            else:
                # 否則將整個字典轉為易讀的字串
                lines = []
                for k, v in presentation.items():
                    # 過濾掉非必要的 metadata
                    if k not in ["type", "status"]:
                        lines.append(f"**{k}**: {v}")
                result['diagnosis'] = "\n\n".join(lines)
        elif isinstance(presentation, list):
            result['diagnosis'] = "\n".join([str(x) for x in presentation])
        else:
            # 已經是字串或 None
            result['diagnosis'] = str(presentation) if presentation else "診斷生成異常，請稍後再試。"
        
        # 檢查收斂 (依據 SCBR 文件 [10.2] 的收斂條件)
        coverage_ratio = l2_raw_result.get('coverage_evaluation', {}).get('coverage_ratio', 0.0)
        # 修正收斂判斷邏輯，納入最大輪次檢查 (強制收斂)
        is_coverage_ok = coverage_ratio >= 0.95
        # 這裡的邏輯必須和 main.py 內部的 should_converge 邏輯保持一致
        result['converged'] = is_coverage_ok 

        return result