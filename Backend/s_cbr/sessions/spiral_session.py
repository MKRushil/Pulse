"""
螺旋推理會話管理 v2.0

管理單個用戶的螺旋推理狀態：
- 已使用案例列表
- 推理輪次記錄
- 原始問題追蹤
- 智能問題更新檢測
"""

import datetime
from typing import Dict, Any

class SpiralSession:
    """
    螺旋推理會話管理類
    
    管理單個用戶的螺旋推理狀態，包括：
    - 會話唯一標識
    - 原始查詢記錄
    - 已使用案例ID列表
    - 推理輪次計數
    - 時間戳記錄
    """
    
    def __init__(self, session_id: str):
        """
        初始化螺旋會話
        
        Args:
            session_id: 會話唯一標識符
        """
        self.session_id = session_id
        self.original_query = ""  # 原始問題
        self.used_cases = []      # 已使用案例ID列表
        self.round_count = 0      # 推理輪數
        self.current_result = {}  # 當前推理結果
        self.created_at = datetime.datetime.now()
        self.last_updated = datetime.datetime.now()
        
    def is_query_updated(self, new_query: str) -> bool:
        """
        判斷問題是否有實質更新
        
        使用文本相似度判斷，相似度 < 80% 視為有更新
        
        Args:
            new_query: 新的查詢字符串
            
        Returns:
            bool: True 表示查詢有更新，False 表示查詢相同
        """
        if not self.original_query:
            return True
            
        # 計算文本相似度（簡單實現）
        similarity = self._calculate_text_similarity(self.original_query, new_query)
        return similarity < 0.8
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        計算兩個文本的相似度
        
        使用字符集合的Jaccard相似度算法
        
        Args:
            text1: 第一個文本
            text2: 第二個文本
            
        Returns:
            float: 相似度值，範圍 0-1
        """
        # 簡單的字符級相似度計算
        set1 = set(text1.replace(" ", "").lower())
        set2 = set(text2.replace(" ", "").lower())
        
        if not set1 or not set2:
            return 0.0
            
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def update_query(self, new_query: str):
        """
        更新查詢，如果有變化則重置已使用案例
        
        Args:
            new_query: 新的查詢字符串
        """
        if self.is_query_updated(new_query):
            self.original_query = new_query
            self.used_cases = []  # 重置已使用案例
            self.round_count = 0  # 重置輪次
            self.last_updated = datetime.datetime.now()
        elif not self.original_query:
            # 首次設置查詢
            self.original_query = new_query
            self.last_updated = datetime.datetime.now()
            
    def add_used_case(self, case_id: str):
        """
        添加已使用的案例ID
        
        Args:
            case_id: 案例的唯一標識符
        """
        if case_id and case_id not in self.used_cases:
            self.used_cases.append(case_id)
            self.last_updated = datetime.datetime.now()
        
    def increment_round(self):
        """增加推理輪次"""
        self.round_count += 1
        self.last_updated = datetime.datetime.now()
        
    def get_available_cases_limit(self) -> int:
        """
        獲取可繼續使用的案例數量限制
        
        Returns:
            int: 還可以使用的案例數量
        """
        max_cases = 10  # 最多使用10個案例
        return max(0, max_cases - len(self.used_cases))
        
    def can_continue(self) -> bool:
        """
        判斷是否可以繼續推理
        
        Returns:
            bool: True 表示可以繼續，False 表示應該結束
        """
        return self.get_available_cases_limit() > 0
        
    def get_session_summary(self) -> str:
        """
        獲取會話摘要信息
        
        Returns:
            str: 會話摘要
        """
        duration = datetime.datetime.now() - self.created_at
        return (f"會話 {self.session_id}: "
                f"已進行 {self.round_count} 輪推理, "
                f"使用 {len(self.used_cases)} 個案例, "
                f"持續時間 {duration.seconds//60} 分鐘")
        
    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式，用於序列化
        
        Returns:
            Dict[str, Any]: 包含所有會話信息的字典
        """
        return {
            'session_id': self.session_id,
            'original_query': self.original_query,
            'used_cases': self.used_cases,
            'round_count': self.round_count,
            'can_continue': self.can_continue(),
            'available_cases_limit': self.get_available_cases_limit(),
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'session_summary': self.get_session_summary()
        }
        
    def __repr__(self) -> str:
        """會話的字符串表示"""
        return (f"SpiralSession(id='{self.session_id}', "
                f"rounds={self.round_count}, "
                f"cases_used={len(self.used_cases)})")