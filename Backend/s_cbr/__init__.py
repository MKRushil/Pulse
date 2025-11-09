# -*- coding: utf-8 -*-
"""
S-CBR (Spiral Case-Based Reasoning) 中醫輔助診斷系統
版本: 2.2.0

主要模組：
- main: 四層 SCBR 核心引擎
- api: FastAPI 路由
- dialog_manager: 對話管理
- security: 安全模組（輸入淨化、輸出驗證、速率限制）
"""

__version__ = "2.2.0"
__author__ = "S-CBR Team"
__description__ = "中醫螺旋推理輔助診斷系統"

# 導出主要介面
from .main import SCBREngine, run_spiral_cbr, get_engine

__all__ = [
    "SCBREngine",
    "run_spiral_cbr",
    "get_engine"
]
