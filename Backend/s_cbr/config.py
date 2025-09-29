# -*- coding: utf-8 -*-
"""
S-CBR v2.1 統一配置管理
集中管理所有系統配置，包括向量數據庫、LLM、嵌入服務等
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class WeaviateConfig:
    url: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    api_key: Optional[str] = os.getenv("WEAVIATE_API_KEY", "key-admin")
    timeout: int = int(os.getenv("WEAVIATE_TIMEOUT", "30"))

@dataclass
class LLMConfig:
    api_url: str = os.getenv("LLM_API_URL", "https://integrate.api.nvidia.com/v1")
    api_key: str = os.getenv("LLM_API_KEY", "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")
    model: str = os.getenv("LLM_MODEL", "meta/llama-3.3-70b-instruct")
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

@dataclass
class EmbeddingConfig:
    api_url: str = os.getenv("EMBEDDING_API_URL", "https://integrate.api.nvidia.com/v1")
    api_key: str = os.getenv("NVIDIA_API_KEY", "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")
    model: str = os.getenv("EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5")
    dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

@dataclass
class SearchConfig:
    hybrid_alpha: float = 0.5
    vector_limit: int = 20
    bm25_limit: int = 20
    search_fields: list = field(default_factory=lambda: ["search_all", "search_all_seg"])
    retry_enabled: bool = True
    retry_max_attempts: int = 3

@dataclass
class SpiralConfig:
    max_rounds: int = 5
    max_cases_per_session: int = 10
    case_weight: float = 0.6
    rpcase_weight: float = 0.3
    pulse_weight: float = 0.1
    convergence_threshold: float = 0.8
    min_confidence: float = 0.7

@dataclass
class TextProcessorConfig:
    jieba_dict_path: str = os.getenv("JIEBA_DICT", r"C:\work\系統-中醫\Pulse-project\Backend\prompt\tcm_userdict_jieba_v2.txt")
    stopwords: list = field(default_factory=lambda: ["的","了","和","與","及","呢","啊","嗎"])
    negation_pattern: str = r"(不|無|沒有|未見|否認)\s*([^\s，,。；;]{1,8})"

class SCBRConfig:
    def __init__(self):
        self.version = "2.1.0"
        self.weaviate = WeaviateConfig()
        self.llm = LLMConfig()
        self.embedding = EmbeddingConfig()
        self.search = SearchConfig()
        self.spiral = SpiralConfig()
        self.text_processor = TextProcessorConfig()
    def validate(self):
        if not self.llm.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        if not self.embedding.api_key:
            raise ValueError("NVIDIA_API_KEY 未配置")
        total = self.spiral.case_weight + self.spiral.rpcase_weight + self.spiral.pulse_weight
        if abs(total-1.0)>0.01:
            raise ValueError("螺旋權重總和需為 1.0")
        
cfg = SCBRConfig()

