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
        user_query: str, 
        retrieved_cases: List[Dict[str, Any]], 
        l1_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        執行 L2 Agentic 診斷流程 (修復參數傳遞與類型轉換)
        """
        # 1. [穩定性] 強制鎖定最佳錨定 (Top-1)
        target_anchors = retrieved_cases
        best_anchor = None
        if retrieved_cases and len(retrieved_cases) > 0:
            best_anchor = retrieved_cases[0]
            target_anchors = [best_anchor]
            logger.info(f"[L2Agentic] 強制鎖定單一錨定案例: {best_anchor.get('case_id')} (Score: {best_anchor.get('score')})")

        # 2. 執行初步診斷 (L2)
        # [FIX] 處理 _anchor_and_diagnose 參數數量不定的問題
        try:
            l2_raw_result = await self._anchor_and_diagnose(user_query, target_anchors)
        except TypeError:
            # 兼容舊版定義 (多一個 l1_decision)
            l2_raw_result = await self._anchor_and_diagnose(user_query, target_anchors, l1_decision)

        # [FIX] 處理 tuple 返回值 (針對 AttributeError: tuple has no attribute get)
        initial_diagnosis = l2_raw_result
        if isinstance(l2_raw_result, tuple):
            # 根據您的代碼，tuple 結構通常是 (anchored_case, diagnosis_dict)
            if len(l2_raw_result) >= 2:
                initial_diagnosis = l2_raw_result[1]
                logger.info("[L2Agentic] 成功從 tuple 解包出診斷字典")
            else:
                initial_diagnosis = l2_raw_result[0] if len(l2_raw_result) > 0 else {}

        # 3. 調用增強流程 (Enhance Diagnosis)
        # [CRITICAL FIX] 使用關鍵字參數 (keyword arguments) 確保順序正確，避免 KeyError: 0
        # 之前錯誤將 l1_decision 傳給了 retrieved_cases
        l2_agentic_output = await self.enhance_diagnosis(
            l2_raw_result=initial_diagnosis,
            l1_decision=l1_decision,
            retrieved_cases=target_anchors  # 這裡必須傳入列表！
        )
        
        # 4. [格式轉換] 將 dataclass 轉換為 Dict，以符合 FourLayerPipeline 的預期
        # 如果不轉，FourLayerPipeline 裡的 isinstance(x, dict) 會失敗
        return {
            "final_diagnosis": {
                "primary_syndrome": l2_agentic_output.syndrome_analysis,
                "reasoning": l2_agentic_output.diagnosis_reasoning,
                "pathogenesis": l2_agentic_output.anchored_case.get("pathogenesis", ""),
                "treatment_principle": l2_agentic_output.anchored_case.get("treatment", ""),
                "knowledge_supplements": l2_agentic_output.knowledge_supplements
            },
            "metrics": {
                "case_completeness": l2_agentic_output.coverage_score,
                "final_confidence": l2_agentic_output.coverage_score + l2_agentic_output.confidence_boost
            },
            "tool_outputs": {r.tool_name: r.content for r in l2_agentic_output.tool_results},
            "tool_decision": l2_agentic_output.tool_decisions,
            "initial_diagnosis": initial_diagnosis
        }

        # 步驟 6：執行工具 (如果需要)
        if tool_decision.should_call_any():
            tool_outputs = await self._execute_tools(tool_decision)
            
            # 再次增強診斷 (注入工具結果)
            final_diagnosis = await self._synthesize_final_diagnosis(
                initial_diagnosis,
                tool_outputs
            )
            final_result["tool_outputs"] = tool_outputs
            final_result["final_diagnosis"] = final_diagnosis
            
            # 更新置信度
            final_confidence = min(0.95, diagnosis_confidence + 0.15) # 簡單提升
            final_result["metrics"]["final_confidence"] = final_confidence
            
            logger.info(f"[L2Agentic] 增強完成\n  驗證狀態: validated\n  工具調用數: {len(tool_outputs)}\n  置信度提升: +0.15")
        else:
            logger.info("[L2Agentic] 無需調用工具，條件未觸發")
            final_result["metrics"]["final_confidence"] = diagnosis_confidence
            
            # 標記狀態
            final_result["tool_outputs"] = {}
            logger.info(f"[L2Agentic] 增強完成\n  驗證狀態: unvalidated\n  工具調用數: 0\n  置信度提升: +0.00")

        return final_result
    
    # [NEW] 內部知識庫查詢方法
    async def _query_internal_knowledge(self, query_text: str, vector_search_only: bool = False) -> Dict[str, Any]:
        """
        從 Weaviate TCM Class 查詢標準證型知識，具備完整術語映射與病位過濾。
        """
        if not self.se or not query_text:
            return None
            
        try:
            # --- 1. 否定詞預處理 (Negative Filter) ---
            # 僅移除明確的否定句，保留 "不舒服" 等描述
            import re
            negative_markers = ["沒有", "無", "未見", "非"] # 移除 "不"，避免誤殺
            must_not_terms = []
            
            clauses = re.split(r'[，,。.;；]', query_text)
            positive_clauses = []
            
            for clause in clauses:
                clause = clause.strip()
                if not clause: continue
                
                is_negative = False
                for m in negative_markers:
                    # 只有當否定詞位於句首附近時才視為否定 (e.g. "無口苦")
                    if m in clause and clause.index(m) < 2:
                        is_negative = True
                        term = clause.split(m)[-1].strip()
                        if len(term) > 1: must_not_terms.append(term)
                        break
                
                if not is_negative:
                    positive_clauses.append(clause)
            
            clean_query = " ".join(positive_clauses) if positive_clauses else query_text

            # --- 2. 全方位術語映射 (Comprehensive Term Mapping) ---
            # 將口語轉譯為 TCM 標準庫 (scbr_syndromes_cleaned_verified.json) 中的詞彙
            term_mapping = {
                # [核心部位]
                "胃": "胃脘 脾胃 中焦", "肚子": "腹部 大腹 小腹 脘腹",
                "胸": "胸膈 心胸", "脅": "脅肋", "腰": "腰府 腎府", "頭": "巔頂",
                "背": "背俞", "肋": "脅肋", "喉": "咽喉", "眼": "目",
                
                # [消化系統]
                "拉肚子": "泄瀉 下利 便溏", "大便稀": "便溏 完穀不化", "便秘": "大便秘結 大便乾結",
                "想吐": "嘔吐 噁心 嘔逆 乾嘔", "吃不下": "納呆 食少 納差 厭食",
                "脹": "痞滿 脹滿", "打嗝": "噯氣 呃逆", "口苦": "膽火", "口乾": "口燥 咽乾 津傷",
                "痛": "疼痛", "刺痛": "瘀血", "脹痛": "氣滯", "冷痛": "寒凝", "灼痛": "火熱",
                
                # [全身與精神]
                "睡不著": "不寐 失眠 入睡困難", "多夢": "夢擾",
                "很累": "神疲 乏力 倦怠 少氣懶言", "沒力氣": "肢倦 無力",
                "煩": "心煩 煩躁 五心煩熱", "怕冷": "畏寒 惡風 肢冷", "怕熱": "惡熱 壯熱",
                "出汗": "自汗 盜汗", "頭暈": "眩暈", "手腳冰冷": "手足厥冷",
                
                # [五官與其他]
                "心跳": "心悸 怔忡", "喘": "氣喘 短氣", "咳": "咳嗽 咯痰",
                "痰": "痰濁 痰飲", "月經": "經行 經期", "白帶": "帶下"
            }
            
            expansion_terms = []
            for colloquial, formal in term_mapping.items():
                if colloquial in clean_query:
                    expansion_terms.append(formal)
            
            if expansion_terms:
                expanded_query = f"{clean_query} {' '.join(expansion_terms)}"
                logger.info(f"[L2Agentic] 術語擴展: '{clean_query}' -> '{expanded_query}'")
                search_text = expanded_query
            else:
                search_text = clean_query

            # --- 3. 生成向量與檢索 ---
            vector = None
            if self.embed:
                try:
                    vector = await self.embed.embed(search_text)
                except Exception as e:
                    logger.warning(f"向量生成失敗: {e}")

            # 設定 Alpha=0.2 (關鍵字優先)，Limit=10 (擴大召回)
            results = await self.se.hybrid_search(
                index="TCM",
                text=search_text,
                vector=vector,
                alpha=0.2, 
                limit=10, 
                search_fields=["name_zh", "definition", "clinical_manifestations", "vector_text"] 
            )
            
            # --- 4. 中醫病位過濾 (Full Scope Guard) ---
            # 確保搜尋結果包含主訴的核心部位
            key_locations = [
                "胃", "心", "肝", "脾", "肺", "腎", "膽", "腸", "膀胱", "三焦", 
                "頭", "面", "目", "眼", "耳", "鼻", "口", "齒", "咽", "喉", 
                "腹", "肚", "臍", "胸", "脅", "背", "腰", "肩", "頸", 
                "手", "足", "四肢", "肢", "腿", "膝", "骨", "節", "筋", "脈",
                "胞宮", "子宮", "少腹", "陰器", "二便", "皮", "膚", "肌"
            ]
            query_locations = [k for k in key_locations if k in query_text]
            
            valid_result = None
            
            if results:
                top3_names = [r.get('name_zh') for r in results[:3]]
                logger.info(f"[L2Agentic] 內部檢索候選: {top3_names}")

                for res in results:
                    score = res.get("score", 0)
                    name = res.get("name_zh", "")
                    content_str = str(res.get("definition", "")) + str(res.get("clinical_manifestations", ""))
                    
                    if score < 0.40: continue

                    # A. 排除否定詞衝突
                    if any(term in content_str for term in must_not_terms):
                         continue

                    # B. 病位檢查 (Scope Guard)
                    if query_locations:
                        is_relevant = False
                        for loc in query_locations:
                            if loc in name or loc in content_str:
                                is_relevant = True
                                break
                            # 智能映射：腹包含胃腸脾
                            if loc in ["腹", "肚"] and any(x in content_str for x in ["胃", "腸", "胞宮", "脾"]):
                                is_relevant = True
                                break
                            
                        if not is_relevant:
                            # logger.info(f"過濾: {name}") # 減少日誌雜訊
                            continue

                    valid_result = res
                    break
            
            if valid_result:
                logger.info(f"[L2Agentic] 內部知識庫命中: {valid_result.get('name_zh')} (Score: {valid_result.get('score', 0):.3f})")
                return valid_result
            
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
        
        # [中醫思維 0] 強制鎖定最佳錨定 (Force Top-1 Anchor)
        # 解決 LLM 在分數接近時隨機選擇導致的不穩定問題
        # 我們直接覆蓋 prompt 中的 implicitly chosen anchor，強制使用 Search Engine 的 No.1
        best_anchor = None
        if retrieved_cases and len(retrieved_cases) > 0:
            best_anchor = retrieved_cases[0] # 取分數最高的
            logger.info(f"[L2Agentic] 強制鎖定最佳錨定案例: {best_anchor.get('case_id')} (Score: {best_anchor.get('score')})")

        # 步驟 3：從 l2_raw_result 提取診斷資訊
        # 這裡我們傳入強制鎖定的錨定，確保後續處理一致
        initial_diagnosis = self._extract_diagnosis_from_l2_result(
            l2_raw_result,
            retrieved_cases=[best_anchor] if best_anchor else retrieved_cases
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
            
            # [中醫思維 3] 衝突檢測 (Conflict Detection)
            # 比較「錨定案例診斷」與「內部知識庫檢索結果」
            l2_primary = initial_diagnosis.get("primary_syndrome", "未定")
            conflict_detected = False
            
            # 比對邏輯：如果標準庫結果不在 L2 初步診斷中，且標準庫結果分數夠高 (>0.75)
            # 則視為重大衝突，需要強制引導
            internal_score = internal_knowledge.get("score", 0)
            
            if tcm_name not in l2_primary and l2_primary not in tcm_name:
                conflict_detected = True
                logger.warning(f"[L2Agentic] ⚠️ 發現診斷衝突: 錨定推斷='{l2_primary}' vs 標準庫='{tcm_name}' (Score: {internal_score:.2f})")

            # 注入補充資訊，使用更強烈的語氣
            supplement_text = (
                f"【內部標準知識庫對照】\n"
                f"系統依據症狀檢索出的最佳匹配證型為：{tcm_name} (匹配度: {internal_score:.2f})\n"
                f"定義：{def_text}\n"
                f"典型表現：{manifest_str}\n"
            )
            
            if conflict_detected:
                # [FIX] 如果內部知識分數很高，強制要求 LLM 考慮修正方向
                if internal_score > 0.8:
                    priority_instruction = "請優先考慮標準庫的建議，因為其症狀匹配度極高。"
                else:
                    priority_instruction = "請仔細鑑別兩者差異。"

                supplement_text += (
                    f"\n🚨 **系統發現關鍵疑點**：\n"
                    f"錨定案例指向「{l2_primary}」，但症狀特徵與標準庫的「{tcm_name}」更為吻合。\n"
                    f"{priority_instruction}\n"
                    f"請在【辨證分析】中明確執行鑑別：為何放棄 A 而選擇 B (或兼證)？"
                )
                
                # 寫入 reasoning 欄位，強迫 LLM 在思考過程中看到
                current_reasoning = initial_diagnosis.get("reasoning", "")
                initial_diagnosis["reasoning"] = f"【系統警示】{l2_primary} 與 {tcm_name} 存在衝突，需進行鑑別。{current_reasoning}"
                
                initial_diagnosis["conflict_needs_resolution"] = True
            
            if "knowledge_supplements" not in initial_diagnosis:
                initial_diagnosis["knowledge_supplements"] = []
            initial_diagnosis["knowledge_supplements"].append(supplement_text)
            
            initial_diagnosis["internal_validated"] = True
            
            # 若 L2 診斷名稱不明確，直接採用內部結果
            if not l2_primary or "待定" in l2_primary:
                initial_diagnosis["primary_syndrome"] = f"{tcm_name} (基於症狀檢索推斷)"
                logger.info(f"[L2Agentic] 填補空白診斷: {tcm_name}")
            

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
        retrieved_cases: List[Dict[str, Any]],
        l1_decision: Dict[str, Any] = None  # 確保參數簽名兼容
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        執行案例錨定與初步診斷 (修復欄位讀取)
        """
        if not retrieved_cases:
            return {}, {"primary_syndrome": "待分析", "reasoning": "無可用案例"}
        
        anchored_case = retrieved_cases[0]
        
        # [FIX] 鍵名兼容性處理 (Key Compatibility)
        # 資料庫中的 key 可能是 diagnosis, syndrome, 或 primary_pattern
        syndrome_name = (
            anchored_case.get("diagnosis") or 
            anchored_case.get("syndrome") or 
            anchored_case.get("primary_pattern") or 
            "待分析"
        )
        
        # 簡單的推理文字生成
        reasoning = f"基於錨定案例 {anchored_case.get('case_id', 'Unknown')} ({syndrome_name}) 進行推斷。"
        
        initial_diagnosis = {
            "primary_syndrome": syndrome_name,
            "secondary_syndromes": [],
            "pathogenesis": anchored_case.get("pathogenesis", "") or anchored_case.get("mechanism", ""),
            "treatment_principle": anchored_case.get("treatment", "") or anchored_case.get("treatment_principle", ""),
            "confidence": 0.7,
            "reasoning": reasoning
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