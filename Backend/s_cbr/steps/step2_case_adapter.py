"""
STEP 2: 案例適配與協商器 v1.0

v1.0 功能：
- 整合 Case 案例和 PulsePJ 脈診知識
- 智能適配治療方案
- 多維度權重調整
- 與用戶協商確認

版本：v1.0
"""

from typing import Dict, Any, List
from s_cbr.utils.api_manager import SCBRAPIManager
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger

class Step2CaseAdapter:
    """
    STEP 2: 案例適配與協商器 v1.0
    
    v1.0 特色：
    - Case + PulsePJ 雙重知識整合
    - 智能權重動態調整
    - 個人化方案適配
    - 協商式用戶交互
    """
    
    def __init__(self):
        """初始化案例適配器 v1.0"""
        self.config = SCBRConfig()
        self.api_manager = SCBRAPIManager()
        self.logger = SpiralLogger.get_logger("Step2CaseAdapter")
        self.version = "1.0"
        
        self.logger.info(f"STEP 2 案例適配器 v{self.version} 初始化完成")
    
    async def adapt_case_v1(self, base_case: Dict[str, Any], 
                           patient_analysis: Dict[str, Any],
                           pulse_support: List[Dict],  # v1.0 新參數
                           adaptation_strategy: Dict[str, Any],
                           adaptation_weights: Dict[str, float]) -> Dict[str, Any]:
        """
        執行案例適配 v1.0 (整合脈診支持)
        
        v1.0 流程：
        1. 分析基礎案例
        2. 整合脈診知識
        3. 計算適配差異
        4. 生成適配方案
        5. 評估適配信心度
        """
        self.logger.info("開始執行 STEP 2 v1.0: 案例適配與協商")
        
        try:
            if not base_case:
                return self._create_no_case_solution_v1(patient_analysis, pulse_support)
            
            # Step 2.1: 分析基礎案例
            case_analysis = self._analyze_base_case_v1(base_case)
            
            # Step 2.2: 整合脈診知識 (v1.0 新功能)
            pulse_integration = self._integrate_pulse_knowledge_v1(pulse_support, patient_analysis)
            
            # Step 2.3: 計算適配需求
            adaptation_requirements = self._calculate_adaptation_requirements_v1(
                case_analysis, patient_analysis, pulse_integration, adaptation_weights
            )
            
            # Step 2.4: 生成適配方案
            adapted_solution = await self._generate_adapted_solution_v1(
                base_case, adaptation_requirements, adaptation_strategy
            )
            
            # Step 2.5: 評估適配信心度
            confidence_assessment = self._assess_adaptation_confidence_v1(
                adapted_solution, case_analysis, pulse_integration
            )
            
            # Step 2.6: 組裝最終結果
            final_result = self._assemble_adaptation_result_v1(
                adapted_solution, confidence_assessment, pulse_integration
            )
            
            self.logger.info(f"STEP 2 v1.0 完成 - 適配信心度: {final_result.get('confidence', 0):.3f}")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"STEP 2 v1.0 執行異常: {str(e)}")
            return self._create_error_adaptation_v1(str(e))
    
    def _analyze_base_case_v1(self, base_case: Dict[str, Any]) -> Dict[str, Any]:
        """分析基礎案例 v1.0"""
        analysis = {
            'case_id': base_case.get('case_id'),
            'original_diagnosis': base_case.get('diagnosis_main', ''),
            'original_treatment': base_case.get('llm_struct', ''),
            'patient_profile': {
                'age': base_case.get('age'),
                'gender': base_case.get('gender'),
                'chief_complaint': base_case.get('chief_complaint'),
                'pulse_info': base_case.get('pulse_text', '')
            },
            'case_strength': base_case.get('similarity', 0.0),
            'adaptability_score': self._calculate_case_adaptability(base_case)
        }
        
        self.logger.debug(f"基礎案例分析完成 - 適應性評分: {analysis['adaptability_score']:.3f}")
        return analysis
    
    def _integrate_pulse_knowledge_v1(self, pulse_support: List[Dict], 
                                     patient_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """整合脈診知識 v1.0"""
        if not pulse_support:
            return {
                'pulse_insights': [],
                'diagnostic_support': [],
                'treatment_modifications': [],
                'integration_strength': 0.0
            }
        
        # 提取患者脈象資訊
        patient_pulse = patient_analysis.get('脈象描述', '') or patient_analysis.get('pulse_pattern', '')
        
        # 分析脈診支持
        pulse_insights = []
        diagnostic_support = []
        treatment_modifications = []
        
        for pulse in pulse_support:
            # 脈診洞察
            pulse_insights.append({
                'pulse_name': pulse.get('name'),
                'description': pulse.get('description'),
                'relevance': pulse.get('relevance', 0.0)
            })
            
            # 診斷支持
            if pulse.get('main_disease'):
                diagnostic_support.append({
                    'pulse': pulse.get('name'),
                    'suggested_diagnosis': pulse.get('main_disease'),
                    'supporting_symptoms': pulse.get('symptoms', '')
                })
            
            # 治療建議修正
            if pulse.get('knowledge_chain'):
                treatment_modifications.append({
                    'pulse': pulse.get('name'),
                    'modification_suggestion': pulse.get('knowledge_chain'),
                    'category': pulse.get('category')
                })
        
        # 計算整合強度
        integration_strength = self._calculate_pulse_integration_strength(
            pulse_support, patient_pulse
        )
        
        integration = {
            'pulse_insights': pulse_insights,
            'diagnostic_support': diagnostic_support,
            'treatment_modifications': treatment_modifications,
            'integration_strength': integration_strength,
            'patient_pulse_match': self._assess_pulse_match(pulse_support, patient_pulse)
        }
        
        self.logger.debug(f"脈診知識整合完成 - 整合強度: {integration_strength:.3f}")
        return integration
    
    def _calculate_adaptation_requirements_v1(self, case_analysis: Dict, 
                                            patient_analysis: Dict,
                                            pulse_integration: Dict,
                                            adaptation_weights: Dict) -> Dict[str, Any]:
        """計算適配需求 v1.0"""
        
        # 症狀差異分析
        symptom_diff = self._analyze_symptom_differences(
            case_analysis, patient_analysis, adaptation_weights['symptom_weight']
        )
        
        # 體質差異分析
        constitution_diff = self._analyze_constitution_differences(
            case_analysis, patient_analysis, adaptation_weights['constitution_weight']
        )
        
        # 病史差異分析
        history_diff = self._analyze_history_differences(
            case_analysis, patient_analysis, adaptation_weights['history_weight']
        )
        
        # v1.0 脈診差異分析
        pulse_diff = self._analyze_pulse_differences(
            case_analysis, pulse_integration, adaptation_weights['pulse_weight']
        )
        
        # 綜合適配需求
        overall_adaptation_need = (
            symptom_diff['adaptation_score'] * adaptation_weights['symptom_weight'] +
            constitution_diff['adaptation_score'] * adaptation_weights['constitution_weight'] +
            history_diff['adaptation_score'] * adaptation_weights['history_weight'] +
            pulse_diff['adaptation_score'] * adaptation_weights['pulse_weight']
        )
        
        requirements = {
            'symptom_adaptations': symptom_diff,
            'constitution_adaptations': constitution_diff,
            'history_adaptations': history_diff,
            'pulse_adaptations': pulse_diff,  # v1.0 新增
            'overall_adaptation_need': overall_adaptation_need,
            'priority_areas': self._identify_priority_adaptation_areas(
                symptom_diff, constitution_diff, history_diff, pulse_diff
            )
        }
        
        self.logger.debug(f"適配需求分析完成 - 總體需求度: {overall_adaptation_need:.3f}")
        return requirements
    
    async def _generate_adapted_solution_v1(self, base_case: Dict,
                                           adaptation_requirements: Dict,
                                           adaptation_strategy: Dict) -> Dict[str, Any]:
        """生成適配方案 v1.0"""
        
        # 構建適配提示
        adaptation_prompt = self._build_adaptation_prompt_v1(
            base_case, adaptation_requirements, adaptation_strategy
        )
        
        # 調用 LLM 生成適配方案
        adapted_treatment = await self.api_manager.generate_llm_response(
            adaptation_prompt, 
            self.config.get_agent_config('adaptation_agent')
        )
        
        # 解析和結構化適配結果
        structured_solution = self._structure_adaptation_result_v1(
            adapted_treatment, base_case, adaptation_requirements
        )
        
        return structured_solution
    
    def _build_adaptation_prompt_v1(self, base_case: Dict, 
                                   adaptation_requirements: Dict,
                                   adaptation_strategy: Dict) -> str:
        """構建適配提示 v1.0 (整合脈診)"""
        
        prompt = f"""
作為專業中醫適配智能體，請基於以下資訊進行治療方案適配：

【參考案例】
- 案例ID: {base_case.get('case_id')}
- 原始診斷: {base_case.get('diagnosis_main')}
- 原始治療: {base_case.get('llm_struct', '未提供')}
- 患者資訊: 年齡 {base_case.get('age')}，性別 {base_case.get('gender')}
- 主訴: {base_case.get('chief_complaint')}
- 脈象: {base_case.get('pulse_text', '未記錄')}

【當前患者適配需求】
症狀適配需求: {adaptation_requirements.get('symptom_adaptations', {}).get('requirements', '無')}
體質適配需求: {adaptation_requirements.get('constitution_adaptations', {}).get('requirements', '無')}
病史適配需求: {adaptation_requirements.get('history_adaptations', {}).get('requirements', '無')}

【脈診知識整合 (v1.0)】
"""
        
        # v1.0 添加脈診適配需求
        pulse_adaptations = adaptation_requirements.get('pulse_adaptations', {})
        if pulse_adaptations.get('requirements'):
            prompt += f"脈診適配需求: {pulse_adaptations['requirements']}\n"
            
        pulse_insights = adaptation_requirements.get('pulse_adaptations', {}).get('pulse_insights', [])
        if pulse_insights:
            prompt += "相關脈診知識:\n"
            for insight in pulse_insights[:3]:  # 取前3個最相關
                prompt += f"- 脈象 {insight.get('pulse_name')}: {insight.get('description')}\n"
        
        prompt += f"""
【適配策略】
{adaptation_strategy.get('strategy_description', '標準適配')}

請提供：
1. 適配後的診斷建議
2. 調整後的治療方案 
3. 用藥劑量建議
4. 脈診指導要點 (v1.0)
5. 注意事項和禁忌
6. 適配的理由說明

請以專業、準確、個人化的方式進行適配，確保安全有效。
"""
        
        return prompt
    
    def _structure_adaptation_result_v1(self, llm_response: str, base_case: Dict,
                                       adaptation_requirements: Dict) -> Dict[str, Any]:
        """結構化適配結果 v1.0"""
        
        # 基本結構化（可以進一步改進解析邏輯）
        structured = {
            'original_case_id': base_case.get('case_id'),
            'adapted_diagnosis': self._extract_diagnosis_from_response(llm_response),
            'adapted_treatment': llm_response,
            'treatment_summary': self._extract_treatment_summary(llm_response),
            'dosage_adjustments': self._extract_dosage_info(llm_response),
            'pulse_guidance': self._extract_pulse_guidance_v1(llm_response),  # v1.0 新增
            'precautions': self._extract_precautions(llm_response),
            'adaptation_reasoning': self._extract_reasoning(llm_response),
            'confidence': 0.0,  # 稍後計算
            'version': self.version
        }
        
        return structured
    
    def _assess_adaptation_confidence_v1(self, adapted_solution: Dict,
                                        case_analysis: Dict,
                                        pulse_integration: Dict) -> Dict[str, Any]:
        """評估適配信心度 v1.0"""
        
        # 基礎案例信心度
        base_confidence = case_analysis.get('case_strength', 0.0)
        
        # 適應性評分
        adaptability = case_analysis.get('adaptability_score', 0.0)
        
        # v1.0 脈診整合信心度
        pulse_confidence = pulse_integration.get('integration_strength', 0.0)
        
        # 綜合信心度計算
        overall_confidence = (
            base_confidence * 0.4 +
            adaptability * 0.35 +
            pulse_confidence * 0.25  # v1.0 脈診權重
        )
        
        # 信心度等級
        if overall_confidence >= 0.8:
            confidence_level = 'high'
        elif overall_confidence >= 0.6:
            confidence_level = 'medium'
        elif overall_confidence >= 0.4:
            confidence_level = 'low'
        else:
            confidence_level = 'very_low'
        
        assessment = {
            'overall_confidence': overall_confidence,
            'confidence_level': confidence_level,
            'base_case_confidence': base_confidence,
            'adaptability_confidence': adaptability,
            'pulse_integration_confidence': pulse_confidence,  # v1.0 新增
            'confidence_factors': self._identify_confidence_factors_v1(
                base_confidence, adaptability, pulse_confidence
            )
        }
        
        return assessment
    
    def _assemble_adaptation_result_v1(self, adapted_solution: Dict,
                                      confidence_assessment: Dict,
                                      pulse_integration: Dict) -> Dict[str, Any]:
        """組裝適配結果 v1.0"""
        
        # 更新信心度
        adapted_solution['confidence'] = confidence_assessment['overall_confidence']
        adapted_solution['confidence_level'] = confidence_assessment['confidence_level']
        
        # v1.0 添加脈診整合資訊
        adapted_solution['pulse_integration'] = {
            'pulse_insights_used': len(pulse_integration.get('pulse_insights', [])),
            'diagnostic_support': pulse_integration.get('diagnostic_support', []),
            'treatment_modifications': pulse_integration.get('treatment_modifications', []),
            'integration_quality': pulse_integration.get('integration_strength', 0.0)
        }
        
        # 添加詳細評估
        adapted_solution['detailed_assessment'] = confidence_assessment
        
        return adapted_solution
    
    # 輔助方法
    def _calculate_case_adaptability(self, case: Dict) -> float:
        """計算案例適應性"""
        # 簡單實現，可以進一步優化
        adaptability = 0.7  # 基礎適應性
        
        # 如果有完整診斷資訊，提高適應性
        if case.get('diagnosis_main'):
            adaptability += 0.1
        
        # 如果有治療結構化資訊，提高適應性    
        if case.get('llm_struct'):
            adaptability += 0.1
            
        # 如果有脈診資訊，提高適應性 (v1.0)
        if case.get('pulse_text'):
            adaptability += 0.1
        
        return min(adaptability, 1.0)
    
    def _calculate_pulse_integration_strength(self, pulse_support: List[Dict], 
                                            patient_pulse: str) -> float:
        """計算脈診整合強度 v1.0"""
        if not pulse_support:
            return 0.0
            
        # 基於脈診知識數量和相關性
        base_strength = min(len(pulse_support) / 5.0, 1.0)  # 最多5個脈診知識
        
        # 基於患者脈象匹配度
        if patient_pulse:
            match_score = 0.5  # 基礎匹配分
            # 簡單關鍵詞匹配（可以改進）
            for pulse in pulse_support:
                if pulse.get('name', '').lower() in patient_pulse.lower():
                    match_score += 0.2
            base_strength *= min(match_score, 1.0)
        
        return base_strength
    
    def _assess_pulse_match(self, pulse_support: List[Dict], patient_pulse: str) -> float:
        """評估脈象匹配度 v1.0"""
        if not pulse_support or not patient_pulse:
            return 0.0
            
        match_count = 0
        for pulse in pulse_support:
            if pulse.get('name', '').lower() in patient_pulse.lower():
                match_count += 1
                
        return match_count / len(pulse_support)
    
    def _analyze_symptom_differences(self, case_analysis: Dict, patient_analysis: Dict, weight: float) -> Dict[str, Any]:
        """分析症狀差異"""
        return {
            'adaptation_score': 0.6 * weight,  # 簡化實現
            'requirements': '根據個體症狀調整治療重點',
            'priority': 'medium'
        }
    
    def _analyze_constitution_differences(self, case_analysis: Dict, patient_analysis: Dict, weight: float) -> Dict[str, Any]:
        """分析體質差異"""
        return {
            'adaptation_score': 0.5 * weight,
            'requirements': '考慮體質差異調整用藥',
            'priority': 'medium'
        }
    
    def _analyze_history_differences(self, case_analysis: Dict, patient_analysis: Dict, weight: float) -> Dict[str, Any]:
        """分析病史差異"""
        return {
            'adaptation_score': 0.4 * weight,
            'requirements': '結合既往病史調整療程',
            'priority': 'low'
        }
    
    def _analyze_pulse_differences(self, case_analysis: Dict, pulse_integration: Dict, weight: float) -> Dict[str, Any]:
        """分析脈診差異 v1.0"""
        integration_strength = pulse_integration.get('integration_strength', 0.0)
        
        return {
            'adaptation_score': integration_strength * weight,
            'requirements': '結合脈診特點調整方案',
            'priority': 'high' if integration_strength > 0.6 else 'medium',
            'pulse_insights': pulse_integration.get('pulse_insights', [])
        }
    
    def _identify_priority_adaptation_areas(self, symptom_diff: Dict, constitution_diff: Dict, 
                                          history_diff: Dict, pulse_diff: Dict) -> List[str]:
        """識別優先適配領域"""
        areas = []
        
        if symptom_diff.get('priority') == 'high':
            areas.append('症狀調整')
        if constitution_diff.get('priority') == 'high':
            areas.append('體質適配')
        if history_diff.get('priority') == 'high':
            areas.append('病史考量')
        if pulse_diff.get('priority') == 'high':
            areas.append('脈診指導')  # v1.0
            
        return areas
    
    def _extract_diagnosis_from_response(self, response: str) -> str:
        """從回應中提取診斷"""
        # 簡單實現，可以用更複雜的 NLP
        lines = response.split('\n')
        for line in lines:
            if '診斷' in line:
                return line.strip()
        return "適配診斷建議"
    
    def _extract_treatment_summary(self, response: str) -> str:
        """提取治療摘要"""
        # 簡化實現
        return response[:200] + "..." if len(response) > 200 else response
    
    def _extract_dosage_info(self, response: str) -> List[str]:
        """提取劑量資訊"""
        return ["請遵醫囑用藥"]  # 簡化實現
    
    def _extract_pulse_guidance_v1(self, response: str) -> List[str]:
        """提取脈診指導 v1.0"""
        guidance = []
        lines = response.split('\n')
        for line in lines:
            if '脈' in line and ('指導' in line or '建議' in line):
                guidance.append(line.strip())
        
        if not guidance:
            guidance = ["建議定期監測脈象變化"]
            
        return guidance
    
    def _extract_precautions(self, response: str) -> List[str]:
        """提取注意事項"""
        return ["注意觀察療效", "如有不適及時就醫"]  # 簡化實現
    
    def _extract_reasoning(self, response: str) -> str:
        """提取推理說明"""
        return "基於案例相似性和個體差異進行適配"  # 簡化實現
    
    def _identify_confidence_factors_v1(self, base_conf: float, adapt_conf: float, pulse_conf: float) -> List[str]:
        """識別信心度影響因子 v1.0"""
        factors = []
        
        if base_conf > 0.8:
            factors.append("高相似度參考案例")
        if adapt_conf > 0.7:
            factors.append("良好的案例適應性")
        if pulse_conf > 0.6:
            factors.append("脈診知識支持")  # v1.0
            
        if base_conf < 0.5:
            factors.append("參考案例相似度偏低")
        if pulse_conf < 0.3:
            factors.append("脈診知識匹配度不足")
            
        return factors
    
    def _create_no_case_solution_v1(self, patient_analysis: Dict, pulse_support: List[Dict]) -> Dict[str, Any]:
        """創建無案例時的解決方案 v1.0"""
        return {
            'original_case_id': None,
            'adapted_diagnosis': "基於症狀分析的初步診斷",
            'adapted_treatment': "建議專業中醫師面診確認",
            'confidence': 0.3,
            'confidence_level': 'low',
            'pulse_integration': {
                'pulse_insights_used': len(pulse_support),
                'diagnostic_support': [p.get('main_disease', '') for p in pulse_support],
                'integration_quality': 0.2
            },
            'version': self.version,
            'note': '無相似參考案例，基於脈診知識提供初步建議'
        }
    
    def _create_error_adaptation_v1(self, error_message: str) -> Dict[str, Any]:
        """創建錯誤適配結果 v1.0"""
        return {
            'error': True,
            'error_message': error_message,
            'adapted_treatment': "適配過程發生錯誤，請重試或諮詢專業醫師",
            'confidence': 0.0,
            'confidence_level': 'error',
            'version': self.version
        }
