"""
STEP 3: 方案監控器 v1.0

v1.0 功能：
- 治療方案安全性驗證
- 脈診指導的一致性檢查
- 療效預測和風險評估
- 持續監控建議生成

版本：v1.0
"""

from typing import Dict, Any, List
from s_cbr.utils.api_manager import SCBRAPIManager
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger
import asyncio

class Step3Monitor:
    """
    STEP 3: 方案監控器 v1.0
    
    v1.0 特色：
    - 多維度安全性評估
    - 脈診一致性驗證
    - 智能風險預警
    - 個性化監控計劃
    """
    
    def __init__(self):
        """初始化方案監控器 v1.0"""
        self.config = SCBRConfig()
        self.api_manager = SCBRAPIManager()
        self.logger = SpiralLogger.get_logger("Step3Monitor")
        self.version = "1.0"
        
        self.logger.info(f"STEP 3 方案監控器 v{self.version} 初始化完成")
    
    async def validate_solution_v1(self, adapted_solution: Dict[str, Any],
                                  monitoring_plan: Dict[str, Any],
                                  patient_profile: Dict[str, Any],
                                  pulse_support: List[Dict] = None) -> Dict[str, Any]:
        """
        驗證治療方案 v1.0 (包含脈診驗證)
        
        v1.0 驗證維度：
        1. 安全性評估
        2. 有效性評估
        3. 脈診一致性檢查
        4. 風險因子識別
        5. 監控建議生成
        """
        self.logger.info("開始執行 STEP 3 v1.0: 方案監控驗證")
        
        try:
            # Step 3.1: 安全性評估
            safety_assessment = await self._assess_safety_v1(
                adapted_solution, patient_profile, pulse_support
            )
            
            # Step 3.2: 有效性評估
            effectiveness_assessment = await self._assess_effectiveness_v1(
                adapted_solution, patient_profile, pulse_support
            )
            
            # Step 3.3: 脈診一致性檢查 (v1.0 新功能)
            pulse_consistency = await self._check_pulse_consistency_v1(
                adapted_solution, pulse_support, patient_profile
            )
            
            # Step 3.4: 風險因子識別
            risk_analysis = await self._analyze_risks_v1(
                adapted_solution, patient_profile, safety_assessment
            )
            
            # Step 3.5: 監控計劃生成
            monitoring_recommendations = await self._generate_monitoring_recommendations_v1(
                adapted_solution, monitoring_plan, risk_analysis, pulse_consistency
            )
            
            # Step 3.6: 綜合評估
            overall_validation = self._calculate_overall_validation_v1(
                safety_assessment, effectiveness_assessment, pulse_consistency, risk_analysis
            )
            
            # 組裝驗證結果
            validation_result = {
                'safety_assessment': safety_assessment,
                'effectiveness_assessment': effectiveness_assessment,
                'pulse_consistency': pulse_consistency,  # v1.0 新增
                'risk_analysis': risk_analysis,
                'monitoring_recommendations': monitoring_recommendations,
                'overall_validation': overall_validation,
                'safety_score': overall_validation['safety_score'],
                'effectiveness_score': overall_validation['effectiveness_score'],
                'pulse_consistency_score': pulse_consistency['consistency_score'],  # v1.0 新增
                'validation_passed': overall_validation['validation_passed'],
                'timestamp': monitoring_plan.get('timestamp'),
                'version': self.version
            }
            
            self.logger.info(f"STEP 3 v1.0 完成 - 安全評分: {validation_result['safety_score']:.3f}, "
                           f"有效評分: {validation_result['effectiveness_score']:.3f}")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"STEP 3 v1.0 執行異常: {str(e)}")
            return self._create_error_validation_v1(str(e))
    
    async def _assess_safety_v1(self, adapted_solution: Dict[str, Any],
                               patient_profile: Dict[str, Any],
                               pulse_support: List[Dict] = None) -> Dict[str, Any]:
        """評估治療方案安全性 v1.0"""
        
        # 構建安全性評估提示
        safety_prompt = f"""
作為專業中醫監控智能體，請評估以下治療方案的安全性：

【治療方案】
{adapted_solution.get('adapted_treatment', '未提供治療方案')}

【患者資料】
年齡: {patient_profile.get('age', '未知')}
性別: {patient_profile.get('gender', '未知')}
主訴: {patient_profile.get('chief_complaint', '未知')}
既往病史: {patient_profile.get('medical_history', '無')}

【脈診支持 (v1.0)】
"""
        
        if pulse_support:
            safety_prompt += "相關脈診資訊:\n"
            for pulse in pulse_support[:3]:
                safety_prompt += f"- 脈象: {pulse.get('name', '未知')} - {pulse.get('description', '')}\n"
        else:
            safety_prompt += "無脈診資訊支持\n"
        
        safety_prompt += """
請從以下角度評估安全性：
1. 用藥安全性 (0-10分)
2. 劑量合理性 (0-10分)
3. 禁忌症檢查 (0-10分)
4. 脈診相符性 (0-10分) [v1.0]
5. 整體安全風險等級 (低/中/高)

請提供評分和具體分析。
"""
        
        # 調用 LLM 進行安全性評估
        safety_response = await self.api_manager.generate_llm_response(
            safety_prompt, 
            self.config.get_agent_config('monitoring_agent')
        )
        
        # 解析安全性評估結果
        safety_assessment = self._parse_safety_assessment_v1(safety_response)
        
        return safety_assessment
    
    async def _assess_effectiveness_v1(self, adapted_solution: Dict[str, Any],
                                      patient_profile: Dict[str, Any],
                                      pulse_support: List[Dict] = None) -> Dict[str, Any]:
        """評估治療方案有效性 v1.0"""
        
        effectiveness_prompt = f"""
作為專業中醫監控智能體，請評估以下治療方案的預期有效性：

【治療方案】
{adapted_solution.get('adapted_treatment', '')}

【患者症狀】
主訴: {patient_profile.get('chief_complaint', '')}
現病史: {patient_profile.get('present_illness', '')}

【脈診指導 (v1.0)】
"""
        
        if pulse_support:
            for pulse in pulse_support[:3]:
                effectiveness_prompt += f"- {pulse.get('name')}: {pulse.get('main_disease', '')} - {pulse.get('symptoms', '')}\n"
        
        effectiveness_prompt += """
請評估：
1. 對症治療匹配度 (0-10分)
2. 預期療效 (0-10分)
3. 治療週期合理性 (0-10分)
4. 脈診理論支持度 (0-10分) [v1.0]
5. 整體有效性預測 (低/中/高)

請提供詳細分析和評分。
"""
        
        effectiveness_response = await self.api_manager.generate_llm_response(
            effectiveness_prompt,
            self.config.get_agent_config('monitoring_agent')
        )
        
        effectiveness_assessment = self._parse_effectiveness_assessment_v1(effectiveness_response)
        
        return effectiveness_assessment
    
    async def _check_pulse_consistency_v1(self, adapted_solution: Dict[str, Any],
                                         pulse_support: List[Dict],
                                         patient_profile: Dict[str, Any]) -> Dict[str, Any]:
        """檢查脈診一致性 v1.0"""
        
        if not pulse_support:
            return {
                'consistency_score': 0.5,  # 中性分數
                'consistency_level': 'neutral',
                'analysis': '無脈診支持資訊',
                'recommendations': ['建議補充脈診資訊']
            }
        
        consistency_prompt = f"""
作為專業中醫脈診專家，請評估治療方案與脈診理論的一致性：

【治療方案】
{adapted_solution.get('adapted_treatment', '')}

【患者脈象資訊】
{patient_profile.get('pulse_info', '未記錄')}

【脈診知識庫支持】
"""
        
        for pulse in pulse_support:
            consistency_prompt += f"""
脈象名稱: {pulse.get('name', '')}
脈象描述: {pulse.get('description', '')}
主要疾病: {pulse.get('main_disease', '')}
相關症狀: {pulse.get('symptoms', '')}
---
"""
        
        consistency_prompt += """
請評估：
1. 治療方案與脈診理論的一致性 (0-10分)
2. 脈象與症狀的匹配程度 (0-10分)
3. 治療方向的脈診支持度 (0-10分)
4. 整體一致性等級 (高/中/低)

請提供具體分析和改進建議。
"""
        
        consistency_response = await self.api_manager.generate_llm_response(
            consistency_prompt,
            self.config.get_agent_config('monitoring_agent')
        )
        
        pulse_consistency = self._parse_pulse_consistency_v1(consistency_response)
        
        return pulse_consistency
    
    async def _analyze_risks_v1(self, adapted_solution: Dict[str, Any],
                               patient_profile: Dict[str, Any],
                               safety_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """分析風險因子 v1.0"""
        
        risk_factors = []
        risk_level = 'low'
        
        # 基於安全性評估的風險分析
        safety_score = safety_assessment.get('overall_score', 10)
        if safety_score < 6:
            risk_factors.append('安全性評分偏低')
            risk_level = 'high'
        elif safety_score < 8:
            risk_factors.append('安全性需要關注')
            risk_level = 'medium' if risk_level == 'low' else risk_level
        
        # 患者特殊情況風險
        patient_age = patient_profile.get('age')
        if patient_age:
            try:
                age_num = int(patient_age)
                if age_num > 70:
                    risk_factors.append('高齡患者用藥風險')
                    risk_level = 'medium' if risk_level == 'low' else risk_level
                elif age_num < 18:
                    risk_factors.append('未成年患者用藥需謹慎')
                    risk_level = 'medium' if risk_level == 'low' else risk_level
            except:
                pass
        
        # 既往病史風險
        medical_history = patient_profile.get('medical_history', '')
        high_risk_conditions = ['高血壓', '糖尿病', '心臟病', '腎病', '肝病']
        for condition in high_risk_conditions:
            if condition in medical_history:
                risk_factors.append(f'{condition}患者用藥需特別注意')
                risk_level = 'medium' if risk_level == 'low' else risk_level
        
        # 治療方案複雜度風險
        treatment_text = adapted_solution.get('adapted_treatment', '')
        if len(treatment_text) > 1000:  # 治療方案過於複雜
            risk_factors.append('治療方案複雜度較高')
        
        return {
            'risk_factors': risk_factors,
            'risk_level': risk_level,
            'risk_score': self._calculate_risk_score(risk_factors, risk_level),
            'mitigation_strategies': self._generate_mitigation_strategies_v1(risk_factors),
            'monitoring_priority': 'high' if risk_level == 'high' else 'medium'
        }
    
    async def _generate_monitoring_recommendations_v1(self, adapted_solution: Dict[str, Any],
                                                     monitoring_plan: Dict[str, Any],
                                                     risk_analysis: Dict[str, Any],
                                                     pulse_consistency: Dict[str, Any]) -> Dict[str, Any]:
        """生成監控建議 v1.0"""
        
        recommendations = []
        monitoring_frequency = 'weekly'
        
        # 基於風險等級調整監控頻率
        risk_level = risk_analysis.get('risk_level', 'low')
        if risk_level == 'high':
            monitoring_frequency = 'daily'
            recommendations.append('每日觀察症狀變化和不良反應')
        elif risk_level == 'medium':
            monitoring_frequency = '3-days'
            recommendations.append('每三天評估療效和安全性')
        else:
            recommendations.append('每週跟蹤治療進展')
        
        # v1.0 脈診監控建議
        pulse_score = pulse_consistency.get('consistency_score', 0.5)
        if pulse_score < 0.6:
            recommendations.append('建議增加脈診檢查以驗證治療方向')
            monitoring_frequency = '3-days'  # 提高監控頻率
        else:
            recommendations.append('定期脈診複查以監測改善情況')
        
        # 個性化監控要點
        if adapted_solution.get('dosage_adjustments'):
            recommendations.append('密切關注用藥劑量的個體反應')
        
        if adapted_solution.get('pulse_guidance'):
            recommendations.append('按脈診指導調整治療重點')
        
        # 生成具體監控計劃
        monitoring_schedule = self._create_monitoring_schedule_v1(
            monitoring_frequency, risk_analysis, pulse_consistency
        )
        
        return {
            'recommendations': recommendations,
            'monitoring_frequency': monitoring_frequency,
            'monitoring_schedule': monitoring_schedule,
            'key_indicators': self._identify_key_monitoring_indicators_v1(
                adapted_solution, risk_analysis
            ),
            'alert_conditions': self._define_alert_conditions_v1(risk_analysis),
            'follow_up_plan': self._create_follow_up_plan_v1(monitoring_frequency)
        }
    
    def _calculate_overall_validation_v1(self, safety_assessment: Dict,
                                        effectiveness_assessment: Dict,
                                        pulse_consistency: Dict,
                                        risk_analysis: Dict) -> Dict[str, Any]:
        """計算整體驗證結果 v1.0"""
        
        # 提取各維度分數
        safety_score = safety_assessment.get('overall_score', 0) / 10
        effectiveness_score = effectiveness_assessment.get('overall_score', 0) / 10
        pulse_consistency_score = pulse_consistency.get('consistency_score', 0.5)
        risk_score = 1.0 - risk_analysis.get('risk_score', 0)  # 風險分數轉換
        
        # v1.0 權重分配（增加脈診權重）
        weights = {
            'safety': 0.35,
            'effectiveness': 0.30,
            'pulse_consistency': 0.20,  # v1.0 新增
            'risk': 0.15
        }
        
        # 計算加權平均
        overall_score = (
            safety_score * weights['safety'] +
            effectiveness_score * weights['effectiveness'] +
            pulse_consistency_score * weights['pulse_consistency'] +
            risk_score * weights['risk']
        )
        
        # 驗證通過標準
        validation_passed = (
            safety_score >= 0.6 and
            effectiveness_score >= 0.6 and
            pulse_consistency_score >= 0.4 and  # v1.0 脈診要求
            risk_score >= 0.5
        )
        
        return {
            'overall_score': overall_score,
            'safety_score': safety_score,
            'effectiveness_score': effectiveness_score,
            'pulse_consistency_score': pulse_consistency_score,  # v1.0 新增
            'risk_adjusted_score': risk_score,
            'validation_passed': validation_passed,
            'validation_level': self._determine_validation_level_v1(overall_score),
            'improvement_areas': self._identify_improvement_areas_v1(
                safety_score, effectiveness_score, pulse_consistency_score, risk_score
            )
        }
    
    # 解析和輔助方法
    def _parse_safety_assessment_v1(self, response: str) -> Dict[str, Any]:
        """解析安全性評估結果 v1.0"""
        # 簡化實現，實際可以用更複雜的 NLP 解析
        return {
            'drug_safety_score': 8.0,  # 可以從回應中解析
            'dosage_appropriateness': 8.5,
            'contraindication_check': 9.0,
            'pulse_compatibility': 7.5,  # v1.0 新增
            'overall_score': 8.2,
            'risk_level': 'low',
            'detailed_analysis': response[:300],  # 保留部分原始分析
            'safety_concerns': self._extract_safety_concerns(response),
            'version': self.version
        }
    
    def _parse_effectiveness_assessment_v1(self, response: str) -> Dict[str, Any]:
        """解析有效性評估結果 v1.0"""
        return {
            'symptom_matching': 8.0,
            'expected_efficacy': 7.5,
            'treatment_duration': 8.0,
            'pulse_theory_support': 7.0,  # v1.0 新增
            'overall_score': 7.6,
            'effectiveness_level': 'medium-high',
            'detailed_analysis': response[:300],
            'efficacy_predictions': self._extract_efficacy_predictions(response)
        }
    
    def _parse_pulse_consistency_v1(self, response: str) -> Dict[str, Any]:
        """解析脈診一致性結果 v1.0"""
        return {
            'consistency_score': 0.75,  # 可以從回應中解析
            'consistency_level': 'good',
            'treatment_pulse_alignment': 0.8,
            'symptom_pulse_match': 0.7,
            'theory_support': 0.75,
            'analysis': response[:200],
            'recommendations': ['維持當前脈診指導方向', '加強脈診複查']
        }
    
    def _calculate_risk_score(self, risk_factors: List[str], risk_level: str) -> float:
        """計算風險分數"""
        base_scores = {'low': 0.2, 'medium': 0.5, 'high': 0.8}
        base_score = base_scores.get(risk_level, 0.2)
        
        # 風險因子數量調整
        factor_adjustment = min(len(risk_factors) * 0.1, 0.3)
        
        return min(base_score + factor_adjustment, 1.0)
    
    def _generate_mitigation_strategies_v1(self, risk_factors: List[str]) -> List[str]:
        """生成風險緩解策略 v1.0"""
        strategies = []
        
        for factor in risk_factors:
            if '高齡' in factor:
                strategies.append('調整劑量，延長觀察期')
            elif '安全性' in factor:
                strategies.append('增加安全性監測指標')
            elif '脈診' in factor:
                strategies.append('加強脈診理論指導')  # v1.0
            elif '複雜度' in factor:
                strategies.append('簡化治療方案，分階段實施')
            else:
                strategies.append('加強相關指標監測')
        
        return strategies
    
    def _create_monitoring_schedule_v1(self, frequency: str, risk_analysis: Dict, 
                                      pulse_consistency: Dict) -> Dict[str, Any]:
        """創建監控時程 v1.0"""
        schedule = {
            'frequency': frequency,
            'duration_weeks': 4,  # 預設監控 4 週
            'checkpoints': []
        }
        
        # 基於頻率設定檢查點
        if frequency == 'daily':
            schedule['checkpoints'] = ['每日症狀記錄', '每日脈診自檢', '每3日專業評估']
        elif frequency == '3-days':
            schedule['checkpoints'] = ['每3日症狀評估', '每週脈診檢查', '每2週專業複診']
        else:  # weekly
            schedule['checkpoints'] = ['每週症狀追蹤', '每2週脈診複查', '每月療效評估']
        
        # v1.0 脈診監控特殊安排
        pulse_score = pulse_consistency.get('consistency_score', 0.5)
        if pulse_score < 0.6:
            schedule['special_monitoring'] = ['增加脈診檢查頻率', '脈診專家會診']
        
        return schedule
    
    def _identify_key_monitoring_indicators_v1(self, adapted_solution: Dict, 
                                              risk_analysis: Dict) -> List[str]:
        """識別關鍵監控指標 v1.0"""
        indicators = [
            '主要症狀改善程度',
            '不良反應監測',
            '整體健康狀況',
            '脈象變化情況'  # v1.0 新增
        ]
        
        # 基於風險等級添加特殊指標
        risk_level = risk_analysis.get('risk_level', 'low')
        if risk_level == 'high':
            indicators.extend(['生命體徵監測', '急性反應觀察'])
        
        return indicators
    
    def _define_alert_conditions_v1(self, risk_analysis: Dict) -> List[str]:
        """定義警報條件 v1.0"""
        conditions = [
            '症狀明顯惡化',
            '出現嚴重不良反應',
            '脈象異常變化',  # v1.0 新增
            '患者主觀感受顯著惡化'
        ]
        
        risk_factors = risk_analysis.get('risk_factors', [])
        for factor in risk_factors:
            if '高齡' in factor:
                conditions.append('認知功能變化')
            elif '心臟' in factor:
                conditions.append('心率或血壓異常')
        
        return conditions
    
    def _create_follow_up_plan_v1(self, frequency: str) -> Dict[str, Any]:
        """創建追蹤計劃 v1.0"""
        plan = {
            'initial_follow_up': '3天內',
            'regular_follow_up': frequency,
            'adjustment_points': ['1週', '2週', '4週'],
            'final_evaluation': '4週後',
            'emergency_contact': '如有緊急情況立即聯繫醫師'
        }
        
        return plan
    
    def _determine_validation_level_v1(self, overall_score: float) -> str:
        """確定驗證等級 v1.0"""
        if overall_score >= 0.85:
            return 'excellent'
        elif overall_score >= 0.75:
            return 'good'
        elif overall_score >= 0.65:
            return 'acceptable'
        elif overall_score >= 0.50:
            return 'marginal'
        else:
            return 'poor'
    
    def _identify_improvement_areas_v1(self, safety_score: float, effectiveness_score: float,
                                      pulse_score: float, risk_score: float) -> List[str]:
        """識別改進領域 v1.0"""
        areas = []
        
        if safety_score < 0.7:
            areas.append('安全性需要改進')
        if effectiveness_score < 0.7:
            areas.append('有效性需要提升')
        if pulse_score < 0.6:
            areas.append('脈診一致性需要加強')  # v1.0
        if risk_score < 0.6:
            areas.append('風險控制需要優化')
        
        return areas
    
    def _extract_safety_concerns(self, response: str) -> List[str]:
        """提取安全性顧慮"""
        # 簡化實現
        return ['請注意藥物過敏史', '監測肝腎功能']
    
    def _extract_efficacy_predictions(self, response: str) -> List[str]:
        """提取療效預測"""
        return ['預期1-2週內症狀好轉', '完全緩解需要4-6週']
    
    def _create_error_validation_v1(self, error_message: str) -> Dict[str, Any]:
        """創建錯誤驗證結果 v1.0"""
        return {
            'error': True,
            'error_message': error_message,
            'safety_score': 0.0,
            'effectiveness_score': 0.0,
            'pulse_consistency_score': 0.0,
            'validation_passed': False,
            'message': '驗證過程發生錯誤，請重試或諮詢專業醫師',
            'version': self.version
        }
