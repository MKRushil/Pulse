"""
S-CBR 配置模組 v1.0

提供配置管理功能：
- 外部 config.py 整合
- S-CBR 專有配置
- 知識庫配置管理

版本：v1.0
"""

from .scbr_config import SCBRConfig

__all__ = ["SCBRConfig"]
__version__ = "1.0"
