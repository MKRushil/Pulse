"""
螺旋推理會話管理器 v2.0

管理所有活躍的螺旋推理會話：
- 會話創建與獲取
- 會話生命週期管理
- 過期會話清理
- 會話統計信息
"""

import datetime
import hashlib
import threading
from typing import Dict, List, Optional, Any
from .spiral_session import SpiralSession

# 動態導入logger，避免循環導入
try:
    from ..utils.spiral_logger import SpiralLogger
except ImportError:
    # 降級處理，使用標準logging
    import logging
    class SpiralLogger:
        @staticmethod
        def get_logger(name):
            return logging.getLogger(name)

class SpiralSessionManager:
    """
    螺旋推理會話管理器
    
    管理所有活躍的螺旋推理會話，提供：
    - 會話的創建、獲取、刪除
    - 基於查詢內容的智能會話ID生成
    - 過期會話的自動清理
    - 會話統計與監控
    - 線程安全的會話操作
    """
    
    def __init__(self, max_sessions: int = 1000):
        """
        初始化會話管理器
        
        Args:
            max_sessions: 最大同時活躍會話數
        """
        self.sessions: Dict[str, SpiralSession] = {}
        self.max_sessions = max_sessions
        self.logger = SpiralLogger.get_logger("SpiralSessionManager")
        self._lock = threading.Lock()  # 線程安全鎖
        self._last_cleanup = datetime.datetime.now()
        
        self.logger.info(f"螺旋會話管理器初始化 - 最大會話數: {max_sessions}")
        
    def get_or_create_session(self, session_id: Optional[str], query: str) -> SpiralSession:
        """
        獲取或創建會話
        
        Args:
            session_id: 會話ID，如果為None則自動生成
            query: 查詢字符串
            
        Returns:
            SpiralSession: 會話實例
        """
        with self._lock:
            # 自動清理過期會話
            self._auto_cleanup_if_needed()
            
            if not session_id:
                session_id = self._generate_session_id(query)
                
            if session_id not in self.sessions:
                # 檢查會話數量限制
                if len(self.sessions) >= self.max_sessions:
                    self._cleanup_oldest_sessions(int(self.max_sessions * 0.1))
                
                session = SpiralSession(session_id)
                session.update_query(query)
                self.sessions[session_id] = session
                self.logger.info(f"創建新螺旋會話: {session_id} (總會話數: {len(self.sessions)})")
            else:
                session = self.sessions[session_id]
                session.update_query(query)  # 檢查查詢是否更新
                
            return self.sessions[session_id]
    
    def _generate_session_id(self, query: str) -> str:
        """
        基於查詢內容生成會話ID
        
        Args:
            query: 查詢字符串
            
        Returns:
            str: 生成的會話ID
        """
        # 生成查詢內容的哈希
        query_normalized = query.strip().lower().replace(" ", "")
        query_hash = hashlib.md5(query_normalized.encode('utf-8')).hexdigest()[:8]
        
        # 生成時間戳
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 添加隨機後綴避免衝突
        import random
        random_suffix = f"{random.randint(100, 999)}"
        
        return f"spiral_{timestamp}_{query_hash}_{random_suffix}"
    
    def get_session(self, session_id: str) -> Optional[SpiralSession]:
        """
        獲取指定的會話
        
        Args:
            session_id: 會話ID
            
        Returns:
            Optional[SpiralSession]: 會話實例，如果不存在則返回None
        """
        with self._lock:
            return self.sessions.get(session_id)
    
    def session_exists(self, session_id: str) -> bool:
        """
        檢查會話是否存在
        
        Args:
            session_id: 會話ID
            
        Returns:
            bool: True 表示存在，False 表示不存在
        """
        with self._lock:
            return session_id in self.sessions
    
    def reset_session(self, session_id: str) -> bool:
        """
        重置指定會話
        
        Args:
            session_id: 要重置的會話ID
            
        Returns:
            bool: True 表示重置成功，False 表示會話不存在
        """
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                self.logger.info(f"重置螺旋會話: {session_id}")
                return True
            return False
            
    def reset_all_sessions(self):
        """重置所有會話"""
        with self._lock:
            count = len(self.sessions)
            self.sessions.clear()
            self.logger.info(f"重置所有螺旋會話: {count} 個會話")
            
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        清理超過指定時間的會話
        
        Args:
            max_age_hours: 會話最大存活時間（小時）
            
        Returns:
            int: 清理的會話數量
        """
        with self._lock:
            cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=max_age_hours)
            old_sessions = [
                sid for sid, session in self.sessions.items()
                if session.last_updated < cutoff_time
            ]
            
            for sid in old_sessions:
                del self.sessions[sid]
                
            if old_sessions:
                self.logger.info(f"清理過期螺旋會話: {len(old_sessions)} 個")
                
            self._last_cleanup = datetime.datetime.now()
            return len(old_sessions)
    
    def _cleanup_oldest_sessions(self, count: int):
        """
        清理最老的會話
        
        Args:
            count: 要清理的會話數量
        """
        if not self.sessions or count <= 0:
            return
            
        # 按最後更新時間排序，清理最舊的會話
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1].last_updated
        )
        
        for i in range(min(count, len(sorted_sessions))):
            session_id = sorted_sessions[i][0]
            del self.sessions[session_id]
            
        self.logger.info(f"清理最老的 {count} 個會話")
    
    def _auto_cleanup_if_needed(self):
        """如果需要，自動執行清理"""
        # 每小時自動清理一次
        if (datetime.datetime.now() - self._last_cleanup).seconds > 3600:
            cleaned = self.cleanup_old_sessions()
            if cleaned > 0:
                self.logger.info(f"自動清理完成，清理了 {cleaned} 個過期會話")
    
    def get_sessions_info(self) -> List[Dict[str, Any]]:
        """
        獲取所有會話資訊
        
        Returns:
            List[Dict[str, Any]]: 包含所有會話信息的列表
        """
        with self._lock:
            return [session.to_dict() for session in self.sessions.values()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取會話管理器統計信息
        
        Returns:
            Dict[str, Any]: 統計信息
        """
        with self._lock:
            total_sessions = len(self.sessions)
            total_rounds = sum(session.round_count for session in self.sessions.values())
            total_cases_used = sum(len(session.used_cases) for session in self.sessions.values())
            
            # 計算平均值
            avg_rounds = total_rounds / total_sessions if total_sessions > 0 else 0
            avg_cases = total_cases_used / total_sessions if total_sessions > 0 else 0
            
            # 活躍會話（最近1小時有活動）
            recent_cutoff = datetime.datetime.now() - datetime.timedelta(hours=1)
            active_sessions = sum(
                1 for session in self.sessions.values()
                if session.last_updated > recent_cutoff
            )
            
            return {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'max_sessions': self.max_sessions,
                'total_rounds_processed': total_rounds,
                'total_cases_used': total_cases_used,
                'avg_rounds_per_session': round(avg_rounds, 2),
                'avg_cases_per_session': round(avg_cases, 2),
                'last_cleanup': self._last_cleanup.isoformat(),
                'memory_usage_mb': self._estimate_memory_usage()
            }
    
    def _estimate_memory_usage(self) -> float:
        """
        估算內存使用量（MB）
        
        Returns:
            float: 估算的內存使用量
        """
        # 粗略估算每個會話的內存使用量
        bytes_per_session = 1024  # 估算每個會話1KB
        total_bytes = len(self.sessions) * bytes_per_session
        return round(total_bytes / (1024 * 1024), 2)
    
    def get_session_by_query_similarity(self, query: str, similarity_threshold: float = 0.8) -> Optional[SpiralSession]:
        """
        根據查詢相似度找到現有會話
        
        Args:
            query: 查詢字符串
            similarity_threshold: 相似度閾值
            
        Returns:
            Optional[SpiralSession]: 最相似的會話，如果沒有找到則返回None
        """
        with self._lock:
            best_session = None
            best_similarity = 0.0
            
            for session in self.sessions.values():
                if not session.original_query:
                    continue
                    
                # 使用SpiralSession的相似度計算方法
                similarity = session._calculate_text_similarity(session.original_query, query)
                
                if similarity >= similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_session = session
                    
            if best_session:
                self.logger.info(f"找到相似會話: {best_session.session_id} (相似度: {best_similarity:.3f})")
                
            return best_session
    
    def __len__(self) -> int:
        """返回當前會話數量"""
        return len(self.sessions)
    
    def __repr__(self) -> str:
        """會話管理器的字符串表示"""
        return f"SpiralSessionManager(sessions={len(self.sessions)}, max={self.max_sessions})"