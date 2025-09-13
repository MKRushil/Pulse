"""
回饋智能體 v1.0

v1.0 功能：
- 治療回饋深度分析
- 脈診效果評估
- 學習洞察提取
- 知識更新建議

版本：v1.0
"""

from typing import Dict, Any, List
from s_cbr.utils.api_manager import SCBRAPIManager
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger

class FeedbackAgent:
    """
    回饋智能體 v1.0
    
    v1.0 特色：
    - 多維度回饋分析
    - 脈診效果整合評估
    - 智能學習萃取
    - 知識庫更新優化
    """
    
    def __init__(self):
        """初始化回饋智能體 v1.0"""
        self.config = SCBRConfig()
        self.api_manager = SCBRAPIManager()
        self.logger = SpiralLogger.get_logger("FeedbackAgent")
        self.version = "1.0"
        
        self.logger.info(f"回饋智能體 v{self.version} 初始化完成")
    
    async def analyze_treatment_feedback_v1(self, user_feedback: Dict[str, Any],
                                           monitoring_result: Dict[str, Any],
                                           pulse_support: List[Dict],
                                           context: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析治療回饋 v1.0 (整合脈診效果評估)
        
        v1.0 分析維度：
        1. 用戶滿意度分析
        2. 臨床效果評估
        3. 脈診一致性分析
        4. 學習價值評估
        5. 改進建議生成
        """
        self.logger.info("分析治療回饋 v1.0")
        
        try:
            # Step 1: 用戶回饋解析
            feedback_parsing = await self._parse_user_feedback_v1(user_feedback)
            
            # Step 2: 臨床效果評估
            clinical_effectiveness = await self._evaluate_clinical_effectiveness_v1(
                user_feedback, monitoring_result
            )
            
            # Step 3: 脈診效果分析 (v1.0)
            pulse_effectiveness = await self._analyze_pulse_effectiveness_v1(
                pulse_support, user_feedback, monitoring_result, context
            )
            
            # Step 4: 綜合療效評估
            comprehensive_assessment = await self._conduct_comprehensive_assessment_v1(
                feedback_parsing, clinical_effectiveness, pulse_effectiveness
            )
            
            # Step 5: 學習洞察萃取
            learning_insights = await self._extract_learning_insights_v1(
                comprehensive_assessment, context
            )
            
            # Step 6: 改進建議生成
            improvement_recommendations = await self._generate_improvement_recommendations_v1(
                comprehensive_assessment, learning_insights, pulse_effectiveness
            )
            
            # 組裝分析結果
            analysis_result = {
                'analysis_id': f"feedback_v1_{context.get('session_id', '')[:8]}",
                'feedback_parsing': feedback_parsing,
                'clinical_effectiveness': clinical_effectiveness,
                'pulse_effectiveness': pulse_effectiveness,  # v1.0 新增
                'comprehensive_assessment': comprehensive_assessment,
                'learning_insights': learning_insights,
                'improvement_recommendations': improvement_recommendations,
                'is_effective': comprehensive_assessment.get('overall_effectiveness', False),
                'satisfaction_score': comprehensive_assessment.get('satisfaction_score', 0.0),
                'confidence_score': self._calculate_analysis_confidence_v1(comprehensive_assessment),
                'ai_insights': self._generate_ai_insights_v1(comprehensive_assessment, pulse_effectiveness),
                'recommended_action': self._determine_recommended_action_v1(comprehensive_assessment),
                'timestamp': context.get('timestamp'),
                'version': self.version
            }
            
            self.logger.info(f"回饋分析 v1.0 完成 - 有效性: {analysis_result['is_effective']}, "
                           f"滿意度: {analysis_result['satisfaction_score']:.3f}")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"回饋分析失敗: {str(e)}")
            return self._create_error_analysis_v1(str(e))
    
    async def _parse_user_feedback_v1(self, user_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """解析用戶回饋 v1.0"""
        
        # 提取量化指標
        satisfaction_rating = user_feedback.get('satisfaction_rating', 0)
        symptom_improvement = user_feedback.get('symptom_improvement_rating', 0)
        
        # 分析文字回饋
        feedback_text = user_feedback.get('feedback_text', '')
        text_analysis = await self._analyze_feedback_text_v1(feedback_text)
        
        # 提取關鍵資訊
        key_points = self._extract_key_feedback_points_v1(user_feedback)
        
        # 情感分析
        sentiment_analysis = self._analyze_feedback_sentiment_v1(feedback_text)
        
        parsing_result = {
            'quantitative_metrics': {
                'satisfaction_rating': satisfaction_rating / 10.0 if satisfaction_rating > 0 else 0.5,
                'symptom_improvement': symptom_improvement / 10.0 if symptom_improvement > 0 else 0.5,
                'overall_score': (satisfaction_rating + symptom_improvement) / 20.0 if satisfaction_rating and symptom_improvement else 0.5
            },
            'text_analysis': text_analysis,
            'key_points': key_points,
            'sentiment_analysis': sentiment_analysis,
            'feedback_completeness': self._assess_feedback_completeness_v1(user_feedback),
            'feedback_reliability': self._assess_feedback_reliability_v1(user_feedback, text_analysis)
        }
        
        return parsing_result
    
    async def _evaluate_clinical_effectiveness_v1(self, user_feedback: Dict[str, Any],
                                                 monitoring_result: Dict[str, Any]) -> Dict[str, Any]:
        """評估臨床效果 v1.0"""
        
        effectiveness_prompt = f"""
作為專業中醫回饋分析智能體，請評估治療的臨床效果：

【用戶回饋】
主觀改善感受: {user_feedback.get('subjective_improvement', '未提及')}
症狀變化描述: {user_feedback.get('symptom_changes', '未描述')}
整體滿意度: {user_feedback.get('satisfaction_rating', 0)}/10

【監控結果】
安全性評分: {monitoring_result.get('safety_score', 0)}
有效性評分: {monitoring_result.get('effectiveness_score', 0)}
監控期間發現: {monitoring_result.get('monitoring_findings', '無特殊發現')}

請評估：
1. 客觀臨床效果 (改善/無效/惡化)
2. 主客觀一致性 (高/中/低)
3. 療效持續性預測 (良好/一般/不佳)
4. 臨床意義評估 (顯著/中等/輕微)
5. 安全性表現 (良好/可接受/需關注)

請提供詳細的臨床分析。
"""
        
        effectiveness_response = await self.api_manager.generate_llm_response(
            effectiveness_prompt,
            self.config.get_agent_config('feedback_agent')
        )
        
        # 結構化臨床效果評估
        clinical_evaluation = self._structure_clinical_evaluation_v1(
            effectiveness_response, user_feedback, monitoring_result
        )
        
        return clinical_evaluation
    
    async def _analyze_pulse_effectiveness_v1(self, pulse_support: List[Dict],
                                             user_feedback: Dict[str, Any],
                                             monitoring_result: Dict[str, Any],
                                             context: Dict[str, Any]) -> Dict[str, Any]:
        """分析脈診效果 v1.0"""
        
        if not pulse_support:
            return {
                'pulse_analysis_feasible': False,
                'pulse_theory_validation': 0.5,  # 中性評分
                'pulse_guidance_effectiveness': 0.0,
                'pulse_learning_value': 0.0,
                'recommendations': ['建議補充脈診資訊以提升分析品質']
            }
        
        # 構建脈診效果分析提示
        pulse_analysis_prompt = f"""
基於脈診理論，分析治療效果與脈診預測的一致性：

【脈診支持資訊】
"""
        
        for pulse in pulse_support[:3]:
            pulse_analysis_prompt += f"""
脈象: {pulse.get('name', '')}
相關疾病: {pulse.get('main_disease', '')}  
預期症狀: {pulse.get('symptoms', '')}
---
"""
        
        pulse_analysis_prompt += f"""
【實際治療結果】
患者主觀改善: {user_feedback.get('subjective_improvement', '未描述')}
客觀監控結果: {monitoring_result.get('effectiveness_score', 0)}/10
脈診一致性: {monitoring_result.get('pulse_consistency_score', 0.5)}

【分析要求】
1. 脈診預測與實際效果的符合程度 (0-10分)
2. 脈診理論在本案例的驗證效果 (有效/部分有效/無效)
3. 脈診指導對治療的貢獻度 (高/中/低)
4. 本案例對脈診知識庫的學習價值 (高/中/低)
5. 脈診理論改進建議

請提供專業的脈診效果分析。
"""
        
        pulse_analysis_response = await self.api_manager.generate_llm_response(
            pulse_analysis_prompt,
            self.config.get_agent_config('feedback_agent')
        )
        
        # 結構化脈診效果分析
        pulse_effectiveness = self._structure_pulse_effectiveness_v1(
            pulse_analysis_response, pulse_support, user_feedback, monitoring_result
        )
        
        return pulse_effectiveness
    
    async def _conduct_comprehensive_assessment_v1(self, feedback_parsing: Dict[str, Any],
                                                  clinical_effectiveness: Dict[str, Any],
                                                  pulse_effectiveness: Dict[str, Any]) -> Dict[str, Any]:
        """綜合療效評估 v1.0"""
        
        # 用戶滿意度權重評估
        user_satisfaction = feedback_parsing.get('quantitative_metrics', {}).get('satisfaction_rating', 0.5)
        
        # 臨床效果權重評估  
        clinical_score = clinical_effectiveness.get('clinical_effectiveness_score', 0.5)
        
        # v1.0 脈診效果權重評估
        pulse_score = pulse_effectiveness.get('pulse_theory_validation', 0.5)
        
        # 綜合評分計算 (v1.0 權重分配)
        comprehensive_score = (
            user_satisfaction * 0.4 +          # 用戶體驗權重
            clinical_score * 0.35 +            # 臨床效果權重
            pulse_score * 0.25                 # v1.0 脈診驗證權重
        )
        
        # 效果等級判定
        if comprehensive_score >= 0.8:
            effectiveness_level = 'excellent'
            overall_effectiveness = True
        elif comprehensive_score >= 0.65:
            effectiveness_level = 'good'
            overall_effectiveness = True
        elif comprehensive_score >= 0.5:
            effectiveness_level = 'moderate'
            overall_effectiveness = True
        elif comprehensive_score >= 0.35:
            effectiveness_level = 'poor'
            overall_effectiveness = False
        else:
            effectiveness_level = 'ineffective'
            overall_effectiveness = False
        
        # 成功因子分析
        success_factors = self._identify_success_factors_v1(
            feedback_parsing, clinical_effectiveness, pulse_effectiveness
        )
        
        # 改進領域識別
        improvement_areas = self._identify_improvement_areas_v1(
            feedback_parsing, clinical_effectiveness, pulse_effectiveness
        )
        
        comprehensive_assessment = {
            'satisfaction_score': user_satisfaction,
            'clinical_score': clinical_score,
            'pulse_validation_score': pulse_score,  # v1.0 新增
            'comprehensive_score': comprehensive_score,
            'effectiveness_level': effectiveness_level,
            'overall_effectiveness': overall_effectiveness,
            'success_factors': success_factors,
            'improvement_areas': improvement_areas,
            'assessment_confidence': self._calculate_assessment_confidence_v1(
                feedback_parsing, clinical_effectiveness, pulse_effectiveness
            ),
            'key_insights': self._extract_key_assessment_insights_v1(
                comprehensive_score, success_factors, improvement_areas
            )
        }
        
        return comprehensive_assessment
    
    async def _extract_learning_insights_v1(self, comprehensive_assessment: Dict[str, Any],
                                           context: Dict[str, Any]) -> Dict[str, Any]:
        """萃取學習洞察 v1.0"""
        
        insights = {
            'case_learning_value': self._assess_case_learning_value_v1(comprehensive_assessment),
            'pattern_insights': self._extract_pattern_insights_v1(comprehensive_assessment, context),
            'methodology_insights': self._extract_methodology_insights_v1(comprehensive_assessment),
            'pulse_insights': self._extract_pulse_learning_insights_v1(comprehensive_assessment),  # v1.0
            'improvement_insights': self._extract_improvement_insights_v1(comprehensive_assessment),
            'knowledge_gaps': self._identify_knowledge_gaps_v1(comprehensive_assessment, context),
            'best_practices': self._extract_best_practices_v1(comprehensive_assessment),
            'learning_recommendations': self._generate_learning_recommendations_v1(comprehensive_assessment)
        }
        
        # 學習價值總評
        insights['overall_learning_value'] = self._calculate_overall_learning_value_v1(insights)
        
        return insights
    
    async def _generate_improvement_recommendations_v1(self, comprehensive_assessment: Dict[str, Any],
                                                      learning_insights: Dict[str, Any],
                                                      pulse_effectiveness: Dict[str, Any]) -> Dict[str, Any]:
        """生成改進建議 v1.0"""
        
        recommendations = {
            'immediate_actions': [],
            'short_term_improvements': [],
            'long_term_strategies': [],
            'pulse_specific_recommendations': [],  # v1.0 新增
            'system_enhancements': [],
            'knowledge_updates': [],
            'process_optimizations': []
        }
        
        # 基於綜合評估的建議
        effectiveness_level = comprehensive_assessment.get('effectiveness_level', 'moderate')
        
        if effectiveness_level in ['poor', 'ineffective']:
            recommendations['immediate_actions'].extend([
                '重新評估診斷準確性',
                '檢討治療方案選擇',
                '增強患者溝通和教育'
            ])
            recommendations['short_term_improvements'].extend([
                '優化案例匹配算法',
                '改進適配策略',
                '強化安全監控'
            ])
        
        elif effectiveness_level == 'moderate':
            recommendations['short_term_improvements'].extend([
                '微調治療參數',
                '優化患者體驗',
                '加強療效監控'
            ])
        
        else:  # good, excellent
            recommendations['long_term_strategies'].extend([
                '推廣成功模式',
                '萃取最佳實踐',
                '持續優化流程'
            ])
        
        # v1.0 脈診特殊建議
        pulse_guidance_effectiveness = pulse_effectiveness.get('pulse_guidance_effectiveness', 0.0)
        if pulse_guidance_effectiveness < 0.5:
            recommendations['pulse_specific_recommendations'].extend([
                '改進脈診知識匹配準確性',
                '增強脈診理論驗證機制',
                '擴充脈診知識庫內容'
            ])
        elif pulse_guidance_effectiveness > 0.8:
            recommendations['pulse_specific_recommendations'].extend([
                '推廣優秀脈診整合模式',
                '深化脈診理論應用',
                '建立脈診效果標準'
            ])
        
        # 基於學習洞察的建議
        learning_value = learning_insights.get('overall_learning_value', 0.5)
        if learning_value > 0.7:
            recommendations['knowledge_updates'].append('將成功案例納入知識庫')
        
        if learning_insights.get('knowledge_gaps'):
            recommendations['system_enhancements'].extend([
                '填補已識別的知識空白',
                '強化相關領域的案例收集'
            ])
        
        # 生成優先級
        recommendations['priority_matrix'] = self._create_priority_matrix_v1(recommendations)
        
        return recommendations
    
    # 輔助分析方法
    async def _analyze_feedback_text_v1(self, feedback_text: str) -> Dict[str, Any]:
        """分析回饋文字 v1.0"""
        if not feedback_text:
            return {
                'key_themes': [],
                'positive_aspects': [],
                'negative_aspects': [],
                'suggestions': [],
                'text_quality': 'insufficient'
            }
        
        # 簡單的文字分析（可以用更複雜的 NLP）
        positive_keywords = ['好', '有效', '改善', '滿意', '感謝', '推薦']
        negative_keywords = ['不好', '無效', '惡化', '不滿', '失望', '痛苦']
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in feedback_text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in feedback_text)
        
        return {
            'key_themes': self._extract_themes_from_text(feedback_text),
            'positive_aspects': [f'正面關鍵詞出現 {positive_count} 次'] if positive_count > 0 else [],
            'negative_aspects': [f'負面關鍵詞出現 {negative_count} 次'] if negative_count > 0 else [],
            'suggestions': self._extract_suggestions_from_text(feedback_text),
            'text_quality': 'good' if len(feedback_text) > 50 else 'basic',
            'sentiment_balance': positive_count - negative_count
        }
    
    def _extract_key_feedback_points_v1(self, user_feedback: Dict[str, Any]) -> List[str]:
        """提取關鍵回饋要點 v1.0"""
        key_points = []
        
        # 滿意度相關
        satisfaction = user_feedback.get('satisfaction_rating', 0)
        if satisfaction >= 8:
            key_points.append('高滿意度評價')
        elif satisfaction <= 4:
            key_points.append('低滿意度需要關注')
        
        # 症狀改善相關
        improvement = user_feedback.get('symptom_improvement_rating', 0)
        if improvement >= 7:
            key_points.append('症狀明顯改善')
        elif improvement <= 3:
            key_points.append('症狀改善不明顯')
        
        # 文字回饋相關
        feedback_text = user_feedback.get('feedback_text', '')
        if '脈診' in feedback_text or '脈象' in feedback_text:
            key_points.append('提及脈診相關內容')  # v1.0
        
        if '副作用' in feedback_text or '不適' in feedback_text:
            key_points.append('報告不良反應')
        
        return key_points
    
    def _analyze_feedback_sentiment_v1(self, feedback_text: str) -> Dict[str, Any]:
        """分析回饋情感 v1.0"""
        if not feedback_text:
            return {
                'overall_sentiment': 'neutral',
                'sentiment_confidence': 0.5,
                'emotional_indicators': []
            }
        
        # 簡化的情感分析
        positive_emotions = ['高興', '感謝', '滿意', '信任', '希望']
        negative_emotions = ['失望', '擔心', '痛苦', '不安', '懷疑']
        
        pos_count = sum(1 for emotion in positive_emotions if emotion in feedback_text)
        neg_count = sum(1 for emotion in negative_emotions if emotion in feedback_text)
        
        if pos_count > neg_count:
            sentiment = 'positive'
        elif neg_count > pos_count:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        confidence = abs(pos_count - neg_count) / max(pos_count + neg_count, 1)
        
        return {
            'overall_sentiment': sentiment,
            'sentiment_confidence': confidence,
            'emotional_indicators': {
                'positive_emotions': pos_count,
                'negative_emotions': neg_count
            }
        }
    
    def _assess_feedback_completeness_v1(self, user_feedback: Dict[str, Any]) -> float:
        """評估回饋完整性 v1.0"""
        completeness_score = 0.0
        
        # 量化評分
        if user_feedback.get('satisfaction_rating'):
            completeness_score += 0.3
        
        if user_feedback.get('symptom_improvement_rating'):
            completeness_score += 0.3
        
        # 文字描述
        feedback_text = user_feedback.get('feedback_text', '')
        if len(feedback_text) > 20:
            completeness_score += 0.4
        
        return completeness_score
    
    def _assess_feedback_reliability_v1(self, user_feedback: Dict[str, Any],
                                       text_analysis: Dict[str, Any]) -> float:
        """評估回饋可靠性 v1.0"""
        reliability_score = 0.7  # 基礎可靠性
        
        # 量化評分與文字描述的一致性
        satisfaction_rating = user_feedback.get('satisfaction_rating', 5)
        sentiment_balance = text_analysis.get('sentiment_balance', 0)
        
        # 檢查一致性
        if satisfaction_rating >= 7 and sentiment_balance > 0:
            reliability_score += 0.2  # 正面一致
        elif satisfaction_rating <= 4 and sentiment_balance < 0:
            reliability_score += 0.2  # 負面一致
        elif abs(satisfaction_rating - 5) > 2 and sentiment_balance == 0:
            reliability_score -= 0.1  # 不一致
        
        return min(reliability_score, 1.0)
    
    def _structure_clinical_evaluation_v1(self, evaluation_response: str,
                                         user_feedback: Dict[str, Any],
                                         monitoring_result: Dict[str, Any]) -> Dict[str, Any]:
        """結構化臨床評估 v1.0"""
        # 簡化實現
        safety_score = monitoring_result.get('safety_score', 0.8)
        effectiveness_score = monitoring_result.get('effectiveness_score', 0.7)
        
        return {
            'clinical_effectiveness_score': (safety_score + effectiveness_score) / 2,
            'objective_improvement': 'moderate',
            'subjective_objective_consistency': 'high',
            'sustainability_prediction': 'good',
            'clinical_significance': 'moderate',
            'safety_performance': 'good',
            'detailed_analysis': evaluation_response[:300],
            'evidence_strength': self._assess_evidence_strength_v1(user_feedback, monitoring_result)
        }
    
    def _structure_pulse_effectiveness_v1(self, analysis_response: str,
                                         pulse_support: List[Dict],
                                         user_feedback: Dict[str, Any],
                                         monitoring_result: Dict[str, Any]) -> Dict[str, Any]:
        """結構化脈診效果分析 v1.0"""
        
        pulse_consistency_score = monitoring_result.get('pulse_consistency_score', 0.6)
        
        return {
            'pulse_analysis_feasible': len(pulse_support) > 0,
            'pulse_theory_validation': pulse_consistency_score,
            'pulse_guidance_effectiveness': pulse_consistency_score * 0.8,
            'pulse_learning_value': self._calculate_pulse_learning_value(pulse_support, pulse_consistency_score),
            'theory_practice_alignment': 'good' if pulse_consistency_score > 0.7 else 'moderate',
            'pulse_contribution_assessment': self._assess_pulse_contribution_v1(pulse_support, monitoring_result),
            'detailed_analysis': analysis_response[:300],
            'recommendations': self._generate_pulse_recommendations_v1(pulse_consistency_score, pulse_support)
        }
    
    def _identify_success_factors_v1(self, feedback_parsing: Dict, clinical_effectiveness: Dict, pulse_effectiveness: Dict) -> List[str]:
        """識別成功因子 v1.0"""
        factors = []
        
        if feedback_parsing.get('quantitative_metrics', {}).get('satisfaction_rating', 0) > 0.7:
            factors.append('高用戶滿意度')
        
        if clinical_effectiveness.get('clinical_effectiveness_score', 0) > 0.7:
            factors.append('良好臨床效果')
        
        # v1.0 脈診成功因子
        if pulse_effectiveness.get('pulse_theory_validation', 0) > 0.7:
            factors.append('脈診理論高度驗證')
        
        if pulse_effectiveness.get('pulse_guidance_effectiveness', 0) > 0.6:
            factors.append('有效的脈診指導')
        
        return factors
    
    def _identify_improvement_areas_v1(self, feedback_parsing: Dict, clinical_effectiveness: Dict, pulse_effectiveness: Dict) -> List[str]:
        """識別改進領域 v1.0"""
        areas = []
        
        if feedback_parsing.get('quantitative_metrics', {}).get('satisfaction_rating', 0) < 0.6:
            areas.append('用戶體驗需改善')
        
        if clinical_effectiveness.get('clinical_effectiveness_score', 0) < 0.6:
            areas.append('臨床效果需提升')
        
        # v1.0 脈診改進領域
        if pulse_effectiveness.get('pulse_theory_validation', 0) < 0.5:
            areas.append('脈診理論匹配度待提升')
        
        return areas
    
    def _calculate_assessment_confidence_v1(self, feedback_parsing: Dict, clinical_effectiveness: Dict, pulse_effectiveness: Dict) -> float:
        """計算評估信心度 v1.0"""
        feedback_reliability = feedback_parsing.get('feedback_reliability', 0.5)
        clinical_evidence = clinical_effectiveness.get('evidence_strength', 0.5)
        pulse_analysis_quality = pulse_effectiveness.get('pulse_analysis_feasible', False) and 0.8 or 0.5
        
        confidence = (feedback_reliability * 0.4 + clinical_evidence * 0.4 + pulse_analysis_quality * 0.2)
        return confidence
    
    def _extract_key_assessment_insights_v1(self, comprehensive_score: float, success_factors: List[str], improvement_areas: List[str]) -> List[str]:
        """提取關鍵評估洞察 v1.0"""
        insights = []
        
        if comprehensive_score > 0.8:
            insights.append('治療效果優秀，可作為標桿案例')
        elif comprehensive_score > 0.6:
            insights.append('治療效果良好，適合推廣應用')
        else:
            insights.append('治療效果有待改善，需要調整策略')
        
        if len(success_factors) > len(improvement_areas):
            insights.append('成功因子明顯，值得深入分析')
        
        return insights
    
    # 學習洞察萃取輔助方法
    def _assess_case_learning_value_v1(self, comprehensive_assessment: Dict) -> float:
        """評估案例學習價值 v1.0"""
        effectiveness_level = comprehensive_assessment.get('effectiveness_level', 'moderate')
        confidence = comprehensive_assessment.get('assessment_confidence', 0.5)
        
        value_map = {'excellent': 0.9, 'good': 0.8, 'moderate': 0.6, 'poor': 0.4, 'ineffective': 0.3}
        base_value = value_map.get(effectiveness_level, 0.5)
        
        return base_value * confidence
    
    def _extract_pattern_insights_v1(self, comprehensive_assessment: Dict, context: Dict) -> List[str]:
        """提取模式洞察 v1.0"""
        insights = []
        success_factors = comprehensive_assessment.get('success_factors', [])
        
        if '高用戶滿意度' in success_factors and '良好臨床效果' in success_factors:
            insights.append('用戶滿意度與臨床效果高度相關')
        
        if '脈診理論高度驗證' in success_factors:
            insights.append('脈診理論在此類案例中具有指導價值')
        
        return insights
    
    def _extract_methodology_insights_v1(self, comprehensive_assessment: Dict) -> List[str]:
        """提取方法學洞察 v1.0"""
        return [
            '螺旋推理方法有效性得到驗證',
            '多維度評估提供全面視角',
            'Agentive AI 協作機制運作良好'
        ]
    
    def _extract_pulse_learning_insights_v1(self, comprehensive_assessment: Dict) -> List[str]:
        """提取脈診學習洞察 v1.0"""
        pulse_score = comprehensive_assessment.get('pulse_validation_score', 0.5)
        
        insights = []
        if pulse_score > 0.7:
            insights.append('脈診理論在本案例中高度有效')
            insights.append('脈診知識庫質量得到驗證')
        elif pulse_score > 0.5:
            insights.append('脈診理論部分有效，需要改進')
        else:
            insights.append('脈診理論匹配度不足，需要重新評估')
        
        return insights
    
    def _extract_improvement_insights_v1(self, comprehensive_assessment: Dict) -> List[str]:
        """提取改進洞察 v1.0"""
        improvement_areas = comprehensive_assessment.get('improvement_areas', [])
        
        insights = []
        for area in improvement_areas:
            if '用戶體驗' in area:
                insights.append('需要加強用戶溝通和期望管理')
            elif '臨床效果' in area:
                insights.append('需要優化治療方案選擇和適配')
            elif '脈診' in area:
                insights.append('需要改進脈診知識匹配算法')
        
        return insights
    
    def _identify_knowledge_gaps_v1(self, comprehensive_assessment: Dict, context: Dict) -> List[str]:
        """識別知識空白 v1.0"""
        gaps = []
        
        if comprehensive_assessment.get('effectiveness_level') in ['poor', 'ineffective']:
            gaps.append('缺乏相似案例的有效治療方案')
        
        pulse_score = comprehensive_assessment.get('pulse_validation_score', 0.5)
        if pulse_score < 0.5:
            gaps.append('相關脈診知識不完整或不準確')
        
        return gaps
    
    def _extract_best_practices_v1(self, comprehensive_assessment: Dict) -> List[str]:
        """提取最佳實踐 v1.0"""
        practices = []
        
        if comprehensive_assessment.get('effectiveness_level') in ['excellent', 'good']:
            practices.extend([
                '成功的案例匹配模式',
                '有效的適配策略',
                '良好的患者溝通方式'
            ])
        
        success_factors = comprehensive_assessment.get('success_factors', [])
        if '脈診理論高度驗證' in success_factors:
            practices.append('優秀的脈診理論整合方法')
        
        return practices
    
    def _generate_learning_recommendations_v1(self, comprehensive_assessment: Dict) -> List[str]:
        """生成學習建議 v1.0"""
        recommendations = []
        
        learning_value = self._assess_case_learning_value_v1(comprehensive_assessment)
        if learning_value > 0.7:
            recommendations.append('將此案例加入優秀案例庫')
            recommendations.append('深入分析成功因子並推廣')
        
        if comprehensive_assessment.get('pulse_validation_score', 0) > 0.7:
            recommendations.append('提煉脈診應用的成功模式')
        
        return recommendations
    
    def _calculate_overall_learning_value_v1(self, insights: Dict) -> float:
        """計算總體學習價值 v1.0"""
        case_value = insights.get('case_learning_value', 0.5)
        pattern_count = len(insights.get('pattern_insights', []))
        pulse_count = len(insights.get('pulse_insights', []))
        
        # 綜合學習價值
        overall_value = case_value * 0.5 + min(pattern_count / 3.0, 1.0) * 0.3 + min(pulse_count / 3.0, 1.0) * 0.2
        
        return overall_value
    
    def _create_priority_matrix_v1(self, recommendations: Dict) -> Dict[str, List[str]]:
        """創建優先級矩陣 v1.0"""
        return {
            'urgent_high_impact': recommendations.get('immediate_actions', []),
            'urgent_low_impact': [],
            'not_urgent_high_impact': recommendations.get('long_term_strategies', []),
            'not_urgent_low_impact': recommendations.get('system_enhancements', [])
        }
    
    def _calculate_analysis_confidence_v1(self, comprehensive_assessment: Dict) -> float:
        """計算分析信心度 v1.0"""
        return comprehensive_assessment.get('assessment_confidence', 0.7)
    
    def _generate_ai_insights_v1(self, comprehensive_assessment: Dict, pulse_effectiveness: Dict) -> Dict[str, Any]:
        """生成 AI 洞察 v1.0"""
        return {
            'effectiveness_prediction': comprehensive_assessment.get('effectiveness_level', 'moderate'),
            'key_success_indicators': comprehensive_assessment.get('success_factors', []),
            'risk_assessment': comprehensive_assessment.get('improvement_areas', []),
            'pulse_integration_quality': pulse_effectiveness.get('pulse_theory_validation', 0.5),
            'recommendation_confidence': self._calculate_analysis_confidence_v1(comprehensive_assessment)
        }
    
    def _determine_recommended_action_v1(self, comprehensive_assessment: Dict) -> str:
        """確定推薦行動 v1.0"""
        effectiveness_level = comprehensive_assessment.get('effectiveness_level', 'moderate')
        
        action_map = {
            'excellent': 'terminate_successful',
            'good': 'continue_monitoring',
            'moderate': 'minor_adjustment',
            'poor': 'major_adjustment',
            'ineffective': 'restart_spiral'
        }
        
        return action_map.get(effectiveness_level, 'continue_spiral')
    
    # 輔助解析方法
    def _extract_themes_from_text(self, text: str) -> List[str]:
        """從文字提取主題"""
        themes = []
        if '改善' in text:
            themes.append('症狀改善')
        if '滿意' in text:
            themes.append('治療滿意')
        if '脈診' in text or '脈象' in text:
            themes.append('脈診相關')
        return themes
    
    def _extract_suggestions_from_text(self, text: str) -> List[str]:
        """從文字提取建議"""
        suggestions = []
        if '建議' in text:
            suggestions.append('用戶提出具體建議')
        if '希望' in text:
            suggestions.append('用戶表達期望')
        return suggestions
    
    def _assess_evidence_strength_v1(self, user_feedback: Dict, monitoring_result: Dict) -> float:
        """評估證據強度 v1.0"""
        evidence_score = 0.5
        
        # 用戶回饋完整性
        if user_feedback.get('feedback_text') and len(user_feedback['feedback_text']) > 50:
            evidence_score += 0.2
        
        # 監控資料可用性
        if monitoring_result.get('safety_score') and monitoring_result.get('effectiveness_score'):
            evidence_score += 0.3
        
        return min(evidence_score, 1.0)
    
    def _calculate_pulse_learning_value(self, pulse_support: List[Dict], consistency_score: float) -> float:
        """計算脈診學習價值"""
        if not pulse_support:
            return 0.0
        
        # 基於脈診支持數量和一致性
        base_value = min(len(pulse_support) / 3.0, 1.0)
        consistency_factor = consistency_score
        
        return base_value * consistency_factor
    
    def _assess_pulse_contribution_v1(self, pulse_support: List[Dict], monitoring_result: Dict) -> str:
        """評估脈診貢獻 v1.0"""
        if not pulse_support:
            return 'none'
        
        consistency_score = monitoring_result.get('pulse_consistency_score', 0.5)
        
        if consistency_score > 0.8:
            return 'significant'
        elif consistency_score > 0.6:
            return 'moderate'
        elif consistency_score > 0.4:
            return 'limited'
        else:
            return 'minimal'
    
    def _generate_pulse_recommendations_v1(self, consistency_score: float, pulse_support: List[Dict]) -> List[str]:
        """生成脈診建議 v1.0"""
        recommendations = []
        
        if consistency_score > 0.8:
            recommendations.append('脈診理論應用成功，值得推廣')
        elif consistency_score > 0.6:
            recommendations.append('脈診指導基本有效，可繼續優化')
        else:
            recommendations.append('脈診理論匹配度待提升，需要改進')
        
        if len(pulse_support) < 2:
            recommendations.append('建議增加更多相關脈診知識支持')
        
        return recommendations
    
    def _create_error_analysis_v1(self, error_message: str) -> Dict[str, Any]:
        """創建錯誤分析結果 v1.0"""
        return {
            'analysis_id': 'error_v1',
            'error': True,
            'error_message': error_message,
            'is_effective': False,
            'satisfaction_score': 0.0,
            'confidence_score': 0.0,
            'ai_insights': {},
            'recommended_action': 'error_recovery',
            'message': '回饋分析過程發生錯誤，請重試',
            'version': self.version
        }

