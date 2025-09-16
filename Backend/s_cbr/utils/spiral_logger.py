"""
螺旋日誌器 v1.1 - 修復重複日誌問題
"""

import logging
import sys
from typing import Optional

class SpiralLogger:
    """螺旋日誌器 - 防止重複日誌"""
    
    _loggers = {}  # 類級別的日誌器緩存
    _initialized = set()  # 追蹤已初始化的日誌器
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """獲取日誌器 - 防止重複創建"""
        
        # 🔥 關鍵修復：檢查是否已存在
        if name in cls._loggers:
            return cls._loggers[name]
        
        # 創建新的日誌器
        logger = logging.getLogger(name)
        
        # 🔥 關鍵修復：防止重複初始化
        if name not in cls._initialized:
            # 設置日誌級別
            logger.setLevel(logging.INFO)
            
            # 🔥 關鍵修復：清除現有 handlers (如果有)
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
            
            # 創建格式化器
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)8s] %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # 創建控制台處理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            
            # 添加處理器
            logger.addHandler(console_handler)
            
            # 🔥 關鍵修復：禁用向上傳播，防止重複
            logger.propagate = False
            
            # 標記為已初始化
            cls._initialized.add(name)
        
        # 緩存並返回
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def cleanup_loggers(cls):
        """清理所有日誌器"""
        for logger in cls._loggers.values():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        
        cls._loggers.clear()
        cls._initialized.clear()
