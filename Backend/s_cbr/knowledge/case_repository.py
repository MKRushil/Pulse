"""
案例知識庫管理器 v2.0

管理中醫案例的檢索、存儲與更新
支援案例過濾與智能排除功能

版本：v2.0 - 螺旋互動版
更新：支援排除已用案例的智能檢索
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
    from ..utils.api_manager import SCBRAPIManager
    from ..knowledge.pulse_repository import PulseRepository
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    SCBRAPIManager = None
    PulseRepository = None

class CaseRepository:
    """
    中醫案例知識庫管理器 v2.0
    
    v2.0 特色：
    - 智能案例過濾與排除
    - 多維度相似度計算
    - 案例品質評估
    - 動態案例推薦
    """
    
    def __init__(self):
        """初始化案例知識庫管理器 v2.0"""
        self.logger = SpiralLogger.get_logger("CaseRepository") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("CaseRepository")
        self.version = "2.0"
        
        # 初始化相關組件
        self.api_manager = SCBRAPIManager() if SCBRAPIManager else None
        self.pulse_repository = PulseRepository() if PulseRepository else None
        
        # v2.0 檢索參數
        self.similarity_weights = {
            "symptom_similarity": 0.35,
            "demographic_similarity": 0.15,
            "constitution_similarity": 0.20,
            "pulse_similarity": 0.20,
            "severity_similarity": 0.10
        }
        
        self.quality_thresholds = {
            "excellent": 0.85,
            "good": 0.70,
            "acceptable": 0.55,
            "poor": 0.40
        }
        
        # 模擬案例數據庫（實際應連接真實數據庫）
        self._mock_cases = self._initialize_mock_cases()
        
        self.logger.info(f"案例知識庫管理器 v{self.version} 初始化完成")
    
    async def get_similar_cases_v2(self, 
                                 query: str,
                                 patient_context: Optional[Dict[str, Any]] = None,
                                 exclude_cases: Optional[List[str]] = None,
                                 max_results: int = 10) -> List[Dict[str, Any]]:
        """
        獲取相似案例 v2.0 - 支援排除已用案例
        
        Args:
            query: 查詢字符串（症狀描述）
            patient_context: 患者上下文信息
            exclude_cases: 要排除的案例ID列表
            max_results: 最大返回結果數
            
        Returns:
            List[Dict[str, Any]]: 相似案例列表，按相似度排序
        """
        try:
            self.logger.info(f"開始案例檢索 v2.0 - 查詢: {query[:50]}...")
            if exclude_cases:
                self.logger.info(f"排除案例數量: {len(exclude_cases)}")
            
            # 1. 基礎案例檢索
            candidate_cases = await self._retrieve_candidate_cases(query, patient_context)
            
            # 2. 過濾排除案例
            filtered_cases = self._filter_excluded_cases(candidate_cases, exclude_cases or [])
            
            # 3. 計算相似度評分
            scored_cases = await self._calculate_similarity_scores_v2(
                filtered_cases, query, patient_context
            )
            
            # 4. 案例品質評估
            quality_assessed_cases = await self._assess_case_quality_v2(scored_cases)
            
            # 5. 智能排序與篩選
            final_cases = await self._intelligent_ranking_v2(
                quality_assessed_cases, query, patient_context, max_results
            )
            
            # 6. 豐富案例信息
            enriched_cases = await self._enrich_case_information_v2(final_cases)
            
            self.logger.info(f"案例檢索 v2.0 完成 - 返回 {len(enriched_cases)} 個案例")
            
            return enriched_cases
            
        except Exception as e:
            self.logger.error(f"案例檢索 v2.0 失敗: {str(e)}")
            return await self._create_fallback_cases_v2(query, exclude_cases or [])
    
    def _filter_excluded_cases(self, cases: List[Dict], exclude_cases: List[str]) -> List[Dict]:
        """
        過濾排除的案例
        
        Args:
            cases: 候選案例列表
            exclude_cases: 要排除的案例ID列表
            
        Returns:
            List[Dict]: 過濾後的案例列表
        """
        if not exclude_cases:
            return cases
        
        exclude_set = set(exclude_cases)
        filtered_cases = []
        
        for case in cases:
            case_id = case.get("id") or case.get("case_id")
            if case_id not in exclude_set:
                filtered_cases.append(case)
        
        self.logger.info(f"案例過濾: {len(cases)} → {len(filtered_cases)} (排除 {len(exclude_cases)} 個)")
        
        return filtered_cases
    
    async def _retrieve_candidate_cases(self, query: str, patient_context: Optional[Dict]) -> List[Dict]:
        """
        檢索候選案例
        
        Returns:
            List[Dict]: 候選案例列表
        """
        # 實際實現應該連接真實的案例數據庫
        # 這裡使用模擬數據
        
        # 基於查詢關鍵詞過濾案例
        query_keywords = self._extract_keywords(query)
        candidate_cases = []
        
        for case in self._mock_cases:
            if self._case_matches_query(case, query_keywords, patient_context):
                candidate_cases.append(case.copy())
        
        return candidate_cases
    
    async def _calculate_similarity_scores_v2(self, 
                                            cases: List[Dict], 
                                            query: str, 
                                            patient_context: Optional[Dict]) -> List[Dict]:
        """
        計算相似度評分 v2.0 - 多維度評分
        
        Returns:
            List[Dict]: 帶有相似度評分的案例列表
        """
        scored_cases = []
        
        for case in cases:
            # 計算各維度相似度
            symptom_sim = await self._calculate_symptom_similarity(case, query)
            demographic_sim = await self._calculate_demographic_similarity(case, patient_context)
            constitution_sim = await self._calculate_constitution_similarity(case, patient_context)
            pulse_sim = await self._calculate_pulse_similarity_v2(case, patient_context)
            severity_sim = await self._calculate_severity_similarity(case, query)
            
            # 加權計算總相似度
            total_similarity = (
                symptom_sim * self.similarity_weights["symptom_similarity"] +
                demographic_sim * self.similarity_weights["demographic_similarity"] +
                constitution_sim * self.similarity_weights["constitution_similarity"] +
                pulse_sim * self.similarity_weights["pulse_similarity"] +
                severity_sim * self.similarity_weights["severity_similarity"]
            )
            
            # 添加詳細評分信息
            case["similarity"] = total_similarity
            case["similarity_details"] = {
                "symptom_similarity": symptom_sim,
                "demographic_similarity": demographic_sim,
                "constitution_similarity": constitution_sim,
                "pulse_similarity": pulse_sim,
                "severity_similarity": severity_sim,
                "total_similarity": total_similarity
            }
            
            scored_cases.append(case)
        
        return scored_cases
    
    async def _assess_case_quality_v2(self, cases: List[Dict]) -> List[Dict]:
        """
        評估案例品質 v2.0
        
        Returns:
            List[Dict]: 帶有品質評估的案例列表
        """
        for case in cases:
            # 品質評估維度
            completeness = self._assess_case_completeness(case)
            reliability = self._assess_case_reliability(case)
            clinical_value = self._assess_clinical_value(case)
            data_quality = self._assess_data_quality(case)
            
            # 計算綜合品質評分
            quality_score = (
                completeness * 0.3 +
                reliability * 0.3 +
                clinical_value * 0.25 +
                data_quality * 0.15
            )
            
            # 品質等級判定
            if quality_score >= self.quality_thresholds["excellent"]:
                quality_level = "優秀"
            elif quality_score >= self.quality_thresholds["good"]:
                quality_level = "良好"
            elif quality_score >= self.quality_thresholds["acceptable"]:
                quality_level = "可接受"
            else:
                quality_level = "待改善"
            
            case["quality_score"] = quality_score
            case["quality_level"] = quality_level
            case["quality_details"] = {
                "completeness": completeness,
                "reliability": reliability,
                "clinical_value": clinical_value,
                "data_quality": data_quality
            }
        
        return cases
    
    async def _intelligent_ranking_v2(self, 
                                    cases: List[Dict], 
                                    query: str, 
                                    patient_context: Optional[Dict],
                                    max_results: int) -> List[Dict]:
        """
        智能排序與篩選 v2.0
        
        Returns:
            List[Dict]: 排序後的案例列表
        """
        # 綜合評分：相似度 + 品質評分
        for case in cases:
            similarity_score = case.get("similarity", 0.0)
            quality_score = case.get("quality_score", 0.0)
            
            # 綜合評分權重
            composite_score = similarity_score * 0.7 + quality_score * 0.3
            
            # 添加多樣性加成（避免過度相似的案例）
            diversity_bonus = await self._calculate_diversity_bonus(case, cases)
            
            case["composite_score"] = composite_score + diversity_bonus
            case["diversity_bonus"] = diversity_bonus
        
        # 按綜合評分排序
        sorted_cases = sorted(cases, key=lambda x: x.get("composite_score", 0.0), reverse=True)
        
        # 返回前 max_results 個案例
        return sorted_cases[:max_results]
    
    async def _enrich_case_information_v2(self, cases: List[Dict]) -> List[Dict]:
        """
        豐富案例信息 v2.0
        
        Returns:
            List[Dict]: 信息豐富的案例列表
        """
        enriched_cases = []
        
        for case in cases:
            # 添加推薦理由
            recommendation_reason = await self._generate_recommendation_reason(case)
            
            # 添加使用建議
            usage_suggestions = await self._generate_usage_suggestions(case)
            
            # 添加相關脈診信息
            pulse_insights = await self._get_pulse_insights_v2(case)
            
            # 標準化案例格式
            enriched_case = {
                "id": case.get("id", f"case_{hash(str(case))}"),
                "title": case.get("title", "中醫診療案例"),
                "summary": case.get("summary", case.get("description", "")),
                "diagnosis": case.get("diagnosis", ""),
                "treatment": case.get("treatment", ""),
                "symptoms": case.get("symptoms", []),
                "patient_info": case.get("patient_info", {}),
                "pulse_info": case.get("pulse_info", {}),
                "outcome": case.get("outcome", ""),
                "similarity": case.get("similarity", 0.0),
                "similarity_details": case.get("similarity_details", {}),
                "quality_score": case.get("quality_score", 0.0),
                "quality_level": case.get("quality_level", ""),
                "composite_score": case.get("composite_score", 0.0),
                "recommendation_reason": recommendation_reason,
                "usage_suggestions": usage_suggestions,
                "pulse_insights": pulse_insights,
                "retrieval_timestamp": datetime.now().isoformat(),
                "version": self.version
            }
            
            enriched_cases.append(enriched_case)
        
        return enriched_cases
    
    # 輔助方法實現
    def _extract_keywords(self, query: str) -> List[str]:
        """提取查詢關鍵詞"""
        # 簡化實現：基於常見中醫術語
        keywords = []
        common_terms = [
            "頭痛", "失眠", "疲勞", "焦慮", "抑鬱", "胃痛", "腹瀉", "便秘",
            "咳嗽", "感冒", "發熱", "盗汗", "心悸", "氣短", "腰痛", "關節痛"
        ]
        
        for term in common_terms:
            if term in query:
                keywords.append(term)
        
        return keywords if keywords else ["general"]
    
    def _case_matches_query(self, case: Dict, keywords: List[str], patient_context: Optional[Dict]) -> bool:
        """判斷案例是否匹配查詢"""
        case_text = f"{case.get('diagnosis', '')} {case.get('symptoms', '')} {case.get('summary', '')}"
        
        # 關鍵詞匹配
        for keyword in keywords:
            if keyword in case_text:
                return True
        
        return len(keywords) == 0 or "general" in keywords
    
    async def _calculate_symptom_similarity(self, case: Dict, query: str) -> float:
        """計算症狀相似度"""
        case_symptoms = case.get("symptoms", [])
        query_lower = query.lower()
        
        if not case_symptoms:
            return 0.5
        
        # 簡化實現：關鍵詞匹配
        matches = sum(1 for symptom in case_symptoms if symptom.lower() in query_lower)
        return min(1.0, matches / len(case_symptoms) + 0.3)
    
    async def _calculate_demographic_similarity(self, case: Dict, patient_context: Optional[Dict]) -> float:
        """計算人口統計學相似度"""
        if not patient_context:
            return 0.5
        
        case_patient = case.get("patient_info", {})
        similarity = 0.5
        
        # 年齡相似度
        if "age" in patient_context and "age" in case_patient:
            age_diff = abs(patient_context["age"] - case_patient["age"])
            age_similarity = max(0, 1 - age_diff / 50)
            similarity += age_similarity * 0.3
        
        # 性別匹配
        if "gender" in patient_context and "gender" in case_patient:
            if patient_context["gender"] == case_patient["gender"]:
                similarity += 0.2
        
        return min(1.0, similarity)
    
    async def _calculate_constitution_similarity(self, case: Dict, patient_context: Optional[Dict]) -> float:
        """計算體質相似度"""
        # 簡化實現
        return 0.7
    
    async def _calculate_pulse_similarity_v2(self, case: Dict, patient_context: Optional[Dict]) -> float:
        """計算脈診相似度 v2.0"""
        if not patient_context or not patient_context.get("pulse_text"):
            return 0.5
        
        case_pulse = case.get("pulse_info", {})
        patient_pulse = patient_context.get("pulse_text", "")
        
        if not case_pulse:
            return 0.5
        
        # 簡化實現：基於脈診描述的文本相似度
        case_pulse_text = case_pulse.get("description", "")
        if not case_pulse_text:
            return 0.5
        
        # 計算文本相似度
        similarity = self._calculate_text_similarity(patient_pulse, case_pulse_text)
        return similarity
    
    async def _calculate_severity_similarity(self, case: Dict, query: str) -> float:
        """計算嚴重程度相似度"""
        # 簡化實現
        return 0.6
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """計算文本相似度"""
        set1 = set(text1.replace(" ", "").lower())
        set2 = set(text2.replace(" ", "").lower())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _assess_case_completeness(self, case: Dict) -> float:
        """評估案例完整性"""
        required_fields = ["diagnosis", "treatment", "symptoms", "patient_info"]
        present_fields = sum(1 for field in required_fields if case.get(field))
        return present_fields / len(required_fields)
    
    def _assess_case_reliability(self, case: Dict) -> float:
        """評估案例可靠性"""
        # 簡化實現：基於數據來源和驗證狀態
        return case.get("reliability_score", 0.8)
    
    def _assess_clinical_value(self, case: Dict) -> float:
        """評估臨床價值"""
        # 簡化實現：基於治療效果和典型性
        return case.get("clinical_value", 0.75)
    
    def _assess_data_quality(self, case: Dict) -> float:
        """評估數據品質"""
        # 簡化實現：基於數據格式和一致性
        return 0.8
    
    async def _calculate_diversity_bonus(self, case: Dict, all_cases: List[Dict]) -> float:
        """計算多樣性加成"""
        # 簡化實現：避免選擇過度相似的案例
        return 0.05
    
    async def _generate_recommendation_reason(self, case: Dict) -> str:
        """生成推薦理由"""
        similarity = case.get("similarity", 0.0)
        quality_level = case.get("quality_level", "")
        
        if similarity >= 0.8 and quality_level == "優秀":
            return "高度相似且案例品質優秀，強烈推薦參考"
        elif similarity >= 0.7:
            return "症狀相似度較高，適合作為參考案例"
        elif quality_level in ["優秀", "良好"]:
            return "案例品質良好，可作為診療參考"
        else:
            return "具有一定參考價值的相關案例"
    
    async def _generate_usage_suggestions(self, case: Dict) -> List[str]:
        """生成使用建議"""
        suggestions = []
        similarity = case.get("similarity", 0.0)
        quality_score = case.get("quality_score", 0.0)
        
        if similarity >= 0.8:
            suggestions.append("可直接參考診斷思路")
        
        if quality_score >= 0.8:
            suggestions.append("治療方案值得借鑒")
        
        if case.get("pulse_info"):
            suggestions.append("注意脈診特徵對比")
        
        suggestions.append("結合患者具體情況進行適配")
        
        return suggestions
    
    async def _get_pulse_insights_v2(self, case: Dict) -> Dict[str, Any]:
        """獲取脈診洞察 v2.0"""
        pulse_info = case.get("pulse_info", {})
        
        if not pulse_info:
            return {"available": False}
        
        return {
            "available": True,
            "pulse_type": pulse_info.get("type", ""),
            "characteristics": pulse_info.get("characteristics", []),
            "clinical_significance": pulse_info.get("significance", ""),
            "diagnostic_value": pulse_info.get("diagnostic_value", 0.7)
        }
    
    def _initialize_mock_cases(self) -> List[Dict]:
        """初始化模擬案例數據"""
        return [
            {
                "id": "case_001",
                "title": "肝鬱氣滯型頭痛失眠案例",
                "summary": "35歲女性，工作壓力大，頭痛失眠2週",
                "diagnosis": "肝鬱氣滯，心神不寧",
                "treatment": "疏肝解鬱，養心安神。方用甘麥大棗湯合逍遙散加減",
                "symptoms": ["頭痛", "失眠", "煩躁", "胸悶"],
                "patient_info": {"age": 35, "gender": "女", "occupation": "白領"},
                "pulse_info": {"type": "弦脈", "characteristics": ["弦細", "略數"], "significance": "肝鬱氣滯"},
                "outcome": "治療2週後症狀明顯改善",
                "reliability_score": 0.9,
                "clinical_value": 0.85
            },
            {
                "id": "case_002", 
                "title": "脾胃虛弱型失眠案例",
                "summary": "42歲男性，消化不良伴失眠",
                "diagnosis": "脾胃虛弱，心神失養",
                "treatment": "健脾益氣，養心安神。方用歸脾湯加減",
                "symptoms": ["失眠", "多夢", "食慾不振", "腹脹"],
                "patient_info": {"age": 42, "gender": "男", "constitution": "氣虛質"},
                "pulse_info": {"type": "細脈", "characteristics": ["細弱", "略緩"], "significance": "氣血不足"},
                "outcome": "治療3週後睡眠質量改善",
                "reliability_score": 0.85,
                "clinical_value": 0.8
            },
            {
                "id": "case_003",
                "title": "陰虛火旺型頭痛案例", 
                "summary": "28歲女性，偏頭痛伴心煩",
                "diagnosis": "陰虛火旺，肝陽上亢",
                "treatment": "滋陰降火，平肝潛陽。方用天麻鉤藤飲加減",
                "symptoms": ["偏頭痛", "心煩", "口乾", "潮熱"],
                "patient_info": {"age": 28, "gender": "女", "constitution": "陰虛質"},
                "pulse_info": {"type": "細數脈", "characteristics": ["細", "數", "弦"], "significance": "陰虛火旺"},
                "outcome": "治療4週後頭痛發作減少",
                "reliability_score": 0.88,
                "clinical_value": 0.82
            }
        ]
    
    async def _create_fallback_cases_v2(self, query: str, exclude_cases: List[str]) -> List[Dict]:
        """創建降級案例 v2.0"""
        fallback_cases = []
        
        # 生成基本的降級案例
        for i in range(1, 4):
            case_id = f"fallback_case_{i}"
            if case_id not in exclude_cases:
                fallback_cases.append({
                    "id": case_id,
                    "title": f"相關案例 {i}",
                    "summary": f"與查詢相關的中醫案例 {i}",
                    "diagnosis": "辨證論治",
                    "treatment": "因證施治",
                    "similarity": max(0.3, 0.7 - i * 0.1),
                    "quality_score": 0.6,
                    "quality_level": "可接受",
                    "recommendation_reason": "降級推薦案例",
                    "fallback": True,
                    "version": self.version
                })
        
        return fallback_cases
    
    # 向後兼容方法（v1.0）
    async def get_similar_cases(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """向後兼容的相似案例檢索"""
        return await self.get_similar_cases_v2(query, None, None, 10)
    
    async def add_case(self, case_data: Dict[str, Any]) -> bool:
        """添加案例（向後兼容）"""
        try:
            # 簡化實現：添加到模擬數據庫
            case_data["id"] = f"user_case_{len(self._mock_cases) + 1}"
            self._mock_cases.append(case_data)
            self.logger.info(f"添加案例成功: {case_data['id']}")
            return True
        except Exception as e:
            self.logger.error(f"添加案例失敗: {str(e)}")
            return False
    
    async def remove_case(self, case_id: str) -> bool:
        """移除案例（向後兼容）"""
        try:
            self._mock_cases = [case for case in self._mock_cases if case.get("id") != case_id]
            self.logger.info(f"移除案例成功: {case_id}")
            return True
        except Exception as e:
            self.logger.error(f"移除案例失敗: {str(e)}")
            return False

# 向後兼容的類別名稱
CaseRepositoryV2 = CaseRepository

__all__ = ["CaseRepository", "CaseRepositoryV2"]