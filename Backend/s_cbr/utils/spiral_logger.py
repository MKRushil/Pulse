"""
螺旋推理日誌器 v1.0

v1.0 功能：
- S-CBR 專用日誌管理
- 多級別日誌記錄
- 效能追蹤日誌
- 錯誤與警告追蹤

版本：v1.0
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler

class SpiralLogger:
    """
    螺旋推理日誌器 v1.0
    
    v1.0 特色：
    - 統一的日誌管理接口
    - 自動日誌輪替
    - 效能監控集成
    - 結構化日誌格式
    """
    
    _loggers: Dict[str, logging.Logger] = {}
    _initialized = False
    
    @classmethod
    def _initialize_logging(cls):
        """初始化日誌系統"""
        if cls._initialized:
            return
        
        # 創建日誌目錄
        log_dir = "logs/s_cbr"
        os.makedirs(log_dir, exist_ok=True)
        
        # 設置根日誌格式
        log_format = "%(asctime)s [%(levelname)8s] %(name)s - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        
        # 配置根 logger
        root_logger = logging.getLogger("s_cbr")
        root_logger.setLevel(logging.DEBUG)
        
        # 避免重複配置
        if not root_logger.handlers:
            # 控制台處理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(log_format, date_format)
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
            
            # 文件處理器（輪替）
            file_handler = RotatingFileHandler(
                filename=os.path.join(log_dir, "spiral_cbr.log"),
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(log_format, date_format)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            
            # 錯誤專用文件處理器
            error_handler = RotatingFileHandler(
                filename=os.path.join(log_dir, "spiral_cbr_errors.log"),
                maxBytes=5*1024*1024,  # 5MB
                backupCount=3,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)8s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
                date_format
            )
            error_handler.setFormatter(error_formatter)
            root_logger.addHandler(error_handler)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        獲取 S-CBR 日誌器實例
        
        Args:
            name: 日誌器名稱（通常是模組名）
            
        Returns:
            配置好的日誌器實例
        """
        if not cls._initialized:
            cls._initialize_logging()
        
        if name in cls._loggers:
            return cls._loggers[name]
        
        # 創建子日誌器
        full_name = f"s_cbr.{name}"
        logger = logging.getLogger(full_name)
        
        # 設置日誌級別
        logger.setLevel(logging.DEBUG)
        
        # 不要傳播到父日誌器（避免重複輸出）
        logger.propagate = True  # 讓它傳播到根日誌器
        
        cls._loggers[name] = logger
        
        return logger
    
    @classmethod
    def log_performance(cls, logger_name: str, operation: str, 
                       duration_ms: float, details: Optional[Dict[str, Any]] = None):
        """
        記錄效能日誌
        
        Args:
            logger_name: 日誌器名稱
            operation: 操作名稱
            duration_ms: 執行時間（毫秒）
            details: 額外詳細資訊
        """
        logger = cls.get_logger(logger_name)
        
        performance_info = f"PERFORMANCE: {operation} completed in {duration_ms:.2f}ms"
        
        if details:
            detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            performance_info += f" | {detail_str}"
        
        logger.info(performance_info)
    
    @classmethod
    def log_spiral_step(cls, logger_name: str, session_id: str, step_number: int,
                       step_name: str, result: str, duration_ms: float = 0):
        """
        記錄螺旋推理步驟
        
        Args:
            logger_name: 日誌器名稱
            session_id: 會話ID
            step_number: 步驟編號
            step_name: 步驟名稱
            result: 執行結果
            duration_ms: 執行時間
        """
        logger = cls.get_logger(logger_name)
        
        step_info = f"SPIRAL_STEP: Session[{session_id}] Step{step_number}({step_name}) -> {result}"
        
        if duration_ms > 0:
            step_info += f" | Duration: {duration_ms:.2f}ms"
        
        logger.info(step_info)
    
    @classmethod
    def log_pulse_integration(cls, logger_name: str, session_id: str,
                            pulse_count: int, integration_quality: float,
                            details: Optional[Dict[str, Any]] = None):
        """
        記錄脈診整合日誌 v1.0
        
        Args:
            logger_name: 日誌器名稱
            session_id: 會話ID
            pulse_count: 脈診知識數量
            integration_quality: 整合品質分數
            details: 額外詳細資訊
        """
        logger = cls.get_logger(logger_name)
        
        pulse_info = (f"PULSE_INTEGRATION: Session[{session_id}] "
                     f"Integrated {pulse_count} pulse knowledge, "
                     f"Quality: {integration_quality:.1%}")
        
        if details:
            detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            pulse_info += f" | {detail_str}"
        
        logger.info(pulse_info)
    
    @classmethod
    def log_agent_activity(cls, logger_name: str, agent_name: str, 
                          activity: str, session_id: str, 
                          details: Optional[Dict[str, Any]] = None):
        """
        記錄智能體活動
        
        Args:
            logger_name: 日誌器名稱
            agent_name: 智能體名稱
            activity: 活動描述
            session_id: 會話ID
            details: 額外詳細資訊
        """
        logger = cls.get_logger(logger_name)
        
        agent_info = f"AGENT_ACTIVITY: {agent_name} -> {activity} | Session[{session_id}]"
        
        if details:
            detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            agent_info += f" | {detail_str}"
        
        logger.debug(agent_info)
    
    @classmethod
    def log_error_with_context(cls, logger_name: str, error_msg: str,
                             context: Dict[str, Any], exception: Exception = None):
        """
        記錄帶上下文的錯誤
        
        Args:
            logger_name: 日誌器名稱
            error_msg: 錯誤消息
            context: 上下文資訊
            exception: 異常對象
        """
        logger = cls.get_logger(logger_name)
        
        context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
        full_error_msg = f"{error_msg} | Context: {context_str}"
        
        if exception:
            logger.error(full_error_msg, exc_info=exception)
        else:
            logger.error(full_error_msg)
    
    @classmethod
    def log_user_interaction(cls, logger_name: str, session_id: str,
                           interaction_type: str, details: Dict[str, Any]):
        """
        記錄用戶交互
        
        Args:
            logger_name: 日誌器名稱
            session_id: 會話ID
            interaction_type: 交互類型
            details: 詳細資訊
        """
        logger = cls.get_logger(logger_name)
        
        detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
        interaction_info = f"USER_INTERACTION: Session[{session_id}] {interaction_type} | {detail_str}"
        
        logger.info(interaction_info)
    
    @classmethod
    def set_log_level(cls, logger_name: str, level: str):
        """
        設置特定日誌器的日誌級別
        
        Args:
            logger_name: 日誌器名稱
            level: 日誌級別 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        logger = cls.get_logger(logger_name)
        
        level_mapping = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() in level_mapping:
            logger.setLevel(level_mapping[level.upper()])
    
    @classmethod
    def get_logger_stats(cls) -> Dict[str, Any]:
        """獲取日誌器統計資訊"""
        return {
            "active_loggers": len(cls._loggers),
            "logger_names": list(cls._loggers.keys()),
            "initialized": cls._initialized,
            "timestamp": datetime.now().isoformat()
        }
