# -*- coding: utf-8 -*-
"""
日誌管理器
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# 創建日誌目錄
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 配置格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 全局配置標記
_configured = False

def configure_logging(level: str = "INFO", to_file: bool = True):
    """配置全局日誌"""
    global _configured
    
    if _configured:
        return
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 控制台處理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    )
    
    handlers = [console_handler]
    
    # 文件處理器
    if to_file:
        log_file = LOG_DIR / f"scbr_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter(LOG_FORMAT, DATE_FORMAT)
        )
        handlers.append(file_handler)
    
    # 配置根日誌
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True
    )
    
    _configured = True

def get_logger(name: str) -> logging.Logger:
    """獲取日誌器"""
    
    # 確保已配置
    if not _configured:
        configure_logging()
    
    # 創建日誌器
    logger = logging.getLogger(f"s_cbr.{name}")
    
    return logger

# 特殊日誌器
def get_query_logger() -> logging.Logger:
    """獲取查詢專用日誌器"""
    logger = get_logger("query")
    
    # 添加額外的查詢日誌文件
    query_file = LOG_DIR / f"queries_{datetime.now().strftime('%Y%m%d')}.log"
    query_handler = logging.FileHandler(query_file, encoding="utf-8")
    query_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(message)s", DATE_FORMAT)
    )
    logger.addHandler(query_handler)
    
    return logger