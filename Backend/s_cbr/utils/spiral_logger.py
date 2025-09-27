"""
螺旋日誌工具 v2.0

提供結構化日誌記錄與事件追蹤
支援會話級別日誌與性能監控

版本：v2.0 - 螺旋互動版
更新：結構化JSON日誌與會話事件記錄
"""

from typing import Dict, Any, List, Optional, Union
import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 動態導入避免循環依賴
try:
    from ..config.scbr_config import SCBRConfig, get_config
    from ..sessions.spiral_session_manager import SpiralSessionManager
except ImportError:
    # 降級處理
    SCBRConfig = None
    SpiralSessionManager = None

class SpiralLogger:
    """
    螺旋日誌工具 v2.0
    
    v2.0 特色：
    - 結構化JSON日誌
    - 會話級別事件記錄
    - 性能指標日誌
    - 自動日誌輪轉
    - 多重輸出目標
    """
    
    _instances = {}
    _config = None
    
    def __init__(self, name: str, config = None):
        """初始化螺旋日誌工具 v2.0"""
        self.name = name
        self.version = "2.0"
        
        # 配置管理
        if config is None and SCBRConfig:
            config = get_config()
        self.config = config
        
        # 日誌配置
        self.logging_config = self._get_logging_config()
        
        # 創建基礎logger
        self.logger = logging.getLogger(f"SCBR.{name}")
        
        # 防止重複配置
        if not self.logger.handlers:
            self._setup_logger()
        
        # 會話管理器引用（懶載入）
        self._session_manager = None
        
        # 性能指標收集
        self.performance_metrics = []
        self.error_counts = {}
        self.session_events = []
        
    @classmethod
    def get_logger(cls, name: str, config = None) -> 'SpiralLogger':
        """
        獲取日誌實例（單例模式）
        
        Args:
            name: 日誌器名稱
            config: 配置實例
            
        Returns:
            SpiralLogger: 日誌實例
        """
        if name not in cls._instances:
            cls._instances[name] = cls(name, config)
        
        return cls._instances[name]
    
    def _get_logging_config(self) -> Dict[str, Any]:
        """獲取日誌配置"""
        if self.config:
            return self.config.get_config("logging_config")
        
        # 默認配置
        return {
            "level": "INFO",
            "format": "json",
            "file_enabled": True,
            "file_path": "./logs/scbr.log",
            "file_max_size": "10MB",
            "file_backup_count": 5,
            "console_enabled": True,
            "structured_logging": True,
            "log_session_events": True,
            "log_performance_metrics": True
        }
    
    def _setup_logger(self):
        """設置日誌器"""
        try:
            # 設置日誌級別
            level_str = self.logging_config.get("level", "INFO")
            level = getattr(logging, level_str.upper(), logging.INFO)
            self.logger.setLevel(level)
            
            # 創建格式化器
            formatter = self._create_formatter()
            
            # 控制台處理器
            if self.logging_config.get("console_enabled", True):
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(level)
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
            
            # 文件處理器
            if self.logging_config.get("file_enabled", True):
                file_handler = self._create_file_handler()
                file_handler.setLevel(level)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            
            # 防止日誌重複傳播
            self.logger.propagate = False
            
        except Exception as e:
            # 降級到基本日誌
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            logging.error(f"設置螺旋日誌失敗: {str(e)}")
    
    def _create_formatter(self) -> logging.Formatter:
        """創建日誌格式化器"""
        format_type = self.logging_config.get("format", "json")
        
        if format_type == "json":
            return JSONFormatter()
        else:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
    
    def _create_file_handler(self) -> logging.Handler:
        """創建文件處理器"""
        file_path = self.logging_config.get("file_path", "./logs/scbr.log")
        
        # 確保日誌目錄存在
        log_dir = Path(file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 解析文件大小
        max_size_str = self.logging_config.get("file_max_size", "10MB")
        max_bytes = self._parse_file_size(max_size_str)
        
        backup_count = self.logging_config.get("file_backup_count", 5)
        
        # 創建輪轉文件處理器
        handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        return handler
    
    def _parse_file_size(self, size_str: str) -> int:
        """解析文件大小字符串"""
        size_str = size_str.upper()
        
        if 'KB' in size_str:
            return int(size_str.replace('KB', '')) * 1024
        elif 'MB' in size_str:
            return int(size_str.replace('MB', '')) * 1024 * 1024
        elif 'GB' in size_str:
            return int(size_str.replace('GB', '')) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def log_event(self, 
                 session_id: str, 
                 round_number: int, 
                 level: str, 
                 message: str, 
                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        記錄會話事件 v2.0
        
        Args:
            session_id: 會話ID
            round_number: 輪次編號
            level: 日誌級別
            message: 日誌消息
            metadata: 額外元數據
        """
        try:
            # 構建事件對象
            event = {
                "session_id": session_id,
                "round": round_number,
                "timestamp": datetime.now().isoformat(),
                "level": level.upper(),
                "message": message,
                "metadata": metadata or {},
                "logger_name": self.name,
                "version": self.version
            }
            
            # 記錄到會話事件列表
            if self.logging_config.get("log_session_events", True):
                self.session_events.append(event)
                
                # 保持最近1000個事件
                if len(self.session_events) > 1000:
                    self.session_events = self.session_events[-1000:]
            
            # 記錄到標準日誌
            log_method = getattr(self.logger, level.lower(), self.logger.info)
            
            if self.logging_config.get("structured_logging", True):
                log_method(json.dumps(event, ensure_ascii=False))
            else:
                log_method(f"[{session_id}:{round_number}] {message}")
                
        except Exception as e:
            self.logger.error(f"記錄事件失敗: {str(e)}")
    
    def log_performance(self, 
                       operation: str, 
                       duration: float, 
                       session_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        記錄性能指標 v2.0
        
        Args:
            operation: 操作名稱
            duration: 執行時間（秒）
            session_id: 會話ID（可選）
            metadata: 額外元數據
        """
        try:
            # 構建性能記錄
            performance_record = {
                "operation": operation,
                "duration": duration,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
                "version": self.version
            }
            
            # 記錄到性能指標列表
            if self.logging_config.get("log_performance_metrics", True):
                self.performance_metrics.append(performance_record)
                
                # 保持最近500個記錄
                if len(self.performance_metrics) > 500:
                    self.performance_metrics = self.performance_metrics[-500:]
            
            # 記錄到日誌
            self.logger.info(
                f"PERFORMANCE: {operation} took {duration:.3f}s" + 
                (f" [session: {session_id}]" if session_id else "")
            )
            
        except Exception as e:
            self.logger.error(f"記錄性能指標失敗: {str(e)}")
    
    def log_error(self, 
                 error: Exception, 
                 session_id: Optional[str] = None,
                 round_number: Optional[int] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        記錄錯誤 v2.0
        
        Args:
            error: 異常對象
            session_id: 會話ID（可選）
            round_number: 輪次編號（可選）  
            metadata: 額外元數據
        """
        try:
            error_type = type(error).__name__
            
            # 統計錯誤次數
            if error_type not in self.error_counts:
                self.error_counts[error_type] = 0
            self.error_counts[error_type] += 1
            
            # 構建錯誤信息
            error_info = {
                "error_type": error_type,
                "error_message": str(error),
                "session_id": session_id,
                "round": round_number,
                "error_count": self.error_counts[error_type],
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
                "version": self.version
            }
            
            # 記錄錯誤
            if session_id and round_number:
                self.log_event(session_id, round_number, "ERROR", str(error), error_info)
            else:
                self.logger.error(json.dumps(error_info, ensure_ascii=False))
                
        except Exception as e:
            self.logger.error(f"記錄錯誤失敗: {str(e)}")
    
    def get_session_logs(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        獲取會話日誌 v2.0
        
        Args:
            session_id: 會話ID
            limit: 返回數量限制
            
        Returns:
            List[Dict[str, Any]]: 會話日誌列表
        """
        try:
            session_logs = [
                event for event in self.session_events
                if event.get("session_id") == session_id
            ]
            
            # 按時間戳排序
            session_logs.sort(key=lambda x: x.get("timestamp", ""))
            
            return session_logs[-limit:] if limit > 0 else session_logs
            
        except Exception as e:
            self.logger.error(f"獲取會話日誌失敗: {str(e)}")
            return []
    
    def get_performance_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取性能統計 v2.0
        
        Args:
            operation: 操作名稱（可選，為空則返回所有）
            
        Returns:
            Dict[str, Any]: 性能統計
        """
        try:
            # 過濾指定操作
            metrics = self.performance_metrics
            if operation:
                metrics = [m for m in metrics if m.get("operation") == operation]
            
            if not metrics:
                return {"operation": operation, "count": 0}
            
            durations = [m.get("duration", 0) for m in metrics]
            
            stats = {
                "operation": operation or "all",
                "count": len(metrics),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "total_duration": sum(durations),
                "last_recorded": metrics[-1].get("timestamp", "")
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"獲取性能統計失敗: {str(e)}")
            return {"error": str(e)}
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        獲取錯誤摘要 v2.0
        
        Returns:
            Dict[str, Any]: 錯誤統計摘要
        """
        try:
            total_errors = sum(self.error_counts.values())
            
            # 按錯誤次數排序
            sorted_errors = sorted(
                self.error_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            return {
                "total_errors": total_errors,
                "error_types": len(self.error_counts),
                "error_breakdown": dict(sorted_errors),
                "most_common_error": sorted_errors[0][0] if sorted_errors else None,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"獲取錯誤摘要失敗: {str(e)}")
            return {"error": str(e)}
    
    def cleanup_old_logs(self, days: int = 7) -> Dict[str, int]:
        """
        清理舊日誌 v2.0
        
        Args:
            days: 保留天數
            
        Returns:
            Dict[str, int]: 清理統計
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            cutoff_timestamp = cutoff_time.isoformat()
            
            # 清理會話事件
            original_events = len(self.session_events)
            self.session_events = [
                event for event in self.session_events
                if event.get("timestamp", "") > cutoff_timestamp
            ]
            events_cleaned = original_events - len(self.session_events)
            
            # 清理性能指標
            original_metrics = len(self.performance_metrics)
            self.performance_metrics = [
                metric for metric in self.performance_metrics
                if metric.get("timestamp", "") > cutoff_timestamp
            ]
            metrics_cleaned = original_metrics - len(self.performance_metrics)
            
            cleanup_stats = {
                "events_cleaned": events_cleaned,
                "metrics_cleaned": metrics_cleaned,
                "total_cleaned": events_cleaned + metrics_cleaned,
                "cutoff_date": cutoff_time.strftime("%Y-%m-%d")
            }
            
            self.logger.info(f"日誌清理完成: {cleanup_stats}")
            
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"清理舊日誌失敗: {str(e)}")
            return {"error": str(e)}
    
    def export_logs(self, 
                   session_id: Optional[str] = None,
                   start_time: Optional[str] = None,
                   end_time: Optional[str] = None,
                   format_type: str = "json") -> str:
        """
        導出日誌 v2.0
        
        Args:
            session_id: 會話ID過濾（可選）
            start_time: 開始時間（ISO格式）
            end_time: 結束時間（ISO格式）
            format_type: 導出格式（json, csv）
            
        Returns:
            str: 導出文件路徑
        """
        try:
            # 過濾日誌
            filtered_events = self.session_events
            
            if session_id:
                filtered_events = [
                    event for event in filtered_events
                    if event.get("session_id") == session_id
                ]
            
            if start_time:
                filtered_events = [
                    event for event in filtered_events
                    if event.get("timestamp", "") >= start_time
                ]
            
            if end_time:
                filtered_events = [
                    event for event in filtered_events
                    if event.get("timestamp", "") <= end_time
                ]
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scbr_logs_{timestamp}.{format_type}"
            
            # 創建導出目錄
            export_dir = Path("./exports/logs")
            export_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = export_dir / filename
            
            # 導出文件
            if format_type == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(filtered_events, f, ensure_ascii=False, indent=2)
            elif format_type == "csv":
                import csv
                if filtered_events:
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=filtered_events[0].keys())
                        writer.writeheader()
                        writer.writerows(filtered_events)
            
            self.logger.info(f"日誌導出完成: {file_path}")
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"導出日誌失敗: {str(e)}")
            return ""
    
    # 標準日誌方法
    def debug(self, message: str, **kwargs):
        """Debug級別日誌"""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Info級別日誌"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Warning級別日誌"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Error級別日誌"""
        self.logger.error(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs):
        """Exception級別日誌（帶堆疊）"""
        self.logger.exception(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Critical級別日誌"""
        self.logger.critical(message, extra=kwargs)

class JSONFormatter(logging.Formatter):
    """JSON格式化器"""
    
    def format(self, record):
        """格式化日誌記錄為JSON"""
        try:
            log_obj = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }
            
            # 添加異常信息
            if record.exc_info:
                log_obj["exception"] = self.formatException(record.exc_info)
            
            # 添加額外字段
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                              'pathname', 'filename', 'module', 'lineno', 
                              'funcName', 'created', 'msecs', 'relativeCreated', 
                              'thread', 'threadName', 'processName', 'process',
                              'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                    log_obj[key] = value
            
            return json.dumps(log_obj, ensure_ascii=False)
            
        except Exception as e:
            # 降級到基本格式
            return f"{datetime.fromtimestamp(record.created).isoformat()} - {record.levelname} - {record.getMessage()}"

class PerformanceLogger:
    """性能日誌記錄器"""
    
    def __init__(self, logger: SpiralLogger, operation: str, session_id: Optional[str] = None):
        """
        初始化性能記錄器
        
        Args:
            logger: 螺旋日誌實例
            operation: 操作名稱
            session_id: 會話ID（可選）
        """
        self.logger = logger
        self.operation = operation
        self.session_id = session_id
        self.start_time = None
    
    def __enter__(self):
        """進入上下文"""
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            
            metadata = {}
            if exc_type:
                metadata["error"] = str(exc_val)
                metadata["error_type"] = exc_type.__name__
            
            self.logger.log_performance(
                self.operation, 
                duration, 
                self.session_id, 
                metadata
            )

# 便捷函數
def get_spiral_logger(name: str) -> SpiralLogger:
    """獲取螺旋日誌實例"""
    return SpiralLogger.get_logger(name)

def log_performance(operation: str, session_id: Optional[str] = None):
    """
    性能記錄裝飾器
    
    Args:
        operation: 操作名稱
        session_id: 會話ID（可選）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_spiral_logger(func.__module__)
            with PerformanceLogger(logger, operation, session_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# 向後兼容的類別名稱
SpiralLoggerV2 = SpiralLogger

__all__ = [
    "SpiralLogger", "SpiralLoggerV2", "JSONFormatter", "PerformanceLogger",
    "get_spiral_logger", "log_performance"
]