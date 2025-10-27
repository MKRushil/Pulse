# -*- coding: utf-8 -*-
"""
螺旋推理引擎 - 優化版
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
import json
import asyncio
from datetime import datetime

from ..config import SCBRConfig
from .search_engine import SearchEngine
from ..llm.embedding import EmbedClient
from ..llm.client import LLMClient
from ..utils.text_processor import TextProcessor
from .syndrome_analyzer import SyndromeAnalyzer, SyndromeDiagnosis
from ..utils.logger import get_logger
from .convergence import ConvergenceMetrics
from .pattern_diagnosis import PatternDiagnosisReasoner
from .context_fuser import ContextFuser

logger = get_logger("SpiralEngine")

class SpiralEngine:
    """螺旋推理引擎"""
    
    def __init__(
        self,
        config: SCBRConfig,
        search_engine: Optional[SearchEngine] = None,
        embed_client: Optional[EmbedClient] = None,
        dialog_manager = None  # ✅ 添加這個參數
    ):
        self.cfg = config
        self.SE = search_engine or SearchEngine(self.cfg)
        self.embedder = embed_client or EmbedClient(self.cfg)
        
        # ✅ 保存 dialog_manager 引用
        self.dialog = dialog_manager
        
        # 正確初始化 LLM 客戶端
        if config.features.enable_llm:
            try:
                self.llm = LLMClient(self.cfg)
                logger.info("✅ LLM 客戶端初始化成功")
            except Exception as e:
                logger.error(f"❌ LLM 客戶端初始化失敗: {e}")
                self.llm = None
        else:
            self.llm = None
            logger.info("LLM 功能已禁用")
        
        self.text_processor = TextProcessor(self.cfg.text_processor)
        
        # 配置參數
        self.alpha = config.search.hybrid_alpha
        self.top_k = config.search.top_k
        self.session_context = {}  # 儲存會話上下文
        
        # ✅ 修正：使用正確的類名導入和初始化
        from .dynamic_retrieval import DynamicRetrievalOptimizer, RetrievalConfig
        from .discriminative_weights import DiscriminativeWeightSystem, DiscriminativeConfig
        from .temporal_smoother import TemporalSmoother, TemporalConfig
        from .query_expander import QueryExpander, ExpansionConfig
        from .output_formatter import OutputFormatter
        
        self.retrieval_optimizer = DynamicRetrievalOptimizer(RetrievalConfig())
        self.discriminative_system = DiscriminativeWeightSystem(DiscriminativeConfig())
        self.temporal_smoother = TemporalSmoother(TemporalConfig())
        self.query_expander = QueryExpander(ExpansionConfig())
        self.output_formatter = OutputFormatter()
        self.convergence = ConvergenceMetrics(self.cfg)
        self.pattern_diagnosis_reasoner = PatternDiagnosisReasoner(self.cfg)
        self.context_fuser = ContextFuser(self.cfg)

        self.session_contexts = {}
        
        # ✅ 內部症狀追蹤器（如果沒有 dialog_manager）
        self._symptom_tracker = {}  # session_id -> symptoms
        
        logger.info("螺旋推理引擎初始化完成")
        self.case_fields = ["jieba_tokens", "syndrome_terms", "symptom_terms"]
        self.case_props = [
            "case_id", "patient_id", "chief_complaint", "diagnosis",
            "treatment_principle", "suggestion", "full_text", 
            "syndrome_terms", "zangfu_terms", "symptom_terms", 
            "pulse_terms", "raw_data"
        ]
        
    def _extract_and_track_symptoms(
        self,
        question: str,
        session_id: str,
        round_num: int
    ) -> Dict[str, Any]:
        """提取並追蹤症狀（自適應版本）"""
        
        # 1. 提取症狀
        extracted = self.text_processor.extract_symptoms(question)
        
        # 2. 驗證症狀
        valid_symptoms = self._validate_symptoms(extracted)
        extracted = list(set(valid_symptoms))
        
        # 3. ✅ 自適應獲取歷史症狀
        history_symptoms = set()
        
        # 優先使用 dialog (如果有)
        if hasattr(self, 'dialog') and self.dialog:
            try:
                session = self.dialog.get_session(session_id)
                if session:
                    for step in session.history:
                        if "symptoms" in step:
                            history_symptoms.update(step["symptoms"])
            except Exception as e:
                logger.warning(f"無法從 dialog 獲取歷史: {e}")
        
        # Fallback: 使用內部追蹤器
        if not history_symptoms:
            if not hasattr(self, '_symptom_tracker'):
                self._symptom_tracker = {}
            
            if session_id in self._symptom_tracker:
                history_symptoms = self._symptom_tracker[session_id].get("accumulated", set())
        
        # 4. 計算新增症狀
        new_symptoms = [s for s in extracted if s not in history_symptoms]
        accumulated = list(history_symptoms | set(extracted))
        
        # 5. 更新內部追蹤器
        if not hasattr(self, '_symptom_tracker'):
            self._symptom_tracker = {}
        
        if session_id not in self._symptom_tracker:
            self._symptom_tracker[session_id] = {"accumulated": set(), "history": []}
        
        self._symptom_tracker[session_id]["accumulated"].update(extracted)
        self._symptom_tracker[session_id]["history"].append({
            "round": round_num,
            "symptoms": extracted,
            "new": new_symptoms
        })
        
        # 6. 選擇核心症狀
        core_symptoms = self._select_core_symptoms(
            new_symptoms, accumulated, self._symptom_tracker[session_id]["history"]
        )
        
        # 7. ✅ 添加權重信息
        weighted_terms = {}
        for symptom in core_symptoms[:5]:
            weighted_terms[symptom] = 3.0  # 核心症狀權重最高
        for symptom in new_symptoms:
            if symptom not in weighted_terms:
                weighted_terms[symptom] = 2.0  # 新增症狀次之
        for symptom in accumulated:
            if symptom not in weighted_terms:
                weighted_terms[symptom] = 1.0  # 其他症狀基礎權重
        
        result = {
            "new_symptoms": new_symptoms,
            "accumulated_symptoms": accumulated,
            "core_symptoms": core_symptoms,
            "symptom_count": len(accumulated),
            "weighted_terms": weighted_terms  # ✅ 添加這個
        }
        
        logger.info(f"📋 症狀追蹤 [輪{round_num}]:")
        logger.info(f"   新增: {new_symptoms}")
        logger.info(f"   累積: {accumulated}")
        logger.info(f"   核心: {core_symptoms[:5]}")
        
        return result

    def _validate_symptoms(self, symptoms: List[str]) -> List[str]:
        """驗證症狀有效性"""
        valid_symptoms = []
        tcm_keywords = set(self.cfg.text_processor.tcm_keywords)
        invalid_words = {"走路", "條件", "證件", "類型", "判斷", "線索"}
        
        for symptom in symptoms:
            if symptom in tcm_keywords:
                valid_symptoms.append(symptom)
            elif (2 <= len(symptom) <= 4 and 
                all('\u4e00' <= c <= '\u9fff' for c in symptom) and
                symptom not in invalid_words):
                valid_symptoms.append(symptom)
        
        return valid_symptoms

    def _select_core_symptoms(
        self,
        new_symptoms: List[str],
        accumulated: List[str],
        history: List[Dict]
    ) -> List[str]:
        """選擇核心症狀"""
        core_symptoms = []
        
        # 優先級 1：新增症狀
        core_symptoms.extend(new_symptoms[:3])
        
        # 優先級 2：高頻症狀
        if len(history) > 1:
            symptom_freq = {}
            for record in history:
                for symptom in record.get("symptoms", []):
                    symptom_freq[symptom] = symptom_freq.get(symptom, 0) + 1
            
            sorted_symptoms = sorted(
                symptom_freq.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for symptom, _ in sorted_symptoms:
                if symptom not in core_symptoms and len(core_symptoms) < 5:
                    core_symptoms.append(symptom)
        
        # 補充其他症狀
        for symptom in accumulated:
            if symptom not in core_symptoms and len(core_symptoms) < 8:
                core_symptoms.append(symptom)
        
        return core_symptoms

    def _build_weighted_search_query(
        self,
        question: str,
        symptom_info: Dict[str, Any],
        round_num: int
    ) -> Dict[str, Any]:
        """
        構建帶權重的檢索查詢
        
        策略：
        1. 核心症狀重複3次（提高BM25權重）
        2. 新增症狀重複2次
        3. 其他症狀出現1次
        """
        core_symptoms = symptom_info["core_symptoms"]
        new_symptoms = symptom_info["new_symptoms"]
        all_symptoms = symptom_info["accumulated_symptoms"]
        
        # 構建加權文本
        weighted_parts = []
        
        # 核心症狀（最高權重）
        for symptom in core_symptoms:
            weighted_parts.extend([symptom] * 3)
        
        # 新增症狀（中等權重）
        for symptom in new_symptoms:
            if symptom not in core_symptoms:
                weighted_parts.extend([symptom] * 2)
        
        # 其他累積症狀（基礎權重）
        for symptom in all_symptoms:
            if symptom not in core_symptoms and symptom not in new_symptoms:
                weighted_parts.append(symptom)
        
        # 組合文本
        weighted_text = " ".join(weighted_parts)
        
        # 分詞處理
        processed_text = self.text_processor.segment_text(weighted_text)
        
        # ✅ 修正：添加缺失的字段
        return {
            "text": processed_text,
            "raw_text": weighted_text,
            "weighted_terms": symptom_info["weighted_terms"],
            "core_symptoms": core_symptoms,
            "new_symptoms": new_symptoms,  # ✅ 新增
            "accumulated_symptoms": all_symptoms,  # ✅ 新增
            "symptom_count": len(all_symptoms)
        }

    def _select_search_fields(self, search_query: Dict[str, Any]) -> List[str]:
        """根據症狀類型動態選擇搜索欄位"""
        core_symptoms = search_query.get("core_symptoms", [])
        
        # 基礎欄位
        fields = ["jieba_tokens", "symptom_terms"]
        
        # 如果有證型關鍵詞，加入 syndrome_terms
        syndrome_keywords = {"虛", "實", "寒", "熱", "氣", "血", "陰", "陽"}
        if any(any(kw in symptom for kw in syndrome_keywords) for symptom in core_symptoms):
            fields.insert(0, "syndrome_terms")  # 優先搜索
        
        # 如果有臟腑關鍵詞，加入 zangfu_terms
        zangfu_keywords = {"心", "肝", "脾", "肺", "腎"}
        if any(any(kw in symptom for kw in zangfu_keywords) for symptom in core_symptoms):
            fields.append("zangfu_terms")
        
        logger.info(f"🎯 動態搜索欄位: {fields}")
        return fields

    async def execute_spiral_cycle(
        self,
        question: str,
        session_id: str,
        round_num: int = 1
    ) -> Dict[str, Any]:
        """執行單輪螺旋推理 """
        logger.info(f"🌀 執行第 {round_num} 輪螺旋推理")
        
        # === 1. 症狀追蹤與分析（✅ 嚴格驗證）===
        symptom_info = self._extract_and_track_symptoms(question, session_id, round_num)
        search_query = self._build_weighted_search_query(
            question, symptom_info, round_num
        )

        # === 1.5 ✅ 新增:Context Fusion ===
        prev_ctx = self.session_contexts.get(session_id, {})
        new_ctx = {
            "question": question,
            "symptoms": symptom_info["accumulated_symptoms"],
            "round": round_num
        }
        
        patient_ctx_fused = self.context_fuser.update(
            prev_ctx=prev_ctx,
            new_ctx=new_ctx,
            round_num=round_num
        )
        
        # 保存融合後的上下文
        self.session_contexts[session_id] = patient_ctx_fused
        
        # === 2. (✅ 修正) 獲取融合查詢文本但不覆蓋 search_query ===
        fused_query_text = self.context_fuser.get_retrieval_query(patient_ctx_fused)  # ✅ 使用新變數名
        
        logger.info(f"🔍 檢索查詢: {fused_query_text[:100] if isinstance(fused_query_text, str) else search_query['text'][:100]}...")
        
        # === 3. 生成向量 ===
        qvec = await self._generate_embedding(question)
        
        # === 4. (✅ 修正) 優化檢索 - 使用原始的 search_query 字典 ===
        optimized_results = await self.retrieval_optimizer.optimized_retrieval(
            search_engine=self.SE,
            query=search_query["text"],  # ✅ 正確:使用字典的 text 欄位
            vector=qvec,
            round_num=round_num,
            symptom_count=search_query["symptom_count"],  # ✅ 正確:使用字典的 symptom_count 欄位
            coverage=0.0
        )
        
        case_hits = optimized_results["case"]
        pulse_hits = optimized_results["pulse"]
        rpcase_hits = optimized_results["rpcase"]
        
        logger.info(f"📊 優化檢索結果 - Case: {len(case_hits)}, Pulse: {len(pulse_hits)}, RPCase: {len(rpcase_hits)}")
        
        # === 4. 高鑑別權重（✅ 擴充關鍵詞）===
        symptoms_list = symptom_info["accumulated_symptoms"]
        base_symptom_scores = {s: 1.0 for s in symptoms_list}
        
        adjusted_symptom_scores, adjusted_syndrome_scores = self.discriminative_system.apply_discriminative_weights(
            symptoms=symptoms_list,
            base_scores=base_symptom_scores
        )
        
        # === 5. 選擇最佳案例 ===
        primary, supplement = self._select_best_cases(
            case_hits, pulse_hits, rpcase_hits
        )
        
        # === 6. 構建融合句 ===
        fused_sentence = self._build_fused_sentence(primary, supplement)

        # === 7. ✅ 新增：雙層推理 ===
        patient_ctx_fused = {
            "symptoms": symptom_info["accumulated_symptoms"],
            "new_symptoms": symptom_info["new_symptoms"],
            "round": round_num,
            "question": question
        }
    
        pattern_diagnosis_result = self.pattern_diagnosis_reasoner.infer(
            patient_ctx_fused=patient_ctx_fused,
            evidence_cases=case_hits[:5],  # 使用前5個案例
            round_num=round_num
        )
            
        # === 8. LLM 生成診斷（✅ 優化 Prompt）===
        llm_diagnosis = await self._generate_diagnosis(
            question, primary, supplement, fused_sentence, round_num
        )
        
        # === 9. 計算收斂度 ===
        convergence_metrics = self.convergence.calculate_convergence(
            session_id=session_id,
            current_result={
                "primary": primary,
                "supplement": supplement,
                "round": round_num,
                "symptoms": symptoms_list,
                "pattern_diagnosis": pattern_diagnosis_result
            }
        )

        # === 10. ✅ 生成 ROC ===
        roc = self.build_roc(
            session_id=session_id,
            round_num=round_num,
            patient_ctx_fused=patient_ctx_fused,
            pattern_diagnosis=pattern_diagnosis_result,
            evidence_cases=case_hits[:3],
            metrics=convergence_metrics,
            next_questions=self._generate_next_questions(symptom_info, convergence_metrics)
        )
        # === 11. 使用輸出格式化器 ===
        formatted_output = self.output_formatter.format_from_roc(roc)
        
        # === 9. ✅ 使用固定輸出模板 ===
        formatted_output = self.output_formatter.format_professional_diagnosis_report(
            session_id=session_id,
            round_num=round_num,
            question=question,
            accumulated_symptoms=symptom_info["accumulated_symptoms"],
            new_symptoms=symptom_info["new_symptoms"],
            syndrome_result={
                "primary_syndrome": primary.get("diagnosis", "證型待定") if primary else "證型待定",
                "confidence": primary.get("_final", 0) if primary else 0,
                "secondary_syndromes": [],
                "key_clues": {
                    "core_symptoms": symptom_info["core_symptoms"],
                    "tongue_pulse": self._extract_tongue_pulse(question)
                },
                "pathogenesis": {}
            },
            pathogenesis={},
            suggestions=self._generate_suggestions(primary, symptom_info),
            convergence_metrics=convergence_metrics,
            next_questions=self._generate_next_questions(symptom_info, convergence_metrics)
                if convergence_metrics.get("overall_convergence", 0) < 0.85 else [],
            case_reference=primary
        )
        
        # === 10. 構建返回結果 ===
        result = {
            "ok": True,
            "roc": roc,
            "pattern_diagnosis": pattern_diagnosis_result,
            "question": question,
            "round": round_num,
            "primary": primary,
            "supplement": supplement,
            "fused_sentence": fused_sentence,
            "final_text": formatted_output,
            "text": formatted_output,
            "answer": formatted_output,
            "convergence_metrics": convergence_metrics,
            "search_results": {
                "case_count": len(case_hits),
                "pulse_count": len(pulse_hits),
                "rpcase_count": len(rpcase_hits)
            }
        }
        
        return result
    
    def build_roc(
        self,
        session_id: str,
        round_num: int,
        patient_ctx_fused: Dict,
        pattern_diagnosis: Dict,
        evidence_cases: List[Dict],
        metrics: Dict[str, float],
        next_questions: List[str]
    ) -> Dict:
        """
        生成 Round Output Contract (ROC)
        每輪推理結束時的標準化輸出
        """
        trace_id = f"ROC_{session_id}_{round_num}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 格式化證據案例
        formatted_cases = []
        for idx, case in enumerate(evidence_cases[:3], 1):
            formatted_case = {
                "rank": idx,
                "case_id": case.get("case_id", f"CASE_{idx}"),
                "similarity": round(case.get("_final", 0.0), 3),
                "diagnosis": case.get("diagnosis", ""),
                "chief_complaint": case.get("chief_complaint", ""),
                "snippets": self._extract_case_snippets(case),
                "match_fields": case.get("_match_fields", []),
                "pattern_tags": case.get("syndrome_terms", [])[:3],
                "diagnosis_tags": [case.get("diagnosis", "")]
            }
            formatted_cases.append(formatted_case)
        
        # 構建 ROC
        roc = {
            "schema_version": "roc_v1.0",
            "meta": {
                "session_id": session_id,
                "round": round_num,
                "timestamp": datetime.now().isoformat(),
                "trace_id": trace_id
            },
            "patient_ctx": patient_ctx_fused,
            "pattern_reasoning": pattern_diagnosis.get("pattern_reasoning"),
            "diagnosis_reasoning": pattern_diagnosis.get("diagnosis_reasoning"),
            "evidence": {
                "retrieval_query": patient_ctx_fused.get("question", ""),
                "retrieval_params": {
                    "alpha": getattr(self, 'last_alpha', 0.5),
                    "k": self.top_k,
                    "mmr_lambda": 0.7,
                    "search_fields": self.case_fields
                },
                "cases": formatted_cases
            },
            "scores": {
                "RCI": metrics.get("RCI", 0.0),
                "CMS": metrics.get("CMS", 0.0),
                "CSC": metrics.get("CSC", 0.0),
                "CAS": metrics.get("CAS", 0.0),
                "Final": metrics.get("Final", 0.0)
            },
            "next_turn": {
                "questions": next_questions[:3],
                "expected_signals": self._get_expected_signals(patient_ctx_fused)
            },
            "audit": {
                "reasoning_trace_id": trace_id,
                "ablation_notes": self._get_ablation_notes(round_num)
            }
        }
        
        logger.info(f"📋 ROC 生成完成: {trace_id}")
        return roc

    def _extract_case_snippets(self, case: Dict) -> List[str]:
        """提取案例片段（7-60字）"""
        snippets = []
        
        # 從主訴提取
        if "chief_complaint" in case:
            cc = case["chief_complaint"]
            if cc and len(cc) >= 7:
                snippets.append(cc[:60])
        
        # 從症狀提取
        if "symptom_terms" in case:
            symptoms = case["symptom_terms"]
            if symptoms:
                symptom_text = "、".join(symptoms[:5])
                if len(symptom_text) >= 7:
                    snippets.append(symptom_text[:60])
        
        # 從診斷提取
        if "diagnosis" in case:
            diag = case["diagnosis"]
            if diag and len(diag) >= 7:
                snippets.append(diag[:60])
        
        return snippets[:3]  # 最多3個片段

    def _get_expected_signals(self, ctx: Dict) -> List[str]:
        """獲取期望的下一輪信號"""
        symptoms = ctx.get("symptoms", [])
        signals = []
        
        # 檢查是否缺少舌脈
        if not any("舌" in s for s in symptoms):
            signals.append("tongue")
        if not any("脈" in s for s in symptoms):
            signals.append("pulse")
        
        # 其他重要信號
        if "失眠" in symptoms:
            signals.append("sleep_quality")
        if "咳嗽" in symptoms:
            signals.append("sputum_character")
        
        return signals[:3]

    def _get_ablation_notes(self, round_num: int) -> Dict:
        """獲取消融筆記（用於調試）"""
        return {
            "round": round_num,
            "pattern_reasoning_enabled": True,
            "llm_enabled": self.llm is not None,
            "mmr_enabled": True,
            "dynamic_alpha": True,
            "timestamp": datetime.now().isoformat()
        }


    def _extract_tongue_pulse(self, question: str) -> List[str]:
        """提取舌脈信息"""
        tongue_pulse = []
        
        # 舌象關鍵詞
        tongue_keywords = ["舌紅", "舌淡", "舌暗", "舌紫", "苔白", "苔黃", "苔膩"]
        for kw in tongue_keywords:
            if kw in question:
                tongue_pulse.append(kw)
        
        # 脈象關鍵詞
        pulse_keywords = ["脈浮", "脈沉", "脈數", "脈遲", "脈弦", "脈細", "脈滑"]
        for kw in pulse_keywords:
            if kw in question:
                tongue_pulse.append(kw)
        
        return tongue_pulse
    
    def _generate_suggestions(
        self,
        primary: Optional[Dict],
        symptom_info: Dict[str, Any]
    ) -> List[str]:
        """生成調理建議"""
        suggestions = []
        
        if primary:
            diagnosis = primary.get("diagnosis", "")
            
            # 基礎建議
            suggestions.append("1. 作息調理：保持規律作息，晚上10點前入睡")
            
            # 根據診斷調整
            if "陰虛" in diagnosis:
                suggestions.append("2. 飲食調養：可多食用滋陰食物如百合、蓮子、銀耳")
            elif "氣虛" in diagnosis or "血虛" in diagnosis:
                suggestions.append("2. 飲食調養：適當補充營養，可食用紅棗、龍眼等")
            else:
                suggestions.append("2. 飲食調養：清淡飲食，避免辛辣刺激")
            
            suggestions.append("3. 情志調節：保持心情舒暢，避免過度緊張焦慮")
        
        return suggestions
    
    def _generate_next_questions(
        self,
        symptom_info: Dict[str, Any],
        convergence_metrics: Dict[str, float]
    ) -> List[str]:
        """生成下一步追問"""
        questions = []
        
        # 如果沒有舌脈信息
        accumulated = symptom_info.get("accumulated_symptoms", [])
        has_tongue = any("舌" in s for s in accumulated)
        has_pulse = any("脈" in s for s in accumulated)
        
        if not has_tongue:
            questions.append("您的舌象如何？（如：舌紅、舌淡、苔黃等）")
        
        if not has_pulse:
            questions.append("您的脈象如何？（如：脈數、脈細、脈弦等）")
        
        # 根據核心症狀追問
        core_symptoms = symptom_info.get("core_symptoms", [])
        if "失眠" in core_symptoms:
            questions.append("失眠是入睡困難還是容易醒？")
        if "疲倦" in core_symptoms or "乏力" in core_symptoms:
            questions.append("疲倦是全天都有還是特定時間？")
        
        return questions[:3]  # 最多3個問題
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """生成向量"""
        try:
            vec = await self.embedder.embed(text)
            logger.info(f"🧭 生成向量: dim={len(vec)}")
            return vec
        except Exception as e:
            logger.warning(f"生成向量失敗，降級為 BM25: {e}")
            return None
    
    def _select_best_cases(
        self,
        case_hits: List[Dict],
        pulse_hits: List[Dict],
        rpcase_hits: List[Dict]
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        選擇最佳主案例和輔助案例
        """
        # 獲取 Top-1
        case_top = self._fuse_case(case_hits[0]) if case_hits else None
        rpcase_top = self._fuse_rpcase(rpcase_hits[0]) if rpcase_hits else None
        pulse_top = self._fuse_pulse(pulse_hits[0]) if pulse_hits else None
        
        # 選擇主案例：比較 TCMCase 和 RPCase
        if case_top and rpcase_top:
            case_score = case_top.get("_final", 0)
            rpcase_score = rpcase_top.get("_final", 0)
            
            # 加權比較
            case_weighted = case_score * self.cfg.spiral.case_weight
            rpcase_weighted = rpcase_score * self.cfg.spiral.rpcase_weight
            
            primary = case_top if case_weighted >= rpcase_weighted else rpcase_top
            logger.info(f"主案例選擇: {primary.get('source')} (分數: {primary.get('_final', 0):.3f})")
        else:
            primary = case_top or rpcase_top
        
        # 輔助案例總是 PulsePJ
        supplement = pulse_top
        
        return primary, supplement
    
    def _fuse_case(self, hit: Optional[Dict]) -> Optional[Dict]:
        """融合 TCMCase 結果"""
        if not hit:
            return None
        
        # ===== 提取基本資訊 =====
        case_id = hit.get("case_id", "")
        patient_id = hit.get("patient_id", "")
        chief_complaint = hit.get("chief_complaint", "")
        diagnosis = hit.get("diagnosis", "")
        treatment = hit.get("treatment_principle", "")
        suggestion = hit.get("suggestion", "")
        full_text = hit.get("full_text", "")
        
        # ===== 解析 raw_data（如果需要更多資訊）=====
        raw_data = {}
        if hit.get("raw_data"):
            try:
                import json
                raw_data = json.loads(hit["raw_data"])
            except Exception:
                pass
        
        # ===== 提取術語（優先使用術語欄位）=====
        syndrome_terms = hit.get("syndrome_terms", []) or []
        symptom_terms = hit.get("symptom_terms", []) or []
        pulse_terms = hit.get("pulse_terms", []) or []
        zangfu_terms = hit.get("zangfu_terms", []) or []
        
        # ===== 智能症狀分類 =====
        # 主要症狀：來自 symptom_terms（實際症狀）
        primary_symptoms = []
        if symptom_terms:
            primary_symptoms = symptom_terms[:10]  # 最多 10 個
        
        # 證型判斷：來自 syndrome_terms
        syndrome_list = syndrome_terms[:5] if syndrome_terms else []
        
        # 臟腑定位：來自 zangfu_terms
        zangfu_list = zangfu_terms[:3] if zangfu_terms else []
        
        # Fallback：如果術語欄位為空，從 full_text 或 chief_complaint 提取
        if not primary_symptoms:
            if chief_complaint:
                primary_symptoms = self._extract_key_symptoms(chief_complaint)
            elif full_text:
                primary_symptoms = self._extract_key_symptoms(full_text[:200])
        
        # 組合症狀文本（只用主要症狀）
        symptoms_text = "、".join(primary_symptoms) if primary_symptoms else chief_complaint
        
        # ===== 計算分數 =====
        confidence = hit.get("_confidence", 0.0)

        # ✅ 新計算：只評估案例本身的質量
        # 實際匹配由 _select_best_cases 計算
        quality_score = min((
            len(syndrome_list) * 0.15 +      # 證型完整度
            len(primary_symptoms) * 0.1 +    # 症狀豐富度
            len(zangfu_list) * 0.1 +         # 臟腑信息
            (1.0 if diagnosis else 0.0) * 0.15  # 有診斷結果
        ) / 0.5, 1.0)

        final_score = confidence * 0.7 + quality_score * 0.3
        
        # ===== 返回結構化結果 =====
        return {
            "source": "TCMCase",
            "id": str(case_id),
            "patient_id": str(patient_id),
            
            # 診斷資訊
            "diagnosis": diagnosis,
            "treatment": treatment,
            "suggestion": suggestion,
            
            # 分類症狀（清晰區分）
            "primary_symptoms": primary_symptoms,  # 主要症狀
            "syndrome": syndrome_list,             # 證型
            "zangfu": zangfu_list,                 # 臟腑
            "pulse": pulse_terms[:3] if pulse_terms else [],  # 脈象
            
            # 兼容性欄位
            "symptoms": symptoms_text,
            "full_text": full_text[:200],
            
            # 分數資訊
            "_confidence": confidence,
            "_term_score": quality_score,
            "_final": final_score,
            "_hits": primary_symptoms[:10],  # 用於收斂計算
            
            # 原始資料
            "raw": hit,
            "parsed_data": raw_data
        }
    
    def _fuse_rpcase(self, hit: Optional[Dict]) -> Optional[Dict]:
        """融合 RPCase 結果"""
        if not hit:
            return None
        
        rid = hit.get("rid", "")
        diagnosis = hit.get("final_diagnosis", "")
        pulse_tags = hit.get("pulse_tags", [])
        symptom_tags = hit.get("symptom_tags", [])
        
        # 合併症狀
        symptoms = " ".join(symptom_tags) if isinstance(symptom_tags, list) else str(symptom_tags)
        pulse = " ".join(pulse_tags) if isinstance(pulse_tags, list) else str(pulse_tags)
        
        confidence = hit.get("_confidence", 0.0)
        
        return {
            "source": "RPCase",
            "id": str(rid),
            "diagnosis": diagnosis,
            "pulse": pulse,
            "symptoms": symptoms,
            "_confidence": confidence,
            "_final": confidence * self.cfg.spiral.rpcase_weight,
            "_hits": symptom_tags if isinstance(symptom_tags, list) else [],
            "raw": hit
        }
    
    def _fuse_pulse(self, hit: Optional[Dict]) -> Optional[Dict]:
        """融合 PulsePJ 結果"""
        if not hit:
            return None
        
        pid = hit.get("pid", "")
        name = hit.get("name", "")
        symptoms = hit.get("symptoms", [])
        
        # 處理症狀
        if isinstance(symptoms, list):
            symptoms_text = "、".join(symptoms)
        else:
            symptoms_text = str(symptoms)
        
        confidence = hit.get("_confidence", 0.0)
        
        return {
            "source": "PulsePJ",
            "id": str(pid),
            "diagnosis": name,
            "pulse": name,
            "symptoms": symptoms_text,
            "_confidence": confidence,
            "_final": confidence * self.cfg.spiral.pulse_weight,
            "_hits": symptoms if isinstance(symptoms, list) else [],
            "raw": hit
        }
    
    def _extract_key_symptoms(self, text: str) -> List[str]:
        """提取關鍵症狀"""
        if not text:
            return []
        
        found_symptoms = []
        for symptom in self.cfg.text_processor.tcm_keywords:
            if symptom in text:
                found_symptoms.append(symptom)
        
        return found_symptoms[:10]  # 最多返回10個
    
    def _build_fused_sentence(
        self,
        primary: Optional[Dict],
        supplement: Optional[Dict]
    ) -> str:
        """構建融合句 - 優化版：清晰區分主輔資訊"""
        if not primary:
            return "無匹配案例"
        
        parts = []
        
        # ===== 主案例資訊 =====
        parts.append(f"【主案例】{primary['source']}#{primary['id']}")
        
        # 關鍵線索（只顯示主要的）
        key_clues = []
        
        # 1. 主要症狀（來自 primary_symptoms）
        if primary.get("primary_symptoms"):
            key_clues.extend(primary["primary_symptoms"][:5])
        
        # 2. 證型（優先級最高）
        if primary.get("syndrome"):
            key_clues.extend(primary["syndrome"])
        
        # 3. 臟腑
        if primary.get("zangfu"):
            key_clues.extend(primary["zangfu"])
        
        # 4. 脈象
        if primary.get("pulse"):
            pulse_str = "、".join(primary["pulse"])
            parts.append(f"脈象:{pulse_str}")
        
        if key_clues:
            parts.append(f"症狀：{', '.join(key_clues[:10])}")
        
        # ===== 輔助案例（明確標示為補充）=====
        if supplement:
            parts.append(f"\n【輔助】{supplement['source']}#{supplement['id']}")
            if supplement.get("symptoms"):
                # 只取前 5 個補充症狀
                supp_symptoms = supplement.get("symptoms", "")
                if isinstance(supp_symptoms, str):
                    supp_list = supp_symptoms.split("、")[:5]
                    parts.append(f"補充梗文：{', '.join(supp_list)}")
        
        # ===== 匹配度 =====
        parts.append(f"\n融合分數：{primary.get('_final', 0):.3f}")
        
        return " | ".join(parts)
    
    async def _generate_diagnosis(
        self,
        question: str,
        primary: Optional[Dict],
        supplement: Optional[Dict],
        fused_sentence: str,
        round_num: int,
        syndrome_result: Optional[SyndromeDiagnosis] = None
    ) -> str:
        """生成診斷結果"""
        
        # 如果沒有 LLM 或主案例,使用模板
        if not self.llm or not primary:
            return self._generate_template_diagnosis(
                question, primary, supplement, round_num
            )
        
        try:
            # 構建 prompt
            prompt = self._build_diagnosis_prompt(
                question, primary, supplement, fused_sentence, round_num
            )
            
            # 調用 LLM
            response = await self.llm.chat_complete(
                system_prompt="你是專業的中醫診斷助手，基於案例推理提供診斷建議。",
                user_prompt=prompt,
                temperature=0.3
            )
            
            # 後處理
            diagnosis = self._postprocess_diagnosis(response)
            
            return self._format_diagnosis_output(
                question, primary, supplement, diagnosis, round_num
            )
            
        except Exception as e:
            logger.error(f"LLM 生成失敗: {e}")
            return self._generate_template_diagnosis(
                question, primary, supplement, round_num
            )
    
    def _build_diagnosis_prompt(
        self,
        question: str,
        primary: Dict,
        supplement: Optional[Dict],
        fused_sentence: str,
        round_num: int
    ) -> str:
        """構建診斷提示詞 - 嚴格結構化版本"""
        
        # 提取關鍵資訊
        symptoms = primary.get("primary_symptoms", [])
        syndrome = primary.get("syndrome", [])
        zangfu = primary.get("zangfu", [])
        diagnosis_ref = primary.get("diagnosis", "未知")
        
        # ✅ 嚴格的結構化提示
        prompt = f"""你是一位專業中醫師，請基於參考案例提供診斷建議。

【第 {round_num} 輪診斷】

【患者主訴】
{question}

【參考案例資訊】
- 參考診斷：{diagnosis_ref}
- 相關症狀：{', '.join(symptoms[:8]) if symptoms else '資訊不足'}
- 證型方向：{', '.join(syndrome) if syndrome else '待判斷'}
- 臟腑定位：{', '.join(zangfu) if zangfu else '待確認'}

【診斷要求】
請提供以下內容（嚴格按照格式）：

1. **證型判斷**（一句話明確表述）
- 如果是首輪且資訊不足，註明"初步判斷"
- 如果是後續輪次，根據新症狀調整診斷

2. **調理建議**（3條具體可操作的建議）
- 作息調理：針對證型特點的具體建議
- 情志調節：具體方法
- 飲食調養：具體食材建議

【輸出格式】
證型判斷：[一句話]

調理建議：
1. [具體建議]
2. [具體建議]
3. [具體建議]

【嚴格禁止】
❌ 不要提及舌診、脈診的具體診法
❌ 不要開具中藥處方
❌ 不要輸出「關鍵線索」、「證件類型」等無關內容
❌ 不要使用佔位符（如XXX、...）
❌ 不要重複患者的原話
❌ 不要包含"根據以上"、"綜合分析"等冗餘前綴

【語言要求】
- 使用繁體中文
- 語言簡潔專業但親和
- 直接給出診斷，避免冗長分析
"""

        # 如果是第 2、3 輪，添加演化指引
        if round_num > 1:
            prompt += f"""

【重要】這是第 {round_num} 輪，患者已補充更多症狀：
- 請分析新症狀對診斷的影響
- 如需調整證型，說明理由
- 建議應更具針對性
"""

        return prompt
    
    def _postprocess_diagnosis(self, llm_response: str) -> Dict[str, str]:
        """後處理 LLM 響應"""
        
        # 過濾舌診相關內容
        if self.cfg.text_processor.ignore_tongue:
            llm_response = self._filter_tongue_content(llm_response)
        
        # 解析診斷和建議
        lines = llm_response.strip().split("\n")
        diagnosis = ""
        advice = []
        
        for line in lines:
            line = line.strip()
            if "診斷" in line or line.startswith("1"):
                diagnosis = line.split("：", 1)[-1].strip()
            elif "建議" in line or line.startswith("2"):
                continue
            elif line and not line.startswith("#"):
                advice.append(line)
        
        return {
            "diagnosis": diagnosis or "證型待定",
            "advice": "\n".join(advice[:3]) or "調理建議待定"
        }
    
    def _filter_tongue_content(self, text: str) -> str:
        """過濾舌診內容"""
        if not text:
            return text
        
        filtered_lines = []
        for line in text.split("\n"):
            if "舌" not in line and "苔" not in line:
                filtered_lines.append(line)
        
        return "\n".join(filtered_lines)
    
    def _format_diagnosis_output(
        self,
        question: str,
        primary: Dict,
        supplement: Optional[Dict],
        diagnosis: Dict[str, str],
        round_num: int
    ) -> str:
        """格式化診斷輸出"""
        
        lines = [
            f"【第 {round_num} 輪診斷】",
            "",
            f"使用案例編號：{primary['id']}",
            "",
            "當前問題：",
            question,
            "",
            "依據過往案例線索：",
        ]
        
        # ===== 關鍵線索（結構化呈現）=====
        clues_added = False
        
        # 1. 主要症狀
        if primary.get("primary_symptoms"):
            symptoms = primary["primary_symptoms"][:8]
            lines.append(f"* 關鍵線索：{', '.join(symptoms)}")
            clues_added = True
        
        # 2. 脈象
        if primary.get("pulse"):
            pulse_str = "、".join(primary["pulse"])
            lines.append(f"* 脈象：{pulse_str}")
            clues_added = True
        
        # 3. 證型（如果有）
        if primary.get("syndrome"):
            syndrome_str = "、".join(primary["syndrome"])
            lines.append(f"* 證型判斷：{syndrome_str}")
            clues_added = True
        
        # 4. 臟腑定位（如果有）
        if primary.get("zangfu"):
            zangfu_str = "、".join(primary["zangfu"])
            lines.append(f"* 臟腑：{zangfu_str}")
            clues_added = True
        
        if not clues_added:
            lines.append(f"* 症狀：{primary.get('symptoms', '無')[:100]}")
        
        # ===== 輔助梗文（明確分開）=====
        if supplement:
            lines.append("")
            lines.append("輔助參考：")
            supp_symptoms = supplement.get("symptoms", "")
            if isinstance(supp_symptoms, str) and supp_symptoms:
                supp_list = supp_symptoms.split("、")[:5]
                lines.append(f"* 補充梗文：{', '.join(supp_list)}")
        
        # ===== 診斷結果 =====
        lines.extend([
            "",
            "診斷結果：",
            diagnosis["diagnosis"],
            "",
            "建議：",
            diagnosis["advice"]
        ])
        
        return "\n".join(lines)
    
    def _generate_template_diagnosis(
        self,
        question: str,
        primary: Optional[Dict],
        supplement: Optional[Dict],
        round_num: int
    ) -> str:
        """生成模板診斷 - 改進版：針對性建議"""
        
        if not primary:
            return f"第 {round_num} 輪：暫無匹配案例，請補充更多症狀資訊。"
        
        # 提取診斷
        diagnosis = primary.get("diagnosis", "證型待定")
        
        # 根據診斷給出具體建議
        advice = self._get_specific_advice(diagnosis, question, round_num)
        
        # 構建輸出
        lines = [
            f"【第 {round_num} 輪診斷】",
            "",
            f"使用案例編號：{primary.get('id', 'NA')}",
            "",
            "當前問題：",
            question,
        ]
        
        # 如果有關鍵症狀，列出來
        if primary.get("primary_symptoms"):
            symptoms = primary["primary_symptoms"][:5]
            lines.append("")
            lines.append("依據過往案例線索：")
            lines.append(f"* 關鍵線索：{', '.join(symptoms)}")
        
        lines.extend([
            "",
            "診斷結果：",
            diagnosis,
            "",
            "建議：",
            advice
        ])
        
        # 顯示匹配度
        confidence = primary.get('_final', 0)
        lines.append(f"\n匹配度：{confidence:.1%}")
        
        # 第一輪如果匹配度低，提示補充
        if round_num == 1 and confidence < 0.7:
            lines.append("\n💡 建議補充：舌象、寒熱傾向、伴隨症狀等資訊可提高診斷準確度")
        
        return "\n".join(lines)
    
    def _get_specific_advice(self, diagnosis: str, question: str, round_num: int) -> str:
        """根據診斷生成具體建議（模板診斷用）"""
        
        # 基礎建議
        advice_parts = []
        
        # 作息調理
        advice_parts.append("1. 作息調理：保持規律作息，晚上10點前入睡，避免熬夜")
        
        # 情志調節
        advice_parts.append("2. 情志調節：保持心情舒暢，避免過度緊張焦慮")
        
        # 飲食調養
        advice_parts.append("3. 飲食調養：清淡飲食，避免辛辣刺激性食物")
        
        # 根據診斷關鍵詞調整建議
        if "陰虛" in diagnosis:
            advice_parts.append("\n針對陰虛證：可多食用滋陰食物如百合、蓮子、銀耳等")
        elif "氣虛" in diagnosis or "血虛" in diagnosis:
            advice_parts.append("\n針對氣血虛證：適當補充營養，可食用紅棗、龍眼等")
        elif "肝鬱" in diagnosis:
            advice_parts.append("\n針對肝鬱證：注意疏肝解鬱，可適當散步、聽音樂放鬆")
        
        return "\n".join(advice_parts)
    
    def clear_session_symptoms(self, session_id: str):
        """清理會話症狀記錄"""
        if hasattr(self, '_symptom_tracker') and session_id in self._symptom_tracker:
            del self._symptom_tracker[session_id]
            logger.info(f"🗑️ 清理會話症狀: {session_id}")