# -*- coding: utf-8 -*-
"""
L2 Agentic 診斷層 - 工具整合模組（修正版）
================================

修正內容：
1. ✅ 添加 enhance_diagnosis() 適配方法（用於 four_layer_pipeline 調用）
2. ✅ 添加 _extract_diagnosis_from_l2_result() 輔助方法
3. ✅ 添加 _evaluate_case_completeness_from_l2() 評估方法
4. ✅ 添加 _evaluate_diagnosis_confidence_from_l2() 評估方法
5. ✅ 動態添加 diagnosis_confidence 和 case_completeness 屬性到輸出
6. 🚨 [NEW] 方案三實裝：檢索為 0 時的虛擬案例保底機制。

職責：
1. 接收 L1 檢索結果，進行案例錨定診斷
2. 自主判斷是否需要調用外部工具
3. 執行幻覺校驗、知識補充、權威背書
4. 輸出經過驗證的診斷結果
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio

# 導入您已開發的工具庫
from ..tools.tcm_tools import TCMTools, TCMUnifiedToolkit
from ..utils.terminology_manager import TerminologyManager
from ..llm.embedding import EmbedClient
# from .search_engine import SearchEngine 

logger = logging.getLogger("L2AgenticDiagnosis")


# ==================== 數據結構定義 ====================

class ToolCallReason(Enum):
    """工具調用原因枚舉"""
    KNOWLEDGE_GAP = "knowledge_gap"           # 案例知識不足
    HALLUCINATION_CHECK = "hallucination_check"  # 需要幻覺校驗
    AUTHORITY_ENDORSEMENT = "authority_endorsement"  # 需要權威背書
    FULL_VALIDATION = "full_validation"       # 完整驗證（fallback）


@dataclass
class ToolCallDecision:
    """工具調用決策結果"""
    should_call_tool_a: bool = False  # ICD-11 術語標準化
    should_call_tool_b: bool = False  # A+百科 辨證邏輯
    should_call_tool_c: bool = False  # ETCM 現代對照
    reasons: List[ToolCallReason] = field(default_factory=list)
    target_terms: List[str] = field(default_factory=list)  # 需要查詢的術語


@dataclass
class ToolCallResult:
    """工具調用結果"""
    tool_name: str
    success: bool
    content: str
    error: Optional[str] = None


@dataclass
class L2AgenticOutput:
    """L2 Agentic 輸出結構"""
    # 核心診斷結果
    anchored_case: Dict[str, Any]           # 錨定案例
    syndrome_analysis: str                   # 證型分析
    diagnosis_reasoning: str                 # 診斷推理
    
    # 工具增強結果
    tool_decisions: ToolCallDecision         # 工具調用決策
    tool_results: List[ToolCallResult]       # 工具調用結果
    
    # 驗證與背書
    validation_status: str                   # "validated" | "partially_validated" | "unvalidated"
    authority_references: List[str]          # 權威引用
    knowledge_supplements: List[str]         # 知識補充
    modern_evidence: List[str]                  # 現代科學證據（Tool C）
    
    # 元數據
    coverage_score: float                    # 覆蓋度
    confidence_boost: float                  # 工具帶來的置信度提升
    follow_up_questions: List[str]           # 追問問題


# ==================== L2 Agentic 核心邏輯 ====================

class L2AgenticDiagnosis:
    """
    L2 Agentic 診斷層
    """
    
    def __init__(self, config: Any, search_engine: Any = None, embed_client: Any = None):
        """
        初始化 L2 Agentic 診斷層
        """
        self.config = config
        self.se = search_engine
        self.embed = embed_client
        self.toolkit = TCMUnifiedToolkit()
        self.tools = TCMTools()
        self.term_manager = TerminologyManager()
        
        # 工具調用配置
        self.tool_config = {
            "enable_tool_calls": True,           # 總開關
            "enable_tool_a": True,               # ICD-11 開關
            "enable_tool_b": True,               # A+百科 開關
            "enable_tool_c": True,               # ETCM 開關
            "knowledge_gap_threshold": 0.6,      # 知識缺口門檻（案例完整度低於此值觸發 Tool B）
            "validation_confidence_threshold": 0.7,  # 需要驗證的置信度門檻
            "max_tool_calls_per_diagnosis": 3,   # 單次診斷最大工具調用次數
            "tool_timeout": 15.0,                # 工具調用超時（秒）
        }
        
        logger.info("[L2Agentic] 初始化完成 - 工具調用已啟用")
    
    # ==================== 主要診斷流程 ====================
    
    async def diagnose_with_tools(
        self,
        user_symptoms: str,
        retrieved_cases: List[Dict[str, Any]],
        l1_decision: Dict[str, Any]
    ) -> L2AgenticOutput:
        """
        執行帶工具增強的診斷流程
        """
        logger.info("[L2Agentic] 開始診斷流程")
        
        # 步驟 1：案例錨定與初步診斷
        anchored_case, initial_diagnosis = await self._anchor_and_diagnose(
            user_symptoms, retrieved_cases
        )
        
        # 步驟 2：評估案例完整度與診斷品質
        case_completeness = self._evaluate_case_completeness(anchored_case)
        diagnosis_confidence = self._evaluate_diagnosis_confidence(
            initial_diagnosis, l1_decision
        )
        
        # 步驟 3：自主決策是否需要工具調用
        tool_decision = self._decide_tool_calls(
            anchored_case=anchored_case,
            initial_diagnosis=initial_diagnosis,
            case_completeness=case_completeness,
            diagnosis_confidence=diagnosis_confidence,
            l1_decision=l1_decision
        )
        
        # 步驟 4：執行工具調用（如有需要）
        tool_results = []
        if self._should_call_any_tool(tool_decision):
            tool_results = await self._execute_tool_calls(
                tool_decision, 
                initial_diagnosis.get("primary_syndrome", "")
            )
        
        # 步驟 5：整合工具結果，增強診斷
        enhanced_diagnosis = self._integrate_tool_results(
            initial_diagnosis, tool_results
        )
        
        # 步驟 6：生成最終輸出
        output = self._build_output(
            anchored_case=anchored_case,
            enhanced_diagnosis=enhanced_diagnosis,
            tool_decision=tool_decision,
            tool_results=tool_results,
            case_completeness=case_completeness
        )
        
        logger.info(f"[L2Agentic] 診斷完成 - 驗證狀態: {output.validation_status}")
        return output
    
    # [NEW] 內部知識庫查詢方法
    async def _query_internal_knowledge(self, query_text: str, vector_search_only: bool = False) -> Dict[str, Any]:
        """
        從 Weaviate TCM Class 查詢標準證型知識
        """
        if not self.se or not query_text:
            return None
            
        try:
            # 1. 生成向量
            vector = None
            if self.embed:
                try:
                    vector = await self.embed.embed(query_text)
                except Exception as e:
                    logger.warning(f"向量生成失敗: {e}")

            # 2. 設定檢索參數
            # [FIX] 大幅調降 Alpha 至 0.2，強力依賴 BM25 關鍵字匹配
            # 這是為了確保"胃"痛不會匹配到"腰"痛 (向量模糊匹配的副作用)
            alpha_val = 0.2 
            
            logger.info(f"[L2Agentic] 內部知識庫查詢: '{query_text[:20]}...' (Alpha={alpha_val}, Vector={'Yes' if vector else 'No'})")

            # 3. 使用混合檢索
            # [FIX] 移除 ^2 語法，確保欄位名稱正確。加入 definition 以增加匹配機會。
            results = await self.se.hybrid_search(
                index="TCM",
                text=query_text,
                vector=vector,
                alpha=alpha_val, 
                limit=3, 
                search_fields=["name_zh", "definition", "clinical_manifestations", "vector_text"] 
            )
            
            # 4. [NEW] 關鍵字驗證 (Scope Guard)
            # 簡單的中醫病位檢查：如果查詢包含明確部位，結果最好也要包含
            key_organs = ["胃", "心", "肝", "脾", "肺", "腎", "膽", "腸", "腰", "膝", "頭"]
            query_organs = [k for k in key_organs if k in query_text]
            
            valid_result = None
            
            if results:
                # 記錄前三名以便除錯
                top3_names = [r.get('name_zh') for r in results]
                logger.info(f"[L2Agentic] 內部檢索候選: {top3_names}")

                for res in results:
                    score = res.get("score", 0)
                    name = res.get("name_zh", "")
                    content_str = str(res.get("definition", "")) + str(res.get("clinical_manifestations", ""))
                    
                    # [FIX] 放寬分數門檻，因為 Alpha 0.2 會拉低整體分數
                    if score < 0.40: continue

                    # [思維檢核] 關鍵字驗證
                    # 如果查詢中有明確臟腑，檢查結果內容是否包含該臟腑關鍵字
                    if query_organs:
                        is_relevant = False
                        for organ in query_organs:
                            if organ in name or organ in content_str:
                                is_relevant = True
                                break
                        
                        if not is_relevant:
                            logger.info(f"[L2Agentic] 過濾不相關結果: {name} (缺關鍵字: {query_organs})")
                            continue

                    valid_result = res
                    break
            
            if valid_result:
                logger.info(f"[L2Agentic] 內部知識庫命中: {valid_result.get('name_zh')} (Score: {valid_result.get('score', 0):.3f})")
                return valid_result
            else:
                if results:
                    top_score = results[0].get('score', 0)
                    logger.info(f"[L2Agentic] 內部知識庫無匹配 (Top: {results[0].get('name_zh')}, Score: {top_score:.3f} - 過濾或分數過低)")
            
            return None
        except Exception as e:
            logger.warning(f"[L2Agentic] 內部知識庫查詢失敗: {e}", exc_info=True)
            return None
    
    # ==================== 適配方法（用於 four_layer_pipeline 調用）====================
    
    async def enhance_diagnosis(
        self,
        l2_raw_result: Dict[str, Any],
        l1_decision: Dict[str, Any],
        retrieved_cases: List[Dict[str, Any]]
    ) -> L2AgenticOutput:
        """
        診斷增強方法 - 適配 four_layer_pipeline.py 的調用介面
        """
        logger.info("[L2Agentic] 使用 enhance_diagnosis 適配方法")
        
        # [MODIFIED] 虛擬案例防護網
        # 萬一真的沒有案例 (retrieved_cases 為空)，創建一個虛擬案例以防崩潰
        if not retrieved_cases:
            logger.warning("⚠️ L2 收到 0 個案例，使用虛擬案例進行純理論診斷")
            
            # 嘗試從 L1 決策中找一個「暫定病名」，避免 "待定" 導致工具不啟動
            kw = l1_decision.get("keyword_extraction", {})
            candidates = kw.get("syndrome_signals", []) + kw.get("symptom_terms", [])
            fallback_name = candidates[0] if candidates else "未名病症"
            
            virtual_case = {
                "case_id": "VIRTUAL_THEORY_CASE",
                "diagnosis": f"{fallback_name}(虛擬)", # 給一個具體名字
                "syndrome": fallback_name,
                "chief_complaint": "資訊不足，啟動純理論推斷模式",
                "treatment": "建議諮詢醫師",
                "score": 0.0,
                "pathogenesis": "", # 留白以觸發 Knowledge Gap
            }
            retrieved_cases = [virtual_case]

        # 步驟 1：評估傳統 L2 診斷的品質
        case_completeness = self._evaluate_case_completeness_from_l2(l2_raw_result, retrieved_cases)
        diagnosis_confidence = self._evaluate_diagnosis_confidence_from_l2(
            l2_raw_result, l1_decision
        )
        
        logger.info(
            f"[L2Agentic] 評估結果\n"
            f"  案例完整度: {case_completeness:.2f}\n"
            f"  診斷置信度: {diagnosis_confidence:.2f}"
        )
        
        # 步驟 2：使用錨定案例（現在保證至少有一個，即使是虛擬的）
        anchored_case = retrieved_cases[0]
        
        # 步驟 3：從 l2_raw_result 提取診斷資訊
        # [MODIFIED] 傳入 retrieved_cases 以供保底使用
        initial_diagnosis = self._extract_diagnosis_from_l2_result(
            l2_raw_result,
            retrieved_cases=retrieved_cases
        )

        # 🚨 [Step 3.5] 內部知識庫增強 (Internal Knowledge Enrichment)
        user_query_text = ""
        # 嘗試從 L1 決策中獲取原始輸入
        if l1_decision and "input" in l1_decision:
            user_query_text = l1_decision["input"].get("user_query", "")
        
        # 如果 L1 沒傳，嘗試從 L2 payload 找 (有些實作會放)
        if not user_query_text and "user_accumulated_query" in l2_raw_result:
             user_query_text = l2_raw_result.get("user_accumulated_query", "")

        internal_knowledge = None
        if user_query_text:
            # 使用原始症狀進行檢索 (Vector Search)
            internal_knowledge = await self._query_internal_knowledge(user_query_text, vector_search_only=True)
        else:
            # 保底：如果真的拿不到原始輸入，才用 L2 的診斷名稱去查
            logger.warning("[L2Agentic] 無法獲取原始輸入，降級使用 L2 診斷名稱查詢")
            primary_syndrome = initial_diagnosis.get("primary_syndrome", "")
            # 這裡需要簡單清洗一下名稱
            import re
            clean_name = re.sub(r'[（\(].*?[）\)]', '', primary_syndrome).strip()
            internal_knowledge = await self._query_internal_knowledge(clean_name, vector_search_only=False)

        if internal_knowledge:
            tcm_name = internal_knowledge.get("name_zh", "")
            def_text = internal_knowledge.get("definition", "")
            manifest = internal_knowledge.get("clinical_manifestations", [])
            manifest_str = "、".join(manifest) if isinstance(manifest, list) else str(manifest)
            
            # [FIX] 思維比對：L2 的初步判斷 vs 內部標準庫檢索結果
            l2_primary = initial_diagnosis.get("primary_syndrome", "未定")
            
            # 注入補充資訊
            supplement_text = (
                f"【內部知識庫檢索結果】\n"
                f"系統依據您的症狀描述，檢索到最相似的標準證型為：{tcm_name}\n"
                f"定義：{def_text}\n"
                f"典型表現：{manifest_str}\n"
            )
            
            if "knowledge_supplements" not in initial_diagnosis:
                initial_diagnosis["knowledge_supplements"] = []
            initial_diagnosis["knowledge_supplements"].append(supplement_text)
            
            # [FIX] 如果 L2 判斷與內部庫差異過大，強制修正或標記疑點
            # 例如 L2 說是"脾虛"，但內部庫說是"胃熱"，這是一個值得注意的衝突
            if tcm_name not in l2_primary and len(l2_primary) > 1:
                conflict_note = f"發現疑點：初步推斷為'{l2_primary}'，但症狀特徵更接近標準庫中的'{tcm_name}'。"
                
                # 將此疑點注入到病機分析中，強迫後續流程面對這個衝突
                current_reasoning = initial_diagnosis.get("reasoning", "")
                initial_diagnosis["reasoning"] = f"{conflict_note} {current_reasoning}"
                
                # 標記為需要工具進一步核實
                initial_diagnosis["internal_conflict_detected"] = True
            
            # 標記已獲得內部檢索（無論是否衝突，都算查過了）
            initial_diagnosis["internal_validated"] = True
            
            logger.info(f"[L2Agentic] 已注入內部知識: {tcm_name} (與 L2 '{l2_primary}' 比對)")
            

        # 步驟 4：決策是否需要工具調用
        tool_decision = self._decide_tool_calls(
            anchored_case=anchored_case,
            initial_diagnosis=initial_diagnosis, # 這裡已經包含內部知識了
            case_completeness=case_completeness,
            diagnosis_confidence=diagnosis_confidence,
            l1_decision=l1_decision
        )
        
        # 步驟 5：執行工具調用（如有需要）
        tool_results = []
        if self._should_call_any_tool(tool_decision):
            num_tools = sum([
                tool_decision.should_call_tool_a,
                tool_decision.should_call_tool_b,
                tool_decision.should_call_tool_c
            ])
            logger.info(f"[L2Agentic] 並行執行 {num_tools} 個工具調用")
            tool_results = await self._execute_tool_calls(
                tool_decision,
                initial_diagnosis.get("primary_syndrome", "")
            )
        else:
            logger.info("[L2Agentic] 無需調用工具，條件未觸發")
        
        # 步驟 6：整合工具結果
        enhanced_diagnosis = self._integrate_tool_results(
            initial_diagnosis, tool_results
        )
        
        # 步驟 7：構建輸出
        output = self._build_output(
            anchored_case=anchored_case,
            enhanced_diagnosis=enhanced_diagnosis,
            tool_decision=tool_decision,
            tool_results=tool_results,
            case_completeness=case_completeness
        )
        
        # 🆕 動態添加屬性供 four_layer_pipeline 使用
        output.diagnosis_confidence = diagnosis_confidence
        output.case_completeness = case_completeness
        
        logger.info(
            f"[L2Agentic] 增強完成\n"
            f"  驗證狀態: {output.validation_status}\n"
            f"  工具調用數: {len(tool_results)}\n"
            f"  置信度提升: +{output.confidence_boost:.2f}"
        )
        
        return output
    
    # ==================== [新增] 輔助方法 ====================

    def _extract_diagnosis_from_l2_result(
        self,
        l2_result: Dict[str, Any],
        retrieved_cases: List[Dict[str, Any]] = None  # [MODIFIED] 新增參數
    ) -> Dict[str, Any]:
        """
        從傳統 L2 診斷結果中提取診斷資訊 (修正嵌套結構讀取 + 強制保底)
        """
        # 優先從 tcm_inference 提取，如果沒有則嘗試從根目錄提取 (兼容舊版)
        inference = l2_result.get("tcm_inference", {})
        
        if not inference and "primary_pattern" in l2_result:
             inference = l2_result

        primary = (
            inference.get("primary_pattern") or 
            l2_result.get("primary_pattern") or 
            l2_result.get("primary_syndrome") or 
            ""
        ).strip()

        # [MODIFIED] 強制保底邏輯：檢測 LLM 是否拒絕診斷
        refusal_keywords = [
            "無法形成", "無法判斷", "資訊不足", "not be determined", 
            "no primary pattern", "n/a", "unknown", "none"
        ]
        
        if not primary or any(k in primary.lower() for k in refusal_keywords):
            # 嘗試使用檢索到的第一個案例作為保底
            if retrieved_cases and len(retrieved_cases) > 0:
                top_case = retrieved_cases[0]
                fallback_diag = (
                    top_case.get("diagnosis") or 
                    top_case.get("syndrome") or 
                    top_case.get("primary_pattern")
                )
                if fallback_diag:
                    primary = f"{fallback_diag} (系統強制錨定)"
                    logger.warning(f"⚠️ LLM 拒絕診斷，已強制使用 Top-1 案例保底: {primary}")
            
            # 如果連案例都沒有，才給最終保底
            if not primary or any(k in primary.lower() for k in refusal_keywords):
                primary = "待定 (資訊極度缺乏)"

        return {
            "primary_syndrome": primary,
            "secondary_syndromes": [], 
            "pathogenesis": inference.get("pathogenesis", "") or l2_result.get("pathogenesis", ""),
            "treatment_principle": inference.get("treatment_principle", "") or l2_result.get("treatment_principle", ""),
            "confidence": 0.9 if l2_result.get("status") == "ok" else 0.6, 
            "reasoning": inference.get("syndrome_analysis", "基於案例相似度推斷")
        }
    
    def _evaluate_case_completeness_from_l2(
        self,
        l2_result: Dict[str, Any],
        retrieved_cases: List[Dict[str, Any]] = None
    ) -> float:
        """
        從 L2 診斷結果評估案例完整度（引入檢索品質懲罰）
        """
        # 1. 計算基礎內容分數
        content_score = 0.0
        inference = l2_result.get("tcm_inference", {})
        
        field_mapping = {
            "primary_syndrome": "primary_pattern",
            "pathogenesis": "pathogenesis",
            "treatment_principle": "treatment_principle",
            "reasoning": "syndrome_analysis"
        }
        
        weights = {
            "primary_syndrome": 0.4,
            "pathogenesis": 0.3,
            "treatment_principle": 0.2,
            "reasoning": 0.1
        }
        
        for weight_key, weight in weights.items():
            json_key = field_mapping.get(weight_key, weight_key)
            value = inference.get(json_key) or l2_result.get(json_key)
            
            if value:
                if isinstance(value, str) and len(value) > 5 and "待定" not in value:
                    content_score += weight
                elif isinstance(value, (list, dict)) and len(value) > 0:
                    content_score += weight
        
        # 2. 計算檢索懲罰因子
        penalty_factor = 1.0
        if retrieved_cases:
            top_case = retrieved_cases[0]
            max_score = float(
                top_case.get("score") or 
                top_case.get("_additional", {}).get("score") or 
                top_case.get("_final_score") or 
                0.0
            )
            
            if max_score < 0.60:
                penalty_factor = 0.5
            elif max_score < 0.75:
                penalty_factor = 0.7
                
        final_score = content_score * penalty_factor
        return min(1.0, final_score)
    
    def _evaluate_diagnosis_confidence_from_l2(
        self,
        l2_result: Dict[str, Any],
        l1_decision: Dict[str, Any]
    ) -> float:
        """
        從 L2 診斷結果和 L1 決策評估診斷置信度
        """
        base_confidence = l2_result.get("confidence", 0.7)
        l1_confidence = l1_decision.get("overall_confidence", 0.7)
        
        # L2 診斷置信度占 70%，L1 檢索置信度占 30%
        combined_confidence = base_confidence * 0.7 + l1_confidence * 0.3
        
        if l2_result.get("reasoning") and len(str(l2_result["reasoning"])) > 50:
            combined_confidence += 0.05
        
        if l2_result.get("pathogenesis") and len(str(l2_result["pathogenesis"])) > 30:
            combined_confidence += 0.05
        
        return min(1.0, combined_confidence)
    
    # ==================== 案例錨定與初步診斷 ====================
    
    async def _anchor_and_diagnose(
        self,
        user_symptoms: str,
        retrieved_cases: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        執行案例錨定與初步診斷（原有 L2 邏輯）
        """
        if not retrieved_cases:
            return {}, {"error": "無可用案例"}
        
        anchored_case = retrieved_cases[0]
        
        initial_diagnosis = {
            "primary_syndrome": anchored_case.get("syndrome", "待分析"),
            "secondary_syndromes": [],
            "pathogenesis": anchored_case.get("pathogenesis", ""),
            "treatment_principle": anchored_case.get("treatment", ""),
            "confidence": 0.7,
            "reasoning": "基於案例相似度推斷"
        }
        
        return anchored_case, initial_diagnosis
    
    # ==================== 評估函數 ====================
    
    def _evaluate_case_completeness(self, case: Dict[str, Any]) -> float:
        """
        評估案例資訊完整度
        """
        if not case:
            return 0.0
        
        required_fields = {
            "symptoms": 0.25,
            "tongue_pulse": 0.20,
            "pathogenesis": 0.20,
            "syndrome": 0.20,
            "treatment": 0.15
        }
        
        score = 0.0
        for field, weight in required_fields.items():
            if case.get(field):
                value = case[field]
                if isinstance(value, str) and len(value) > 5:
                    score += weight
                elif isinstance(value, (list, dict)) and len(value) > 0:
                    score += weight
        
        return score
    
    def _evaluate_diagnosis_confidence(
        self,
        diagnosis: Dict[str, Any],
        l1_decision: Dict[str, Any]
    ) -> float:
        """
        評估診斷的置信度
        """
        base_confidence = diagnosis.get("confidence", 0.7)
        
        if diagnosis.get("primary_syndrome") and diagnosis["primary_syndrome"] not in ["待分析", ""]:
            base_confidence += 0.05
        
        if diagnosis.get("pathogenesis") and len(diagnosis["pathogenesis"]) > 20:
            base_confidence += 0.05
        
        l1_confidence = l1_decision.get("overall_confidence", 0.7)
        final_confidence = (base_confidence + l1_confidence) / 2
        
        return min(1.0, final_confidence)
    
    # ==================== 工具調用決策 ====================
    
    def _decide_tool_calls(self, anchored_case, initial_diagnosis, case_completeness, diagnosis_confidence, l1_decision):
        decision = ToolCallDecision()
        """
        自主決策是否需要調用工具(深度整合決策樹)
        """
        target_syndrome = initial_diagnosis.get("primary_syndrome", "")
        
        # [FIX] 如果是虛擬案例 (case_id 為 VIRTUAL)，強制設定一個目標詞，不讓它 return
        if anchored_case.get("case_id") == "VIRTUAL_THEORY_CASE":
            # 嘗試用 L1 的輸入當作查詢詞
            target_syndrome = l1_decision.get("input", {}).get("user_query", "")[:20] 
            logger.info(f"[L2Agentic] 虛擬案例模式：強制設定工具查詢詞為 '{target_syndrome}'")

        # 基礎檢查：如果是空的，且不是虛擬案例，才返回
        if (not target_syndrome or "待定" in target_syndrome) and anchored_case.get("case_id") != "VIRTUAL_THEORY_CASE":
            return decision

        # --- 策略 A: 知識缺口 (Knowledge Gap) -> Tool B (A+百科) ---
        has_pathogenesis = len(initial_diagnosis.get("pathogenesis", "")) > 20
        # [MODIFIED] 檢查是否已經有內部知識驗證
        has_internal_knowledge = initial_diagnosis.get("internal_validated", False)
        
        # 如果完整度低，且沒有內部知識支撐，才調用外部百科
        if (case_completeness < self.tool_config["knowledge_gap_threshold"] or not has_pathogenesis) and not has_internal_knowledge:
            if self.tool_config["enable_tool_b"]:
                decision.should_call_tool_b = True
                decision.reasons.append(ToolCallReason.KNOWLEDGE_GAP)
                decision.target_terms.append(target_syndrome)
                logger.info(f"[L2Agentic] 觸發 Tool B (病機缺失且無內部庫存: {case_completeness:.2f})")
        elif has_internal_knowledge:
            logger.info(f"[L2Agentic] 內部知識庫已滿足知識缺口，跳過 Tool B")

        # --- 策略 B: 幻覺校驗 (Hallucination Check) -> Tool C (ETCM) ---
        if diagnosis_confidence < self.tool_config["validation_confidence_threshold"]:
            if self.tool_config["enable_tool_c"]:
                decision.should_call_tool_c = True
                decision.reasons.append(ToolCallReason.HALLUCINATION_CHECK)
                if target_syndrome not in decision.target_terms:
                    decision.target_terms.append(target_syndrome)
                logger.info(f"[L2Agentic] 觸發 Tool C (置信度不足: {diagnosis_confidence:.2f})")

        # --- 策略 C: 權威背書 (Authority Endorsement) -> Tool A (ICD-11) ---
        if target_syndrome and len(target_syndrome) < 10: 
            if self.tool_config["enable_tool_a"]:
                decision.should_call_tool_a = True
                decision.reasons.append(ToolCallReason.AUTHORITY_ENDORSEMENT)
                if target_syndrome not in decision.target_terms:
                    decision.target_terms.append(target_syndrome)
                logger.info("[L2Agentic] 觸發 Tool A (尋求 ICD-11 標準化背書)")
        
        return decision
    
    def _should_call_any_tool(self, decision: ToolCallDecision) -> bool:
        """檢查是否需要調用任何工具"""
        return (
            decision.should_call_tool_a or
            decision.should_call_tool_b or
            decision.should_call_tool_c
        )
    
    # ==================== 工具調用執行 ====================
    
    async def _execute_tool_calls(
        self,
        decision: ToolCallDecision,
        primary_syndrome: str
    ) -> List[ToolCallResult]:
        """
        並行執行所有需要的工具調用
        """
        tasks = []
        
        if decision.should_call_tool_a:
            tasks.append(self._call_tool_a(primary_syndrome))
        
        if decision.should_call_tool_b:
            tasks.append(self._call_tool_b(primary_syndrome))
        
        if decision.should_call_tool_c:
            tasks.append(self._call_tool_c(primary_syndrome))
        
        results = []
        if tasks:
            try:
                completed = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.tool_config["tool_timeout"]
                )
                
                for result in completed:
                    if isinstance(result, Exception):
                        results.append(ToolCallResult(
                            tool_name="unknown",
                            success=False,
                            content="",
                            error=str(result)
                        ))
                    else:
                        results.append(result)
            except asyncio.TimeoutError:
                logger.error("[L2Agentic] 工具調用總體超時")
                results.append(ToolCallResult(
                    tool_name="batch",
                    success=False,
                    content="",
                    error="工具調用批次超時"
                ))
        
        return results
    
    async def _call_tool_a(self, term: str) -> ToolCallResult:
        """調用 Tool A - ICD-11 術語標準化"""
        try:
            loop = asyncio.get_event_loop()
            content = await asyncio.wait_for(
                loop.run_in_executor(None, self.tools.tool_a_standardize_term, term),
                timeout=self.tool_config["tool_timeout"]
            )
            return ToolCallResult(
                tool_name="Tool A (ICD-11)",
                success=True,
                content=content
            )
        except asyncio.TimeoutError:
            return ToolCallResult(
                tool_name="Tool A (ICD-11)",
                success=False,
                content="",
                error="工具調用超時"
            )
        except Exception as e:
            return ToolCallResult(
                tool_name="Tool A (ICD-11)",
                success=False,
                content="",
                error=str(e)
            )
    
    async def _call_tool_b(self, syndrome_name: str) -> ToolCallResult:
        """調用 Tool B - A+百科辨證邏輯"""
        try:
            loop = asyncio.get_event_loop()
            content = await asyncio.wait_for(
                loop.run_in_executor(None, self.tools.tool_b_syndrome_logic, syndrome_name),
                timeout=self.tool_config["tool_timeout"]
            )
            return ToolCallResult(
                tool_name="Tool B (A+百科)",
                success=True,
                content=content
            )
        except asyncio.TimeoutError:
            return ToolCallResult(
                tool_name="Tool B (A+百科)",
                success=False,
                content="",
                error="工具調用超時"
            )
        except Exception as e:
            return ToolCallResult(
                tool_name="Tool B (A+百科)",
                success=False,
                content="",
                error=str(e)
            )
    
    async def _call_tool_c(self, syndrome_name: str) -> ToolCallResult:
        """調用 Tool C - ETCM 現代對照"""
        try:
            loop = asyncio.get_event_loop()
            content = await asyncio.wait_for(
                loop.run_in_executor(None, self.tools.tool_c_modern_evidence, syndrome_name),
                timeout=self.tool_config["tool_timeout"]
            )
            return ToolCallResult(
                tool_name="Tool C (ETCM)",
                success=True,
                content=content
            )
        except asyncio.TimeoutError:
            return ToolCallResult(
                tool_name="Tool C (ETCM)",
                success=False,
                content="",
                error="工具調用超時"
            )
        except Exception as e:
            return ToolCallResult(
                tool_name="Tool C (ETCM)",
                success=False,
                content="",
                error=str(e)
            )
    
    # ==================== 結果整合 ====================
    
    def _integrate_tool_results(
        self,
        initial_diagnosis: Dict[str, Any],
        tool_results: List[ToolCallResult]
    ) -> Dict[str, Any]:
        """
        整合工具結果到診斷中(資訊融合)
        """
        enhanced = initial_diagnosis.copy()
        for field in ["authority_references", "knowledge_supplements", "modern_evidence", "validation_notes"]:
            if field not in enhanced: enhanced[field] = []
        
        for result in tool_results:
            if not result.success:
                enhanced["validation_notes"].append(f"{result.tool_name} 調用失敗: {result.error}")
                continue

            target_term = initial_diagnosis.get("primary_syndrome", "")
            if target_term and len(target_term) > 1 and "待定" not in target_term:
                if hasattr(self, 'term_manager'):
                    self.term_manager.add_term(target_term)
            
            if "Tool A" in result.tool_name:
                if "ICD-11" in result.content and "未找到" not in result.content:
                    enhanced["authority_references"].append(result.content)
                    enhanced["validation_notes"].insert(0, "★ 證型名稱已獲 WHO ICD-11 標準驗證")
            
            elif "Tool B" in result.tool_name:
                if "臨床表現" in result.content or "辨證" in result.content:
                    enhanced["knowledge_supplements"].append(result.content)
                    enhanced["validation_notes"].append("✓ 已補充辨證邏輯")
                    
                    if not enhanced.get("pathogenesis") or len(enhanced.get("pathogenesis", "")) < 10:
                        enhanced["pathogenesis"] = f"(由外部知識庫補充) 參考 A+百科：{result.content[:100]}..."
            
            elif "Tool C" in result.tool_name:
                if "ETCM" in result.content and "未找到" not in result.content:
                    enhanced["modern_evidence"].append(result.content)
                    enhanced["validation_notes"].append("✓ 已獲取現代科學證據")
        
        return enhanced
    
    # ==================== 輸出構建-使用動態模型 ====================
    
    def _build_output(
        self,
        anchored_case: Dict[str, Any],
        enhanced_diagnosis: Dict[str, Any],
        tool_decision: ToolCallDecision,
        tool_results: List[ToolCallResult],
        case_completeness: float
    ) -> L2AgenticOutput:
        """
        構建最終的 L2 輸出
        """
        successful_tools = sum(1 for r in tool_results if r.success)
        total_tools = len(tool_results)
        
        if total_tools == 0:
            validation_status = "unvalidated"
        elif successful_tools == total_tools:
            validation_status = "validated"
        else:
            validation_status = "partially_validated"
        
        confidence_boost = self._calculate_confidence_boost(enhanced_diagnosis)
        
        follow_up_questions = []
        if case_completeness < 0.7:
            follow_up_questions = self._generate_follow_up_questions(
                anchored_case, enhanced_diagnosis
            )
        
        return L2AgenticOutput(
            anchored_case=anchored_case,
            syndrome_analysis=enhanced_diagnosis.get("primary_syndrome", ""),
            diagnosis_reasoning=self._format_diagnosis_reasoning(enhanced_diagnosis),
            tool_decisions=tool_decision,
            tool_results=tool_results,
            validation_status=validation_status,
            authority_references=enhanced_diagnosis.get("authority_references", []),
            knowledge_supplements=enhanced_diagnosis.get("knowledge_supplements", []),
            modern_evidence=enhanced_diagnosis.get("modern_evidence", []),
            coverage_score=case_completeness,
            confidence_boost=confidence_boost,
            follow_up_questions=follow_up_questions
        )
    
    def _format_diagnosis_reasoning(self, diagnosis: Dict[str, Any]) -> str:
        """格式化診斷推理說明"""
        parts = []
        
        if diagnosis.get("reasoning"):
            parts.append(f"推理依據：{diagnosis['reasoning']}")
        
        if diagnosis.get("pathogenesis"):
            parts.append(f"病因病機：{diagnosis['pathogenesis']}")
        
        if diagnosis.get("validation_notes"):
            parts.append("驗證狀態：" + " | ".join(diagnosis["validation_notes"]))
        
        return "\n".join(parts) if parts else "基於案例相似度推斷"
    
    def _generate_follow_up_questions(
        self,
        case: Dict[str, Any],
        diagnosis: Dict[str, Any]
    ) -> List[str]:
        """生成追問問題"""
        questions = []
        
        if not case.get("tongue_pulse"):
            questions.append("請問您的舌象如何？舌質顏色、舌苔厚薄？")
            questions.append("您的脈象有什麼特點？是否有醫師把過脈？")
        
        if not case.get("duration"):
            questions.append("這些症狀持續多長時間了？")
        
        if not case.get("triggers"):
            questions.append("有什麼情況會加重或緩解這些症狀？")
        
        return questions[:3]
    
    def _calculate_confidence_boost(self, enhanced_diagnosis: Dict[str, Any]) -> float:
        """
        計算診斷置信度增益 (Confidence Gain Model)
        """
        boost = 0.0
        
        if enhanced_diagnosis.get("authority_references"):
            boost += 0.15
            
        supplements = enhanced_diagnosis.get("knowledge_supplements", [])
        if supplements:
            content_len = sum(len(s) for s in supplements)
            if content_len > 100:
                boost += 0.10
            elif content_len > 0:
                boost += 0.05
                
        if enhanced_diagnosis.get("modern_evidence"):
            boost += 0.05
            
        return min(0.3, boost)