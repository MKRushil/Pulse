"""
對話編排器 v1.0

v1.0 功能：
- 協調對話流程
- 管理多輪對話狀態
- 整合各步驟的對話生成
- 提供統一的對話接口

版本：v1.0
"""

from typing import Dict, Any, List
from s_cbr.dialog.dialog_manager import DialogManager
from s_cbr.dialog.conversation_state import ConversationState
from s_cbr.utils.spiral_logger import SpiralLogger

class DialogOrchestrator:
    """
    對話編排器 v1.0
    
    v1.0 特色：
    - 統一對話流程管理
    - 多輪對話狀態追蹤
    - 智能回應生成
    - 上下文感知對話
    """
    
    def __init__(self):
        """初始化對話編排器 v1.0"""
        self.dialog_manager = DialogManager()
        self.logger = SpiralLogger.get_logger("DialogOrchestrator")
        self.version = "1.0"
        
        # 對話狀態管理
        self.active_conversations = {}
        
        self.logger.info(f"對話編排器 v{self.version} 初始化完成")
    
    async def orchestrate_spiral_dialog(self, session_id: str, 
                                      spiral_state, step_results: List[Dict]) -> Dict[str, Any]:
        """編排螺旋對話流程 v1.0"""
        self.logger.debug(f"編排螺旋對話 v{self.version} - 會話: {session_id}")
        
        # 獲取或創建對話狀態
        conversation = self._get_or_create_conversation(session_id, spiral_state)
        
        # 生成綜合對話回應
        dialog_response = await self._generate_integrated_response(
            conversation, step_results
        )
        
        # 更新對話狀態
        conversation.add_dialog_turn(dialog_response)
        
        return {
            'session_id': session_id,
            'dialog_response': dialog_response,
            'conversation_state': conversation.get_state_summary(),
            'version': self.version
        }
    
    def _get_or_create_conversation(self, session_id: str, spiral_state) -> ConversationState:
        """獲取或創建對話狀態 v1.0"""
        if session_id not in self.active_conversations:
            self.active_conversations[session_id] = ConversationState(
                session_id=session_id,
                spiral_state=spiral_state,
                version=self.version
            )
        
        return self.active_conversations[session_id]
    
    async def _generate_integrated_response(self, conversation: ConversationState, 
                                          step_results: List[Dict]) -> Dict[str, Any]:
        """生成整合的對話回應 v1.0"""
        # 使用 DialogManager 生成回應
        return await self.dialog_manager.generate_integrated_dialog_v1(
            conversation, step_results
        )
