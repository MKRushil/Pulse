# -*- coding: utf-8 -*-
"""
S-CBR (Spiral Case-Based Reasoning) v2.1 - 28脈診中醫輔助診斷系統
重構版本 - 專注於螺旋推理、Hybrid搜索、中醫脈診知識整合

版本：v2.1.0
作者：SCBR Team
日期：2025-09-28
"""

__version__ = "2.1.0"
__author__ = "SCBR Team"
__description__ = "脈診中醫輔助診斷系統 - 螺旋推理重構版"

from .main import run_spiral_cbr, SCBREngine
from .api import router as scbr_router
from .config import SCBRConfig

__all__ = [
    "__version__", "__author__", "__description__",
    "run_spiral_cbr", "SCBREngine", "scbr_router", "SCBRConfig"
]
