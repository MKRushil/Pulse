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

職責：
1. 接收 L1 檢索結果，進行案例錨定診斷
2. 自主判斷是否需要調用外部工具
3. 執行幻覺校驗、知識補充、權威背書
4. 輸出經過驗證的診斷結果

工具調用策略：
- Tool A (ICD-11)：權威性背書，診斷輸出時調用
- Tool B (A+百科)：知識補充，案例資訊不足時調用
- Tool C (ETCM)：幻覺校驗，證型判斷需要科學驗證時調用

設計原則：
- 工具調用是「可選增強」，不是「必要步驟」
- 優先使用案例知識，工具用於補充和驗證
- 工具失敗不應阻斷診斷流程
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
    
    核心能力：
    1. 案例錨定與診斷推理（原有功能）
    2. 自主決策是否需要工具輔助（新增）
    3. 工具調用與結果整合（新增）
    4. 診斷結果驗證與增強（新增）
    """
    
    def __init__(self, config: Any):
        """
        初始化 L2 Agentic 診斷層
        
        Args:
            config: SCBRConfig 配置實例
        """
        self.config = config
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
        
        Args:
            user_symptoms: 用戶症狀描述（累積後的完整描述）
            retrieved_cases: L1 檢索到的案例列表
            l1_decision: L1 的決策資訊（包含關鍵詞、置信度等）
        
        Returns:
            L2AgenticOutput: 完整的診斷輸出
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
    
    # ==================== 適配方法（用於 four_layer_pipeline 調用）====================
    
    async def enhance_diagnosis(
        self,
        l2_raw_result: Dict[str, Any],
        l1_decision: Dict[str, Any],
        retrieved_cases: List[Dict[str, Any]]
    ) -> L2AgenticOutput:
        """
        診斷增強方法 - 適配 four_layer_pipeline.py 的調用介面
        
        🆕 這是一個適配器方法，將 four_layer_pipeline 的調用格式
        轉換為內部診斷邏輯的格式。
        """
        logger.info("[L2Agentic] 使用 enhance_diagnosis 適配方法")
        
        # [MODIFIED] 虛擬案例防護網
        # 萬一真的沒有案例 (retrieved_cases 為空)，創建一個虛擬案例以防崩潰
        if not retrieved_cases:
            logger.warning("⚠️ L2 收到 0 個案例，使用虛擬案例進行純理論診斷")
            virtual_case = {
                "case_id": "VIRTUAL_THEORY_CASE",
                "diagnosis": "待定(依症狀推斷)",
                "syndrome": "待定",
                "chief_complaint": "資訊不足，啟動純理論推斷模式",
                "treatment": "建議諮詢醫師",
                "score": 0.0,
                "full_text": "本案例為系統生成的虛擬案例，用於在缺乏檢索結果時維持推理流程。"
            }
            # 這裡必須使用 list 替換，不能 append，因為原變數可能是 None
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
        # [MODIFIED] 傳入 retrieved_cases 以供保底使用 (利用我們先前修改過的 _extract 方法)
        initial_diagnosis = self._extract_diagnosis_from_l2_result(
            l2_raw_result,
            retrieved_cases=retrieved_cases
        )
        
        # 步驟 4：決策是否需要工具調用
        tool_decision = self._decide_tool_calls(
            anchored_case=anchored_case,
            initial_diagnosis=initial_diagnosis,
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
        l2_result: Dict[str, Any], retrieved_cases: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        從傳統 L2 診斷結果中提取診斷資訊 (修正嵌套結構讀取)
        """
        # 優先從 tcm_inference 提取，如果沒有則嘗試從根目錄提取 (兼容舊版)
        inference = l2_result.get("tcm_inference", {})
        
        # 相容性處理：如果 LLM 沒輸出 tcm_inference 層，但直接輸出了欄位
        if not inference and "primary_pattern" in l2_result:
             inference = l2_result

        # 注意：Prompt 中的欄位名是 primary_pattern，但這裡內部變數用 primary_syndrome，需映射
        primary = (
            inference.get("primary_pattern") or 
            l2_result.get("primary_pattern") or 
            l2_result.get("primary_syndrome") or 
            "待定(資訊不足)"
        )

        refusal_keywords = [
            "無法形成", "無法判斷", "資訊不足", "not be determined", 
            "no primary pattern", "n/a", "unknown", "none"
        ]
        
        # 如果 primary 為空，或包含拒絕關鍵詞
        if not primary or any(k in primary.lower() for k in refusal_keywords):
            # 嘗試使用檢索到的第一個案例作為保底
            if retrieved_cases and len(retrieved_cases) > 0:
                top_case = retrieved_cases[0]
                # 嘗試從案例中提取診斷
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
            
            # status 也不在 inference 裡，而是在根目錄
            "confidence": 0.9 if l2_result.get("status") == "ok" else 0.6, 
            
            # reasoning 對應 syndrome_analysis
            "reasoning": inference.get("syndrome_analysis", "基於案例相似度推斷")
        }
    
    def _evaluate_case_completeness_from_l2(
            self,
            l2_result: Dict[str, Any],
            retrieved_cases: List[Dict[str, Any]] = None
        ) -> float:
            """
            從 L2 診斷結果評估案例完整度（引入檢索品質懲罰 & 修正路徑）
            
            檢查診斷結果中是否包含完整的辨證要素，並根據檢索分數進行加權。
            如果檢索分數過低，代表 LLM 的內容可能是強行生成的，需降低完整度以觸發工具。
            
            Returns:
                完整度分數 (0.0 - 1.0)
            """
            # 1. 計算基礎內容分數 (Based on Content)
            content_score = 0.0
            
            # 提取推論層資料
            inference = l2_result.get("tcm_inference", {})
            
            # 定義欄位映射 (權重名 -> JSON 欄位名)
            # 因為 Prompt 輸出的是 primary_pattern, syndrome_analysis 等
            field_mapping = {
                "primary_syndrome": "primary_pattern",
                "pathogenesis": "pathogenesis",
                "treatment_principle": "treatment_principle",
                "reasoning": "syndrome_analysis"
            }
            
            weights = {
                "primary_syndrome": 0.4,      # 主證 (權重調高)
                "pathogenesis": 0.3,          # 病因病機
                "treatment_principle": 0.2,   # 治法
                "reasoning": 0.1              # 推理依據
            }
            
            for weight_key, weight in weights.items():
                # 取得正確的 JSON 鍵名
                json_key = field_mapping.get(weight_key, weight_key)
                
                # 優先查 tcm_inference，沒有查 root (相容性)
                value = inference.get(json_key) or l2_result.get(json_key)
                
                if value:
                    # 檢查是否為有意義的內容
                    # 簡單過濾：長度 > 5 且不包含明顯的「待定」字眼
                    if isinstance(value, str) and len(value) > 5 and "待定" not in value:
                        content_score += weight
                    elif isinstance(value, (list, dict)) and len(value) > 0:
                        content_score += weight
            
            # 2. 計算檢索懲罰因子 (Retrieval Penalty)
            penalty_factor = 1.0
            if retrieved_cases and len(retrieved_cases) > 0:
                top_case = retrieved_cases[0]
                # 兼容多種分數格式 (SearchEngine 的不同版本可能回傳不同結構)
                max_score = float(
                    top_case.get("score") or 
                    top_case.get("_additional", {}).get("score") or 
                    top_case.get("_final_score") or 
                    0.0
                )
                
                # 邏輯：如果最高分案例分數低於 0.75，說明知識庫支持不足
                if max_score < 0.60:
                    penalty_factor = 0.5  # 嚴重不足 -> 必觸發工具
                elif max_score < 0.75:
                    penalty_factor = 0.7  # 中度不足 -> 極可能觸發工具

            final_score = content_score * penalty_factor
            return min(1.0, final_score)
    
    def _evaluate_case_completeness_from_l2(
        self,
        l2_result: Dict[str, Any],
        retrieved_cases: List[Dict[str, Any]] = None
    ) -> float:
        """
        從 L2 診斷結果評估案例完整度（引入檢索品質懲罰）
        
        檢查診斷結果中是否包含完整的辨證要素，並根據檢索分數進行加權。
        如果檢索分數過低，代表 LLM 的內容可能是強行生成的，需降低完整度以觸發工具。
        
        Returns:
            完整度分數 (0.0 - 1.0)
        """
        # 1. 計算基礎內容分數 (Based on Content)
        content_score = 0.0
        # 提取推論層資料
        inference = l2_result.get("tcm_inference", {})
        
        # 定義欄位映射 (權重名 -> JSON 欄位名)
        field_mapping = {
            "primary_syndrome": "primary_pattern",
            "pathogenesis": "pathogenesis",
            "treatment_principle": "treatment_principle",
            "reasoning": "syndrome_analysis"
        }
        
        weights = {
            "primary_syndrome": 0.4,      # 主證 (權重調高)
            "pathogenesis": 0.3,          # 病因病機
            "treatment_principle": 0.2,   # 治法
            "reasoning": 0.1              # 推理依據
        }
        
        for weight_key, weight in weights.items():
            json_key = field_mapping.get(weight_key, weight_key)
            # 優先查 tcm_inference，沒有查 root
            value = inference.get(json_key) or l2_result.get(json_key)
            
            if value:
                # 檢查是否為有意義的內容
                if isinstance(value, str) and len(value) > 5 and "待定" not in value:
                    content_score += weight
        
        # 2. 計算檢索懲罰因子 (Retrieval Penalty)
        penalty_factor = 1.0
        if retrieved_cases:
            # 獲取最高分案例的分數 (兼容多種格式)
            top_case = retrieved_cases[0]
            max_score = float(
                top_case.get("score") or 
                top_case.get("_additional", {}).get("score") or 
                top_case.get("_final_score") or 
                0.0
            )
            
            # 邏輯：如果最高分案例分數低於 0.75，說明知識庫支持不足
            # 強制打折以觸發 Tool B (Knowledge Gap)
            if max_score < 0.60:
                penalty_factor = 0.5  # 嚴重不足，分數減半 -> 必觸發工具
            elif max_score < 0.75:
                penalty_factor = 0.7  # 中度不足，打七折 -> 極可能觸發工具
                
        final_score = content_score * penalty_factor
        return min(1.0, final_score)
    
    def _evaluate_diagnosis_confidence_from_l2(
        self,
        l2_result: Dict[str, Any],
        l1_decision: Dict[str, Any]
    ) -> float:
        """
        從 L2 診斷結果和 L1 決策評估診斷置信度
        
        綜合考慮：
        - L2 診斷的明確性
        - L1 檢索的置信度
        - 診斷推理的完整性
        
        Returns:
            置信度分數 (0.0 - 1.0)
        """
        # 基礎置信度來自 L2 診斷本身
        base_confidence = l2_result.get("confidence", 0.7)
        
        # L1 的整體置信度影響
        l1_confidence = l1_decision.get("overall_confidence", 0.7)
        
        # 綜合評估（加權平均）
        # L2 診斷置信度占 70%，L1 檢索置信度占 30%
        combined_confidence = base_confidence * 0.7 + l1_confidence * 0.3
        
        # 如果診斷推理充分，給予獎勵
        if l2_result.get("reasoning") and len(str(l2_result["reasoning"])) > 50:
            combined_confidence += 0.05
        
        # 如果有明確的病因病機，給予獎勵
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
        
        Returns:
            Tuple[錨定案例, 初步診斷結果]
        """
        # 選擇最佳錨定案例
        if not retrieved_cases:
            return {}, {"error": "無可用案例"}
        
        # 簡化版：選擇第一個案例作為錨定
        # 實際應使用加權算法選擇
        anchored_case = retrieved_cases[0]
        
        # 生成初步診斷（這裡應調用 LLM）
        # 目前返回佔位結構
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
        
        檢查項目：
        - 症狀描述
        - 舌脈資訊
        - 病因病機
        - 辨證分析
        - 治療方案
        
        Returns:
            完整度分數 (0.0 - 1.0)
        """
        if not case:
            return 0.0
        
        # 定義必要欄位及其權重
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
                # 簡單檢查：存在且非空
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
        
        綜合考慮：
        - L1 檢索的置信度
        - 診斷的完整性
        - 證型的明確性
        
        Returns:
            置信度分數 (0.0 - 1.0)
        """
        # 基礎置信度來自診斷本身
        base_confidence = diagnosis.get("confidence", 0.7)
        
        # 如果有明確的主證，提升置信度
        if diagnosis.get("primary_syndrome") and diagnosis["primary_syndrome"] not in ["待分析", ""]:
            base_confidence += 0.05
        
        # 如果有病因病機說明，提升置信度
        if diagnosis.get("pathogenesis") and len(diagnosis["pathogenesis"]) > 20:
            base_confidence += 0.05
        
        # 綜合 L1 的置信度
        l1_confidence = l1_decision.get("overall_confidence", 0.7)
        final_confidence = (base_confidence + l1_confidence) / 2
        
        return min(1.0, final_confidence)
    
    # ==================== 工具調用決策 ====================
    
    def _decide_tool_calls(
        self,
        anchored_case: Dict[str, Any],
        initial_diagnosis: Dict[str, Any],
        case_completeness: float,
        diagnosis_confidence: float,
        l1_decision: Dict[str, Any]
    ) -> ToolCallDecision:
        """
        自主決策是否需要調用工具(深度整合決策樹)
        
        決策邏輯：
        1. 案例完整度 < 0.6 → 調用 Tool B 補充知識
        2. 診斷置信度 < 0.7 → 調用 Tool C 進行幻覺校驗
        3. 有明確證型 → 調用 Tool A 獲取權威背書
        
        Returns:
            工具調用決策
        """
        decision = ToolCallDecision()
        target_syndrome = initial_diagnosis.get("primary_syndrome", "")
        
        # 基礎檢查：如果沒有目標證型，工具也無法查詢，直接返回
        if not target_syndrome or "待定" in target_syndrome:
            return decision

        # --- 策略 A: 知識缺口 (Knowledge Gap) -> Tool B (A+百科) ---
        # 觸發條件：完整度低，或「病因病機」欄位缺失/過短
        has_pathogenesis = len(initial_diagnosis.get("pathogenesis", "")) > 20
        if case_completeness < self.tool_config["knowledge_gap_threshold"] or not has_pathogenesis:
            if self.tool_config["enable_tool_b"]:
                decision.should_call_tool_b = True
                decision.reasons.append(ToolCallReason.KNOWLEDGE_GAP)
                decision.target_terms.append(target_syndrome)
                logger.info(f"[L2Agentic] 觸發 Tool B (病機缺失/完整度不足: {case_completeness:.2f})")

        # --- 策略 B: 幻覺校驗 (Hallucination Check) -> Tool C (ETCM) ---
        # 觸發條件：置信度低，或缺乏現代科學證據支持
        # 這裡假設 LLM 輸出的 initial_diagnosis 可能包含空的 modern_evidence 欄位
        if diagnosis_confidence < self.tool_config["validation_confidence_threshold"]:
            if self.tool_config["enable_tool_c"]:
                decision.should_call_tool_c = True
                decision.reasons.append(ToolCallReason.HALLUCINATION_CHECK)
                if target_syndrome not in decision.target_terms:
                    decision.target_terms.append(target_syndrome)
                logger.info(f"[L2Agentic] 觸發 Tool C (置信度不足: {diagnosis_confidence:.2f})")

        # --- 策略 C: 權威背書 (Authority Endorsement) -> Tool A (ICD-11) ---
        # 觸發條件：只要有明確證型，就嘗試進行標準化驗證 (不再只看高置信度)
        # 這是為了達成「缺乏標準病名 -> 調用 Tool A」的邏輯
        if target_syndrome and len(target_syndrome) < 10: # 避免拿長句子去查
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
        
        Args:
            decision: 工具調用決策
            primary_syndrome: 主要證型名稱
        
        Returns:
            工具調用結果列表
        """
        tasks = []
        
        # 準備工具調用任務
        if decision.should_call_tool_a:
            tasks.append(self._call_tool_a(primary_syndrome))
        
        if decision.should_call_tool_b:
            tasks.append(self._call_tool_b(primary_syndrome))
        
        if decision.should_call_tool_c:
            tasks.append(self._call_tool_c(primary_syndrome))
        
        # 並行執行，設置總超時
        results = []
        if tasks:
            try:
                # 使用 wait_for 設置總體超時
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
            # 使用 asyncio 包裝同步調用
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
        
        整合策略：
        - Tool A 結果 → 添加到權威引用
        - Tool B 結果 → 補充病因病機、辨證要點
        - Tool C 結果 → 添加現代科學說明
        
        Returns:
            增強後的診斷結果
        """
        enhanced = initial_diagnosis.copy()
        # 初始化增強欄位
        for field in ["authority_references", "knowledge_supplements", "modern_evidence", "validation_notes"]:
            if field not in enhanced: enhanced[field] = []
        
        for result in tool_results:
            if not result.success:
                enhanced["validation_notes"].append(f"{result.tool_name} 調用失敗: {result.error}")
                continue

            # 自動學習新詞 (保留原本邏輯)
            target_term = initial_diagnosis.get("primary_syndrome", "")
            if target_term and len(target_term) > 1 and "待定" not in target_term:
                if hasattr(self, 'term_manager'):
                    self.term_manager.add_term(target_term)
            
            # --- 融合邏輯 ---
            if "Tool A" in result.tool_name:
                # ICD-11 (權威性最高)
                if "ICD-11" in result.content and "未找到" not in result.content:
                    enhanced["authority_references"].append(result.content)
                    # 標記為標準化名稱參考 (雖然不直接覆蓋 primary_syndrome 以免破壞上下文，但給予最高權重標註)
                    enhanced["validation_notes"].insert(0, "★ 證型名稱已獲 WHO ICD-11 標準驗證")
            
            elif "Tool B" in result.tool_name:
                # A+百科 (內容最豐富)
                if "臨床表現" in result.content or "辨證" in result.content:
                    enhanced["knowledge_supplements"].append(result.content)
                    enhanced["validation_notes"].append("✓ 已補充辨證邏輯")
                    
                    # [關鍵融合] 若原診斷缺乏病機，直接使用 Tool B 的內容填補
                    if not enhanced.get("pathogenesis") or len(enhanced.get("pathogenesis", "")) < 10:
                        # 這裡做簡單提取，實際可用 Regex 提取 "病機" 段落
                        enhanced["pathogenesis"] = f"(由外部知識庫補充) 參考 A+百科：{result.content[:100]}..."
            
            elif "Tool C" in result.tool_name:
                # ETCM (科學證據)
                if "ETCM" in result.content and "未找到" not in result.content:
                    enhanced["modern_evidence"].append(result.content)
                    enhanced["validation_notes"].append("✓ 已獲取現代科學證據")
        
        return enhanced
    
    # ==================== 輸出構建-使用動態模型 ====================
    
    # [修改 3] 輸出構建：使用動態模型
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
        # 計算驗證狀態
        successful_tools = sum(1 for r in tool_results if r.success)
        total_tools = len(tool_results)
        
        if total_tools == 0:
            validation_status = "unvalidated"
        elif successful_tools == total_tools:
            validation_status = "validated"
        else:
            validation_status = "partially_validated"
        
        # [修改點] 使用動態算法計算置信度增益
        confidence_boost = self._calculate_confidence_boost(enhanced_diagnosis)
        
        # 生成追問問題（如果覆蓋度不足）
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
            confidence_boost=confidence_boost, # 這裡使用動態計算的值
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
        
        # 檢查缺失的資訊類型
        if not case.get("tongue_pulse"):
            questions.append("請問您的舌象如何？舌質顏色、舌苔厚薄？")
            questions.append("您的脈象有什麼特點？是否有醫師把過脈？")
        
        if not case.get("duration"):
            questions.append("這些症狀持續多長時間了？")
        
        if not case.get("triggers"):
            questions.append("有什麼情況會加重或緩解這些症狀？")
        
        return questions[:3]  # 最多返回 3 個追問
    
    #  動態置信度增益算法
    def _calculate_confidence_boost(self, enhanced_diagnosis: Dict[str, Any]) -> float:
        """
        計算診斷置信度增益 (Confidence Gain Model)
        公式: Boost = Σ (Tool_Relevance * Authority_Weight)
        """
        boost = 0.0
        
        # 1. 權威背書 (權重最高 0.15)
        # 邏輯：如果有 ICD-11 的結果，代表方向正確
        if enhanced_diagnosis.get("authority_references"):
            boost += 0.15
            
        # 2. 知識補充 (權重 0.10)
        # 邏輯：內容越長，代表知識填補越完整 (簡單的 heuristic)
        supplements = enhanced_diagnosis.get("knowledge_supplements", [])
        if supplements:
            content_len = sum(len(s) for s in supplements)
            if content_len > 100:
                boost += 0.10
            elif content_len > 0:
                boost += 0.05
                
        # 3. 科學驗證 (權重 0.05)
        # 邏輯：這是加分項
        if enhanced_diagnosis.get("modern_evidence"):
            boost += 0.05
            
        # 上限控制：工具最多提升 0.3 (30%) 的置信度，避免過度依賴
        return min(0.3, boost)