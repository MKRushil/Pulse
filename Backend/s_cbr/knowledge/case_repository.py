"""
案例知識庫 v1.0

v1.0 功能：
- 現有 Case 知識庫訪問
- 智能案例檢索
- 案例相似度計算
- 案例品質評估

版本：v1.0
"""

from typing import Dict, Any, List, Optional
from s_cbr.utils.api_manager import SCBRAPIManager
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger
from s_cbr.utils.similarity_calculator import SimilarityCalculator

class CaseRepository:
    """
    案例知識庫 v1.0
    
    v1.0 特色：
    - 整合現有 Case Weaviate 類別
    - 智能相似度匹配
    - 多維度案例評估
    - 案例品質分級
    """
    
    def __init__(self):
        """初始化案例知識庫 v1.0"""
        self.config = SCBRConfig()
        self.api_manager = SCBRAPIManager()
        self.similarity_calculator = SimilarityCalculator()
        self.logger = SpiralLogger.get_logger("CaseRepository")
        self.version = "1.0"
        
        self.logger.info(f"案例知識庫 v{self.version} 初始化完成")
    
    async def search_similar_cases(self, query_vector: List[float],
                                  patient_profile: Dict[str, Any] = None,
                                  filters: Optional[Dict] = None,
                                  limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜尋相似案例 v1.0
        
        在現有 Case 知識庫中搜尋最相似的案例
        """
        self.logger.info(f"搜尋相似案例 - 限制: {limit}")
        
        try:
            # 使用 API 管理器搜尋案例
            similar_cases = await self.api_manager.search_similar_cases(
                query_vector=query_vector,
                filters=filters,
                limit=limit
            )
            
            if not similar_cases:
                self.logger.warning("未找到相似案例")
                return []
            
            # v1.0 增強案例分析
            enhanced_cases = []
            for case in similar_cases:
                enhanced_case = await self._enhance_case_analysis_v1(case, patient_profile)
                enhanced_cases.append(enhanced_case)
            
            # 按相似度排序
            enhanced_cases.sort(key=lambda x: x.get('similarity', 0.0), reverse=True)
            
            self.logger.info(f"找到 {len(enhanced_cases)} 個相似案例")
            
            return enhanced_cases
            
        except Exception as e:
            self.logger.error(f"案例搜尋失敗: {str(e)}")
            return []
    
    async def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """根據 ID 獲取特定案例 v1.0"""
        self.logger.debug(f"獲取案例: {case_id}")
        
        try:
            # 通過 Weaviate 查詢特定案例
            case_config = self.config.get_case_search_config()
            
            query_result = (
                self.api_manager.weaviate_client.query
                .get(case_config['class_name'], case_config['fields'])
                .with_where({
                    "path": ["case_id"],
                    "operator": "Equal",
                    "valueString": case_id
                })
                .with_limit(1)
                .do()
            )
            
            cases = query_result.get("data", {}).get("Get", {}).get(case_config['class_name'], [])
            
            if cases:
                case = cases[0]
                enhanced_case = await self._enhance_case_analysis_v1(case)
                return enhanced_case
            
            return None
            
        except Exception as e:
            self.logger.error(f"獲取案例失敗: {str(e)}")
            return None
    
    async def analyze_case_patterns(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析案例模式 v1.0"""
        self.logger.debug(f"分析 {len(cases)} 個案例的模式")
        
        if not cases:
            return {"patterns": [], "insights": [], "recommendations": []}
        
        patterns_analysis = {
            "demographic_patterns": self._analyze_demographic_patterns(cases),
            "symptom_patterns": self._analyze_symptom_patterns(cases),
            "diagnosis_patterns": self._analyze_diagnosis_patterns(cases),
            "pulse_patterns": self._analyze_pulse_patterns_v1(cases),  # v1.0 新增
            "treatment_patterns": self._analyze_treatment_patterns(cases),
            "outcome_patterns": self._analyze_outcome_patterns(cases)
        }
        
        # 生成洞察
        insights = self._generate_pattern_insights_v1(patterns_analysis)
        
        # 生成建議
        recommendations = self._generate_pattern_recommendations_v1(patterns_analysis, insights)
        
        return {
            "patterns": patterns_analysis,
            "insights": insights,
            "recommendations": recommendations,
            "analysis_confidence": self._calculate_pattern_confidence(patterns_analysis),
            "case_count": len(cases),
            "version": self.version
        }
    
    async def evaluate_case_quality(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """評估案例品質 v1.0"""
        self.logger.debug("評估案例品質")
        
        quality_factors = {
            "completeness": self._evaluate_case_completeness_v1(case),
            "accuracy": self._evaluate_case_accuracy_v1(case),
            "relevance": self._evaluate_case_relevance_v1(case),
            "uniqueness": self._evaluate_case_uniqueness_v1(case),
            "pulse_integration": self._evaluate_pulse_integration_v1(case)  # v1.0 新增
        }
        
        # 計算綜合品質分數
        weights = {
            "completeness": 0.25,
            "accuracy": 0.30,
            "relevance": 0.20,
            "uniqueness": 0.15,
            "pulse_integration": 0.10  # v1.0 脈診整合權重
        }
        
        overall_quality = sum(
            quality_factors[factor] * weights[factor] 
            for factor in quality_factors
        )
        
        # 品質等級
        if overall_quality >= 0.8:
            quality_grade = "excellent"
        elif overall_quality >= 0.6:
            quality_grade = "good"
        elif overall_quality >= 0.4:
            quality_grade = "fair"
        else:
            quality_grade = "poor"
        
        return {
            "quality_factors": quality_factors,
            "overall_quality": overall_quality,
            "quality_grade": quality_grade,
            "improvement_suggestions": self._generate_quality_improvements_v1(quality_factors),
            "version": self.version
        }
    
    async def _enhance_case_analysis_v1(self, case: Dict[str, Any],
                                       patient_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """增強案例分析 v1.0"""
        
        enhanced_case = case.copy()
        
        # 添加案例品質評估
        quality_evaluation = await self.evaluate_case_quality(case)
        enhanced_case["quality_assessment"] = quality_evaluation
        
        # v1.0 添加脈診分析
        pulse_analysis = self._analyze_case_pulse_info_v1(case)
        enhanced_case["pulse_analysis"] = pulse_analysis
        
        # 如果有患者資料，計算個人化相似度
        if patient_profile:
            personalized_similarity = self._calculate_personalized_similarity_v1(
                case, patient_profile
            )
            enhanced_case["personalized_similarity"] = personalized_similarity
        
        # 添加臨床洞察
        clinical_insights = self._generate_clinical_insights_v1(case)
        enhanced_case["clinical_insights"] = clinical_insights
        
        return enhanced_case
    
    def _analyze_case_pulse_info_v1(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """分析案例脈診資訊 v1.0"""
        
        pulse_text = case.get('pulse_text', '')
        pulse_tags = case.get('pulse_tags', [])
        
        if not pulse_text and not pulse_tags:
            return {
                "pulse_info_available": False,
                "pulse_quality": "none",
                "pulse_insights": []
            }
        
        # 分析脈診品質
        pulse_quality = "basic"
        if pulse_text and len(pulse_text) > 10:
            pulse_quality = "detailed"
        elif pulse_tags and len(pulse_tags) > 2:
            pulse_quality = "structured"
        
        # 提取脈診洞察
        pulse_insights = []
        if pulse_text:
            pulse_insights.extend(self._extract_pulse_insights_from_text(pulse_text))
        
        if pulse_tags:
            pulse_insights.extend([f"脈象標籤: {tag}" for tag in pulse_tags[:3]])
        
        return {
            "pulse_info_available": True,
            "pulse_text": pulse_text,
            "pulse_tags": pulse_tags,
            "pulse_quality": pulse_quality,
            "pulse_insights": pulse_insights,
            "pulse_analysis_confidence": self._assess_pulse_analysis_confidence(pulse_text, pulse_tags)
        }
    
    def _calculate_personalized_similarity_v1(self, case: Dict[str, Any],
                                             patient_profile: Dict[str, Any]) -> Dict[str, Any]:
        """計算個人化相似度 v1.0"""
        
        similarity_factors = {}
        
        # 年齡相似度
        case_age = case.get('age')
        patient_age = patient_profile.get('age')
        if case_age and patient_age:
            age_similarity = self.similarity_calculator.calculate_age_similarity(
                int(case_age), int(patient_age)
            )
            similarity_factors["age_similarity"] = age_similarity
        
        # 性別匹配
        gender_match = (case.get('gender') == patient_profile.get('gender'))
        similarity_factors["gender_match"] = 1.0 if gender_match else 0.0
        
        # 症狀相似度
        case_symptoms = case.get('chief_complaint', '') + ' ' + case.get('summary_text', '')
        patient_symptoms = patient_profile.get('chief_complaint', '')
        if case_symptoms and patient_symptoms:
            symptom_similarity = self.similarity_calculator.calculate_text_similarity(
                case_symptoms, patient_symptoms
            )
            similarity_factors["symptom_similarity"] = symptom_similarity
        
        # v1.0 脈診相似度
        case_pulse = case.get('pulse_text', '')
        patient_pulse = patient_profile.get('pulse_info', '')
        if case_pulse and patient_pulse:
            pulse_similarity = self.similarity_calculator.calculate_text_similarity(
                case_pulse, patient_pulse
            )
            similarity_factors["pulse_similarity"] = pulse_similarity
        
        # 綜合相似度計算
        weights = {"age_similarity": 0.2, "gender_match": 0.2, "symptom_similarity": 0.4, "pulse_similarity": 0.2}
        overall_similarity = sum(
            similarity_factors.get(factor, 0.5) * weight 
            for factor, weight in weights.items()
        )
        
        return {
            "similarity_factors": similarity_factors,
            "overall_similarity": overall_similarity,
            "similarity_confidence": self._assess_similarity_confidence(similarity_factors)
        }
    
    # 模式分析方法
    def _analyze_demographic_patterns(self, cases: List[Dict]) -> Dict[str, Any]:
        """分析人口統計學模式"""
        ages = [int(case.get('age', 0)) for case in cases if case.get('age') and case['age'].isdigit()]
        genders = [case.get('gender', '') for case in cases if case.get('gender')]
        
        return {
            "age_distribution": {
                "mean": sum(ages) / len(ages) if ages else 0,
                "range": [min(ages), max(ages)] if ages else [0, 0],
                "count": len(ages)
            },
            "gender_distribution": {
                "male": genders.count('男'),
                "female": genders.count('女'),
                "total": len(genders)
            }
        }
    
    def _analyze_symptom_patterns(self, cases: List[Dict]) -> Dict[str, Any]:
        """分析症狀模式"""
        all_complaints = []
        for case in cases:
            complaint = case.get('chief_complaint', '')
            if complaint:
                all_complaints.append(complaint)
        
        # 簡單的關鍵詞頻率分析
        symptom_keywords = {}
        common_symptoms = ['頭痛', '失眠', '疲勞', '胸悶', '咳嗽', '腹痛', '眩暈']
        
        for symptom in common_symptoms:
            count = sum(1 for complaint in all_complaints if symptom in complaint)
            if count > 0:
                symptom_keywords[symptom] = count
        
        return {
            "total_cases_with_symptoms": len(all_complaints),
            "common_symptoms": symptom_keywords,
            "most_frequent_symptom": max(symptom_keywords.items(), key=lambda x: x[1]) if symptom_keywords else None
        }
    
    def _analyze_diagnosis_patterns(self, cases: List[Dict]) -> Dict[str, Any]:
        """分析診斷模式"""
        diagnoses = [case.get('diagnosis_main', '') for case in cases if case.get('diagnosis_main')]
        
        diagnosis_frequency = {}
        for diagnosis in diagnoses:
            if diagnosis:
                diagnosis_frequency[diagnosis] = diagnosis_frequency.get(diagnosis, 0) + 1
        
        return {
            "total_diagnoses": len(diagnoses),
            "unique_diagnoses": len(diagnosis_frequency),
            "diagnosis_frequency": diagnosis_frequency,
            "most_common_diagnosis": max(diagnosis_frequency.items(), key=lambda x: x[1]) if diagnosis_frequency else None
        }
    
    def _analyze_pulse_patterns_v1(self, cases: List[Dict]) -> Dict[str, Any]:
        """分析脈診模式 v1.0"""
        pulse_info_available = sum(1 for case in cases if case.get('pulse_text') or case.get('pulse_tags'))
        pulse_texts = [case.get('pulse_text', '') for case in cases if case.get('pulse_text')]
        pulse_tags_all = []
        for case in cases:
            tags = case.get('pulse_tags', [])
            if isinstance(tags, list):
                pulse_tags_all.extend(tags)
        
        # 脈象關鍵詞分析
        pulse_patterns = ['浮', '沉', '遲', '數', '滑', '澀', '弦', '緩']
        pulse_frequency = {}
        
        for pattern in pulse_patterns:
            count = sum(1 for text in pulse_texts if pattern in text)
            count += pulse_tags_all.count(pattern)
            if count > 0:
                pulse_frequency[pattern] = count
        
        return {
            "cases_with_pulse_info": pulse_info_available,
            "pulse_coverage": pulse_info_available / len(cases) if cases else 0,
            "pulse_pattern_frequency": pulse_frequency,
            "most_common_pulse": max(pulse_frequency.items(), key=lambda x: x[1]) if pulse_frequency else None,
            "pulse_info_quality": "good" if pulse_info_available > len(cases) * 0.7 else "limited"
        }
    
    def _analyze_treatment_patterns(self, cases: List[Dict]) -> Dict[str, Any]:
        """分析治療模式"""
        treatments = [case.get('llm_struct', '') for case in cases if case.get('llm_struct')]
        
        return {
            "cases_with_treatment": len(treatments),
            "treatment_coverage": len(treatments) / len(cases) if cases else 0,
            "average_treatment_length": sum(len(t) for t in treatments) / len(treatments) if treatments else 0
        }
    
    def _analyze_outcome_patterns(self, cases: List[Dict]) -> Dict[str, Any]:
        """分析結果模式"""
        # 由於現有 Case schema 沒有結果欄位，返回基礎分析
        return {
            "outcome_data_available": False,
            "recommendation": "建議在案例中添加治療結果追蹤"
        }
    
    # 品質評估方法
    def _evaluate_case_completeness_v1(self, case: Dict[str, Any]) -> float:
        """評估案例完整性 v1.0"""
        required_fields = ['case_id', 'age', 'gender', 'chief_complaint', 'diagnosis_main']
        optional_fields = ['present_illness', 'pulse_text', 'summary_text', 'llm_struct']
        
        required_score = sum(1 for field in required_fields if case.get(field)) / len(required_fields)
        optional_score = sum(1 for field in optional_fields if case.get(field)) / len(optional_fields)
        
        return required_score * 0.7 + optional_score * 0.3
    
    def _evaluate_case_accuracy_v1(self, case: Dict[str, Any]) -> float:
        """評估案例準確性 v1.0"""
        # 簡化實現：基於資料一致性
        consistency_score = 0.8  # 預設高一致性
        
        # 檢查年齡合理性
        age = case.get('age')
        if age and age.isdigit():
            age_num = int(age)
            if not (0 <= age_num <= 120):
                consistency_score -= 0.1
        
        # 檢查性別有效性
        gender = case.get('gender')
        if gender and gender not in ['男', '女']:
            consistency_score -= 0.1
        
        return max(0.0, consistency_score)
    
    def _evaluate_case_relevance_v1(self, case: Dict[str, Any]) -> float:
        """評估案例相關性 v1.0"""
        # 基於案例資訊豐富度
        relevance = 0.5
        
        if case.get('chief_complaint'):
            relevance += 0.2
        if case.get('diagnosis_main'):
            relevance += 0.2
        if case.get('pulse_text'):
            relevance += 0.1
        
        return min(1.0, relevance)
    
    def _evaluate_case_uniqueness_v1(self, case: Dict[str, Any]) -> float:
        """評估案例獨特性 v1.0"""
        # 簡化實現：基於資訊多樣性
        unique_factors = 0
        
        if case.get('present_illness'):
            unique_factors += 1
        if case.get('pulse_text'):
            unique_factors += 1
        if case.get('inquiry_tags'):
            unique_factors += 1
        if case.get('inspection_tags'):
            unique_factors += 1
        
        return min(1.0, unique_factors / 4.0)
    
    def _evaluate_pulse_integration_v1(self, case: Dict[str, Any]) -> float:
        """評估脈診整合 v1.0"""
        pulse_score = 0.0
        
        if case.get('pulse_text'):
            pulse_score += 0.5
        if case.get('pulse_tags'):
            pulse_score += 0.3
        if case.get('pulse_text') and len(case['pulse_text']) > 20:
            pulse_score += 0.2
        
        return pulse_score
    
    # 輔助方法
    def _generate_pattern_insights_v1(self, patterns: Dict[str, Any]) -> List[str]:
        """生成模式洞察 v1.0"""
        insights = []
        
        # 人口統計學洞察
        demo = patterns.get('demographic_patterns', {})
        if demo.get('age_distribution', {}).get('count', 0) > 0:
            mean_age = demo['age_distribution']['mean']
            insights.append(f"病例平均年齡為 {mean_age:.1f} 歲")
        
        # v1.0 脈診洞察
        pulse = patterns.get('pulse_patterns', {})
        if pulse.get('pulse_coverage', 0) > 0.5:
            insights.append(f"脈診資訊覆蓋率達 {pulse['pulse_coverage']:.1%}")
        
        if pulse.get('most_common_pulse'):
            common_pulse = pulse['most_common_pulse'][0]
            insights.append(f"最常見的脈象是 {common_pulse}")
        
        return insights
    
    def _generate_pattern_recommendations_v1(self, patterns: Dict[str, Any], insights: List[str]) -> List[str]:
        """生成模式建議 v1.0"""
        recommendations = []
        
        pulse = patterns.get('pulse_patterns', {})
        if pulse.get('pulse_coverage', 0) < 0.5:
            recommendations.append("建議增加脈診資訊的記錄以提升案例品質")
        
        treatment = patterns.get('treatment_patterns', {})
        if treatment.get('treatment_coverage', 0) < 0.8:
            recommendations.append("建議完善治療方案資訊記錄")
        
        return recommendations
    
    def _calculate_pattern_confidence(self, patterns: Dict[str, Any]) -> float:
        """計算模式分析信心度"""
        # 基於資料完整性和樣本大小
        return 0.8  # 簡化實現
    
    def _generate_quality_improvements_v1(self, quality_factors: Dict[str, float]) -> List[str]:
        """生成品質改進建議 v1.0"""
        improvements = []
        
        if quality_factors.get('completeness', 0) < 0.7:
            improvements.append("補充必要的基礎資訊欄位")
        
        if quality_factors.get('pulse_integration', 0) < 0.5:
            improvements.append("增加脈診相關資訊")
        
        if quality_factors.get('uniqueness', 0) < 0.5:
            improvements.append("豐富案例詳細描述")
        
        return improvements
    
    def _generate_clinical_insights_v1(self, case: Dict[str, Any]) -> List[str]:
        """生成臨床洞察 v1.0"""
        insights = []
        
        diagnosis = case.get('diagnosis_main', '')
        if diagnosis:
            insights.append(f"主要診斷：{diagnosis}")
        
        pulse_text = case.get('pulse_text', '')
        if pulse_text:
            insights.append(f"脈診特徵：{pulse_text[:50]}...")
        
        return insights
    
    def _extract_pulse_insights_from_text(self, pulse_text: str) -> List[str]:
        """從脈診文字中提取洞察"""
        insights = []
        pulse_keywords = ['浮', '沉', '遲', '數', '滑', '澀', '弦', '緩', '細', '洪']
        
        for keyword in pulse_keywords:
            if keyword in pulse_text:
                insights.append(f"脈象特徵: {keyword}脈")
        
        return insights[:3]  # 返回前3個
    
    def _assess_pulse_analysis_confidence(self, pulse_text: str, pulse_tags: List) -> float:
        """評估脈診分析信心度"""
        confidence = 0.0
        
        if pulse_text:
            confidence += 0.6
        if pulse_tags:
            confidence += 0.4
        
        return confidence
    
    def _assess_similarity_confidence(self, similarity_factors: Dict) -> float:
        """評估相似度計算信心度"""
        available_factors = sum(1 for factor, value in similarity_factors.items() if value is not None)
        total_factors = len(similarity_factors)
        
        return available_factors / total_factors if total_factors > 0 else 0.0
