# Backend/scbr/scbr_config.py  (Pydantic v2 版)

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class ScbrSettings(BaseSettings):
    # === Chroma（IN-PROCESS 模式）===
    CHROMA_MODE: str = Field(default="inprocess")  # 固定走 inprocess
    CHROMA_PERSIST_DIR: str = Field(default="./.chroma")
    CHROMA_COLLECTION_CASE: str = Field(default="Case")
    CHROMA_COLLECTION_PULSE: str = Field(default="PulsePJV")
    CHROMA_COLLECTION_RPCASE: str = Field(default="RPCase")

    # === LLM / Embedding ===
    LLM_BASE_URL: str = Field(default="https://integrate.api.nvidia.com/v1")
    LLM_API_KEY: Optional[str] = Field(default=None)
    LLM_MODEL_NAME: str = Field(default="meta/llama-3.3-70b-instruct")

    EMBEDDING_BASE_URL: str = Field(default="https://integrate.api.nvidia.com/v1")
    EMBEDDING_API_KEY: Optional[str] = Field(default=None)
    EMBEDDING_MODEL_NAME: str = Field(default="nvidia/nv-embedqa-e5-v5")

    # === Hybrid 權重 ===
    WEIGHT_VECTOR: float = Field(default=0.55)
    WEIGHT_BM25: float = Field(default=0.45)

    # === 對話回合上限 ===
    MAX_TURNS: int = Field(default=8)

    # Pydantic v2 的設定方式（取代 v1 的 Config/validator）
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # 忽略未知 env
    )

    @field_validator("WEIGHT_VECTOR", "WEIGHT_BM25")
    @classmethod
    def _check_weights(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("weights must be in [0,1]")
        return v

settings = ScbrSettings()
