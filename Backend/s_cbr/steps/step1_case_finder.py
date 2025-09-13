"""
STEP 1: 高相關案例搜尋器 v1.0

v1.0 功能：
- 整合 Case 和 PulsePJ 知識庫搜尋
- 智能特徵分析
- 多維度相似度計算
- 搜尋結果優化

版本：v1.0
"""

from typing import Dict, Any, List, Optional
import asyncio
from s_cbr.utils.api_manager import SCBRAPIManager
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger

class Step1CaseFinder:
    """
    STEP 1: 高相關案例搜尋器 v1.0
    
    v1.0 特色：
    - 同時搜尋 Case 真實案例和 PulsePJ 脈診知識
    - 智能特徵提取和匹配
    - 多維度相似度評估
    - 自適應搜尋策略
    """
    
    def __init__(self):
        """初始化案例搜尋器 v1.0"""
        self.config = SCBRConfig()
        self.api_manager = SCBRAPIManager()
        self.logger = SpiralLogger.get_logger("Step1CaseFinder")
        self.version = "1.0"
        
        self.logger.info(f"STEP 1 案例搜尋器 v{self.version} 初始化完成")
    
    async def find_most_similar_case(self, patient_analysis: Dict[str, Any], 
                                   search_criteria: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        尋找最相似的案例 v1.0
        
        v1.0 流程：
        1. 分析患者特徵
        2. 構建搜尋策略
        3. 並行搜尋 Case 和 PulsePJ
        4. 綜合評估和排序
        5. 返回最佳匹配結果
        
        參數：
            patient_analysis: 患者特徵分析結果
            search_criteria: 搜尋條件（可選）
            
        返回：
            包含最佳匹配案例和相關脈診知識的字典
        """
        self.logger.info("開始執行 STEP 1: 尋找高相關案例")
        
        try:
            # v1.0 Step 1.1: 準備搜尋查詢
            search_query = self._prepare_search_query(patient_analysis, search_criteria)
            
            # v1.0 Step 1.2: 執行綜合搜尋
            search_results = await self.api_manager.comprehensive_search(
                query_text=search_query['text'],
                patient_context=search_query['context']
            )
            
            if search_results.get('error'):
                self.logger.error(f"搜尋執行失敗: {search_results['error']}")
                return self._create_empty_result(search_results['error'])
            
            # v1.0 Step 1.3: 分析搜尋結果
            analysis_result = self._analyze_search_results(search_results, patient_analysis)
            
            # v1.0 Step 1.4: 選擇最佳匹配案例
            best_match = self._select_best_match(analysis_result)
            
            # v1.0 Step 1.5: 生成結果報告
            final_result = self._generate_search_report(best_match, analysis_result, search_results)
            
            self.logger.info(f"STEP 1 完成 - 找到最佳匹配案例，相似度: {final_result.get('similarity', 0):.3f}")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"STEP 1 執行異常: {str(e)}")
            return self._create_error_result(str(e))
    
    def _prepare_search_query(self, patient_analysis: Dict[str, Any], 
                            search_criteria: Dict[str, Any] = None) -> Dict[str, str]:
        """
        準備搜尋查詢 v1.0
        
        v1.0 特色：
        - 智能提取關鍵搜尋詞
        - 構建結構化查詢上下文
        - 優化搜尋效果
        """
        # 提取主要症狀
        main_symptoms = patient_analysis.get('主要症狀', [])
        if isinstance(main_symptoms, str):
            main_symptoms = [main_symptoms]
        
        # 提取體質特徵
        constitution = patient_analysis.get('體質特徵', [])
        if isinstance(constitution, str):
            constitution = [constitution]
        
        # 提取病史資訊
        history = patient_analysis.get('病史資訊', [])
        if isinstance(history, str):
            history = [history]
        
        # 構建搜尋文本
        search_components = []
        search_components.extend(main_symptoms)
        search_components.extend(constitution)
        search_components.extend(history)
        
        search_text = " ".join(filter(None, search_components))
        
        # 構建搜尋上下文
        search_context = {
            'symptoms': main_symptoms,
            'constitution': constitution,
            'history': history,
            'age': patient_analysis.get('年齡'),
            'gender': patient_analysis.get('性別'),
            'pulse_text': patient_analysis.get('脈象描述', ''),
        }
        
        # 添加搜尋條件過濾
        if search_criteria:
            search_context.update(search_criteria)
        
        self.logger.debug(f"搜尋查詢準備完成 - 文本長度: {len(search_text)}")
        
        return {
            'text': search_text,
            'context': search_context
        }
    
    def _analyze_search_results(self, search_results: Dict[str, Any], 
                              patient_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析搜尋結果 v1.0
        
        v1.0 分析維度：
        - Case 案例相似度分析
        - PulsePJ 脈診知識匹配度
        - 案例與脈診的整合度評估
        - 患者特徵匹配度計算
        """
        similar_cases = search_results.get('similar_cases', [])
        pulse_knowledge = search_results.get('pulse_knowledge', [])
        integration_analysis = search_results.get('integration_analysis', {})
        
        analysis = {
            'case_analysis': self._analyze_case_matches(similar_cases, patient_analysis),
            'pulse_analysis': self._analyze_pulse_matches(pulse_knowledge, patient_analysis),
            'integration_score': integration_analysis.get('consistency_score', 0.0),
            'overall_confidence': 0.0,
            'matching_factors': [],
            'risk_factors': []
        }
        
        # 計算整體信心度
        case_confidence = analysis['case_analysis'].get('average_confidence', 0.0)
        pulse_confidence = analysis['pulse_analysis'].get('average_confidence', 0.0)
        integration_confidence = analysis['integration_score']
        
        # v1.0 綜合信心度算法
        analysis['overall_confidence'] = (
            case_confidence * 0.5 +
            pulse_confidence * 0.3 + 
            integration_confidence * 0.2
        )
        
        # 識別匹配因子
        if case_confidence > 0.7:
            analysis['matching_factors'].append('高相似度歷史案例')
        if pulse_confidence > 0.7:
            analysis['matching_factors'].append('強脈診知識支持')
        if integration_confidence > 0.6:
            analysis['matching_factors'].append('案例脈診高度一致')
        
        # 識別風險因子
        if case_confidence < 0.5:
            analysis['risk_factors'].append('相似案例不足')
        if pulse_confidence < 0.5:
            analysis['risk_factors'].append('脈診知識匹配度低')
        if integration_confidence < 0.3:
            analysis['risk_factors'].append('案例與脈診不一致')
        
        return analysis
    
    def _analyze_case_matches(self, cases: List[Dict], patient_analysis: Dict) -> Dict[str, Any]:
        """分析 Case 匹配結果 v1.0"""
        if not cases:
            return {
                'total_cases': 0,
                'average_confidence': 0.0,
                'best_match': None,
                'matching_patterns': []
            }
        
        # 計算平均相似度
        similarities = [case.get('similarity', 0.0) for case in cases]
        average_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        
        # 尋找最佳匹配
        best_case = max(cases, key=lambda x: x.get('similarity', 0.0))
        
        # 分析匹配模式
        matching_patterns = []
        for case in cases[:3]:  # 分析前3個最佳案例
            patterns = self._identify_case_patterns(case, patient_analysis)
            matching_patterns.extend(patterns)
        
        return {
            'total_cases': len(cases),
            'average_confidence': average_similarity,
            'best_match': best_case,
            'matching_patterns': list(set(matching_patterns))  # 去重
        }
    
    def _analyze_pulse_matches(self, pulse_knowledge: List[Dict], patient_analysis: Dict) -> Dict[str, Any]:
        """分析 PulsePJ 匹配結果 v1.0"""
        if not pulse_knowledge:
            return {
                'total_knowledge': 0,
                'average_confidence': 0.0,
                'relevant_pulses': [],
                'diagnostic_insights': []
            }
        
        # 簡單的匹配度評估（v1.0基礎實現）
        patient_symptoms = patient_analysis.get('主要症狀', [])
        if isinstance(patient_symptoms, str):
            patient_symptoms = [patient_symptoms]
        
        relevant_pulses = []
        total_relevance = 0.0
        
        for pulse in pulse_knowledge:
            relevance_score = self._calculate_pulse_relevance(pulse, patient_symptoms)
            total_relevance += relevance_score
            
            if relevance_score > 0.3:  # 閾值過濾
                relevant_pulses.append({
                    'pulse_name': pulse.get('name'),
                    'relevance': relevance_score,
                    'main_disease': pulse.get('main_disease'),
                    'description': pulse.get('description')
                })
        
        average_confidence = total_relevance / len(pulse_knowledge) if pulse_knowledge else 0.0
        
        # 生成診斷洞察
        diagnostic_insights = []
        for pulse in relevant_pulses[:2]:  # 取前2個最相關
            if pulse['main_disease']:
                diagnostic_insights.append(f"脈象 {pulse['pulse_name']} 提示可能的 {pulse['main_disease']}")
        
        return {
            'total_knowledge': len(pulse_knowledge),
            'average_confidence': average_confidence,
            'relevant_pulses': relevant_pulses,
            'diagnostic_insights': diagnostic_insights
        }
    
    def _identify_case_patterns(self, case: Dict, patient_analysis: Dict) -> List[str]:
        """識別案例匹配模式 v1.0"""
        patterns = []
        
        # 年齡匹配
        case_age = case.get('age')
        patient_age = patient_analysis.get('年齡')
        if case_age and patient_age:
            try:
                case_age_num = int(case_age)
                patient_age_num = int(patient_age)
                if abs(case_age_num - patient_age_num) <= 10:
                    patterns.append('年齡相近')
            except:
                pass
        
        # 性別匹配
        if case.get('gender') == patient_analysis.get('性別'):
            patterns.append('性別相同')
        
        # 主訴相似性
        case_complaint = case.get('chief_complaint', '')
        patient_symptoms = ' '.join(patient_analysis.get('主要症狀', []))
        if case_complaint and patient_symptoms:
            # 簡單的關鍵詞匹配
            common_words = set(case_complaint.split()) & set(patient_symptoms.split())
            if len(common_words) >= 2:
                patterns.append('主訴相似')
        
        return patterns
    
    def _calculate_pulse_relevance(self, pulse: Dict, patient_symptoms: List[str]) -> float:
        """計算脈診相關性 v1.0"""
        if not patient_symptoms:
            return 0.0
        
        # 獲取脈診相關症狀
        pulse_symptoms = pulse.get('symptoms', '')
        if not pulse_symptoms:
            return 0.0
        
        # 簡單的關鍵詞匹配評分
        patient_keywords = set(' '.join(patient_symptoms).split())
        pulse_keywords = set(pulse_symptoms.split())
        
        if not patient_keywords or not pulse_keywords:
            return 0.0
        
        # 計算 Jaccard 相似度
        intersection = len(patient_keywords & pulse_keywords)
        union = len(patient_keywords | pulse_keywords)
        
        return intersection / union if union > 0 else 0.0
    
    def _select_best_match(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """選擇最佳匹配案例 v1.0"""
        case_analysis = analysis_result['case_analysis']
        pulse_analysis = analysis_result['pulse_analysis']
        
        # 主要基於 Case 匹配結果
        best_case = case_analysis.get('best_match')
        
        if not best_case:
            self.logger.warning("未找到匹配的 Case 案例")
            return {
                'case': None,
                'pulse_support': pulse_analysis.get('relevant_pulses', []),
                'confidence': 0.0,
                'reason': '無匹配案例'
            }
        
        # 綜合評估
        case_confidence = best_case.get('similarity', 0.0)
        pulse_support = pulse_analysis.get('relevant_pulses', [])
        overall_confidence = analysis_result.get('overall_confidence', 0.0)
        
        return {
            'case': best_case,
            'pulse_support': pulse_support,
            'confidence': overall_confidence,
            'case_confidence': case_confidence,
            'pulse_insights': pulse_analysis.get('diagnostic_insights', []),
            'matching_factors': analysis_result.get('matching_factors', []),
            'reason': f'相似度 {case_confidence:.3f}，整合度 {overall_confidence:.3f}'
        }
    
    def _generate_search_report(self, best_match: Dict[str, Any], 
                              analysis_result: Dict[str, Any],
                              search_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成搜尋報告 v1.0"""
        return {
            'found_case': best_match['case'] is not None,
            'best_match': best_match['case'],
            'similarity': best_match.get('confidence', 0.0),
            'case_similarity': best_match.get('case_confidence', 0.0),
            'pulse_support': best_match.get('pulse_support', []),
            'pulse_insights': best_match.get('pulse_insights', []),
            'matching_factors': best_match.get('matching_factors', []),
            'risk_factors': analysis_result.get('risk_factors', []),
            'search_summary': search_results.get('search_summary', {}),
            'confidence_level': self._determine_confidence_level(best_match.get('confidence', 0.0)),
            'recommendation': self._generate_search_recommendation(best_match, analysis_result),
            'version': self.version
        }
    
    def _determine_confidence_level(self, confidence: float) -> str:
        """確定信心等級 v1.0"""
        if confidence >= 0.8:
            return 'high'
        elif confidence >= 0.6:
            return 'medium'
        elif confidence >= 0.4:
            return 'low'
        else:
            return 'very_low'
    
    def _generate_search_recommendation(self, best_match: Dict, analysis_result: Dict) -> str:
        """生成搜尋建議 v1.0"""
        confidence = best_match.get('confidence', 0.0)
        matching_factors = best_match.get('matching_factors', [])
        risk_factors = analysis_result.get('risk_factors', [])
        
        if confidence >= 0.8:
            return "找到高度相似的參考案例，可作為主要依據"
        elif confidence >= 0.6:
            return "找到中度相似的參考案例，建議結合其他資訊判斷"
        elif confidence >= 0.4:
            return "找到低相似度案例，建議謹慎參考並尋求更多證據"
        else:
            return "相似案例不足，建議採用新案例推理模式"
    
    # 備選搜尋策略 v1.0
    async def find_with_relaxed_criteria(self, relaxed_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """使用放寬條件搜尋 v1.0"""
        self.logger.info("執行放寬條件搜尋")
        
        try:
            # 降低相似度閾值
            original_threshold = self.config.SPIRAL_SETTINGS['similarity_threshold']
            relaxed_threshold = max(0.3, original_threshold - 0.2)
            
            # 擴大搜尋範圍
            expanded_limit = self.config.SPIRAL_SETTINGS['case_search_limit'] * 2
            
            # 構建放寬查詢
            relaxed_query = relaxed_criteria.get('query_text', '')
            relaxed_context = relaxed_criteria.get('context', {})
            
            # 執行搜尋
            search_results = await self.api_manager.comprehensive_search(
                query_text=relaxed_query,
                patient_context=relaxed_context
            )
            
            if search_results.get('error'):
                return self._create_empty_result(search_results['error'])
            
            # 簡化分析（放寬模式）
            best_case = None
            if search_results.get('similar_cases'):
                best_case = search_results['similar_cases'][0]
            
            return {
                'found_case': best_case is not None,
                'best_match': best_case,
                'similarity': best_case.get('similarity', 0.0) if best_case else 0.0,
                'search_mode': 'relaxed',
                'threshold_used': relaxed_threshold,
                'version': self.version
            }
            
        except Exception as e:
            self.logger.error(f"放寬搜尋失敗: {str(e)}")
            return self._create_error_result(str(e))
    
    # 工具方法
    def _create_empty_result(self, reason: str = "無匹配結果") -> Dict[str, Any]:
        """創建空結果 v1.0"""
        return {
            'found_case': False,
            'best_match': None,
            'similarity': 0.0,
            'reason': reason,
            'recommendation': '建議提供更多症狀資訊或採用專家諮詢',
            'version': self.version
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """創建錯誤結果 v1.0"""
        return {
            'found_case': False,
            'error': True,
            'error_message': error_message,
            'similarity': 0.0,
            'recommendation': '系統異常，請稍後重試',
            'version': self.version
        }
