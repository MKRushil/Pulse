# -*- coding: utf-8 -*-
"""
S-CBR v2.2 統一配置管理 - 精簡版（移除 TCM 配置依賴）
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# ==================== 數據庫配置 ====================

@dataclass
class WeaviateConfig:
    """
    向量數據庫配置
    
    用於連接 Weaviate 向量資料庫，儲存和檢索案例
    """
    url: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    api_key: str = os.getenv("WEAVIATE_API_KEY", "key-admin")
    timeout: int = int(os.getenv("WEAVIATE_TIMEOUT", "30"))


# ==================== LLM 配置 ====================

@dataclass
class LLMConfig:
    """
    LLM 配置
    
    用於設置 LLM API 的連接參數和生成參數
    """
    api_url: str = os.getenv("LLM_API_URL", "https://integrate.api.nvidia.com/v1")
    api_key: str = os.getenv("LLM_API_KEY", "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")
    model: str = os.getenv("LLM_MODEL", "meta/llama-3.3-70b-instruct")
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    timeout: float = float(os.getenv("LLM_TIMEOUT", "30"))
    retry: int = int(os.getenv("LLM_RETRY", "2"))


@dataclass
class EmbeddingConfig:
    """
    嵌入模型配置
    
    用於生成文本向量，支援語義檢索
    """
    api_url: str = os.getenv("EMBEDDING_API_URL", "https://integrate.api.nvidia.com/v1")
    api_key: str = os.getenv("NVIDIA_API_KEY", "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")
    model: str = os.getenv("EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5")
    dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
    timeout: float = float(os.getenv("EMBEDDING_TIMEOUT", "30"))
    retry: int = int(os.getenv("EMBEDDING_RETRY", "2"))


# ==================== 搜索配置 ====================

@dataclass
class SearchConfig:
    """
    搜索引擎配置
    
    用於設置混合檢索的參數和欄位權重
    """
    hybrid_alpha: float = 0.55  # 混合檢索中語義檢索的權重（55% 向量 + 45% BM25）
    top_k: int = 3  # 返回的最相似案例數量（L2需要Top 3）
    
    # BM25 搜索欄位
    search_fields: List[str] = field(default_factory=lambda: [
        "full_text"  # 主要使用 full_text 欄位進行檢索
    ])
    
    # 欄位權重配置（用於 BM25 檢索）
    field_weights: Dict[str, float] = field(default_factory=lambda: {
        "syndrome_terms": 3.0,      # 證型詞彙權重最高
        "zangfu_terms": 2.5,        # 臟腑詞彙
        "symptom_terms": 2.0,       # 症狀詞彙
        "pulse_terms": 2.0,         # 脈象詞彙
        "treatment_terms": 2.0,     # 治療詞彙
        "chief_complaint": 1.5,     # 主訴
        "diagnosis": 1.5            # 診斷
    })


# ==================== Agentic NLU 配置 ====================

@dataclass
class AgenticNLUConfig:
    """
    Agentic NLU 配置
    
    用於控制 Agentic NLU 的自主決策行為
    """
    # 功能開關
    enabled: bool = True  # 啟用 Agentic NLU（False 則使用傳統 L1）
    
    # Alpha 值範圍
    alpha_min: float = 0.2  # 最小 alpha（BM25 為主）
    alpha_max: float = 0.8  # 最大 alpha（向量為主）
    alpha_default: float = 0.5  # 預設 alpha（均衡）
    
    # 置信度門檻
    confidence_high: float = 0.75  # 高置信度門檻
    confidence_mid: float = 0.55   # 中置信度門檻
    confidence_low: float = 0.35   # 低置信度門檻
    
    # 檢索品質控制
    fallback_enabled: bool = True  # 啟用自動 fallback
    fallback_threshold: float = 0.65  # 品質門檻
    max_fallback_attempts: int = 3  # 最大 fallback 嘗試次數
    
    # LLM 參數（Agentic 模式專用）
    llm_temperature: float = 0.2  # Agentic 決策的溫度
    llm_timeout: float = 30.0  # 超時時間



# ==================== 螺旋推理配置 ====================

@dataclass
class SpiralConfig:
    """
    螺旋推理配置
    
    控制螺旋推理的輪次和收斂條件
    """
    max_rounds: int = 7             # 最大推理輪次
    min_rounds: int = 2              # 最小推理輪次
    convergence_threshold: float = 0.85  # 收斂閾值
    min_confidence: float = 0.7      # 最小信心度
    
    # 權重配置（不同來源案例的權重）
    case_weight: float = 0.5         # TCMCase 案例權重
    rpcase_weight: float = 0.3       # RPCase 回饋案例權重
    pulse_weight: float = 0.2        # 脈診資訊權重


@dataclass
class ConvergenceConfig:
    """
    收斂控制配置
    
    用於判斷診斷是否已經收斂（達到穩定狀態）
    """
    # 收斂指標權重
    case_stability_weight: float = 0.3      # 案例穩定性權重
    score_improvement_weight: float = 0.2   # 分數改善權重
    semantic_consistency_weight: float = 0.3  # 語義一致性權重
    evidence_coverage_weight: float = 0.2   # 證據覆蓋度權重
    
    # 停止條件
    convergence_threshold: float = 0.85  # 收斂閾值（0-1）
    min_rounds: int = 2                  # 最小輪次
    max_rounds: int = 7                 # 最大輪次


# ==================== 安全配置 ====================

@dataclass
class SecurityConfig:
    """
    安全配置
    
    用於速率限制、輸入淨化、輸出驗證等安全功能
    """
    # 速率限制
    enable_rate_limiting: bool = True           # 啟用速率限制
    requests_per_ip_per_minute: int = 10        # 每個 IP 每分鐘最多請求數
    requests_per_session_per_hour: int = 50     # 每個會話每小時最多請求數
    max_concurrent_sessions: int = 100          # 最大併發會話數
    
    # 輸入安全
    enable_input_sanitization: bool = True      # 啟用輸入淨化
    enable_pii_masking: bool = True             # 啟用個人資訊脫敏
    max_input_length: int = 1000                # 最大輸入長度（字符）
    
    # 輸出安全
    enable_output_validation: bool = True       # 啟用輸出驗證
    enable_disclaimer: bool = True              # 啟用免責聲明
    
    # LLM 安全
    enable_prompt_injection_detection: bool = True     # 啟用提示詞注入檢測
    enable_sensitive_info_filtering: bool = True       # 啟用敏感資訊過濾


# ==================== 功能開關 ====================

@dataclass
class FeatureFlags:
    """
    功能開關
    
    用於控制系統各項功能的啟用/停用
    """
    enable_llm: bool = True                     # 啟用 LLM 功能
    enable_convergence: bool = True             # 啟用收斂判斷
    enable_dialog_accumulation: bool = True     # 啟用對話累積
    enable_syndrome_analysis: bool = True       # 啟用證型分析
    enable_quality_control: bool = True         # 啟用品質控制
    enable_security_checks: bool = True         # 啟用安全檢查
    mock_when_llm_fail: bool = True             # LLM 失敗時使用模擬響應
    log_level: str = os.getenv("SCBR_LOG_LEVEL", "INFO")  # 日誌級別


# ==================== 工具庫配置 ====================

@dataclass
class ToolCallConfig:
    """外部工具調用配置"""
    enable_tool_calls: bool = True      # 工具調用總開關
    enable_tool_a: bool = True          # ICD-11 開關
    enable_tool_b: bool = True          # A+百科 開關
    enable_tool_c: bool = True          # ETCM 開關
    
    # 觸發條件
    knowledge_gap_threshold: float = 0.6      # 知識缺口門檻
    validation_confidence_threshold: float = 0.7  # 校驗置信度門檻
    
    # 效能控制
    max_tool_calls_per_diagnosis: int = 3     # 單次最大調用數
    tool_timeout: float = 15.0                # 超時時間（秒）



# ==================== 主配置類 ====================

class SCBRConfig:
    """
    S-CBR 主配置類
    
    整合所有子配置模組，提供統一的配置接口
    """
    
    def __init__(self):
        """
        初始化配置
        
        載入所有子配置並進行驗證
        """
        self.version = "2.3.0"  # 系統版本號
        
        # 基礎配置
        self.weaviate = WeaviateConfig()
        self.llm = LLMConfig()
        self.embedding = EmbeddingConfig()
        
        # 功能配置
        self.search = SearchConfig()
        self.agentic_nlu = AgenticNLUConfig()  # Agentic NLU 配置
        self.spiral = SpiralConfig()
        self.convergence = ConvergenceConfig()

        # 添加工具調用配置
        tool_call: ToolCallConfig = field(default_factory=ToolCallConfig)
        
        # 安全配置
        self.security = SecurityConfig()
        
        # 功能開關
        self.features = FeatureFlags()
        
        # 驗證配置
        self.validate()


    
    def validate(self):
        """
        驗證配置有效性
        
        確保所有配置參數都在合理範圍內
        
        Raises:
            ValueError: 配置無效時拋出
        """
        # 驗證 LLM 配置
        if self.features.enable_llm and not self.llm.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        # 驗證嵌入配置
        if not self.embedding.api_key:
            raise ValueError("EMBEDDING_API_KEY 未配置")
        
        # 驗證螺旋權重總和
        total_spiral_weight = (
            self.spiral.case_weight + 
            self.spiral.rpcase_weight + 
            self.spiral.pulse_weight
        )
        if abs(total_spiral_weight - 1.0) > 0.01:
            raise ValueError(f"螺旋權重總和需為1.0，當前為{total_spiral_weight}")
        
        # 驗證收斂權重總和
        total_conv_weight = (
            self.convergence.case_stability_weight +
            self.convergence.score_improvement_weight +
            self.convergence.semantic_consistency_weight +
            self.convergence.evidence_coverage_weight
        )
        if abs(total_conv_weight - 1.0) > 0.01:
            raise ValueError(f"收斂權重總和需為1.0，當前為{total_conv_weight}")
        
        # 驗證安全配置
        if self.security.requests_per_ip_per_minute <= 0:
            raise ValueError("requests_per_ip_per_minute 必須 > 0")
        
        if self.security.max_input_length <= 0:
            raise ValueError("max_input_length 必須 > 0")
        
        # 驗證 Agentic NLU 配置
        if self.agentic_nlu.enabled:
            if not (0.0 <= self.agentic_nlu.alpha_min <= 1.0):
                raise ValueError("alpha_min 必須在 0.0-1.0 範圍內")
            if not (0.0 <= self.agentic_nlu.alpha_max <= 1.0):
                raise ValueError("alpha_max 必須在 0.0-1.0 範圍內")
            if self.agentic_nlu.alpha_min >= self.agentic_nlu.alpha_max:
                raise ValueError("alpha_min 必須小於 alpha_max")
            if not (0.0 <= self.agentic_nlu.confidence_high <= 1.0):
                raise ValueError("confidence_high 必須在 0.0-1.0 範圍內")
            if not (0.0 <= self.agentic_nlu.fallback_threshold <= 1.0):
                raise ValueError("fallback_threshold 必須在 0.0-1.0 範圍內")
            
    
    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        用於序列化配置或日誌記錄
        
        Returns:
            配置字典
        """
        return {
            "version": self.version,
            "weaviate": self.weaviate.__dict__,
            "llm": self.llm.__dict__,
            "embedding": self.embedding.__dict__,
            "search": self.search.__dict__,
            "agentic_nlu": self.agentic_nlu.__dict__,
            "spiral": self.spiral.__dict__,
            "convergence": self.convergence.__dict__,
            "security": self.security.__dict__,
            "features": self.features.__dict__
        }


# ==================== 全域配置實例 ====================

cfg = SCBRConfig()


# ==================== 配置工具函數 ====================

def get_config() -> SCBRConfig:
    """
    獲取全域配置實例
    
    Returns:
        SCBRConfig: 配置實例
    """
    return cfg


def reload_config():
    """
    重新載入配置
    
    用於動態更新配置（例如配置文件修改後）
    """
    global cfg
    cfg = SCBRConfig()
    return cfg


# ==================== 配置測試 ====================

if __name__ == "__main__":
    # 測試配置
    import json
    
    print("=" * 60)
    print("S-CBR 配置測試")
    print("=" * 60)
    
    config = get_config()
    
    print(f"\n版本: {config.version}")
    print(f"\n安全功能啟用:")
    print(f"  - 速率限制: {config.security.enable_rate_limiting}")
    print(f"  - 輸入淨化: {config.security.enable_input_sanitization}")
    print(f"  - 輸出驗證: {config.security.enable_output_validation}")
    print(f"  - PII 脫敏: {config.security.enable_pii_masking}")
    
    print(f"\n功能開關:")
    print(f"  - LLM: {config.features.enable_llm}")
    print(f"  - 品質控制: {config.features.enable_quality_control}")
    print(f"  - 安全檢查: {config.features.enable_security_checks}")
    
    print(f"\n螺旋推理配置:")
    print(f"  - 最大輪次: {config.spiral.max_rounds}")
    print(f"  - 收斂閾值: {config.spiral.convergence_threshold}")
    
    print(f"\n配置驗證: ✅ 通過")
    
    # 輸出為 JSON（部分）
    print(f"\n配置摘要（JSON）:")
    config_dict = config.to_dict()
    print(json.dumps({
        "version": config_dict["version"],
        "security": config_dict["security"],
        "features": config_dict["features"]
    }, indent=2, ensure_ascii=False))