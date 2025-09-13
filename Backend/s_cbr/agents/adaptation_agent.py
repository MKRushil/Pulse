"""
適配智能體 v1.0

v1.0 功能：
- 案例適配策略制定
- 脈診知識整合適配
- 個人化方案調整
- 適配信心度評估

版本：v1.0
"""

from typing import Dict, Any, List
from s_cbr.utils.api_manager import SCBRAPIManager
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger

class AdaptationAgent:
    """
    適配智能體 v1.0
    
    v1.0 特色：
    - Case + PulsePJ 雙重適配
    - 動態權重調整
    - 智能策略生成
    - 多維度適配評估
    """
    
    def __init__(self):
        """初始化適配智能體 v1.0"""
        self.config = SCBRConfig()
        self.api_manager = SCBRAPIManager()
        self.logger = SpiralLogger.get_logger("AdaptationAgent")
        self.version = "1.0"
        
        self.logger.info(f"適配智能體 v{self.version} 初始化完成")
    
    async def create_adaptation_strategy_v1(self, base_case: Dict[str, Any],
                                           patient_analysis: Dict[str, Any],
                                           pulse_support: List[Dict],
                                           context: Dict[str, Any]) -> Dict[str, Any]:
        """
        創建適配策略 v1.0 (整合脈診支持)
        
        v1.0 策略制定：
        1. 分析案例-患者差異
        2. 整合脈診知識指導
        3. 制定適配優先級
        4. 生成適配路徑
        5. 評估適配風險
        """
        self.logger.info("創建適配策略 v1.0")
        
        try:
            # Step 1: 差異分析
            difference_analysis = await self._analyze_case_patient_differences_v1(
                base_case, patient_analysis
            )
            
            # Step 2: 脈診整合分析 (v1.0)
            pulse_integration_strategy = await self._develop_pulse_integration_strategy_v1(
                pulse_support, patient_analysis, difference_analysis
            )
            
            # Step 3: 適配優先級制定
            adaptation_priorities = self._determine_adaptation_priorities_v1(
                difference_analysis, pulse_integration_strategy
            )
            
            # Step 4: 適配路徑生成
            adaptation_pathway = await self._generate_adaptation_pathway_v1(
                base_case, difference_analysis, pulse_integration_strategy, adaptation_priorities
            )
            
            # Step 5: 風險評估
            adaptation_risks = self._assess_adaptation_risks_v1(
                adaptation_pathway, difference_analysis
            )
            
            # 組裝策略結果
            strategy = {
                'strategy_id': f"adapt_v1_{context.get('session_id', '')[:8]}",
                'difference_analysis': difference_analysis,
                'pulse_integration_strategy': pulse_integration_strategy,  # v1.0
                'adaptation_priorities': adaptation_priorities,
                'adaptation_pathway': adaptation_pathway,
                'adaptation_risks': adaptation_risks,
                'strategy_confidence': self._calculate_strategy_confidence_v1(
                    difference_analysis, pulse_integration_strategy, adaptation_risks
                ),
                'estimated_success_rate': self._estimate_success_rate_v1(
                    base_case, difference_analysis, pulse_integration_strategy
                ),
                'strategy_description': self._generate_strategy_description_v1(adaptation_pathway),
                'version': self.version
            }
            
            self.logger.info(f"適配策略 v1.0 完成 - 信心度: {strategy['strategy_confidence']:.3f}")
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"適配策略創建失敗: {str(e)}")
            return self._create_fallback_strategy_v1(str(e))
    
    async def _analyze_case_patient_differences_v1(self, base_case: Dict[str, Any],
                                                  patient_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """分析案例與患者差異 v1.0"""
        
        differences = {
            'demographic_differences': self._analyze_demographic_diff(base_case, patient_analysis),
            'symptom_differences': self._analyze_symptom_diff(base_case, patient_analysis),
            'constitution_differences': self._analyze_constitution_diff(base_case, patient_analysis),
            'pulse_differences': self._analyze_pulse_diff_v1(base_case, patient_analysis),  # v1.0
            'severity_differences': self._analyze_severity_diff(base_case, patient_analysis),
            'overall_similarity': 0.0  # 稍後計算
        }
        
        # 計算整體相似度
        differences['overall_similarity'] = self._calculate_overall_similarity_v1(differences)
        
        # 識別關鍵差異點
        differences['key_differences'] = self._identify_key_differences_v1(differences)
        
        return differences
    
    async def _develop_pulse_integration_strategy_v1(self, pulse_support: List[Dict],
                                                    patient_analysis: Dict[str, Any],
                                                    difference_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """開發脈診整合策略 v1.0"""
        
        if not pulse_support:
            return {
                'integration_feasible': False,
                'strategy_type': 'no_pulse_support',
                'recommendations': ['建議補充脈診資訊'],
                'integration_strength': 0.0
            }
        
        # 分析脈診支持強度
        pulse_strength = self._assess_pulse_support_strength(pulse_support, patient_analysis)
        
        # 制定整合策略
        integration_strategy = await self._formulate_pulse_integration_v1(
            pulse_support, difference_analysis, pulse_strength
        )
        
        return {
            'integration_feasible': True,
            'pulse_strength': pulse_strength,
            'strategy_type': integration_strategy.get('type', 'standard'),
            'integration_points': integration_strategy.get('points', []),
            'pulse_adjustments': integration_strategy.get('adjustments', []),
            'integration_strength': pulse_strength.get('overall_strength', 0.0),
            'recommendations': integration_strategy.get('recommendations', []),
            'pulse_knowledge_utilization': self._calculate_knowledge_utilization(pulse_support)
        }
    
    def _determine_adaptation_priorities_v1(self, difference_analysis: Dict[str, Any],
                                           pulse_integration: Dict[str, Any]) -> List[Dict[str, Any]]:
        """確定適配優先級 v1.0"""
        
        priorities = []
        
        # 基於差異分析的優先級
        key_differences = difference_analysis.get('key_differences', [])
        for diff in key_differences:
            priority_level = 'high' if diff.get('severity') == 'major' else 'medium'
            priorities.append({
                'area': diff.get('area'),
                'priority': priority_level,
                'reason': diff.get('description'),
                'adaptation_type': 'difference_based'
            })
        
        # v1.0 基於脈診整合的優先級
        if pulse_integration.get('integration_feasible'):
            pulse_strength = pulse_integration.get('integration_strength', 0.0)
            if pulse_strength > 0.7:
                priorities.append({
                    'area': 'pulse_integration',
                    'priority': 'high',
                    'reason': '強脈診知識支持',
                    'adaptation_type': 'pulse_based'
                })
            elif pulse_strength > 0.4:
                priorities.append({
                    'area': 'pulse_integration',
                    'priority': 'medium',
                    'reason': '中等脈診知識支持',
                    'adaptation_type': 'pulse_based'
                })
        
        # 按優先級排序
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        priorities.sort(key=lambda x: priority_order.get(x['priority'], 0), reverse=True)
        
        return priorities
    
    async def _generate_adaptation_pathway_v1(self, base_case: Dict[str, Any],
                                             difference_analysis: Dict[str, Any],
                                             pulse_integration: Dict[str, Any],
                                             priorities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成適配路徑 v1.0"""
        
        pathway_prompt = f"""
作為專業中醫適配智能體，請制定詳細的適配路徑：

【基礎案例】
診斷: {base_case.get('diagnosis_main', '')}
治療方案: {base_case.get('llm_struct', '')[:300]}

【關鍵差異】
{self._format_differences_for_prompt(difference_analysis)}

【脈診整合策略 (v1.0)】
可行性: {pulse_integration.get('integration_feasible', False)}
整合強度: {pulse_integration.get('integration_strength', 0.0)}
調整建議: {pulse_integration.get('pulse_adjustments', [])}

【適配優先級】
{self._format_priorities_for_prompt(priorities)}

請提供：
1. 詳細適配步驟（按優先級排序）
2. 每個步驟的具體調整內容
3. 脈診指導的整合方式 (v1.0)
4. 預期的適配效果
5. 潛在的風險點和應對措施

請以結構化、專業的方式回答。
"""
        
        pathway_response = await self.api_manager.generate_llm_response(
            pathway_prompt,
            self.config.get_agent_config('adaptation_agent')
        )
        
        # 結構化路徑結果
        structured_pathway = self._structure_pathway_result_v1(
            pathway_response, priorities, pulse_integration
        )
        
        return structured_pathway
    
    def _assess_adaptation_risks_v1(self, adaptation_pathway: Dict[str, Any],
                                   difference_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """評估適配風險 v1.0"""
        
        risks = {
            'high_risks': [],
            'medium_risks': [],
            'low_risks': [],
            'overall_risk_level': 'low',
            'risk_mitigation_strategies': []
        }
        
        # 基於相似度的風險評估
        overall_similarity = difference_analysis.get('overall_similarity', 0.5)
        if overall_similarity < 0.4:
            risks['high_risks'].append('基礎案例相似度過低')
            risks['risk_mitigation_strategies'].append('增加額外驗證步驟')
        elif overall_similarity < 0.6:
            risks['medium_risks'].append('基礎案例相似度中等')
        
        # 適配複雜度風險
        adaptation_steps = len(adaptation_pathway.get('adaptation_steps', []))
        if adaptation_steps > 5:
            risks['high_risks'].append('適配步驟過於複雜')
            risks['risk_mitigation_strategies'].append('簡化適配流程')
        elif adaptation_steps > 3:
            risks['medium_risks'].append('適配步驟較多')
        
        # v1.0 脈診整合風險
        pulse_integration = adaptation_pathway.get('pulse_integration_quality', 0.0)
        if pulse_integration < 0.3:
            risks['medium_risks'].append('脈診整合支持不足')
            risks['risk_mitigation_strategies'].append('加強脈診驗證')
        
        # 確定整體風險等級
        if risks['high_risks']:
            risks['overall_risk_level'] = 'high'
        elif len(risks['medium_risks']) > 2:
            risks['overall_risk_level'] = 'medium'
        
        return risks
    
    def _calculate_strategy_confidence_v1(self, difference_analysis: Dict,
                                         pulse_integration: Dict,
                                         adaptation_risks: Dict) -> float:
        """計算策略信心度 v1.0"""
        
        # 基礎信心度（基於相似度）
        similarity_confidence = difference_analysis.get('overall_similarity', 0.0)
        
        # v1.0 脈診整合信心度
        pulse_confidence = pulse_integration.get('integration_strength', 0.0) * 0.8
        
        # 風險調整
        risk_level = adaptation_risks.get('overall_risk_level', 'low')
        risk_penalty = {'high': 0.3, 'medium': 0.15, 'low': 0.0}.get(risk_level, 0.0)
        
        # 綜合計算
        strategy_confidence = (
            similarity_confidence * 0.5 +
            pulse_confidence * 0.3 +
            0.2 * 0.2  # 基礎方法學信心
        ) - risk_penalty
        
        return max(0.0, min(1.0, strategy_confidence))
    
    def _estimate_success_rate_v1(self, base_case: Dict, difference_analysis: Dict,
                                 pulse_integration: Dict) -> float:
        """估計成功率 v1.0"""
        
        # 基於案例品質
        case_quality = base_case.get('similarity', 0.0)
        
        # 差異調整因子
        similarity = difference_analysis.get('overall_similarity', 0.0)
        
        # v1.0 脈診支持因子
        pulse_support = pulse_integration.get('integration_strength', 0.0)
        
        # 成功率估計
        success_rate = (
            case_quality * 0.4 +
            similarity * 0.4 +
            pulse_support * 0.2
        )
        
        return success_rate
    
    # 輔助分析方法
    def _analyze_demographic_diff(self, base_case: Dict, patient_analysis: Dict) -> Dict[str, Any]:
        """分析人口統計學差異"""
        case_age = base_case.get('age')
        patient_age = patient_analysis.get('年齡')
        
        age_diff = 0
        if case_age and patient_age:
            try:
                age_diff = abs(int(case_age) - int(patient_age))
            except:
                age_diff = 0
        
        gender_match = (base_case.get('gender') == patient_analysis.get('性別'))
        
        return {
            'age_difference': age_diff,
            'gender_match': gender_match,
            'demographic_similarity': 0.8 if gender_match and age_diff < 10 else 0.5
        }
    
    def _analyze_symptom_diff(self, base_case: Dict, patient_analysis: Dict) -> Dict[str, Any]:
        """分析症狀差異"""
        case_symptoms = base_case.get('chief_complaint', '') + ' ' + base_case.get('summary_text', '')
        patient_symptoms = ' '.join(patient_analysis.get('主要症狀', []))
        
        # 簡單的症狀匹配（可以改進）
        case_words = set(case_symptoms.split())
