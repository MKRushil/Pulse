# -*- coding: utf-8 -*-
"""
S-CBR v2.1 統一配置管理
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path  # ← 新增這行

# ==================== 新增: 載入 TCM 詞典路徑 ====================
try:
    from anc.config import TCM_DICT_PATH
    DEFAULT_JIEBA_DICT = str(TCM_DICT_PATH)
except ImportError:
    DEFAULT_JIEBA_DICT = ""

# ✅ 載入 TCM 配置
try:
    from .knowledge.tcm_config import get_tcm_config
    _tcm_cfg = get_tcm_config()
except Exception as e:
    import logging
    logging.warning(f"⚠️  TCM 配置載入失敗: {e}，使用預設配置")
    _tcm_cfg = None
# ==================== 結束 ====================

@dataclass
class WeaviateConfig:
    """向量數據庫配置"""
    url: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    api_key: str = os.getenv("WEAVIATE_API_KEY", "key-admin")
    timeout: int = int(os.getenv("WEAVIATE_TIMEOUT", "30"))

@dataclass
class LLMConfig:
    """LLM配置"""
    api_url: str = os.getenv("LLM_API_URL", "https://integrate.api.nvidia.com/v1")
    api_key: str = os.getenv("LLM_API_KEY", "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")
    model: str = os.getenv("LLM_MODEL", "meta/llama-3.3-70b-instruct")
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    timeout: float = float(os.getenv("LLM_TIMEOUT", "30"))
    retry: int = int(os.getenv("LLM_RETRY", "2"))

@dataclass
class EmbeddingConfig:
    """嵌入模型配置"""
    api_url: str = os.getenv("EMBEDDING_API_URL", "https://integrate.api.nvidia.com/v1")
    api_key: str = os.getenv("NVIDIA_API_KEY", "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")
    model: str = os.getenv("EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5")
    dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
    timeout: float = float(os.getenv("EMBEDDING_TIMEOUT", "30"))
    retry: int = int(os.getenv("EMBEDDING_RETRY", "2"))

@dataclass
class SearchConfig:
    hybrid_alpha: float = 0.5  # 從 0.7 改為 0.5
    top_k: int = 10
    
    # 新增：BM25 搜索欄位
    search_fields: List[str] = field(default_factory=lambda: [
        "jieba_tokens",
        "syndrome_terms",
        "symptom_terms"
    ])
    
    # 新增：欄位權重配置（供未來使用）
    field_weights: Dict[str, float] = field(default_factory=lambda: {
        "syndrome_terms": 3.0,
        "zangfu_terms": 2.5,
        "symptom_terms": 2.0,
        "pulse_terms": 2.0,
        "treatment_terms": 2.0,
        "chief_complaint": 1.5,
        "diagnosis": 1.5
    })

@dataclass
class SpiralConfig:
    """螺旋推理配置"""
    max_rounds: int = 10
    min_rounds: int = 2
    convergence_threshold: float = 0.85
    min_confidence: float = 0.7
    
    # 權重配置
    case_weight: float = 0.5
    rpcase_weight: float = 0.3
    pulse_weight: float = 0.2

@dataclass
class ConvergenceConfig:
    """收斂控制配置"""
    case_stability_weight: float = 0.3
    score_improvement_weight: float = 0.2
    semantic_consistency_weight: float = 0.3
    evidence_coverage_weight: float = 0.2
    
    # 停止條件
    convergence_threshold: float = 0.85
    min_rounds: int = 2
    max_rounds: int = 10

@dataclass
class TextProcessorConfig:
    """文本處理配置 - 整合外部 TCM 配置"""
    jieba_dict_path: str = field(
        default_factory=lambda: os.getenv("JIEBA_DICT", DEFAULT_JIEBA_DICT)
    )
    
    # ✅ 從 TCM 配置載入
    stopwords: List[str] = field(
        default_factory=lambda: list(_tcm_cfg.get_stopwords()) if _tcm_cfg else [
            "的", "了", "和", "與", "及", "呢", "啊", "嗎"
        ]
    )
    
    tcm_keywords: List[str] = field(
        default_factory=lambda: list(_tcm_cfg.get_tcm_keywords()) if _tcm_cfg else [
            "失眠", "多夢", "心悸", "口乾", "疲倦", "頭暈",
            "腰痠", "耳鳴", "潮熱", "盜汗", "便秘", "腹脹"
        ]
    )
    
    # ✅ 新增：證型、臟腑、症狀分類關鍵詞
    syndrome_keywords: Dict[str, List[str]] = field(
        default_factory=lambda: _tcm_cfg.get_syndrome_keywords() if _tcm_cfg else {}
    )
    
    zangfu_keywords: Dict[str, List[str]] = field(
        default_factory=lambda: _tcm_cfg.get_zangfu_keywords() if _tcm_cfg else {}
    )
    
    symptom_categories: Dict[str, List[str]] = field(
        default_factory=lambda: _tcm_cfg.get_symptom_categories() if _tcm_cfg else {}
    )
    
    negation_pattern: str = r"(無|沒有|不|未)([^。，；]{1,4})"
    ignore_tongue: bool = True

@dataclass
class FeatureFlags:
    """功能開關"""
    enable_llm: bool = True
    enable_convergence: bool = True
    enable_dialog_accumulation: bool = True
    enable_syndrome_analysis: bool = True    # 🆕
    mock_when_llm_fail: bool = True
    log_level: str = os.getenv("SCBR_LOG_LEVEL", "INFO")

class SCBRConfig:
    """主配置類"""
    
    def __init__(self):
        self.version = "2.1.0"
        self.weaviate = WeaviateConfig()
        self.llm = LLMConfig()
        self.embedding = EmbeddingConfig()
        self.search = SearchConfig()
        self.spiral = SpiralConfig()
        self.convergence = ConvergenceConfig()
        self.text_processor = TextProcessorConfig()
        self.features = FeatureFlags()
        
        self.validate()
        

    def validate(self):
        """驗證配置"""
        if self.features.enable_llm and not self.llm.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        if not self.embedding.api_key:
            raise ValueError("EMBEDDING_API_KEY 未配置")
        
        # 驗證權重總和
        total_weight = (
            self.spiral.case_weight + 
            self.spiral.rpcase_weight + 
            self.spiral.pulse_weight
        )
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"螺旋權重總和需為1.0，當前為{total_weight}")
        
        # 驗證收斂權重
        conv_weight = (
            self.convergence.case_stability_weight +
            self.convergence.score_improvement_weight +
            self.convergence.semantic_consistency_weight +
            self.convergence.evidence_coverage_weight
        )
        if abs(conv_weight - 1.0) > 0.01:
            raise ValueError(f"收斂權重總和需為1.0，當前為{conv_weight}")

# 全域配置實例
cfg = SCBRConfig()