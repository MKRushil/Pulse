"""
系統性能監控工具 v2.0

提供系統性能監控、告警與自動報告
支援CPU、內存、磁盤、網路監控

版本：v2.0 - 螺旋互動版
更新：增加性能監控與異常自動報警
"""

from typing import Dict, Any, List, Optional, Union, Callable
import logging
import asyncio
import time
import psutil
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from abc import ABC, abstractmethod

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
    from ..config.scbr_config import SCBRConfig, get_config
    from ..sessions.spiral_session_manager import SpiralSessionManager
    # 告警通知
    import smtplib
    import requests
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    NOTIFICATION_AVAILABLE = True
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    SCBRConfig = None
    SpiralSessionManager = None
    NOTIFICATION_AVAILABLE = False

@dataclass
class PerformanceThreshold:
    """性能閾值配置"""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    unit: str
    description: str

@dataclass
class AlertRule:
    """告警規則"""
    name: str
    condition: str  # "above", "below", "equals"
    threshold: float
    duration: int  # 持續時間（秒）
    severity: str  # "low", "medium", "high", "critical"
    enabled: bool = True

class NotificationChannel(ABC):
    """通知渠道抽象基類"""
    
    @abstractmethod
    async def send_notification(self, message: str, severity: str) -> bool:
        """發送通知"""
        pass

class EmailNotification(NotificationChannel):
    """電子郵件通知"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, 
                 recipients: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients
    
    async def send_notification(self, message: str, severity: str) -> bool:
        """發送電子郵件通知"""
        try:
            if not NOTIFICATION_AVAILABLE:
                return False
            
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"S-CBR 系統告警 - {severity.upper()}"
            
            body = f"""
            S-CBR 系統性能告警
            
            時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            嚴重程度: {severity.upper()}
            
            告警內容:
            {message}
            
            請及時處理！
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            
            text = msg.as_string()
            server.sendmail(self.username, self.recipients, text)
            server.quit()
            
            return True
            
        except Exception as e:
            logging.error(f"發送電子郵件失敗: {str(e)}")
            return False

class SlackNotification(NotificationChannel):
    """Slack 通知"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def send_notification(self, message: str, severity: str) -> bool:
        """發送 Slack 通知"""
        try:
            if not NOTIFICATION_AVAILABLE:
                return False
            
            # 根據嚴重程度選擇顏色
            color_map = {
                "low": "#36a64f",      # 綠色
                "medium": "#ff9500",   # 橙色  
                "high": "#ff0000",     # 紅色
                "critical": "#8B0000"  # 深紅色
            }
            
            payload = {
                "username": "S-CBR Monitor",
                "icon_emoji": ":warning:",
                "attachments": [{
                    "color": color_map.get(severity, "#ff0000"),
                    "title": f"S-CBR 系統告警 - {severity.upper()}",
                    "text": message,
                    "footer": "S-CBR v2.0 Performance Monitor",
                    "ts": int(time.time())
                }]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logging.error(f"發送 Slack 通知失敗: {str(e)}")
            return False

class SystemPerformanceMonitor:
    """
    系統性能監控器 v2.0
    
    v2.0 特色：
    - 多維度性能監控
    - 智能告警系統
    - 自動報告生成
    - 多通道通知
    """
    
    def __init__(self, config = None):
        """初始化系統性能監控器 v2.0"""
        self.logger = SpiralLogger.get_logger("PerformanceMonitor") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("PerformanceMonitor")
        self.version = "2.0"
        
        # 配置管理
        self.config = config or (get_config() if SCBRConfig else self._get_default_config())
        
        # 監控配置
        self.monitoring_config = self._get_monitoring_config()
        
        # 性能閾值
        self.thresholds = self._initialize_thresholds()
        
        # 告警規則
        self.alert_rules = self._initialize_alert_rules()
        
        # 通知渠道
        self.notification_channels = self._initialize_notification_channels()
        
        # 監控數據存儲
        self.performance_history = []
        self.alert_history = []
        
        # 監控狀態
        self.monitoring_active = False
        self.monitor_thread = None
        
        # 告警狀態
        self.active_alerts = {}
        self.alert_cooldowns = {}
        
        # 會話管理器引用（懶載入）
        self._session_manager = None
        
        self.logger.info(f"系統性能監控器 v{self.version} 初始化完成")
    
    def _get_monitoring_config(self) -> Dict[str, Any]:
        """獲取監控配置"""
        if self.config:
            return self.config.get_config("monitoring_config")
        
        return {
            "enabled": True,
            "check_interval": 30,  # 秒
            "history_retention_hours": 24,
            "alert_cooldown_minutes": 10,
            "performance_tracking": {
                "enabled": True,
                "track_cpu": True,
                "track_memory": True,
                "track_disk": True,
                "track_network": True,
                "track_sessions": True
            },
            "alerting": {
                "enabled": True,
                "email_notifications": False,
                "slack_webhook": "",
                "alert_thresholds": {
                    "cpu_percent": 80,
                    "memory_percent": 85,
                    "disk_percent": 90,
                    "response_time_ms": 5000
                }
            }
        }
    
    def _initialize_thresholds(self) -> List[PerformanceThreshold]:
        """初始化性能閾值"""
        return [
            PerformanceThreshold("cpu_percent", 70, 90, "%", "CPU使用率"),
            PerformanceThreshold("memory_percent", 80, 95, "%", "內存使用率"),
            PerformanceThreshold("disk_percent", 85, 95, "%", "磁盤使用率"),
            PerformanceThreshold("response_time", 2000, 5000, "ms", "響應時間"),
            PerformanceThreshold("active_sessions", 800, 950, "個", "活躍會話數"),
            PerformanceThreshold("error_rate", 5, 10, "%", "錯誤率")
        ]
    
    def _initialize_alert_rules(self) -> List[AlertRule]:
        """初始化告警規則"""
        return [
            AlertRule("高CPU使用", "above", 85, 60, "high"),
            AlertRule("高內存使用", "above", 90, 60, "high"), 
            AlertRule("磁盤空間不足", "above", 95, 30, "critical"),
            AlertRule("響應時間過長", "above", 5000, 120, "medium"),
            AlertRule("會話數過多", "above", 900, 300, "medium"),
            AlertRule("錯誤率過高", "above", 10, 180, "high")
        ]
    
    def _initialize_notification_channels(self) -> List[NotificationChannel]:
        """初始化通知渠道"""
        channels = []
        
        try:
            alerting_config = self.monitoring_config.get("alerting", {})
            
            # 電子郵件通知
            if alerting_config.get("email_notifications", False):
                email_config = alerting_config.get("email_config", {})
                if email_config:
                    channels.append(EmailNotification(
                        smtp_server=email_config.get("smtp_server", "smtp.gmail.com"),
                        smtp_port=email_config.get("smtp_port", 587),
                        username=email_config.get("username", ""),
                        password=email_config.get("password", ""),
                        recipients=email_config.get("recipients", [])
                    ))
            
            # Slack 通知
            slack_webhook = alerting_config.get("slack_webhook", "")
            if slack_webhook:
                channels.append(SlackNotification(slack_webhook))
                
        except Exception as e:
            self.logger.error(f"初始化通知渠道失敗: {str(e)}")
        
        return channels
    
    async def start_monitoring(self):
        """啟動性能監控"""
        try:
            if self.monitoring_active:
                self.logger.warning("性能監控已經在運行中")
                return
            
            self.monitoring_active = True
            
            # 啟動監控線程
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            self.logger.info("性能監控已啟動")
            
        except Exception as e:
            self.logger.error(f"啟動性能監控失敗: {str(e)}")
            self.monitoring_active = False
    
    async def stop_monitoring(self):
        """停止性能監控"""
        try:
            self.monitoring_active = False
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)
            
            self.logger.info("性能監控已停止")
            
        except Exception as e:
            self.logger.error(f"停止性能監控失敗: {str(e)}")
    
    def _monitor_loop(self):
        """監控循環"""
        while self.monitoring_active:
            try:
                # 收集性能數據
                performance_data = self._collect_performance_data()
                
                # 存儲數據
                self._store_performance_data(performance_data)
                
                # 檢查告警
                self._check_alerts(performance_data)
                
                # 清理舊數據
                self._cleanup_old_data()
                
                # 等待下次檢查
                time.sleep(self.monitoring_config.get("check_interval", 30))
                
            except Exception as e:
                self.logger.error(f"監控循環錯誤: {str(e)}")
                time.sleep(10)  # 錯誤後等待較短時間
    
    def _collect_performance_data(self) -> Dict[str, Any]:
        """收集性能數據"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "version": self.version
            }
            
            tracking_config = self.monitoring_config.get("performance_tracking", {})
            
            # CPU 使用率
            if tracking_config.get("track_cpu", True):
                data["cpu_percent"] = psutil.cpu_percent(interval=1)
                data["cpu_count"] = psutil.cpu_count()
                data["load_avg"] = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            
            # 內存使用
            if tracking_config.get("track_memory", True):
                memory = psutil.virtual_memory()
                data["memory_percent"] = memory.percent
                data["memory_total"] = memory.total
                data["memory_used"] = memory.used
                data["memory_available"] = memory.available
            
            # 磁盤使用
            if tracking_config.get("track_disk", True):
                disk = psutil.disk_usage('/')
                data["disk_percent"] = (disk.used / disk.total) * 100
                data["disk_total"] = disk.total
                data["disk_used"] = disk.used
                data["disk_free"] = disk.free
            
            # 網路 I/O
            if tracking_config.get("track_network", True):
                network = psutil.net_io_counters()
                data["network_bytes_sent"] = network.bytes_sent
                data["network_bytes_recv"] = network.bytes_recv
                data["network_packets_sent"] = network.packets_sent
                data["network_packets_recv"] = network.packets_recv
            
            # 進程信息
            process = psutil.Process()
            data["process_cpu_percent"] = process.cpu_percent()
            data["process_memory_mb"] = process.memory_info().rss / 1024 / 1024
            data["process_threads"] = process.num_threads()
            
            # 會話統計
            if tracking_config.get("track_sessions", True):
                session_stats = self._get_session_stats()
                data.update(session_stats)
            
            return data
            
        except Exception as e:
            self.logger.error(f"收集性能數據失敗: {str(e)}")
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}
    
    def _get_session_stats(self) -> Dict[str, Any]:
        """獲取會話統計"""
        try:
            if not self._session_manager and SpiralSessionManager:
                self._session_manager = SpiralSessionManager()
            
            if self._session_manager:
                stats = self._session_manager.get_statistics()
                return {
                    "active_sessions": stats.get("active_sessions", 0),
                    "total_sessions": stats.get("total_sessions_created", 0),
                    "total_rounds": stats.get("total_rounds", 0),
                    "success_rate": stats.get("success_rate", 0.0)
                }
        except Exception as e:
            self.logger.error(f"獲取會話統計失敗: {str(e)}")
        
        return {
            "active_sessions": 0,
            "total_sessions": 0,
            "total_rounds": 0,
            "success_rate": 0.0
        }
    
    def _store_performance_data(self, data: Dict[str, Any]):
        """存儲性能數據"""
        try:
            self.performance_history.append(data)
            
            # 限制歷史數據數量
            max_history = self.monitoring_config.get("history_retention_hours", 24) * 120  # 每分鐘2次檢查
            if len(self.performance_history) > max_history:
                self.performance_history = self.performance_history[-max_history:]
                
        except Exception as e:
            self.logger.error(f"存儲性能數據失敗: {str(e)}")
    
    def _check_alerts(self, data: Dict[str, Any]):
        """檢查告警"""
        try:
            if not self.monitoring_config.get("alerting", {}).get("enabled", True):
                return
            
            current_time = datetime.now()
            
            for rule in self.alert_rules:
                if not rule.enabled:
                    continue
                
                metric_value = data.get(rule.name.lower().replace(" ", "_").replace("高", "").replace("使用", ""))
                if metric_value is None:
                    continue
                
                # 檢查是否觸發告警條件
                triggered = False
                if rule.condition == "above" and metric_value > rule.threshold:
                    triggered = True
                elif rule.condition == "below" and metric_value < rule.threshold:
                    triggered = True
                elif rule.condition == "equals" and metric_value == rule.threshold:
                    triggered = True
                
                if triggered:
                    self._handle_alert(rule, metric_value, current_time)
                else:
                    # 清除已解決的告警
                    if rule.name in self.active_alerts:
                        self._resolve_alert(rule.name, current_time)
                        
        except Exception as e:
            self.logger.error(f"檢查告警失敗: {str(e)}")
    
    def _handle_alert(self, rule: AlertRule, metric_value: float, current_time: datetime):
        """處理告警"""
        try:
            # 檢查冷卻時間
            cooldown_key = rule.name
            if cooldown_key in self.alert_cooldowns:
                last_alert_time = self.alert_cooldowns[cooldown_key]
                cooldown_minutes = self.monitoring_config.get("alert_cooldown_minutes", 10)
                if (current_time - last_alert_time).total_seconds() < cooldown_minutes * 60:
                    return
            
            # 記錄告警
            alert_record = {
                "rule_name": rule.name,
                "metric_value": metric_value,
                "threshold": rule.threshold,
                "severity": rule.severity,
                "timestamp": current_time.isoformat(),
                "status": "active"
            }
            
            self.alert_history.append(alert_record)
            self.active_alerts[rule.name] = alert_record
            
            # 發送通知
            message = f"{rule.name}: 當前值 {metric_value} 超過閾值 {rule.threshold}"
            asyncio.create_task(self._send_notifications(message, rule.severity))
            
            # 記錄日誌
            self.logger.warning(f"觸發告警 - {message}")
            
            # 更新冷卻時間
            self.alert_cooldowns[cooldown_key] = current_time
            
        except Exception as e:
            self.logger.error(f"處理告警失敗: {str(e)}")
    
    def _resolve_alert(self, rule_name: str, current_time: datetime):
        """解決告警"""
        try:
            if rule_name in self.active_alerts:
                alert_record = self.active_alerts[rule_name]
                alert_record["status"] = "resolved"
                alert_record["resolved_at"] = current_time.isoformat()
                
                # 從活躍告警中移除
                del self.active_alerts[rule_name]
                
                # 發送解決通知
                message = f"告警已解決: {rule_name}"
                asyncio.create_task(self._send_notifications(message, "info"))
                
                self.logger.info(f"告警已解決 - {rule_name}")
                
        except Exception as e:
            self.logger.error(f"解決告警失敗: {str(e)}")
    
    async def _send_notifications(self, message: str, severity: str):
        """發送通知"""
        try:
            for channel in self.notification_channels:
                try:
                    await channel.send_notification(message, severity)
                except Exception as e:
                    self.logger.error(f"通知渠道發送失敗: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"發送通知失敗: {str(e)}")
    
    def _cleanup_old_data(self):
        """清理舊數據"""
        try:
            retention_hours = self.monitoring_config.get("history_retention_hours", 24)
            cutoff_time = datetime.now() - timedelta(hours=retention_hours)
            cutoff_timestamp = cutoff_time.isoformat()
            
            # 清理性能歷史
            self.performance_history = [
                data for data in self.performance_history
                if data.get("timestamp", "") > cutoff_timestamp
            ]
            
            # 清理告警歷史
            self.alert_history = [
                alert for alert in self.alert_history
                if alert.get("timestamp", "") > cutoff_timestamp
            ]
            
        except Exception as e:
            self.logger.error(f"清理舊數據失敗: {str(e)}")
    
    def get_performance_report(self, hours: int = 1) -> Dict[str, Any]:
        """
        獲取性能報告
        
        Args:
            hours: 統計時間範圍（小時）
            
        Returns:
            Dict[str, Any]: 性能報告
        """
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            start_timestamp = start_time.isoformat()
            
            # 過濾指定時間範圍的數據
            filtered_data = [
                data for data in self.performance_history
                if data.get("timestamp", "") > start_timestamp
            ]
            
            if not filtered_data:
                return {"error": "沒有可用的性能數據", "hours": hours}
            
            # 計算統計指標
            report = {
                "time_range": f"最近 {hours} 小時",
                "data_points": len(filtered_data),
                "start_time": start_timestamp,
                "end_time": datetime.now().isoformat(),
                "statistics": {}
            }
            
            # 計算各項指標的統計
            metrics = ["cpu_percent", "memory_percent", "disk_percent", 
                      "process_cpu_percent", "process_memory_mb", "active_sessions"]
            
            for metric in metrics:
                values = [data.get(metric, 0) for data in filtered_data if metric in data]
                if values:
                    report["statistics"][metric] = {
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "current": values[-1] if values else 0
                    }
            
            # 活躍告警
            report["active_alerts"] = list(self.active_alerts.values())
            
            # 近期告警
            recent_alerts = [
                alert for alert in self.alert_history
                if alert.get("timestamp", "") > start_timestamp
            ]
            report["recent_alerts"] = len(recent_alerts)
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成性能報告失敗: {str(e)}")
            return {"error": str(e)}
    
    def get_current_status(self) -> Dict[str, Any]:
        """獲取當前系統狀態"""
        try:
            if not self.performance_history:
                return {"status": "no_data", "message": "沒有性能數據"}
            
            latest_data = self.performance_history[-1]
            
            status = {
                "timestamp": latest_data.get("timestamp", ""),
                "monitoring_active": self.monitoring_active,
                "system_health": "healthy",
                "metrics": {},
                "alerts": {
                    "active_count": len(self.active_alerts),
                    "active_alerts": list(self.active_alerts.keys())
                }
            }
            
            # 提取關鍵指標
            key_metrics = ["cpu_percent", "memory_percent", "disk_percent", "active_sessions"]
            for metric in key_metrics:
                if metric in latest_data:
                    status["metrics"][metric] = latest_data[metric]
            
            # 判斷系統健康狀態
            if len(self.active_alerts) > 0:
                critical_alerts = [a for a in self.active_alerts.values() 
                                 if a.get("severity") == "critical"]
                high_alerts = [a for a in self.active_alerts.values() 
                             if a.get("severity") == "high"]
                
                if critical_alerts:
                    status["system_health"] = "critical"
                elif high_alerts:
                    status["system_health"] = "warning"
                else:
                    status["system_health"] = "degraded"
            
            return status
            
        except Exception as e:
            self.logger.error(f"獲取系統狀態失敗: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _get_default_config(self) -> Dict[str, Any]:
        """獲取默認配置"""
        return {
            "monitoring_config": {
                "enabled": True,
                "check_interval": 30,
                "alerting": {"enabled": True}
            }
        }
    
    async def __aenter__(self):
        """異步上下文管理器進入"""
        await self.start_monitoring()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        await self.stop_monitoring()

# 便捷函數
def create_performance_monitor(config: Optional[SCBRConfig] = None) -> SystemPerformanceMonitor:
    """創建性能監控器實例"""
    return SystemPerformanceMonitor(config)

async def get_system_health() -> Dict[str, Any]:
    """獲取系統健康狀況"""
    monitor = create_performance_monitor()
    return monitor.get_current_status()

# 向後兼容的類別名稱
SystemPerformanceMonitorV2 = SystemPerformanceMonitor

__all__ = [
    "SystemPerformanceMonitor", "SystemPerformanceMonitorV2",
    "PerformanceThreshold", "AlertRule", "NotificationChannel",
    "EmailNotification", "SlackNotification",
    "create_performance_monitor", "get_system_health"
]