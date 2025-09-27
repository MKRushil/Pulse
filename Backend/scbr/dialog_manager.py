# scbr/dialog_manager.py
from typing import Dict

class DialogManager:
    def __init__(self):
        # 每個 session_id 對應一個 dict，包含累積的對話文本和目前輪數
        self.sessions: Dict[str, Dict[str, str or int]] = {}

    def _init_session(self, session_id: str):
        """內部函式：初始化一個新的會話記錄。"""
        self.sessions[session_id] = {
            "conversation_text": "",
            "turn": 0
        }

    def update_session(self, session_id: str, new_user_input: str) -> str:
        """
        更新指定 session 的對話內容，將新的使用者輸入追加到 conversation_text。
        返回更新後的完整對話內容（或問題描述）。
        """
        if session_id not in self.sessions:
            # 如該 session 尚不存在，初始化新的會話
            self._init_session(session_id)
        # 增加回合計數
        self.sessions[session_id]["turn"] += 1
        # 累積對話文本（這裡簡單地以換行相連，可以更智能地區分角色）
        conv_text = self.sessions[session_id]["conversation_text"]
        if conv_text:
            conv_text += "\n"  # 使用換行符連接
        conv_text += new_user_input
        # 更新會話文本
        self.sessions[session_id]["conversation_text"] = conv_text
        return conv_text

    def get_turn_count(self, session_id: str) -> int:
        """取得當前 session 已進行的對話輪數。如果尚無記錄，返回0。"""
        if session_id not in self.sessions:
            return 0
        return self.sessions[session_id].get("turn", 0)

    def reset_session(self, session_id: str):
        """重置指定 session 的對話記錄。"""
        if session_id in self.sessions:
            del self.sessions[session_id]
