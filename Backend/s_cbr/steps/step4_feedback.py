"""
STEP 4: 回饋處理器 v1.0

v1.0 功能：
- 用戶回饋收集和分析
- 治療效果評估
- 知識庫更新和學習
- 螺旋推理決策支持

版本：v1.0
"""

from typing import Dict, Any, List
from datetime import datetime
from s_cbr.utils.api_manager import SCBRAPIManager
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger
from s_cbr.knowledge.feedback_repository import FeedbackRepository
from s_cbr.models.feedback_case import FeedbackCase

class Step4Feedback:
    """
    STEP 4: 回饋處理器 v1.0
    
    v1.0 特色：
    - 多維度回饋分析
    - 脈診學習整合
    - 知識庫智能更新
    - 螺旋決策支持
    """
    
    def __init__(self):
        """初始化回饋處理器 v1.0"""
        self.config = SCBRConfig()
        self.api_manager = SCBRAPIManager()
        self.feedback_repository = FeedbackRepository()
        self.logger = SpiralLogger.get_logger("Step4Feedback")
        self.version = "1.0"
        
        self.logger.info(f"STEP 4 回饋處理器 v{self.version} 初始化完成")
    
    async def process_feedback_v1(self, user_feedback: Dict[str, Any],
                                 feedback_analysis: Dict[str, Any],
                                 adapted_solution: Dict[str, Any],
                                 pulse_support: List[Dict],
                                 session_id: str) -> Dict[str, Any]:
        """
        處理用戶回饋 v1.0 (整合脈診學習)
        
        v1.0 流程：
        1. 分析回饋內容
        2. 評估治療效果
        3. 提取學習要點
        4. 更新知識庫
        5. 生成螺旋決策
        """
        self.logger.info("開始執行 STEP 4 v1.0: 回饋處理")
        
        try:
            # Step 4.1: 回饋內容分析
            feedback_insights = await self._analyze_feedback_content_v1(
                user_feedback, feedback_analysis
            )
            
            # Step 4.2: 治療效果評估
            treatment_evaluation = await self._evaluate_treatment_effectiveness_v1(
                user_feedback, adapted_solution, pulse_support
            )
            
            # Step 4.3: 學習要點提取 (包含脈診學習)
            learning_insights = await self._extract_learning_insights_v1(
                feedback_insights, treatment_evaluation, pulse_support, adapted_solution
            )
            
            # Step 4.4: 知識庫更新
            knowledge_update_result = await self._update_knowledge_base_v1(
                learning_insights, session_id, adapted_solution, pulse_support
            )
            
            # Step 4.5: 螺旋決策生成
            spiral_decision = await self._generate_spiral_decision_v1(
                feedback_insights, treatment_evaluation, learning_insights
            )
            
            # Step 4.6: 生成回饋回應
            feedback_response = await self._generate_feedback_response_v1(
                spiral_decision, knowledge_update_result, treatment_evaluation
            )
            
            # 組裝最終結果
            process_result = {
                'feedback_insights': feedback_insights,
                'treatment_evaluation': treatment_evaluation,
                'learning_insights': learning_insights,
                'knowledge_update': knowledge_update_result,
                'spiral_decision': spiral_decision,
                'dialog_response': feedback_response,
                'is_effective': treatment_evaluation.get('is_effective', False),
                'satisfaction_score': feedback_insights.get('satisfaction_score', 0.0),
                'pulse_learning': learning_insights.get('pulse_learning', []),  # v1.0
                'next_action': spiral_decision.get('recommended_action', 'continue'),
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'version': self.version
            }
            
            self.logger.info(f"STEP 4 v1.0 完成 - 治療有效: {process_result['is_effective']}, "
                           f"滿意度: {process_result['satisfaction_score']:.3f}")
            
            return process_result
            
        except Exception as e:
            self.logger.error(f"STEP 4 v1.0 執行異常: {str(e)}")
            return self._create_error_feedback_result_v1(str(e))
    
    async def _analyze_feedback_content_v1(self, user_feedback: Dict[str, Any],
                                          feedback_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """分析回饋內容 v1.0"""
        
        # 提取用戶滿意度
        satisfaction_score = user_feedback.get('satisfaction_rating', 0) / 10.0
        if satisfaction_score == 0:
            # 如果沒有數值評分，嘗試從文字回饋推斷
            feedback_text = user_feedback.get('feedback_text', '')
            satisfaction_score = self._infer_satisfaction_from_text(feedback_text)
        
        # 提取回饋類型
        feedback_type = self._classify_feedback_type_v1(user_feedback)
        
        # 提取關鍵觀點
        key_insights = await self._extract_key_insights_v1(user_feedback, feedback_analysis)
        
        # 識別改進建議
        improvement_suggestions = self._identify_improvement_suggestions_v1(
            user_feedback, feedback_analysis
        )
        
        return {
            'satisfaction_score': satisfaction_score,
            'feedback_type': feedback_type,
            'key_insights': key_insights,
            'improvement_suggestions': improvement_suggestions,
            'user_concerns': user_feedback.get('concerns', []),
            'positive_aspects': user_feedback.get('positive_feedback', []),
            'overall_sentiment': self._determine_overall_sentiment(satisfaction_score),
            'feedback_quality': self._assess_feedback_quality_v1(user_feedback)
        }
    
    async def _evaluate_treatment_effectiveness_v1(self, user_feedback: Dict[str, Any],
                                                  adapted_solution: Dict[str, Any],
                                                  pulse_support: List[Dict]) -> Dict[str, Any]:
        """評估治療效果 v1.0"""
        
        # 構建效果評估提示
        effectiveness_prompt = f"""
作為專業中醫回饋分析智能體，請評估治療效果：

【用戶回饋】
滿意度評分: {user_feedback.get('satisfaction_rating', '未評分')}
症狀改善情況: {user_feedback.get('symptom_improvement', '未提及')}
整體感受: {user_feedback.get('feedback_text', '未提供')}

【治療方案】
{adapted_solution.get('adapted_treatment', '')}

【脈診支持 (v1.0)】
"""
        
        if pulse_support:
            for pulse in pulse_support[:3]:
                effectiveness_prompt += f"- 脈象 {pulse.get('name')}: {pulse.get('main_disease')} 相關症狀 {pulse.get('symptoms', '')}\n"
        
        effectiveness_prompt += """
請評估：
1. 治療有效性 (有效/部分有效/無效)
2. 症狀改善程度 (0-100%)
3. 脈診理論符合度 (0-10分) [v1.0]
4. 患者滿意度分析
5. 後續治療建議

請提供詳細的效果分析。
"""
        
        effectiveness_response = await self.api_manager.generate_llm_response(
            effectiveness_prompt,
            self.config.get_agent_config('feedback_agent')
        )
        
        # 解析效果評估
        evaluation = self._parse_effectiveness_evaluation_v1(effectiveness_response, user_feedback)
        
        return evaluation
    
    async def _extract_learning_insights_v1(self, feedback_insights: Dict[str, Any],
                                           treatment_evaluation: Dict[str, Any],
                                           pulse_support: List[Dict],
                                           adapted_solution: Dict[str, Any]) -> Dict[str, Any]:
        """提取學習洞察 v1.0 (包含脈診學習)"""
        
        learning_insights = {
            'case_learning': [],
            'pulse_learning': [],  # v1.0 新增
            'adaptation_learning': [],
            'general_insights': [],
            'success_factors': [],
            'failure_factors': []
        }
        
        # 案例學習要點
        if treatment_evaluation.get('is_effective'):
            learning_insights['case_learning'].append({
                'insight': '成功的案例適配模式',
                'details': adapted_solution.get('adaptation_reasoning', ''),
                'confidence': treatment_evaluation.get('effectiveness_score', 0.0)
            })
            learning_insights['success_factors'].extend([
                '適當的案例選擇',
                '有效的個人化適配'
            ])
        else:
            learning_insights['case_learning'].append({
                'insight': '需要改進的適配方式',
                'details': '分析適配失敗原因',
                'areas_for_improvement': feedback_insights.get('improvement_suggestions', [])
            })
            learning_insights['failure_factors'].extend([
                '案例匹配度不足',
                '適配策略需調整'
            ])
        
        # v1.0 脈診學習要點
        if pulse_support:
            pulse_effectiveness = treatment_evaluation.get('pulse_theory_match', 0.5)
            if pulse_effectiveness > 0.7:
                learning_insights['pulse_learning'].append({
                    'insight': '脈診理論指導有效',
                    'effective_pulses': [p.get('name') for p in pulse_support],
                    'success_pattern': '脈診與療效高度一致'
                })
                learning_insights['success_factors'].append('脈診理論指導正確')
            elif pulse_effectiveness < 0.5:
                learning_insights['pulse_learning'].append({
                    'insight': '脈診理論匹配度待提升',
                    'mismatched_pulses': [p.get('name') for p in pulse_support],
                    'improvement_needed': '需要更精確的脈診分析'
                })
                learning_insights['failure_factors'].append('脈診指導不夠準確')
            
            # 脈診知識應用學習
            for pulse in pulse_support:
                learning_insights['pulse_learning'].append({
                    'pulse_name': pulse.get('name'),
                    'applied_knowledge': pulse.get('knowledge_chain'),
                    'effectiveness': pulse_effectiveness,
                    'patient_match': self._evaluate_pulse_patient_match(pulse, treatment_evaluation)
                })
        
        # 適配學習要點
        adaptation_confidence = adapted_solution.get('confidence', 0.0)
        if adaptation_confidence > 0.8:
            learning_insights['adaptation_learning'].append({
                'insight': '高信心度適配成功模式',
                'pattern': adapted_solution.get('adaptation_reasoning', ''),
                'replicable': True
            })
        
        # 一般性洞察
        learning_insights['general_insights'] = await self._generate_general_insights_v1(
            feedback_insights, treatment_evaluation, pulse_support
        )
        
        return learning_insights
    
    async def _update_knowledge_base_v1(self, learning_insights: Dict[str, Any],
                                       session_id: str,
                                       adapted_solution: Dict[str, Any],
                                       pulse_support: List[Dict]) -> Dict[str, Any]:
        """更新知識庫 v1.0"""
        
        update_result = {
            'updated': False,
            'new_cases_added': 0,
            'pulse_knowledge_updated': False,  # v1.0
            'learning_points_stored': 0,
            'update_summary': []
        }
        
        try:
            # 創建反饋案例
            if learning_insights.get('case_learning'):
                feedback_case = FeedbackCase(
                    case_id=f"fb_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    original_case_id=adapted_solution.get('original_case_id'),
                    patient_symptoms=learning_insights.get('patient_features', {}),
                    adapted_solution=adapted_solution,
                    treatment_result=learning_insights.get('treatment_result', 'unknown'),
                    monitoring_data=learning_insights.get('monitoring_data', {}),
                    feedback_score=learning_insights.get('effectiveness_score', 0.0),
                    adaptation_details=adapted_solution.get('detailed_assessment', {}),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    version=self.version
                )
                
                # 存儲到反饋知識庫
                storage_result = await self.feedback_repository.store_feedback_case_v1(feedback_case)
                if storage_result.get('success'):
                    update_result['updated'] = True
                    update_result['new_cases_added'] = 1
                    update_result['update_summary'].append('新增反饋案例到知識庫')
            
            # v1.0 脈診知識更新
            pulse_learning = learning_insights.get('pulse_learning', [])
            if pulse_learning:
                pulse_update_result = await self.feedback_repository.update_pulse_knowledge_v1(
                    pulse_learning, session_id
                )
                if pulse_update_result.get('success'):
                    update_result['pulse_knowledge_updated'] = True
                    update_result['update_summary'].append('更新脈診知識應用經驗')
            
            # 存儲學習洞察
            insights_count = len(learning_insights.get('general_insights', []))
            if insights_count > 0:
                await self.feedback_repository.store_learning_insights_v1(
                    learning_insights, session_id
                )
                update_result['learning_points_stored'] = insights_count
                update_result['update_summary'].append(f'存儲 {insights_count} 個學習洞察')
            
            self.logger.info(f"知識庫更新 v1.0 完成 - {update_result['update_summary']}")
            
        except Exception as e:
            self.logger.error(f"知識庫更新失敗: {str(e)}")
            update_result['error'] = str(e)
        
        return update_result
    
    async def _generate_spiral_decision_v1(self, feedback_insights: Dict[str, Any],
                                          treatment_evaluation: Dict[str, Any],
                                          learning_insights: Dict[str, Any]) -> Dict[str, Any]:
        """生成螺旋推理決策 v1.0"""
        
        # 基於治療效果決定下一步行動
        is_effective = treatment_evaluation.get('is_effective', False)
        satisfaction_score = feedback_insights.get('satisfaction_score', 0.0)
        
        if is_effective and satisfaction_score >= 0.7:
            # 治療成功，結束螺旋
            decision = {
                'recommended_action': 'terminate_successful',
                'confidence': 0.9,
                'reason': '治療效果良好，用戶滿意',
                'next_steps': ['記錄成功案例', '提供後續保健建議']
            }
        elif satisfaction_score >= 0.5:
            # 部分滿意，可能需要微調
            decision = {
                'recommended_action': 'minor_adjustment',
                'confidence': 0.6,
                'reason': '治療有一定效果但需要優化',
                'next_steps': ['分析改進點', '調整治療方案', '繼續監控']
            }
        else:
            # 效果不佳，需要重新進行螺旋推理
            decision = {
                'recommended_action': 'continue_spiral',
                'confidence': 0.3,
                'reason': '當前方案效果不理想',
                'next_steps': ['重新評估患者特徵', '尋找其他相似案例', '調整適配策略']
            }
        
        # v1.0 脈診因素考量
        pulse_learning = learning_insights.get('pulse_learning', [])
        if pulse_learning:
            pulse_success = any(p.get('effectiveness', 0) > 0.7 for p in pulse_learning)
            if not pulse_success:
                decision['pulse_recommendation'] = '需要重新評估脈診指導'
                if decision['recommended_action'] != 'continue_spiral':
                    decision['recommended_action'] = 'minor_adjustment'
        
        # 調整信心度
        learning_quality = len(learning_insights.get('success_factors', []))
        if learning_quality > 2:
            decision['confidence'] = min(decision['confidence'] + 0.1, 1.0)
        
        return decision
    
    async def _generate_feedback_response_v1(self, spiral_decision: Dict[str, Any],
                                            knowledge_update: Dict[str, Any],
                                            treatment_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """生成回饋回應 v1.0"""
        
        action = spiral_decision.get('recommended_action', 'continue')
        
        if action == 'terminate_successful':
            response_text = """
感謝您的回饋！很高興這個治療方案對您有效。

根據您的回饋，我們已經：
✓ 記錄了成功的治療經驗
✓ 更新了相關的案例知識庫
✓ 整理了脈診應用的有效模式

請繼續按照當前方案進行治療，並注意：
- 定期監測症狀變化
- 保持良好的生活習慣
- 如有任何不適及時就醫

這次的成功經驗將幫助我們為類似症狀的患者提供更好的治療建議。
            """.strip()
            
        elif action == 'minor_adjustment':
            response_text = """
感謝您的詳細回饋！我們注意到治療方案有一定效果，但還有改進空間。

基於您的回饋，我們將：
• 分析當前方案的優點和不足
• 結合脈診理論進行微調
• 提供更個性化的治療建議

請給我們一點時間來優化方案，我們很快會為您提供調整後的建議。
            """.strip()
            
        else:  # continue_spiral
            response_text = """
感謝您的誠實回饋。我們理解當前方案未能完全滿足您的需求。

我們將重新進行分析：
🔄 重新評估您的症狀特徵
🔍 尋找更匹配的參考案例  
⚡ 調整脈診指導方向
📋 制定新的治療策略

請不要灰心，中醫治療需要個人化調整。我們會繼續努力找到最適合您的方案。
            """.strip()
        
        # v1.0 添加脈診學習反饋
        if knowledge_update.get('pulse_knowledge_updated'):
            response_text += "\n\n🔮 您的案例幫助我們改進了脈診知識的應用，這將使我們的診斷更加精準。"
        
        return {
            'dialog_text': response_text,
            'response_type': action,
            'confidence': spiral_decision.get('confidence', 0.5),
            'next_steps': spiral_decision.get('next_steps', []),
            'knowledge_contribution': knowledge_update.get('update_summary', []),
            'version': self.version
        }
    
    # 輔助方法
    def _classify_feedback_type_v1(self, user_feedback: Dict[str, Any]) -> str:
        """分類回饋類型 v1.0"""
        satisfaction = user_feedback.get('satisfaction_rating', 5)
        
        if satisfaction >= 8:
            return 'highly_positive'
        elif satisfaction >= 6:
            return 'positive'
        elif satisfaction >= 4:
            return 'neutral'
        elif satisfaction >= 2:
            return 'negative'
        else:
            return 'highly_negative'
    
    async def _extract_key_insights_v1(self, user_feedback: Dict[str, Any],
                                      feedback_analysis: Dict[str, Any]) -> List[str]:
        """提取關鍵洞察 v1.0"""
        insights = []
        
        # 從用戶文字回饋提取
        feedback_text = user_feedback.get('feedback_text', '')
        if feedback_text:
            # 簡單關鍵詞分析（可以用更複雜的 NLP）
            if '症狀改善' in feedback_text:
                insights.append('患者感受到症狀改善')
            if '效果不佳' in feedback_text:
                insights.append('患者對治療效果不滿意')
            if '脈象' in feedback_text or '脈診' in feedback_text:
                insights.append('患者關注脈診相關內容')  # v1.0
        
        # 從分析結果提取
        if feedback_analysis.get('effectiveness_score', 0) > 0.7:
            insights.append('高效治療模式')
        
        return insights
    
    def _identify_improvement_suggestions_v1(self, user_feedback: Dict[str, Any],
                                            feedback_analysis: Dict[str, Any]) -> List[str]:
        """識別改進建議 v1.0"""
        suggestions = []
        
        # 基於用戶回饋
        concerns = user_feedback.get('concerns', [])
        for concern in concerns:
            if '劑量' in concern:
                suggestions.append('調整用藥劑量')
            elif '時間' in concern:
                suggestions.append('優化服藥時間')
            elif '脈診' in concern:
                suggestions.append('加強脈診指導說明')  # v1.0
        
        return suggestions
    
    def _infer_satisfaction_from_text(self, text: str) -> float:
        """從文字推斷滿意度"""
        if not text:
            return 0.5
        
        positive_words = ['好', '有效', '改善', '滿意', '不錯']
        negative_words = ['不好', '無效', '惡化', '不滿意', '失望']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return 0.7
        elif negative_count > positive_count:
            return 0.3
        else:
            return 0.5
    
    def _determine_overall_sentiment(self, satisfaction_score: float) -> str:
        """確定整體情感傾向"""
        if satisfaction_score >= 0.7:
            return 'positive'
        elif satisfaction_score >= 0.4:
            return 'neutral'
        else:
            return 'negative'
    
    def _assess_feedback_quality_v1(self, user_feedback: Dict[str, Any]) -> float:
        """評估回饋品質 v1.0"""
        quality = 0.0
        
        # 有數值評分
        if user_feedback.get('satisfaction_rating'):
            quality += 0.3
        
        # 有文字描述
        if user_feedback.get('feedback_text'):
            quality += 0.4
        
        # 有具體症狀描述
        if user_feedback.get('symptom_improvement'):
            quality += 0.3
        
        return quality
    
    def _parse_effectiveness_evaluation_v1(self, response: str, user_feedback: Dict) -> Dict[str, Any]:
        """解析效果評估 v1.0"""
        # 簡化實現
        satisfaction = user_feedback.get('satisfaction_rating', 5) / 10.0
        
        return {
            'is_effective': satisfaction >= 0.6,
            'effectiveness_score': satisfaction,
            'symptom_improvement': satisfaction * 100,  # 轉換為百分比
            'pulse_theory_match': 0.7,  # v1.0 脈診理論符合度
            'patient_satisfaction': satisfaction,
            'detailed_analysis': response[:200],
            'improvement_areas': ['用藥時機', '劑量調整'] if satisfaction < 0.7 else [],
            'success_factors': ['準確診斷', '個人化適配'] if satisfaction >= 0.7 else []
        }
    
    def _evaluate_pulse_patient_match(self, pulse: Dict, treatment_evaluation: Dict) -> float:
        """評估脈診與患者匹配度"""
        # 簡化實現
        return treatment_evaluation.get('pulse_theory_match', 0.5)
    
    async def _generate_general_insights_v1(self, feedback_insights: Dict,
                                           treatment_evaluation: Dict,
                                           pulse_support: List[Dict]) -> List[str]:
        """生成一般性洞察 v1.0"""
        insights = []
        
        satisfaction = feedback_insights.get('satisfaction_score', 0.0)
        if satisfaction > 0.8:
            insights.append('高滿意度治療模式值得推廣')
        
        if pulse_support and treatment_evaluation.get('pulse_theory_match', 0) > 0.7:
            insights.append('脈診理論指導在此案例中發揮重要作用')  # v1.0
        
        if treatment_evaluation.get('is_effective'):
            insights.append('個人化適配策略有效')
        
        return insights
    
    def _create_error_feedback_result_v1(self, error_message: str) -> Dict[str, Any]:
        """創建錯誤回饋結果 v1.0"""
        return {
            'error': True,
            'error_message': error_message,
            'is_effective': False,
            'satisfaction_score': 0.0,
            'next_action': 'error_recovery',
            'dialog_response': {
                'dialog_text': '回饋處理過程發生錯誤，請重試或聯繫技術支援',
                'response_type': 'error',
                'confidence': 0.0
            },
            'version': self.version
        }
