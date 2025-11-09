# -*- coding: utf-8 -*-
"""
速率限制器 (Rate Limiter)
職責：防止 LLM10 無限資源耗盡攻擊

實施策略：
1. IP 級別速率限制
2. 會話級別速率限制
3. 全局資源監控
"""

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from dataclasses import dataclass
from ..utils.logger import get_logger

logger = get_logger("RateLimiter")


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    requests_per_ip_per_minute: int = 10
    requests_per_session_per_hour: int = 50
    max_concurrent_sessions: int = 100
    request_timeout: int = 30  # 秒


class RateLimiter:
    """
    速率限制器
    
    使用滑動窗口算法實施速率限制
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        初始化速率限制器
        
        Args:
            config: 速率限制配置
        """
        self.config = config or RateLimitConfig()
        
        # IP 訪問記錄 {ip: [timestamp1, timestamp2, ...]}
        self.ip_requests = defaultdict(list)
        
        # 會話訪問記錄 {session_id: [timestamp1, timestamp2, ...]}
        self.session_requests = defaultdict(list)
        
        # 封鎖記錄 {ip: unblock_time}
        self.blocked_ips = {}
        
        # 活躍會話數
        self.active_sessions = set()
        
        logger.info("✅ RateLimiter 初始化完成")
    
    def check_rate_limit(
        self,
        ip: str,
        session_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        檢查速率限制
        
        Args:
            ip: 請求來源 IP
            session_id: 會話 ID（可選）
            
        Returns:
            (是否允許, 拒絕原因)
        """
        current_time = time.time()
        
        # 檢查 1: IP 是否被封鎖
        if ip in self.blocked_ips:
            unblock_time = self.blocked_ips[ip]
            if current_time < unblock_time:
                remaining = int(unblock_time - current_time)
                return False, f"IP 已被封鎖，{remaining} 秒後解除"
            else:
                # 解除封鎖
                del self.blocked_ips[ip]
                logger.info(f"🔓 IP {ip} 已解除封鎖")
        
        # 檢查 2: IP 級別速率限制（每分鐘）
        ip_allowed, ip_reason = self._check_ip_rate(ip, current_time)
        if not ip_allowed:
            return False, ip_reason
        
        # 檢查 3: 會話級別速率限制（每小時）
        if session_id:
            session_allowed, session_reason = self._check_session_rate(
                session_id, current_time
            )
            if not session_allowed:
                return False, session_reason
        
        # 檢查 4: 併發會話數限制
        if session_id:
            concurrent_allowed, concurrent_reason = self._check_concurrent_sessions(
                session_id
            )
            if not concurrent_allowed:
                return False, concurrent_reason
        
        # 通過所有檢查，記錄請求
        self.ip_requests[ip].append(current_time)
        if session_id:
            self.session_requests[session_id].append(current_time)
            self.active_sessions.add(session_id)
        
        # 定期清理過期記錄
        self._cleanup_old_records(current_time)
        
        return True, None
    
    def _check_ip_rate(self, ip: str, current_time: float) -> Tuple[bool, Optional[str]]:
        """檢查 IP 級別速率限制"""
        # 獲取最近 1 分鐘的請求
        one_minute_ago = current_time - 60
        recent_requests = [
            t for t in self.ip_requests[ip]
            if t > one_minute_ago
        ]
        
        # 更新記錄
        self.ip_requests[ip] = recent_requests
        
        # 檢查是否超限
        if len(recent_requests) >= self.config.requests_per_ip_per_minute:
            logger.warning(f"⚠️ IP {ip} 超過速率限制")
            
            # 連續 3 次超限則封鎖 10 分鐘
            if len(recent_requests) >= self.config.requests_per_ip_per_minute * 1.5:
                self.blocked_ips[ip] = current_time + 600  # 10 分鐘
                logger.warning(f"🔒 IP {ip} 已被封鎖 10 分鐘")
            
            return False, f"請求過於頻繁，請稍後再試（每分鐘最多 {self.config.requests_per_ip_per_minute} 次）"
        
        return True, None
    
    def _check_session_rate(
        self,
        session_id: str,
        current_time: float
    ) -> Tuple[bool, Optional[str]]:
        """檢查會話級別速率限制"""
        # 獲取最近 1 小時的請求
        one_hour_ago = current_time - 3600
        recent_requests = [
            t for t in self.session_requests[session_id]
            if t > one_hour_ago
        ]
        
        # 更新記錄
        self.session_requests[session_id] = recent_requests
        
        # 檢查是否超限
        if len(recent_requests) >= self.config.requests_per_session_per_hour:
            return False, f"會話請求次數已達上限（每小時最多 {self.config.requests_per_session_per_hour} 次）"
        
        return True, None
    
    def _check_concurrent_sessions(
        self,
        session_id: str
    ) -> Tuple[bool, Optional[str]]:
        """檢查併發會話數限制"""
        if len(self.active_sessions) >= self.config.max_concurrent_sessions:
            if session_id not in self.active_sessions:
                return False, f"系統當前負載較高，請稍後再試（最大併發會話數: {self.config.max_concurrent_sessions}）"
        
        return True, None
    
    def _cleanup_old_records(self, current_time: float):
        """清理過期記錄"""
        # 每 100 次請求清理一次
        if int(current_time) % 100 == 0:
            # 清理 IP 記錄（保留最近 1 小時）
            one_hour_ago = current_time - 3600
            for ip in list(self.ip_requests.keys()):
                self.ip_requests[ip] = [
                    t for t in self.ip_requests[ip]
                    if t > one_hour_ago
                ]
                if not self.ip_requests[ip]:
                    del self.ip_requests[ip]
            
            # 清理會話記錄（保留最近 24 小時）
            one_day_ago = current_time - 86400
            for session_id in list(self.session_requests.keys()):
                self.session_requests[session_id] = [
                    t for t in self.session_requests[session_id]
                    if t > one_day_ago
                ]
                if not self.session_requests[session_id]:
                    del self.session_requests[session_id]
                    self.active_sessions.discard(session_id)
            
            # 清理過期封鎖
            for ip in list(self.blocked_ips.keys()):
                if current_time >= self.blocked_ips[ip]:
                    del self.blocked_ips[ip]
    
    def get_stats(self) -> Dict:
        """獲取統計信息"""
        return {
            "active_ips": len(self.ip_requests),
            "active_sessions": len(self.active_sessions),
            "blocked_ips": len(self.blocked_ips),
            "total_requests_last_minute": sum(
                len([t for t in requests if t > time.time() - 60])
                for requests in self.ip_requests.values()
            )
        }


# ============================================
# 使用範例
# ============================================
if __name__ == "__main__":
    # 創建速率限制器
    limiter = RateLimiter()
    
    # 模擬請求
    ip = "192.168.1.100"
    session = "session-123"
    
    for i in range(15):
        allowed, reason = limiter.check_rate_limit(ip, session)
        if allowed:
            print(f"請求 {i+1}: ✅ 允許")
        else:
            print(f"請求 {i+1}: ❌ 拒絕 - {reason}")
        
        time.sleep(0.1)
    
    # 獲取統計
    stats = limiter.get_stats()
    print(f"\n統計信息: {stats}")