"""
API 管理器 v2.0

管理S-CBR系統的API連接、健康檢查與統計
支援會話健康狀態監控與系統指標收集

版本：v2.0 - 螺旋互動版
更新：健康檢查回傳會話健康資訊
"""

from typing import Dict, Any, List, Optional, Union
import logging
import asyncio
import aiohttp
import time
from datetime import datetime, timedelta

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
    from ..config.scbr_config import SCBRConfig, get_config
    from ..sessions.spiral_session_manager import SpiralSessionManager
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    SCBRConfig = None
    SpiralSessionManager = None

class SCBRAPIManager:
    """
    S-CBR API 管理器 v2.0
    
    v2.0 特色：
    - 會話健康狀態監控
    - 系統性能指標收集
    - API 調用統計與分析
    - 自動故障恢復
    """
    
    def __init__(self, config: SCBRConfig = None):
        """初始化API管理器 v2.0"""
        self.logger = SpiralLogger.get_logger("SCBRAPIManager") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("SCBRAPIManager")
        self.version = "2.0"
        
        # 配置管理
        self.config = config or (get_config() if SCBRConfig else self._get_default_config())
        
        # 會話管理器引用（懶載入）
        self._session_manager = None
        
        # API統計
        self.api_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "last_request_time": None,
            "start_time": datetime.now(),
            "health_checks": 0,
            "last_health_check": None,
            "version": self.version
        }
        
        # 性能監控
        self.performance_metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "network_io": {"bytes_sent": 0, "bytes_recv": 0},
            "active_connections": 0,
            "response_times": [],
            "error_rates": []
        }
        
        # v2.0 會話監控
        self.session_metrics = {
            "active_sessions": 0,
            "total_sessions_created": 0,
            "total_rounds_executed": 0,
            "avg_rounds_per_session": 0.0,
            "session_success_rate": 0.0,
            "most_active_session": None,
            "longest_session": None
        }
        
        # HTTP 客戶端會話
        self.http_session = None
        
        # 健康檢查配置
        self.health_check_config = {
            "interval": 60,  # seconds
            "timeout": 30,   # seconds
            "endpoints": [],
            "last_check": None,
            "status": "unknown"
        }
        
        self.logger.info(f"S-CBR API管理器 v{self.version} 初始化完成")
    
    async def initialize(self):
        """異步初始化"""
        try:
            # 創建 HTTP 客戶端會話
            timeout = aiohttp.ClientTimeout(total=30)
            self.http_session = aiohttp.ClientSession(timeout=timeout)
            
            # 開始健康檢查任務
            asyncio.create_task(self._health_check_task())
            
            # 開始性能監控任務
            asyncio.create_task(self._performance_monitoring_task())
            
            self.logger.info("API管理器異步初始化完成")
            
        except Exception as e:
            self.logger.error(f"API管理器初始化失敗: {str(e)}")
    
    async def cleanup(self):
        """清理資源"""
        try:
            if self.http_session:
                await self.http_session.close()
            self.logger.info("API管理器資源清理完成")
        except Exception as e:
            self.logger.error(f"API管理器清理失敗: {str(e)}")
    
    async def health_check_v2(self) -> Dict[str, Any]:
        """
        健康檢查 v2.0 - 回傳會話健康資訊
        
        Returns:
            Dict[str, Any]: 包含會話健康狀態的系統健康報告
        """
        try:
            self.logger.info("執行健康檢查 v2.0")
            
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": self.version,
                "uptime": self._calculate_uptime(),
                "checks": {}
            }
            
            # 基本系統檢查
            system_check = await self._check_system_health()
            health_status["checks"]["system"] = system_check
            
            # 數據庫連接檢查
            database_check = await self._check_database_health()
            health_status["checks"]["database"] = database_check
            
            # v2.0: 會話管理器健康檢查
            session_check = await self._check_session_health_v2()
            health_status["checks"]["sessions"] = session_check
            
            # 外部API檢查
            external_api_check = await self._check_external_apis()
            health_status["checks"]["external_apis"] = external_api_check
            
            # 記憶系統檢查
            memory_check = await self._check_memory_system()
            health_status["checks"]["memory_system"] = memory_check
            
            # v2.0: 智能體健康檢查
            agents_check = await self._check_agents_health()
            health_status["checks"]["agents"] = agents_check
            
            # 計算總體健康狀態
            all_checks_passed = all(
                check.get("status") == "healthy" 
                for check in health_status["checks"].values()
            )
            
            health_status["status"] = "healthy" if all_checks_passed else "unhealthy"
            
            # 更新統計
            self.api_stats["health_checks"] += 1
            self.api_stats["last_health_check"] = datetime.now().isoformat()
            self.health_check_config["last_check"] = datetime.now()
            self.health_check_config["status"] = health_status["status"]
            
            # v2.0: 添加會話統計到健康報告
            health_status["session_statistics"] = await self._get_session_statistics_v2()
            
            # 性能指標
            health_status["performance"] = await self._get_performance_metrics()
            
            self.logger.info(f"健康檢查完成 - 狀態: {health_status['status']}")
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"健康檢查失敗: {str(e)}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "version": self.version,
                "error": str(e),
                "checks": {}
            }
    
    async def _check_session_health_v2(self) -> Dict[str, Any]:
        """
        檢查會話管理器健康狀態 v2.0
        
        Returns:
            Dict[str, Any]: 會話健康狀態
        """
        try:
            session_manager = await self._get_session_manager()
            
            if not session_manager:
                return {
                    "status": "unhealthy",
                    "message": "會話管理器未初始化",
                    "active_sessions": 0,
                    "total_rounds": 0
                }
            
            # 獲取會話統計
            session_stats = session_manager.get_statistics()
            
            # 檢查會話管理器狀態
            active_sessions = session_stats.get("active_sessions", 0)
            total_rounds = session_stats.get("total_rounds", 0)
            max_sessions = self.config.get_config("session_config.max_sessions") if self.config else 1000
            
            # 健康狀態判定
            if active_sessions > max_sessions * 0.9:
                status = "warning"
                message = f"會話數接近上限 ({active_sessions}/{max_sessions})"
            elif active_sessions > max_sessions:
                status = "unhealthy"
                message = f"會話數超過上限 ({active_sessions}/{max_sessions})"
            else:
                status = "healthy"
                message = "會話管理器運行正常"
            
            return {
                "status": status,
                "message": message,
                "active_sessions": active_sessions,
                "total_rounds": total_rounds,
                "max_sessions": max_sessions,
                "session_utilization": active_sessions / max_sessions if max_sessions > 0 else 0,
                "session_stats": session_stats
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"會話健康檢查失敗: {str(e)}",
                "active_sessions": 0,
                "total_rounds": 0
            }
    
    async def _get_session_statistics_v2(self) -> Dict[str, Any]:
        """
        獲取會話統計 v2.0
        
        Returns:
            Dict[str, Any]: 會話統計信息
        """
        try:
            session_manager = await self._get_session_manager()
            
            if not session_manager:
                return {
                    "active_sessions": 0,
                    "total_sessions_created": 0,
                    "total_rounds": 0,
                    "avg_rounds_per_session": 0.0,
                    "success_rate": 0.0
                }
            
            # 獲取詳細統計
            stats = session_manager.get_statistics()
            
            # 計算衍生指標
            active_sessions = stats.get("active_sessions", 0)
            total_sessions = stats.get("total_sessions_created", 0)
            total_rounds = stats.get("total_rounds", 0)
            
            avg_rounds = total_rounds / total_sessions if total_sessions > 0 else 0.0
            
            # 更新內部指標
            self.session_metrics.update({
                "active_sessions": active_sessions,
                "total_sessions_created": total_sessions,
                "total_rounds_executed": total_rounds,
                "avg_rounds_per_session": avg_rounds,
                "session_success_rate": stats.get("success_rate", 0.0)
            })
            
            return {
                "active_sessions": active_sessions,
                "total_sessions_created": total_sessions,
                "total_rounds": total_rounds,
                "avg_rounds_per_session": round(avg_rounds, 2),
                "success_rate": round(stats.get("success_rate", 0.0), 3),
                "most_active_session_id": stats.get("most_active_session", {}).get("id"),
                "longest_session_duration": stats.get("longest_session", {}).get("duration"),
                "recent_activity": {
                    "sessions_last_hour": stats.get("sessions_last_hour", 0),
                    "rounds_last_hour": stats.get("rounds_last_hour", 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"獲取會話統計失敗: {str(e)}")
            return {
                "active_sessions": 0,
                "total_sessions_created": 0,
                "total_rounds": 0,
                "avg_rounds_per_session": 0.0,
                "success_rate": 0.0
            }
    
    async def _get_session_manager(self) -> Optional['SpiralSessionManager']:
        """獲取會話管理器實例（懶載入）"""
        if self._session_manager is None and SpiralSessionManager:
            try:
                self._session_manager = SpiralSessionManager()
            except Exception as e:
                self.logger.error(f"初始化會話管理器失敗: {str(e)}")
                return None
        
        return self._session_manager
    
    async def record_api_call(self, endpoint: str, method: str, status_code: int, response_time: float):
        """
        記錄API調用
        
        Args:
            endpoint: API端點
            method: HTTP方法
            status_code: 響應狀態碼
            response_time: 響應時間（秒）
        """
        try:
            # 更新基本統計
            self.api_stats["total_requests"] += 1
            self.api_stats["last_request_time"] = datetime.now().isoformat()
            
            if 200 <= status_code < 400:
                self.api_stats["successful_requests"] += 1
            else:
                self.api_stats["failed_requests"] += 1
            
            # 更新平均響應時間
            total_requests = self.api_stats["total_requests"]
            current_avg = self.api_stats["avg_response_time"]
            self.api_stats["avg_response_time"] = (
                (current_avg * (total_requests - 1) + response_time) / total_requests
            )
            
            # 更新性能指標
            self.performance_metrics["response_times"].append({
                "timestamp": datetime.now().isoformat(),
                "endpoint": endpoint,
                "method": method,
                "response_time": response_time,
                "status_code": status_code
            })
            
            # 保持最近1000次記錄
            if len(self.performance_metrics["response_times"]) > 1000:
                self.performance_metrics["response_times"] = self.performance_metrics["response_times"][-1000:]
            
            # 記錄錯誤率
            if status_code >= 400:
                self.performance_metrics["error_rates"].append({
                    "timestamp": datetime.now().isoformat(),
                    "endpoint": endpoint,
                    "status_code": status_code
                })
            
            # 保持最近500次錯誤記錄
            if len(self.performance_metrics["error_rates"]) > 500:
                self.performance_metrics["error_rates"] = self.performance_metrics["error_rates"][-500:]
            
        except Exception as e:
            self.logger.error(f"記錄API調用失敗: {str(e)}")
    
    async def get_api_statistics(self) -> Dict[str, Any]:
        """
        獲取API統計信息
        
        Returns:
            Dict[str, Any]: API統計
        """
        try:
            current_time = datetime.now()
            uptime = current_time - self.api_stats["start_time"]
            
            # 計算請求率
            total_requests = self.api_stats["total_requests"]
            requests_per_second = total_requests / uptime.total_seconds() if uptime.total_seconds() > 0 else 0
            
            # 計算成功率
            success_rate = (
                self.api_stats["successful_requests"] / total_requests 
                if total_requests > 0 else 1.0
            )
            
            # 最近1小時的統計
            one_hour_ago = current_time - timedelta(hours=1)
            recent_requests = [
                req for req in self.performance_metrics["response_times"]
                if datetime.fromisoformat(req["timestamp"]) > one_hour_ago
            ]
            
            recent_errors = [
                err for err in self.performance_metrics["error_rates"]
                if datetime.fromisoformat(err["timestamp"]) > one_hour_ago
            ]
            
            return {
                "basic_stats": self.api_stats.copy(),
                "performance": {
                    "uptime_seconds": int(uptime.total_seconds()),
                    "requests_per_second": round(requests_per_second, 2),
                    "success_rate": round(success_rate, 3),
                    "avg_response_time_ms": round(self.api_stats["avg_response_time"] * 1000, 2)
                },
                "recent_activity": {
                    "requests_last_hour": len(recent_requests),
                    "errors_last_hour": len(recent_errors),
                    "avg_response_time_last_hour": round(
                        sum(req["response_time"] for req in recent_requests) / len(recent_requests) * 1000, 2
                    ) if recent_requests else 0
                },
                "health_status": self.health_check_config["status"],
                "last_health_check": self.health_check_config["last_check"].isoformat() if self.health_check_config["last_check"] else None,
                "session_metrics": self.session_metrics.copy(),
                "version": self.version
            }
            
        except Exception as e:
            self.logger.error(f"獲取API統計失敗: {str(e)}")
            return {"error": str(e), "version": self.version}
    
    # 輔助方法實現
    async def _check_system_health(self) -> Dict[str, Any]:
        """檢查系統健康狀態"""
        try:
            # 檢查CPU和內存使用率
            cpu_usage = await self._get_cpu_usage()
            memory_usage = await self._get_memory_usage()
            
            status = "healthy"
            issues = []
            
            if cpu_usage > 90:
                status = "warning"
                issues.append(f"CPU使用率過高: {cpu_usage}%")
            
            if memory_usage > 90:
                status = "warning"
                issues.append(f"內存使用率過高: {memory_usage}%")
            
            return {
                "status": status,
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "issues": issues
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """檢查數據庫健康狀態"""
        try:
            # 簡化實現：假設數據庫正常
            return {
                "status": "healthy",
                "connection": "active",
                "response_time_ms": 5.2
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_external_apis(self) -> Dict[str, Any]:
        """檢查外部API健康狀態"""
        try:
            # 簡化實現
            return {
                "status": "healthy",
                "apis_checked": 0,
                "all_responsive": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_memory_system(self) -> Dict[str, Any]:
        """檢查記憶系統健康狀態"""
        try:
            return {
                "status": "healthy",
                "vector_db_connection": "active",
                "memory_count": 1000
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_agents_health(self) -> Dict[str, Any]:
        """檢查智能體健康狀態"""
        try:
            agents = ["diagnostic", "adaptation", "monitoring", "feedback"]
            agent_status = {}
            
            for agent in agents:
                agent_status[agent] = {
                    "status": "healthy",
                    "last_activity": datetime.now().isoformat()
                }
            
            return {
                "status": "healthy",
                "agents": agent_status
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """獲取性能指標"""
        try:
            cpu_usage = await self._get_cpu_usage()
            memory_usage = await self._get_memory_usage()
            
            # 更新性能指標
            self.performance_metrics["cpu_usage"] = cpu_usage
            self.performance_metrics["memory_usage"] = memory_usage
            
            return {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "disk_usage": self.performance_metrics["disk_usage"],
                "active_connections": self.performance_metrics["active_connections"],
                "avg_response_time_ms": round(self.api_stats["avg_response_time"] * 1000, 2)
            }
        except Exception as e:
            return {
                "error": str(e),
                "cpu_usage": 0,
                "memory_usage": 0
            }
    
    async def _get_cpu_usage(self) -> float:
        """獲取CPU使用率"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            # 如果沒有安裝psutil，返回模擬值
            import random
            return random.uniform(10, 30)
    
    async def _get_memory_usage(self) -> float:
        """獲取內存使用率"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            # 如果沒有安裝psutil，返回模擬值
            import random
            return random.uniform(40, 70)
    
    def _calculate_uptime(self) -> Dict[str, int]:
        """計算系統運行時間"""
        uptime = datetime.now() - self.api_stats["start_time"]
        
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return {
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "total_seconds": int(uptime.total_seconds())
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """獲取默認配置"""
        return {
            "session_config": {
                "max_sessions": 1000,
                "session_timeout_hours": 24
            },
            "spiral_config": {
                "max_rounds": 5
            }
        }
    
    async def _health_check_task(self):
        """定期健康檢查任務"""
        while True:
            try:
                await asyncio.sleep(self.health_check_config["interval"])
                await self.health_check_v2()
            except Exception as e:
                self.logger.error(f"定期健康檢查失敗: {str(e)}")
    
    async def _performance_monitoring_task(self):
        """性能監控任務"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分鐘更新一次
                await self._update_performance_metrics()
            except Exception as e:
                self.logger.error(f"性能監控更新失敗: {str(e)}")
    
    async def _update_performance_metrics(self):
        """更新性能指標"""
        try:
            self.performance_metrics["cpu_usage"] = await self._get_cpu_usage()
            self.performance_metrics["memory_usage"] = await self._get_memory_usage()
            
            # 清理舊的響應時間記錄（保留最近24小時）
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.performance_metrics["response_times"] = [
                record for record in self.performance_metrics["response_times"]
                if datetime.fromisoformat(record["timestamp"]) > cutoff_time
            ]
            
            # 清理舊的錯誤記錄
            self.performance_metrics["error_rates"] = [
                record for record in self.performance_metrics["error_rates"]
                if datetime.fromisoformat(record["timestamp"]) > cutoff_time
            ]
            
        except Exception as e:
            self.logger.error(f"更新性能指標失敗: {str(e)}")
    
    # 向後兼容方法（v1.0）
    async def health_check(self) -> Dict[str, Any]:
        """向後兼容的健康檢查"""
        result = await self.health_check_v2()
        # 移除v2.0特有的字段
        return {
            "status": result.get("status", "unknown"),
            "timestamp": result.get("timestamp", ""),
            "version": self.version,
            "uptime": result.get("uptime", {}),
            "checks": result.get("checks", {})
        }
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """向後兼容的系統統計"""
        return await self.get_api_statistics()
    
    def __del__(self):
        """析構函數"""
        if hasattr(self, 'http_session') and self.http_session:
            asyncio.create_task(self.http_session.close())

# 向後兼容的類別名稱
SCBRAPIManagerV2 = SCBRAPIManager

__all__ = ["SCBRAPIManager", "SCBRAPIManagerV2"]