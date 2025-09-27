# scbr/scbr_config.py
from pydantic import BaseSettings, Field, validator
from typing import Optional

class ScbrSettings(BaseSettings):
    # === 向量庫（Chroma）===
    CHROMA_HOST: str = Field("localhost", env="CHROMA_HOST")
    CHROMA_PORT: int = Field(8000, env="CHROMA_PORT")
    CHROMA_COLLECTION_CASE: str = Field("Case", env="CHROMA_COLLECTION_CASE")
    CHROMA_COLLECTION_PULSE: str = Field("PulsePJV", env="CHROMA_COLLECTION_PULSE")
    CHROMA_COLLECTION_RPCASE: str = Field("RPCase", env="CHROMA_COLLECTION_RPCASE")

    # === LLM/Embedding（請改用環境變數，不要硬編碼金鑰）===
    LLM_BASE_URL: str = Field("https://integrate.api.nvidia.com/v1", env="LLM_BASE_URL")
    LLM_API_KEY: Optional[str] = Field("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", env="LLM_API_KEY")
    LLM_MODEL_NAME: str = Field("meta/llama-3.3-70b-instruct", env="LLM_MODEL_NAME")

    EMBEDDING_BASE_URL: str = Field("https://integrate.api.nvidia.com/v1", env="EMBEDDING_BASE_URL")
    EMBEDDING_API_KEY: Optional[str] = Field("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", env="EMBEDDING_API_KEY")
    EMBEDDING_MODEL_NAME: str = Field("nvidia/nv-embedqa-e5-v5", env="EMBEDDING_MODEL_NAME")

    # === Hybrid 權重 ===
    WEIGHT_VECTOR: float = 0.55
    WEIGHT_BM25: float = 0.45

    # === 對話回合上限 ===
    MAX_TURNS: int = 8

    class Config:
        env_file = ".env"

    @validator("WEIGHT_VECTOR", "WEIGHT_BM25")
    def _check_weights(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("weights must be in [0,1]")
        return v

settings = ScbrSettings()
