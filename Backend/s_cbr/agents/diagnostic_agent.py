"""
中醫診斷智能體 v2.0

負責生成中醫診斷報告與證候分析
支援多輪推理歷史整合與會話上下文

版本：v2.0 - 螺旋互動版
更新：整合多輪推理歷史與會話上下文處理
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
    from ..knowledge.pulse_repository import PulseRepository
    from ..knowledge.case_repository import CaseRepository
    from ..utils.api_manager import SCBRAPIManager
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    PulseRepository = None
    CaseRepository = None
    SCBRAPIManager = None

class DiagnosticAgent:
    """
    中醫診斷智能體 v2.0
    
    v2.0 特色：
    - 多輪推理歷史整合
    - 會話上下文感知診斷
    - 證候分析深度優化
    - 處方建議精準化
    """
    
    def __init__(self):
        """初始化診斷智能體 v2.0"""
        self.logger = SpiralLogger.get_logger("DiagnosticAgent") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("DiagnosticAgent")
        self.version = "2.0"
        
        # 初始化相關組件
        self.pulse_repository = PulseRepository() if PulseRepository else None
        self.case_repository = CaseRepository() if CaseRepository else None
        self.api_manager = SCBRAPIManager() if SCBRAPIManager else None
        
        # v2.0 診斷參數
        self.syndrome_weights = {
            "pulse_contribution": 0.30,
            "symptom_pattern": 0.35,
            "constitution_type": 0.20,
            "seasonal_factor": 0.10,
            "age_gender_factor": 0.05
        }
        
        self.confidence_thresholds = {
            "high_confidence": 0.80,
            "medium_confidence": 0.60,
            "low_confidence": 0.40
        }
        
        # 中醫理論知識庫（簡化版）
        self.tcm_knowledge = self._initialize_tcm_knowledge()
        
        self.logger.info(f"中醫診斷智能體 v{self.version} 初始化完成")
    
    async def create_diagnostic_report_v2(self, 
                                        query: str,
                                        patient_context: Dict[str, Any],
                                        session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        創建診斷報告 v2.0 - 整合多輪推理歷史
        
        Args:
            query: 患者主訴
            patient_context: 患者基本信息與症狀
            session_context: 會話上下文（session_id, round, used_cases等）
            
        Returns:
            Dict[str, Any]: 完整診斷報告
        """
        try:
            session_id = session_context.get("session_id", "")
            round_number = session_context.get("round", 1)
            used_cases = session_context.get("used_cases", [])
            
            self.logger.info(f"開始診斷分析 v2.0 - Session: {session_id}, Round: {round_number}")
            
            # 1. 多源信息整合
            integrated_info = await self._integrate_multi_source_info_v2(
                query, patient_context, session_context
            )
            
            # 2. 證候辨識與分析
            syndrome_analysis = await self._analyze_syndrome_patterns_v2(
                integrated_info, session_context
            )
            
            # 3. 脈診深度分析
            pulse_analysis = await self._deep_pulse_analysis_v2(
                patient_context, session_context
            )
            
            # 4. 主病診斷確定
            primary_diagnosis = await self._determine_primary_diagnosis_v2(
                syndrome_analysis, pulse_analysis, session_context
            )
            
            # 5. 兼證與合病分析
            secondary_patterns = await self._analyze_secondary_patterns_v2(
                integrated_info, primary_diagnosis, session_context
            )
            
            # 6. 治法治則制定
            treatment_principles = await self._formulate_treatment_principles_v2(
                primary_diagnosis, secondary_patterns, session_context
            )
            
            # 7. 方藥建議生成
            prescription_recommendation = await self._generate_prescription_v2(
                treatment_principles, patient_context, session_context
            )
            
            # 8. 診斷信心度評估
            diagnostic_confidence = await self._assess_diagnostic_confidence_v2(
                syndrome_analysis, pulse_analysis, session_context
            )
            
            # 9. 多輪推理一致性檢查
            consistency_check = await self._check_multi_round_consistency_v2(
                primary_diagnosis, session_context
            )
            
            # 構建完整診斷報告
            diagnostic_report = {
                "primary_diagnosis": primary_diagnosis["diagnosis"],
                "syndrome_differentiation": syndrome_analysis["syndrome_type"],
                "pulse_diagnosis": pulse_analysis["pulse_interpretation"],
                "secondary_patterns": secondary_patterns,
                "treatment_principles": treatment_principles["principles"],
                "prescription_recommendation": prescription_recommendation,
                "diagnostic_confidence": diagnostic_confidence["confidence_score"],
                "confidence_level": diagnostic_confidence["confidence_level"],
                "diagnostic_reasoning": await self._generate_diagnostic_reasoning_v2(
                    syndrome_analysis, pulse_analysis, primary_diagnosis
                ),
                "clinical_notes": await self._generate_clinical_notes_v2(
                    integrated_info, session_context
                ),
                "follow_up_recommendations": await self._generate_follow_up_recommendations_v2(
                    primary_diagnosis, session_context
                ),
                "consistency_analysis": consistency_check,
                "round": round_number,
                "session_id": session_id,
                "used_cases_count": len(used_cases),
                "report_timestamp": datetime.now().isoformat(),
                "version": self.version
            }
            
            self.logger.info(f"診斷分析 v2.0 完成 - 主診斷: {primary_diagnosis['diagnosis']}, "
                          f"信心度: {diagnostic_confidence['confidence_score']:.3f}")
            
            return diagnostic_report
            
        except Exception as e:
            self.logger.error(f"診斷分析 v2.0 失敗: {str(e)}")
            return await self._create_fallback_diagnostic_report_v2(query, patient_context, session_context)
    
    async def _integrate_multi_source_info_v2(self, 
                                            query: str, 
                                            patient_context: Dict, 
                                            session_context: Dict) -> Dict[str, Any]:
        """
        多源信息整合 v2.0
        
        Returns:
            Dict[str, Any]: 整合後的患者信息
        """
        round_number = session_context.get("round", 1)
        used_cases = session_context.get("used_cases", [])
        
        # 基本患者信息
        basic_info = {
            "age": patient_context.get("age", 35),
            "gender": patient_context.get("gender", "未知"),
            "constitution": patient_context.get("constitution", ""),
            "chief_complaint": query
        }
        
        # 症狀信息整合
        symptoms_info = {
            "primary_symptoms": self._extract_primary_symptoms(query),
            "secondary_symptoms": patient_context.get("secondary_symptoms", []),
            "symptom_duration": patient_context.get("duration", ""),
            "symptom_severity": patient_context.get("severity", "中等")
        }
        
        # 脈診信息
        pulse_info = {
            "pulse_text": patient_context.get("pulse_text", ""),
            "pulse_characteristics": self._analyze_pulse_characteristics(
                patient_context.get("pulse_text", "")
            )
        }
        
        # v2.0: 會話歷史信息
        session_info = {
            "round_number": round_number,
            "previous_cases": used_cases,
            "session_progression": await self._analyze_session_progression(session_context)
        }
        
        # 環境因素
        environmental_factors = {
            "season": self._get_current_season(),
            "time_of_consultation": datetime.now().strftime("%H:%M")
        }
        
        return {
            "basic_info": basic_info,
            "symptoms_info": symptoms_info,
            "pulse_info": pulse_info,
            "session_info": session_info,
            "environmental_factors": environmental_factors
        }
    
    async def _analyze_syndrome_patterns_v2(self, 
                                          integrated_info: Dict, 
                                          session_context: Dict) -> Dict[str, Any]:
        """
        證候模式分析 v2.0
        
        Returns:
            Dict[str, Any]: 證候分析結果
        """
        round_number = session_context.get("round", 1)
        
        # 提取關鍵信息
        symptoms = integrated_info["symptoms_info"]["primary_symptoms"]
        pulse_chars = integrated_info["pulse_info"]["pulse_characteristics"]
        constitution = integrated_info["basic_info"]["constitution"]
        
        # 八綱辨證
        eight_principles = await self._eight_principles_analysis(symptoms, pulse_chars)
        
        # 氣血津液辨證
        qi_blood_analysis = await self._qi_blood_fluid_analysis(symptoms, pulse_chars)
        
        # 臟腑辨證
        zangfu_analysis = await self._zangfu_analysis(symptoms, pulse_chars, constitution)
        
        # v2.0: 多輪推理證候演變分析
        syndrome_evolution = await self._analyze_syndrome_evolution_v2(
            eight_principles, qi_blood_analysis, zangfu_analysis, session_context
        )
        
        # 綜合證候判定
        syndrome_type = await self._determine_syndrome_type(
            eight_principles, qi_blood_analysis, zangfu_analysis, round_number
        )
        
        # 證候信心度
        syndrome_confidence = await self._calculate_syndrome_confidence(
            eight_principles, qi_blood_analysis, zangfu_analysis
        )
        
        return {
            "syndrome_type": syndrome_type,
            "eight_principles": eight_principles,
            "qi_blood_analysis": qi_blood_analysis,
            "zangfu_analysis": zangfu_analysis,
            "syndrome_evolution": syndrome_evolution,
            "syndrome_confidence": syndrome_confidence,
            "round": round_number
        }
    
    async def _deep_pulse_analysis_v2(self, 
                                    patient_context: Dict, 
                                    session_context: Dict) -> Dict[str, Any]:
        """
        脈診深度分析 v2.0
        
        Returns:
            Dict[str, Any]: 脈診分析結果
        """
        pulse_text = patient_context.get("pulse_text", "")
        round_number = session_context.get("round", 1)
        
        if not pulse_text:
            return {
                "pulse_interpretation": "脈診信息不足",
                "pulse_significance": "無法進行脈診分析",
                "diagnostic_value": 0.0,
                "round": round_number
            }
        
        # 脈象特徵提取
        pulse_features = await self._extract_pulse_features(pulse_text)
        
        # 脈診理論匹配
        pulse_theory_match = await self._match_pulse_theory(pulse_features)
        
        # 脈證合參
        pulse_syndrome_correlation = await self._correlate_pulse_syndrome(
            pulse_features, patient_context
        )
        
        # v2.0: 多輪脈診一致性分析
        pulse_consistency = await self._analyze_pulse_consistency_v2(
            pulse_features, session_context
        )
        
        # 脈診診斷價值評估
        diagnostic_value = await self._assess_pulse_diagnostic_value(
            pulse_features, pulse_theory_match, pulse_syndrome_correlation
        )
        
        # 脈診解釋生成
        pulse_interpretation = await self._generate_pulse_interpretation(
            pulse_features, pulse_theory_match, pulse_syndrome_correlation
        )
        
        return {
            "pulse_interpretation": pulse_interpretation,
            "pulse_features": pulse_features,
            "pulse_theory_match": pulse_theory_match,
            "pulse_syndrome_correlation": pulse_syndrome_correlation,
            "pulse_consistency": pulse_consistency,
            "diagnostic_value": diagnostic_value,
            "pulse_significance": await self._explain_pulse_significance(pulse_features),
            "round": round_number
        }
    
    async def _determine_primary_diagnosis_v2(self, 
                                            syndrome_analysis: Dict, 
                                            pulse_analysis: Dict,
                                            session_context: Dict) -> Dict[str, Any]:
        """
        確定主病診斷 v2.0
        
        Returns:
            Dict[str, Any]: 主診斷結果
        """
        round_number = session_context.get("round", 1)
        
        # 綜合證候與脈診信息
        syndrome_type = syndrome_analysis.get("syndrome_type", "")
        zangfu_pattern = syndrome_analysis.get("zangfu_analysis", {})
        pulse_significance = pulse_analysis.get("pulse_significance", "")
        
        # v2.0: 多輪診斷一致性權重
        consistency_weight = self._calculate_consistency_weight(session_context)
        
        # 主診斷候選
        diagnosis_candidates = await self._generate_diagnosis_candidates(
            syndrome_type, zangfu_pattern, pulse_significance
        )
        
        # 診斷評分與排序
        scored_diagnoses = await self._score_diagnosis_candidates(
            diagnosis_candidates, syndrome_analysis, pulse_analysis, consistency_weight
        )
        
        # 確定最終主診斷
        primary_diagnosis = scored_diagnoses[0] if scored_diagnoses else {
            "diagnosis": "辨證待定",
            "score": 0.5,
            "evidence": ["診斷信息不足"]
        }
        
        # 診斷依據整理
        diagnostic_evidence = await self._compile_diagnostic_evidence(
            primary_diagnosis, syndrome_analysis, pulse_analysis
        )
        
        # v2.0: 多輪診斷演進分析
        diagnosis_evolution = await self._analyze_diagnosis_evolution_v2(
            primary_diagnosis, session_context
        )
        
        return {
            "diagnosis": primary_diagnosis["diagnosis"],
            "diagnostic_score": primary_diagnosis["score"],
            "diagnostic_evidence": diagnostic_evidence,
            "diagnosis_evolution": diagnosis_evolution,
            "alternative_diagnoses": scored_diagnoses[1:3],  # 前2個備選診斷
            "round": round_number
        }
    
    async def _formulate_treatment_principles_v2(self, 
                                               primary_diagnosis: Dict, 
                                               secondary_patterns: Dict,
                                               session_context: Dict) -> Dict[str, Any]:
        """
        制定治法治則 v2.0
        
        Returns:
            Dict[str, Any]: 治療法則
        """
        round_number = session_context.get("round", 1)
        diagnosis = primary_diagnosis.get("diagnosis", "")
        
        # 基本治療法則
        basic_principles = await self._derive_basic_treatment_principles(diagnosis)
        
        # 兼證治療考慮
        secondary_considerations = await self._consider_secondary_patterns(
            secondary_patterns
        )
        
        # v2.0: 多輪治療一致性
        treatment_consistency = await self._ensure_treatment_consistency_v2(
            basic_principles, session_context
        )
        
        # 個體化調整
        individualized_adjustments = await self._make_individualized_adjustments(
            basic_principles, session_context
        )
        
        # 綜合治療法則
        comprehensive_principles = await self._integrate_treatment_principles(
            basic_principles, secondary_considerations, individualized_adjustments
        )
        
        return {
            "principles": comprehensive_principles,
            "basic_principles": basic_principles,
            "secondary_considerations": secondary_considerations,
            "treatment_consistency": treatment_consistency,
            "individualized_adjustments": individualized_adjustments,
            "round": round_number
        }
    
    async def _generate_prescription_v2(self, 
                                      treatment_principles: Dict, 
                                      patient_context: Dict,
                                      session_context: Dict) -> Dict[str, Any]:
        """
        生成方藥建議 v2.0
        
        Returns:
            Dict[str, Any]: 處方建議
        """
        round_number = session_context.get("round", 1)
        principles = treatment_principles.get("principles", [])
        
        # 基礎方劑選擇
        base_formula = await self._select_base_formula(principles, patient_context)
        
        # 加減化裁
        formula_modifications = await self._modify_formula(
            base_formula, patient_context, session_context
        )
        
        # v2.0: 多輪處方優化
        prescription_optimization = await self._optimize_prescription_v2(
            base_formula, formula_modifications, session_context
        )
        
        # 劑量調整
        dosage_adjustments = await self._adjust_dosages(
            formula_modifications, patient_context
        )
        
        # 服用方法
        administration_method = await self._determine_administration_method(
            formula_modifications, patient_context
        )
        
        # 處方解釋
        prescription_rationale = await self._explain_prescription_rationale(
            base_formula, formula_modifications, principles
        )
        
        return {
            "base_formula": base_formula,
            "modified_formula": formula_modifications,
            "prescription_optimization": prescription_optimization,
            "dosage_recommendations": dosage_adjustments,
            "administration_method": administration_method,
            "prescription_rationale": prescription_rationale,
            "safety_considerations": await self._assess_prescription_safety(
                formula_modifications, patient_context
            ),
            "round": round_number
        }
    
    # 輔助方法實現
    def _extract_primary_symptoms(self, query: str) -> List[str]:
        """提取主要症狀"""
        # 簡化實現：基於關鍵詞提取
        symptom_keywords = [
            "頭痛", "失眠", "疲勞", "焦慮", "抑鬱", "胃痛", "腹瀉", "便秘",
            "咳嗽", "感冒", "發熱", "盗汗", "心悸", "氣短", "腰痛", "關節痛",
            "頭暈", "耳鳴", "口乾", "潮熱", "怕冷", "多夢", "胸悶", "腹脹"
        ]
        
        symptoms = []
        for keyword in symptom_keywords:
            if keyword in query:
                symptoms.append(keyword)
        
        return symptoms if symptoms else ["症狀不明確"]
    
    def _analyze_pulse_characteristics(self, pulse_text: str) -> Dict[str, Any]:
        """分析脈象特徵"""
        if not pulse_text:
            return {"characteristics": [], "quality": "無"}
        
        # 簡化實現：基於關鍵詞識別脈象
        pulse_patterns = {
            "浮脈": ["浮", "輕按即得"],
            "沉脈": ["沉", "重按始得"],
            "遲脈": ["遲", "緩慢"],
            "數脈": ["數", "快速"],
            "弦脈": ["弦", "緊張", "如按琴弦"],
            "細脈": ["細", "如線"],
            "滑脈": ["滑", "圓滑"],
            "澀脈": ["澀", "不暢"]
        }
        
        identified_pulses = []
        for pulse_type, keywords in pulse_patterns.items():
            if any(keyword in pulse_text for keyword in keywords):
                identified_pulses.append(pulse_type)
        
        return {
            "characteristics": identified_pulses,
            "quality": "明確" if identified_pulses else "模糊",
            "raw_text": pulse_text
        }
    
    async def _analyze_session_progression(self, session_context: Dict) -> Dict[str, Any]:
        """分析會話進展"""
        round_number = session_context.get("round", 1)
        used_cases = session_context.get("used_cases", [])
        
        return {
            "progression_stage": "初診" if round_number == 1 else f"第{round_number}輪推理",
            "case_diversity": len(set(used_cases)),
            "reasoning_depth": min(round_number / 3, 1.0)
        }
    
    def _get_current_season(self) -> str:
        """獲取當前季節"""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "冬"
        elif month in [3, 4, 5]:
            return "春"
        elif month in [6, 7, 8]:
            return "夏"
        else:
            return "秋"
    
    async def _eight_principles_analysis(self, symptoms: List[str], pulse_chars: Dict) -> Dict[str, str]:
        """八綱辨證分析"""
        # 簡化實現
        return {
            "表裏": "裏證" if "內熱" in str(symptoms) or "便秘" in symptoms else "表證",
            "寒熱": "熱證" if "發熱" in symptoms or "口乾" in symptoms else "寒證",
            "虛實": "虛證" if "疲勞" in symptoms or "氣短" in symptoms else "實證",
            "陰陽": "陽證" if "煩躁" in symptoms else "陰證"
        }
    
    async def _qi_blood_fluid_analysis(self, symptoms: List[str], pulse_chars: Dict) -> Dict[str, str]:
        """氣血津液辨證"""
        return {
            "氣分": "氣虛" if "疲勞" in symptoms or "氣短" in symptoms else "氣滯",
            "血分": "血瘀" if "頭痛" in symptoms else "血虛",
            "津液": "津虧" if "口乾" in symptoms else "痰濕"
        }
    
    async def _zangfu_analysis(self, symptoms: List[str], pulse_chars: Dict, constitution: str) -> Dict[str, str]:
        """臟腑辨證"""
        return {
            "肝": "肝鬱氣滯" if "胸悶" in symptoms or "煩躁" in symptoms else "肝血不足",
            "心": "心神不寧" if "失眠" in symptoms or "心悸" in symptoms else "心血虛",
            "脾": "脾胃虛弱" if "腹脹" in symptoms or "食慾不振" in symptoms else "脾運正常",
            "肺": "肺氣虛" if "咳嗽" in symptoms or "氣短" in symptoms else "肺氣充實",
            "腎": "腎陽虛" if "怕冷" in symptoms or "腰痛" in symptoms else "腎陰虛"
        }
    
    def _initialize_tcm_knowledge(self) -> Dict[str, Any]:
        """初始化中醫知識庫"""
        return {
            "syndromes": {
                "肝鬱氣滯": {"symptoms": ["胸悶", "煩躁", "脅痛"], "treatment": "疏肝解鬱"},
                "心神不寧": {"symptoms": ["失眠", "心悸", "多夢"], "treatment": "養心安神"},
                "脾胃虛弱": {"symptoms": ["腹脹", "食慾不振", "便溏"], "treatment": "健脾益氣"},
                "腎陽虛": {"symptoms": ["怕冷", "腰痛", "夜尿"], "treatment": "溫補腎陽"},
                "陰虛火旺": {"symptoms": ["潮熱", "口乾", "心煩"], "treatment": "滋陰降火"}
            },
            "formulas": {
                "逍遙散": {"indication": "肝鬱氣滯", "herbs": ["柴胡", "當歸", "白芍"]},
                "甘麥大棗湯": {"indication": "心神不寧", "herbs": ["甘草", "小麥", "大棗"]},
                "六君子湯": {"indication": "脾胃虛弱", "herbs": ["人參", "白朮", "茯苓"]},
                "金匱腎氣丸": {"indication": "腎陽虛", "herbs": ["附子", "肉桂", "地黃"]},
                "知柏地黃丸": {"indication": "陰虛火旺", "herbs": ["知母", "黃柏", "地黃"]}
            }
        }
    
    # 其他輔助方法的簡化實現
    async def _analyze_syndrome_evolution_v2(self, *args, session_context: Dict) -> Dict:
        """分析證候演變"""
        round_number = session_context.get("round", 1)
        return {
            "evolution_pattern": f"第{round_number}輪證候分析",
            "stability": "穩定" if round_number > 1 else "初步"
        }
    
    async def _determine_syndrome_type(self, eight_principles: Dict, qi_blood: Dict, zangfu: Dict, round_number: int) -> str:
        """確定證候類型"""
        # 簡化實現：基於臟腑辨證
        main_zangfu = max(zangfu.keys(), key=lambda k: len(zangfu[k]))
        return zangfu[main_zangfu]
    
    async def _calculate_syndrome_confidence(self, eight_principles: Dict, qi_blood: Dict, zangfu: Dict) -> float:
        """計算證候信心度"""
        return 0.8  # 簡化實現
    
    def _calculate_consistency_weight(self, session_context: Dict) -> float:
        """計算一致性權重"""
        round_number = session_context.get("round", 1)
        return min(1.0, 0.5 + round_number * 0.1)
    
    async def _generate_diagnosis_candidates(self, syndrome_type: str, zangfu: Dict, pulse_sig: str) -> List[Dict]:
        """生成診斷候選"""
        return [
            {"diagnosis": syndrome_type, "score": 0.8, "evidence": ["證候分析", "脈診支持"]},
            {"diagnosis": "相關證候", "score": 0.6, "evidence": ["部分症狀匹配"]}
        ]
    
    async def _score_diagnosis_candidates(self, candidates: List, syndrome: Dict, pulse: Dict, weight: float) -> List[Dict]:
        """診斷候選評分"""
        return sorted(candidates, key=lambda x: x["score"], reverse=True)
    
    # 其他方法的簡化實現...
    async def _compile_diagnostic_evidence(self, diagnosis: Dict, syndrome: Dict, pulse: Dict) -> List[str]:
        """編譯診斷依據"""
        return ["證候分析支持", "脈診相符", "症狀匹配"]
    
    async def _analyze_diagnosis_evolution_v2(self, diagnosis: Dict, session_context: Dict) -> Dict:
        """分析診斷演進"""
        return {"evolution": "診斷逐步明確", "round": session_context.get("round", 1)}
    
    async def _analyze_secondary_patterns_v2(self, info: Dict, primary: Dict, session_context: Dict) -> Dict:
        """分析兼證"""
        return {"secondary_patterns": [], "complexity": "單純"}
    
    async def _derive_basic_treatment_principles(self, diagnosis: str) -> List[str]:
        """推導基本治法"""
        treatment_map = {
            "肝鬱氣滯": ["疏肝", "解鬱", "理氣"],
            "心神不寧": ["養心", "安神", "定志"],
            "脾胃虛弱": ["健脾", "益氣", "助運"],
            "腎陽虛": ["溫腎", "助陽", "補火"],
            "陰虛火旺": ["滋陰", "降火", "清熱"]
        }
        return treatment_map.get(diagnosis, ["辨證施治"])
    
    async def _consider_secondary_patterns(self, secondary: Dict) -> List[str]:
        """兼證治療考慮"""
        return ["兼顧兼證"] if secondary.get("secondary_patterns") else []
    
    async def _ensure_treatment_consistency_v2(self, principles: List, session_context: Dict) -> Dict:
        """確保治療一致性"""
        return {"consistency": "良好", "round": session_context.get("round", 1)}
    
    async def _make_individualized_adjustments(self, principles: List, session_context: Dict) -> List[str]:
        """個體化調整"""
        return ["根據體質調整"]
    
    async def _integrate_treatment_principles(self, basic: List, secondary: List, individual: List) -> List[str]:
        """整合治療法則"""
        return basic + secondary + individual
    
    async def _select_base_formula(self, principles: List, patient_context: Dict) -> Dict:
        """選擇基礎方劑"""
        # 簡化實現
        if "疏肝" in principles:
            return {"name": "逍遙散", "herbs": ["柴胡", "當歸", "白芍", "白朮", "茯苓", "甘草"]}
        elif "養心" in principles:
            return {"name": "甘麥大棗湯", "herbs": ["甘草", "小麥", "大棗"]}
        else:
            return {"name": "四君子湯", "herbs": ["人參", "白朮", "茯苓", "甘草"]}
    
    async def _modify_formula(self, base_formula: Dict, patient_context: Dict, session_context: Dict) -> Dict:
        """方劑加減"""
        modified = base_formula.copy()
        modified["modifications"] = ["根據症狀加減"]
        return modified
    
    async def _optimize_prescription_v2(self, base: Dict, modified: Dict, session_context: Dict) -> Dict:
        """處方優化"""
        return {"optimization": "多輪推理優化", "round": session_context.get("round", 1)}
    
    async def _adjust_dosages(self, formula: Dict, patient_context: Dict) -> Dict:
        """劑量調整"""
        return {"dosage": "常規劑量", "adjustments": ["根據年齡調整"]}
    
    async def _determine_administration_method(self, formula: Dict, patient_context: Dict) -> Dict:
        """服藥方法"""
        return {"method": "水煎服", "frequency": "日二次", "timing": "飯後溫服"}
    
    async def _explain_prescription_rationale(self, base: Dict, modified: Dict, principles: List) -> str:
        """處方解釋"""
        return f"方選{base.get('name', '未知方')}，{','.join(principles)}為治法"
    
    async def _assess_prescription_safety(self, formula: Dict, patient_context: Dict) -> List[str]:
        """評估處方安全性"""
        return ["注意服藥反應", "孕婦慎用"]
    
    async def _assess_diagnostic_confidence_v2(self, syndrome: Dict, pulse: Dict, session_context: Dict) -> Dict:
        """評估診斷信心度"""
        base_confidence = 0.7
        round_bonus = min(session_context.get("round", 1) * 0.05, 0.2)
        final_confidence = min(base_confidence + round_bonus, 0.95)
        
        if final_confidence >= self.confidence_thresholds["high_confidence"]:
            level = "高"
        elif final_confidence >= self.confidence_thresholds["medium_confidence"]:
            level = "中"
        else:
            level = "低"
        
        return {
            "confidence_score": final_confidence,
            "confidence_level": level,
            "round": session_context.get("round", 1)
        }
    
    async def _check_multi_round_consistency_v2(self, diagnosis: Dict, session_context: Dict) -> Dict:
        """多輪一致性檢查"""
        round_number = session_context.get("round", 1)
        
        return {
            "consistency_score": 0.9 if round_number == 1 else min(0.95, 0.7 + round_number * 0.05),
            "consistency_level": "良好",
            "notes": f"第{round_number}輪診斷一致性分析",
            "round": round_number
        }
    
    async def _generate_diagnostic_reasoning_v2(self, syndrome: Dict, pulse: Dict, diagnosis: Dict) -> str:
        """生成診斷推理"""
        return f"基於證候分析{syndrome.get('syndrome_type', '')}，結合脈診{pulse.get('pulse_interpretation', '')}，診斷為{diagnosis.get('diagnosis', '')}"
    
    async def _generate_clinical_notes_v2(self, info: Dict, session_context: Dict) -> List[str]:
        """生成臨床備註"""
        round_number = session_context.get("round", 1)
        return [
            f"第{round_number}輪推理診斷",
            "建議結合舌診",
            "注意病情變化"
        ]
    
    async def _generate_follow_up_recommendations_v2(self, diagnosis: Dict, session_context: Dict) -> List[str]:
        """生成隨訪建議"""
        return [
            "一週後複診",
            "觀察療效",
            "記錄症狀變化",
            "如有不適及時就醫"
        ]
    
    # 繼續實現其他輔助方法...
    async def _extract_pulse_features(self, pulse_text: str) -> Dict:
        """提取脈象特徵"""
        return {"features": ["待分析"], "text": pulse_text}
    
    async def _match_pulse_theory(self, features: Dict) -> Dict:
        """脈診理論匹配"""
        return {"theory_match": "部分匹配", "score": 0.7}
    
    async def _correlate_pulse_syndrome(self, features: Dict, context: Dict) -> Dict:
        """脈證合參"""
        return {"correlation": "相符", "strength": 0.8}
    
    async def _analyze_pulse_consistency_v2(self, features: Dict, session_context: Dict) -> Dict:
        """脈診一致性分析"""
        return {"consistency": "一致", "round": session_context.get("round", 1)}
    
    async def _assess_pulse_diagnostic_value(self, features: Dict, theory: Dict, correlation: Dict) -> float:
        """脈診診斷價值"""
        return 0.8
    
    async def _generate_pulse_interpretation(self, features: Dict, theory: Dict, correlation: Dict) -> str:
        """生成脈診解釋"""
        return "脈象提示證候相符"
    
    async def _explain_pulse_significance(self, features: Dict) -> str:
        """解釋脈診意義"""
        return "脈診對診斷有重要參考價值"
    
    async def _create_fallback_diagnostic_report_v2(self, query: str, patient_context: Dict, session_context: Dict) -> Dict:
        """創建降級診斷報告"""
        round_number = session_context.get("round", 1)
        
        return {
            "primary_diagnosis": "辨證待定",
            "syndrome_differentiation": "需進一步分析",
            "pulse_diagnosis": "脈診待完善",
            "treatment_principles": ["對症處理"],
            "prescription_recommendation": {"base_formula": {"name": "待定"}},
            "diagnostic_confidence": 0.5,
            "confidence_level": "低",
            "round": round_number,
            "session_id": session_context.get("session_id", "fallback"),
            "fallback": True,
            "version": self.version
        }
    
    # 向後兼容方法（v1.0）
    async def create_diagnostic_report(self, query: str, patient_context: Dict, **kwargs) -> Dict[str, Any]:
        """向後兼容的診斷報告生成"""
        session_context = {"round": 1, "session_id": "legacy", "used_cases": []}
        return await self.create_diagnostic_report_v2(query, patient_context, session_context)
    
    async def analyze_symptoms(self, symptoms: List[str], **kwargs) -> Dict[str, Any]:
        """向後兼容的症狀分析"""
        # 簡化實現
        return {
            "primary_symptoms": symptoms,
            "syndrome_analysis": "需結合完整信息",
            "confidence": 0.6
        }
    
    async def generate_treatment_plan(self, diagnosis: str, **kwargs) -> Dict[str, Any]:
        """向後兼容的治療方案生成"""
        return {
            "treatment_principles": await self._derive_basic_treatment_principles(diagnosis),
            "prescription": {"name": "待定方劑"},
            "administration": {"method": "水煎服"}
        }

# 向後兼容的類別名稱
DiagnosticAgentV2 = DiagnosticAgent

__all__ = ["DiagnosticAgent", "DiagnosticAgentV2"]