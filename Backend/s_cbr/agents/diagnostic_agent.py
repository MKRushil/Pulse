"""
診斷智能體 v1.0

v1.0 功能：
- 患者特徵綜合分析
- 症狀模式識別
- 脈診資訊整合
- 診斷建議生成

版本：v1.0
"""

from typing import Dict, Any, List
import json
from s_cbr.utils.api_manager import SCBRAPIManager
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger

class DiagnosticAgent:
    """
    診斷智能體 v1.0
    
    v1.0 特色：
    - 多維度症狀分析
    - Case + PulsePJ 知識整合
    - 智能特徵提取
    - 結構化診斷建議
    """
    
    def __init__(self):
        """初始化診斷智能體 v1.0"""
        self.config = SCBRConfig()
        self.api_manager = SCBRAPIManager()
        self.logger = SpiralLogger.get_logger("DiagnosticAgent")
        self.version = "1.0"
        
        self.logger.info(f"診斷智能體 v{self.version} 初始化完成")
    
    async def build_patient_profile_v1(self, initial_query: Dict[str, Any]) -> Dict[str, Any]:
        """建立患者檔案 v1.0"""
        self.logger.debug("建立患者檔案 v1.0")
        
        # 提取基本資訊
        basic_info = self._extract_basic_info_v1(initial_query)
        
        # 分析症狀特徵
        symptom_analysis = await self._analyze_symptoms_v1(initial_query)
        
        # 分析脈診資訊 (v1.0)
        pulse_analysis = await self._analyze_pulse_info_v1(initial_query)
        
        # 綜合分析
        comprehensive_profile = {
            'basic_info': basic_info,
            'symptom_analysis': symptom_analysis,
            'pulse_analysis': pulse_analysis,  # v1.0 新增
            'risk_factors': self._identify_risk_factors_v1(basic_info, symptom_analysis),
            'diagnostic_priorities': self._set_diagnostic_priorities_v1(symptom_analysis, pulse_analysis),
            'version': self.version
        }
        
        return comprehensive_profile
    
    async def analyze_comprehensive_features_v1(self, symptoms, history, context) -> Dict[str, Any]:
        """綜合特徵分析 v1.0 (整合 Case + PulsePJ)"""
        self.logger.debug("執行綜合特徵分析 v1.0")
        
        # 構建分析提示
        analysis_prompt = f"""
作為專業中醫診斷智能體，請綜合分析患者特徵：

【主要症狀】
{symptoms if isinstance(symptoms, str) else str(symptoms)}

【病史資訊】  
{history if isinstance(history, str) else str(history)}

【上下文資訊】
{context.get('patient_profile', {}) if context else '無'}

請進行以下分析：
1. 主要症狀分類和優先級
2. 體質特徵判斷
3. 病理機制分析
4. 脈診預期表現 (v1.0)
5. 診斷方向建議
6. 需要進一步確認的資訊

請以結構化方式回答。
"""
        
        # 調用 LLM 分析
        analysis_response = await self.api_manager.generate_llm_response(
            analysis_prompt,
            self.config.get_agent_config('diagnostic_agent')
        )
        
        # 結構化分析結果
        structured_analysis = await self._structure_analysis_result_v1(
            analysis_response, symptoms, history
        )
        
        # v1.0 整合脈診知識
        pulse_integration = await self._integrate_pulse_knowledge_v1(
            structured_analysis, context
        )
        
        final_analysis = {
            **structured_analysis,
            'pulse_integration': pulse_integration,  # v1.0 新增
            'analysis_confidence': self._calculate_analysis_confidence_v1(structured_analysis),
            'version': self.version
        }
        
        return final_analysis
    
    def _extract_basic_info_v1(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """提取基本資訊 v1.0"""
        return {
            'age': query.get('age'),
            'gender': query.get('gender'),
            'chief_complaint': query.get('question') or query.get('chief_complaint'),
            'present_illness': query.get('present_illness', ''),
            'medical_history': query.get('medical_history', ''),
            'pulse_info': query.get('pulse_text') or query.get('pulse_pattern', ''),  # v1.0
        }
    
    async def _analyze_symptoms_v1(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """分析症狀 v1.0"""
        symptom_text = query.get('question', '') + ' ' + query.get('chief_complaint', '')
        
        if not symptom_text.strip():
            return {
                'primary_symptoms': [],
                'secondary_symptoms': [],
                'symptom_severity': 'unknown',
                'symptom_duration': 'unknown'
            }
        
        symptom_prompt = f"""
分析以下症狀描述：{symptom_text}

請識別：
1. 主要症狀 (最重要的2-3個)
2. 次要症狀
3. 症狀嚴重程度 (輕/中/重)
4. 症狀持續時間推測
5. 可能的症狀模式
"""
        
        response = await self.api_manager.generate_llm_response(symptom_prompt)
        
        return {
            'primary_symptoms': self._extract_primary_symptoms(response),
            'secondary_symptoms': self._extract_secondary_symptoms(response),
            'symptom_severity': self._extract_severity(response),
            'symptom_duration': self._extract_duration(response),
            'symptom_pattern': self._extract_pattern(response)
        }
    
    async def _analyze_pulse_info_v1(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """分析脈診資訊 v1.0"""
        pulse_info = query.get('pulse_text') or query.get('pulse_pattern', '')
        
        if not pulse_info:
            return {
                'pulse_description': '',
                'pulse_patterns': [],
                'diagnostic_significance': '',
                'pulse_quality': 'unknown'
            }
        
        # 搜尋相關脈診知識
        pulse_knowledge = await self.api_manager.search_pulse_knowledge(pulse_info)
        
        pulse_prompt = f"""
基於脈診資訊分析：{pulse_info}

相關脈診知識：
{json.dumps(pulse_knowledge[:3], ensure_ascii=False) if pulse_knowledge else '無'}

請分析：
1. 脈象特徵描述
2. 可能的脈象分類
3. 診斷意義
4. 與症狀的關聯性
"""
        
        pulse_response = await self.api_manager.generate_llm_response(pulse_prompt)
        
        return {
            'pulse_description': pulse_info,
            'pulse_patterns': self._extract_pulse_patterns(pulse_response),
            'diagnostic_significance': pulse_response[:200],
            'pulse_quality': self._assess_pulse_quality(pulse_knowledge),
            'related_knowledge': pulse_knowledge[:3]
        }
    
    async def _structure_analysis_result_v1(self, analysis_response: str,
                                           symptoms, history) -> Dict[str, Any]:
        """結構化分析結果 v1.0"""
        # 簡化實現，實際可以用更複雜的 NLP 解析
        return {
            '主要症狀': self._parse_main_symptoms(analysis_response, symptoms),
            '體質特徵': self._parse_constitution_features(analysis_response),
            '病史資訊': self._parse_history_info(analysis_response, history),
            '環境因素': self._parse_environmental_factors(analysis_response),
            '年齡': self._extract_age_info(analysis_response),
            '性別': self._extract_gender_info(analysis_response),
            '脈象描述': self._extract_pulse_description(analysis_response),  # v1.0
            'diagnostic_direction': self._extract_diagnostic_direction(analysis_response),
            'analysis_quality': self._assess_analysis_quality(analysis_response)
        }
    
    async def _integrate_pulse_knowledge_v1(self, structured_analysis: Dict,
                                           context: Dict) -> Dict[str, Any]:
        """整合脈診知識 v1.0"""
        pulse_description = structured_analysis.get('脈象描述', '')
        main_symptoms = structured_analysis.get('主要症狀', [])
        
        if not pulse_description and not main_symptoms:
            return {
                'pulse_knowledge_available': False,
                'integration_quality': 0.0,
                'diagnostic_support': []
            }
        
        # 搜尋相關脈診知識
        pulse_knowledge = []
        if pulse_description:
            pulse_knowledge.extend(
                await self.api_manager.search_pulse_knowledge(pulse_description)
            )
        
        if main_symptoms:
            for symptom in main_symptoms[:3]:
                pulse_knowledge.extend(
                    await self.api_manager.search_pulse_knowledge(symptom)
                )
        
        # 去重並評估
        unique_pulses = {p.get('name'): p for p in pulse_knowledge if p.get('name')}.values()
        
        integration = {
            'pulse_knowledge_available': len(unique_pulses) > 0,
            'available_knowledge': list(unique_pulses)[:5],  # 取前5個最相關
            'integration_quality': min(len(unique_pulses) / 3.0, 1.0),
            'diagnostic_support': [
                {
                    'pulse_name': pulse.get('name'),
                    'main_disease': pulse.get('main_disease'),
                    'symptoms_match': self._calculate_symptom_match(
                        pulse.get('symptoms', ''), main_symptoms
                    )
                }
                for pulse in list(unique_pulses)[:3]
            ]
        }
        
        return integration
    
    def _identify_risk_factors_v1(self, basic_info: Dict, symptom_analysis: Dict) -> List[str]:
        """識別風險因子 v1.0"""
        risk_factors = []
        
        # 年齡風險
        age = basic_info.get('age')
        if age:
            try:
                age_num = int(age)
                if age_num > 70:
                    risk_factors.append('高齡風險')
                elif age_num < 18:
                    risk_factors.append('兒童用藥風險')
            except:
                pass
        
        # 症狀嚴重程度風險
        severity = symptom_analysis.get('symptom_severity', 'unknown')
        if severity == 'severe':
            risk_factors.append('症狀嚴重需謹慎處理')
        
        return risk_factors
    
    def _set_diagnostic_priorities_v1(self, symptom_analysis: Dict, pulse_analysis: Dict) -> List[str]:
        """設定診斷優先級 v1.0"""
        priorities = []
        
        # 基於症狀嚴重程度
        severity = symptom_analysis.get('symptom_severity', 'unknown')
        if severity == 'severe':
            priorities.append('急性症狀處理優先')
        
        # v1.0 基於脈診資訊
        if pulse_analysis.get('diagnostic_significance'):
            priorities.append('結合脈診進行精準診斷')
        
        if not priorities:
            priorities.append('標準診斷流程')
        
        return priorities
    
    def _calculate_analysis_confidence_v1(self, analysis: Dict) -> float:
        """計算分析信心度 v1.0"""
        confidence = 0.5  # 基礎信心度
        
        # 有主要症狀
        if analysis.get('主要症狀'):
            confidence += 0.2
        
        # 有脈診資訊 (v1.0)
        if analysis.get('pulse_integration', {}).get('pulse_knowledge_available'):
            confidence += 0.2
        
        # 有體質特徵
        if analysis.get('體質特徵'):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    # 輔助解析方法
    def _parse_main_symptoms(self, response: str, symptoms) -> List[str]:
        """解析主要症狀"""
        if isinstance(symptoms, list):
            return symptoms[:3]
        elif isinstance(symptoms, str):
            return [symptoms.strip()] if symptoms.strip() else []
        return []
    
    def _parse_constitution_features(self, response: str) -> List[str]:
        """解析體質特徵"""
        constitution_keywords = ['虛', '實', '寒', '熱', '濕', '燥', '氣', '血']
        features = []
        for keyword in constitution_keywords:
            if keyword in response:
                features.append(f"{keyword}性體質特徵")
        return features[:3]
    
    def _parse_history_info(self, response: str, history) -> List[str]:
        """解析病史資訊"""
        if isinstance(history, str) and history.strip():
            return [history.strip()]
        return []
    
    def _parse_environmental_factors(self, response: str) -> List[str]:
        """解析環境因素"""
        env_keywords = ['天氣', '季節', '工作', '壓力', '飲食']
        factors = []
        for keyword in env_keywords:
            if keyword in response:
                factors.append(f"{keyword}相關因素")
        return factors[:2]
    
    def _extract_age_info(self, response: str):
        """提取年齡資訊"""
        return None  # 實際可以用正則表達式提取
    
    def _extract_gender_info(self, response: str):
        """提取性別資訊"""
        return None  # 實際可以用正則表達式提取
    
    def _extract_pulse_description(self, response: str) -> str:
        """提取脈象描述 v1.0"""
        pulse_keywords = ['脈', '浮', '沉', '遲', '數', '滑', '澀']
        for keyword in pulse_keywords:
            if keyword in response:
                # 簡單提取包含脈象關鍵詞的句子
                sentences = response.split('。')
                for sentence in sentences:
                    if keyword in sentence:
                        return sentence.strip()
        return ''
    
    def _extract_diagnostic_direction(self, response: str) -> str:
        """提取診斷方向"""
        return "基於症狀分析的診斷方向"  # 簡化實現
    
    def _assess_analysis_quality(self, response: str) -> float:
        """評估分析品質"""
        return 0.8 if len(response) > 100 else 0.5
    
    def _extract_primary_symptoms(self, response: str) -> List[str]:
        """提取主要症狀"""
        return ["頭痛", "失眠"]  # 簡化實現
    
    def _extract_secondary_symptoms(self, response: str) -> List[str]:
        """提取次要症狀"""
        return ["疲勞"]  # 簡化實現
    
    def _extract_severity(self, response: str) -> str:
        """提取嚴重程度"""
        if '嚴重' in response:
            return 'severe'
        elif '中等' in response:
            return 'moderate'
        else:
            return 'mild'
    
    def _extract_duration(self, response: str) -> str:
        """提取持續時間"""
        return "unknown"  # 簡化實現
    
    def _extract_pattern(self, response: str) -> str:
        """提取症狀模式"""
        return "需進一步觀察"  # 簡化實現
    
    def _extract_pulse_patterns(self, response: str) -> List[str]:
        """提取脈象模式 v1.0"""
        pulse_patterns = ['浮脈', '沉脈', '數脈', '遲脈', '滑脈', '澀脈']
        found_patterns = [pattern for pattern in pulse_patterns if pattern in response]
        return found_patterns[:3]
    
    def _assess_pulse_quality(self, pulse_knowledge: List[Dict]) -> str:
        """評估脈診品質 v1.0"""
        if not pulse_knowledge:
            return 'insufficient'
        elif len(pulse_knowledge) >= 3:
            return 'good'
        else:
            return 'fair'
    
    def _calculate_symptom_match(self, pulse_symptoms: str, patient_symptoms: List[str]) -> float:
        """計算症狀匹配度 v1.0"""
        if not pulse_symptoms or not patient_symptoms:
            return 0.0
        
        pulse_words = set(pulse_symptoms.split())
        patient_words = set(' '.join(patient_symptoms).split())
        
        if not pulse_words or not patient_words:
            return 0.0
        
        intersection = len(pulse_words & patient_words)
        union = len(pulse_words | patient_words)
        
        return intersection / union if union > 0 else 0.0
