# -*- coding: utf-8 -*-
"""
ANC (Archive & Normalize Cases) Configuration
病例存檔與正規化配置
"""

import os
from pathlib import Path

# ============================================
# 目錄配置
# ============================================
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent

# 原始病例 JSON 存儲目錄
RAW_CASES_DIR = PROJECT_ROOT / "data" / "raw_cases"
RAW_CASES_DIR.mkdir(parents=True, exist_ok=True)

# 處理日誌目錄
PROCESS_LOGS_DIR = PROJECT_ROOT / "data" / "process_logs"
PROCESS_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# Weaviate 向量資料庫配置
# ============================================
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "key-admin")

# Case Collection 名稱
CASE_COLLECTION_NAME = "TCMCase"

# ============================================
# 向量化配置
# ============================================
# NVIDIA Embedding API
EMBEDDING_API_URL = "https://integrate.api.nvidia.com/v1"
EMBEDDING_API_KEY = os.getenv(
    "EMBEDDING_API_KEY",
    "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"
)
EMBEDDING_MODEL = "nvidia/nv-embedqa-e5-v5"
EMBEDDING_DIMENSION = 1024

# ============================================
# Jieba 中醫術語詞典配置
# ============================================
TCM_DICT_PATH = BASE_DIR / "tcm_jieba_dict.txt"

# 術語類別權重 (用於 BM25 加權)
TCM_TERM_WEIGHTS = {
    "syndrome": 3.0,      # 證型 (如: 風寒感冒、氣虛)
    "zangfu": 2.5,        # 臟腑 (如: 肝鬱、脾虛)
    "symptom": 2.0,       # 症狀 (如: 咳嗽、頭痛)
    "pulse": 2.0,         # 脈象 (如: 浮脈、弦脈)
    "tongue": 2.0,        # 舌象 (如: 舌紅、苔黃)
    "treatment": 2.0,     # 治法 (如: 疏風散寒)
}

# ============================================
# 資料處理配置
# ============================================
# 是否在儲存時自動上傳向量資料庫
AUTO_VECTORIZE = True

# 批次處理大小
BATCH_SIZE = 10

# 重試配置
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒

# ============================================
# 日誌配置
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================
# 向量化請求配置
# ============================================
EMBEDDING_REQUEST_CONFIG = {
    "input_type": "passage",  # passage 用於文檔向量化,query 用於查詢向量化
    "encoding_format": "float",  # 返回浮點數格式
    "truncate": "END"  # 超長文本截斷策略
}

# 重試配置
EMBEDDING_MAX_RETRIES = 3  # 最大重試次數
EMBEDDING_RETRY_DELAY = 2  # 初始重試延遲(秒)

# 速率限制配置
EMBEDDING_RATE_LIMIT = {
    "requests_per_minute": 30,  # 每分鐘最多請求數
    "delay_between_requests": 0.5  # 請求間延遲(秒)
}

# ============================================
# 備份目錄配置
# ============================================
BACKUP_DIR = PROJECT_ROOT / "data" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)