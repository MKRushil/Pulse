"""
對話管理器 v1.0

v1.0 功能：
- 統一對話流程管理
- 多輪對話狀態追蹤
- 螺旋推理回應生成
- 脈診整合對話

版本：v1.0
"""

from typing import Dict, Any, List
from s_cbr.dialog.conversation_state import ConversationState
from s_cbr.dialog.response_generator import ResponseGenerator
from s_cbr.utils.api_manager import SCBRAPIManager
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger

class DialogManager:
    """
    對話管理器 v1.0
    
    v1.0 特色：
    - 四步驟螺旋對話管理
    - 脈診資訊整合對話
    - 智能回應生成
    - 上下文感知交互
    """
    
    def __init__(self):
        """初始化對話管理器 v1.0"""
        self.config = SCBRConfig()
        self.response_generator = ResponseGenerator()
        self.api_manager = SCBRAPIManager()
        self.logger = SpiralLogger.get_logger("DialogManager")
        self.version = "1.0"
        
        # 對話會話記錄
        self.active_conversations = {}
        
        self.logger.info(f"對話管理器 v{self.version} 初始化完成")
    
    async def generate_step1_dialog(self, search_result: Dict[str, Any],
                                   patient_analysis: Dict[str, Any]) -> Dict[str, str]:
        """生成 STEP 1 對話 v1.0"""
        self.logger.debug("生成 STEP 1 案例搜尋對話")
        
        found_case = search_result.get('found_case')
        similarity = search_result.get('similarity', 0.0)
        pulse_support = search_result.get('pulse_support', [])
        
        if found_case:
            # 找到案例的對話
            dialog_content = f"""
【案例分析完成】

我找到了一個相似度為 {similarity:.1%} 的參考案例：

📋 **相似案例資訊**
- 案例診斷：{found_case.get('diagnosis_main', '相似症狀案例')}
- 主要症狀：{found_case.get('chief_complaint', '相似主訴')[:100]}
- 患者特徵：{found_case.get('age', '相近年齡')}歲，{found_case.get('gender', '同性別')}
"""
            
            # v1.0 脈診支持資訊
            if pulse_support:
                dialog_content += f"\n🔮 **脈診理論支持** ({len(pulse_support)}個相關脈診知識)"
                for pulse in pulse_support[:2]:  # 顯示前2個最相關
                    dialog_content += f"\n- {pulse.get('name', '')}: {pulse.get('main_disease', '')}"
            
            dialog_content += "\n\n接下來我將根據您的個體特徵進行方案適配..."
            
        else:
            # 未找到案例的對話
            dialog_content = """
【案例搜尋結果】

很抱歉，我在現有案例庫中未能找到高度相似的參考案例。

不過這並不意味著無法提供幫助：
"""
            
            # v1.0 脈診知識補充
            if pulse_support:
                dialog_content += f"""
🔮 **脈診理論指導** (找到 {len(pulse_support)} 個相關脈診知識)
根據您的症狀特徵，我找到了相關的脈診理論支持：
"""
                for pulse in pulse_support[:2]:
                    dialog_content += f"\n- {pulse.get('name', '')}: {pulse.get('description', '')}"
                
                dialog_content += "\n\n我將基於脈診理論和症狀分析為您制定個人化方案..."
            else:
                dialog_content += """
💡 我將採用症狀分析和中醫理論相結合的方式為您提供個人化建議。

建議您可以補充：
- 更詳細的症狀描述
- 脈象相關資訊
- 體質特徵等

這將有助於提供更精準的診療建議。
"""
        
        return {"dialog_text": dialog_content.strip()}
    
    async def conduct_negotiation(self, adapted_solution: Dict[str, Any], 
                                 spiral_state) -> Dict[str, Any]:
        """進行 STEP 2 協商對話 v1.0"""
        self.logger.debug("進行 STEP 2 案例適配協商")
        
        # 提取適配方案資訊
        treatment_plan = adapted_solution.get('adapted_treatment', '')
        confidence = adapted_solution.get('confidence', 0.0)
        pulse_integration = adapted_solution.get('pulse_integration', {})
        
        negotiation_prompt = f"""
基於案例適配分析，我為您制定了個人化治療建議：

📋 **適配治療方案**
{treatment_plan[:500]}

🎯 **方案信心度**: {confidence:.1%}
"""
        
        # v1.0 脈診整合說明
        pulse_insights_used = pulse_integration.get('pulse_insights_used', 0)
        if pulse_insights_used > 0:
            negotiation_prompt += f"""

🔮 **脈診整合情況**
- 應用了 {pulse_insights_used} 個脈診知識點
- 整合品質: {pulse_integration.get('integration_quality', 0.0):.1%}
"""
            
            diagnostic_support = pulse_integration.get('diagnostic_support', [])
            if diagnostic_support:
                negotiation_prompt += "\n- 脈診診斷支持: " + ", ".join(diagnostic_support[:2])
        
        # 協商問題
        negotiation_prompt += """

❓ **您的意見**
請問您對這個治療方案的看法如何？
1. 是否認同診斷方向？
2. 治療建議是否符合預期？
3. 是否有其他考慮因素？

請提供您的回饋，我會根據您的意見進一步優化方案。
"""
        
        return {
            "dialog_text": negotiation_prompt.strip(),
            "negotiation_type": "solution_confirmation",
            "confidence_level": confidence,
            "requires_feedback": True
        }
    
    async def generate_monitoring_dialog(self, validation_result: Dict[str, Any],
                                        adapted_solution: Dict[str, Any]) -> str:
        """生成 STEP 3 監控對話 v1.0"""
        self.logger.debug("生成 STEP 3 監控驗證對話")
        
        safety_score = validation_result.get('safety_score', 0.0)
        effectiveness_score = validation_result.get('effectiveness_score', 0.0)
        pulse_consistency = validation_result.get('pulse_consistency_score', 0.0)
        validation_passed = validation_result.get('validation_passed', False)
        
        if validation_passed:
            dialog = f"""
✅ **方案監控驗證完成**

經過全面的安全性和有效性評估：

📊 **評估結果**
- 安全性評分: {safety_score:.1%} 
- 有效性評分: {effectiveness_score:.1%}"""
            
            # v1.0 脈診一致性
            if pulse_consistency > 0:
                dialog += f"\n- 脈診一致性: {pulse_consistency:.1%}"
                
                if pulse_consistency > 0.7:
                    dialog += " (理論高度符合 ✨)"
                elif pulse_consistency > 0.5:
                    dialog += " (理論基本符合 ✓)"
                else:
                    dialog += " (需要關注 ⚠️)"
            
            dialog += """

🎯 **監控建議**
1. 按計劃進行治療
2. 定期觀察症狀變化
3. 記錄治療反應
"""
            
            # 風險提醒
            risk_factors = validation_result.get('risk_analysis', {}).get('risk_factors', [])
            if risk_factors:
                dialog += f"\n⚠️ **注意事項**: {', '.join(risk_factors[:2])}"
            
        else:
            dialog = f"""
⚠️ **方案需要調整**

監控驗證發現一些需要關注的問題：

📊 **評估結果**
- 安全性評分: {safety_score:.1%}
- 有效性評分: {effectiveness_score:.1%}"""
            
            if pulse_consistency > 0:
                dialog += f"\n- 脈診一致性: {pulse_consistency:.1%}"
            
            improvement_areas = validation_result.get('overall_validation', {}).get('improvement_areas', [])
            if improvement_areas:
                dialog += f"\n\n🔧 **需要改進的領域**:\n" + "\n".join(f"- {area}" for area in improvement_areas[:3])
            
            dialog += "\n\n我將調整治療方案以提升安全性和有效性..."
        
        return dialog
    
    async def collect_user_feedback(self, adapted_solution: Dict[str, Any],
                                   validation_result: Dict[str, Any],
                                   spiral_state) -> Dict[str, Any]:
        """收集 STEP 4 用戶回饋 v1.0"""
        self.logger.debug("收集 STEP 4 用戶回饋")
        
        # 模擬用戶回饋收集（實際實作中可以是真實的用戶交互）
        feedback_dialog = """
🗨️ **治療回饋收集**

為了持續改善診療品質，請您分享治療體驗：

1. **症狀改善情況** (1-10分)
   - 主要症狀是否有改善？

2. **治療滿意度** (1-10分) 
   - 對整體治療方案是否滿意？

3. **具體感受**
   - 請描述您的主觀感受和變化

4. **建議和意見**
   - 是否有其他建議或關注點？
"""
        
        # v1.0 脈診相關回饋
        pulse_integration = adapted_solution.get('pulse_integration', {})
        if pulse_integration.get('pulse_insights_used', 0) > 0:
            feedback_dialog += """
5. **脈診指導體驗** (可選)
   - 脈診理論指導是否有幫助？
   - 脈象相關建議是否實用？
"""
        
        # 簡化回饋模擬 (v1.0 基礎實作)
        simulated_feedback = {
            "satisfaction_rating": 7,  # 模擬評分
            "symptom_improvement_rating": 8,
            "feedback_text": "治療方案整體不錯，症狀有明顯改善，希望能繼續優化脈診指導",
            "subjective_improvement": "good",
            "concerns": [],
            "positive_feedback": ["症狀改善", "方案合理"],
            "collection_method": "simulated_v1"  # v1.0 標記
        }
        
        return simulated_feedback
    
    async def generate_session_summary(self, spiral_state) -> str:
        """生成會話總結 v1.0"""
        self.logger.debug("生成螺旋推理會話總結")
        
        total_rounds = spiral_state.current_round
        converged = getattr(spiral_state, 'converged', False)
        
        summary = f"""
📋 **螺旋推理會話總結** (S-CBR v{self.version})

🔄 **推理過程**
- 總推理輪數: {total_rounds} 輪
- 推理結果: {'成功收斂 ✅' if converged else '部分完成 ⏳'}
"""
        
        # 各步驟成果簡述
        if hasattr(spiral_state, 'round_results') and spiral_state.round_results:
            last_round = spiral_state.round_results[-1]
            summary += f"""
- STEP1 案例匹配: {'成功 ✓' if last_round.get('step1_result', {}).get('found_case') else '部分 △'}
- STEP2 方案適配: 信心度 {last_round.get('step2_result', {}).get('confidence_score', 0):.1%}
- STEP3 監控驗證: {'通過 ✅' if last_round.get('step3_result', {}).get('validation_passed') else '需改進 ⚠️'}
- STEP4 用戶回饋: 滿意度 {last_round.get('step4_result', {}).get('user_satisfaction', 0):.1%}
"""
        
        # v1.0 脈診整合總結
        if hasattr(spiral_state, 'pulse_knowledge_used'):
            summary += f"""
🔮 **脈診整合成果**
- 運用脈診知識: {getattr(spiral_state, 'pulse_knowledge_count', 0)} 個
- 脈診理論驗證: {getattr(spiral_state, 'pulse_consistency_avg', 0.0):.1%}
"""
        
        summary += f"""
💡 **主要成就**
- 提供了個人化的中醫診療建議
- 整合了現代AI技術與傳統中醫理論
- 實現了螺旋推理的迭代優化

感謝您對 S-CBR v{self.version} 系統的信任！
"""
        
        return summary
    
    async def generate_integrated_dialog_v1(self, conversation: ConversationState,
                                           step_results: List[Dict]) -> Dict[str, Any]:
        """生成整合的對話回應 v1.0"""
        self.logger.debug("生成整合對話回應 v1.0")
        
        # 使用回應生成器
        integrated_response = await self.response_generator.generate_comprehensive_response_v1(
            conversation, step_results
        )
        
        # 更新對話狀態
        conversation.add_system_response(integrated_response)
        
        return integrated_response
    
    def get_conversation_state(self, session_id: str) -> ConversationState:
        """獲取對話狀態"""
        return self.active_conversations.get(session_id)
    
    def create_conversation(self, session_id: str, spiral_state) -> ConversationState:
        """創建新對話"""
        conversation = ConversationState(
            session_id=session_id,
            spiral_state=spiral_state,
            version=self.version
        )
        self.active_conversations[session_id] = conversation
        return conversation
    
    def cleanup_conversation(self, session_id: str):
        """清理對話狀態"""
        if session_id in self.active_conversations:
            del self.active_conversations[session_id]
            self.logger.debug(f"清理對話狀態: {session_id}")
