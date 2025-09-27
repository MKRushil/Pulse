"""
Agentive AI 協調器 v1.0

v1.0 功能：
- 管理多個 Agentive AI 智能體
- 協調智能體間的協作
- 整合 Case 和 PulsePJ 知識庫分析
- 提供統一的 AI 決策接口

版本：v1.0
"""

from typing import Dict, Any, List
from s_cbr.agents.diagnostic_agent import DiagnosticAgent
from s_cbr.agents.adaptation_agent import AdaptationAgent
from s_cbr.agents.monitoring_agent import MonitoringAgent
from s_cbr.agents.feedback_agent import FeedbackAgent
from s_cbr.utils.spiral_logger import SpiralLogger

class AgentiveCoordinator:
    """
    Agentive AI 協調器 v1.0
    
    v1.0 特色：
    - 四個專業智能體協作
    - Case + PulsePJ 知識整合
    - 動態決策權重調整
    - 智能體間信息共享
    """
    
    def __init__(self):
        """初始化 Agentive 協調器 v1.0"""
        self.logger = SpiralLogger.get_logger("AgentiveCoordinator")
        self.version = "1.0"
        
        # 初始化四個智能體
        self.diagnostic_agent = DiagnosticAgent()
        self.adaptation_agent = AdaptationAgent()
        self.monitoring_agent = MonitoringAgent()
        self.feedback_agent = FeedbackAgent()
        
        self.logger.info(f"Agentive AI 協調器 v{self.version} 初始化完成")
    
    async def initialize_context(self, initial_query: Dict[str, Any], 
                                session_id: str) -> Dict[str, Any]:
        """初始化 Agentive 上下文 v1.0"""
        context = {
            'version': self.version,
            'session_id': session_id,
            'patient_profile': await self.diagnostic_agent.build_patient_profile_v1(initial_query),
            'reasoning_history': [],
            'agent_insights': {
                'diagnostic': {},
                'adaptation': {},
                'monitoring': {},
                'feedback': {}
            },
            'knowledge_integration': {
                'case_references': [],
                'pulse_references': [],
                'integration_score': 0.0
            },
            'decision_confidence': 0.0
        }
        
        self.logger.debug(f"Agentive 上下文 v{self.version} 初始化完成")
        return context
    
    async def analyze_patient_features(self, symptoms, history, context) -> Dict[str, Any]:
        """使用診斷智能體分析患者特徵 v1.0"""
        self.logger.debug("診斷智能體分析患者特徵")
        
        analysis = await self.diagnostic_agent.analyze_comprehensive_features_v1(
            symptoms, history, context
        )
        
        # 更新上下文
        context['agent_insights']['diagnostic'] = analysis
        
        return analysis
    
    async def plan_adaptation_v1(self, base_case, patient_analysis, pulse_support, context) -> Dict[str, Any]:
        """使用適配智能體規劃適配策略 v1.0 (整合脈診)"""
        self.logger.debug("適配智能體規劃適配策略 v1.0")
        
        strategy = await self.adaptation_agent.create_adaptation_strategy_v1(
            base_case, patient_analysis, pulse_support, context
        )
        
        context['agent_insights']['adaptation'] = strategy
        
        return strategy
    
    async def create_monitoring_plan_v1(self, solution, pulse_support, context) -> Dict[str, Any]:
        """使用監控智能體創建監控計劃 v1.0 (包含脈診驗證)"""
        self.logger.debug("監控智能體創建監控計劃 v1.0")
        
        plan = await self.monitoring_agent.create_comprehensive_monitoring_plan_v1(
            solution, pulse_support, context
        )
        
        context['agent_insights']['monitoring'] = plan
        
        return plan
    
    async def analyze_feedback_v1(self, feedback, monitoring_result, pulse_support, context) -> Dict[str, Any]:
        """使用回饋智能體分析回饋 v1.0 (包含脈診學習)"""
        self.logger.debug("回饋智能體分析回饋 v1.0")
        
        analysis = await self.feedback_agent.analyze_treatment_feedback_v1(
            feedback, monitoring_result, pulse_support, context
        )
        
        context['agent_insights']['feedback'] = analysis
        context['decision_confidence'] = analysis.get('confidence_score', 0.0)
        
        return analysis
    
    async def update_context(self, context, step_result) -> Dict[str, Any]:
        """更新 Agentive 上下文 v1.0"""
        context['reasoning_history'].append({
            'step': step_result.get('step'),
            'result': step_result,
            'timestamp': step_result.get('timestamp'),
            'version': self.version
        })
        
        # v1.0 知識整合更新
        if step_result.get('pulse_support'):
            context['knowledge_integration']['pulse_references'].extend(
                step_result['pulse_support']
            )
        
        if step_result.get('found_case'):
            context['knowledge_integration']['case_references'].append(
                step_result['found_case']
            )
        
        return context
