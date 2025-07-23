"""集中管理系統設定，從環境變數讀取敏感資訊"""
import os

LLM_API_URL = os.getenv("LLM_API_URL", "https://integrate.api.nvidia.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "meta/llama-3.3-70b-instruct")

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1",
)
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://integrate.api.nvidia.com/v1")

WV_HTTP_HOST = os.getenv("WV_HTTP_HOST", "localhost")
WV_HTTP_PORT = int(os.getenv("WV_HTTP_PORT", "8080"))
WV_HTTP_SECURE = os.getenv("WV_HTTP_SECURE", "false").lower() == "true"
WV_API_KEY = os.getenv("WV_API_KEY", "")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")


