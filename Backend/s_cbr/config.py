# -*- coding: utf-8 -*-
"""
S-CBR v2.1 統一配置管理
集中管理所有系統配置，包括向量數據庫、LLM、嵌入服務等
"""
from __future__ import annotations

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import re
import httpx
from asyncio import sleep

# -----------------------------
# Dataclass 區
# -----------------------------
@dataclass
class WeaviateConfig:
    url: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    api_key: Optional[str] = os.getenv("WEAVIATE_API_KEY", "key-admin")
    timeout: int = int(os.getenv("WEAVIATE_TIMEOUT", "30"))

@dataclass
class LLMConfig:
    # OpenAI-compatible 端點（NVIDIA、OpenRouter、Azure OAIF 都可）
    # 注意：請給「基底 URL」，程式會自動補上 /chat/completions
    api_url: str = os.getenv("LLM_API_URL", "https://integrate.api.nvidia.com/v1")
    api_key: str = os.getenv("LLM_API_KEY", "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")
    model: str = os.getenv("LLM_MODEL", "meta/llama-3.3-70b-instruct")
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    timeout: float = float(os.getenv("LLM_TIMEOUT", "30"))
    retry: int = int(os.getenv("LLM_RETRY", "2"))

@dataclass
class EmbeddingConfig:
    api_url: str = os.getenv("EMBEDDING_API_URL", "https://integrate.api.nvidia.com/v1")
    api_key: str = os.getenv("NVIDIA_API_KEY", "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")
    model: str = os.getenv("EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5")
    dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
    timeout: float = float(os.getenv("EMBEDDING_TIMEOUT", "30"))
    retry: int = int(os.getenv("EMBEDDING_RETRY", "2"))

@dataclass
class SearchConfig:
    hybrid_alpha: float = 0.5
    vector_limit: int = 20
    bm25_limit: int = 20
    search_fields: List[str] = field(default_factory=lambda: ["search_all", "search_all_seg"])
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
    jieba_dict_path: str = os.getenv(
        "JIEBA_DICT",
        r"C:\work\系統-中醫\Pulse-project\Backend\prompt\tcm_userdict_jieba_v2.txt",
    )
    stopwords: List[str] = field(default_factory=lambda: ["的", "了", "和", "與", "及", "呢", "啊", "嗎"])
    negation_pattern: str = r"(不|無|沒有|未見|否認)\s*([^\s，,。；;]{1,8})"
    ignore_tongue: bool = True  # 明確忽略舌診

@dataclass
class FeatureFlags:
    enable_llm: bool = True                # 打開後端 LLM 生成
    mock_when_llm_fail: bool = True        # LLM 出錯時改用模擬模板
    log_level: str = os.getenv("SCBR_LOG_LEVEL", "INFO")

# -----------------------------
# 主設定物件
# -----------------------------
class SCBRConfig:
    def __init__(self):
        self.version = "2.1.0"
        self.weaviate = WeaviateConfig()
        self.llm = LLMConfig()
        self.embedding = EmbeddingConfig()
        self.search = SearchConfig()
        self.spiral = SpiralConfig()
        self.text_processor = TextProcessorConfig()
        self.features = FeatureFlags()

        # 內部快取（避免重複建 client）
        self._llm_client = None
        self._embed_client = None

    # --------- 驗證 ----------
    def validate(self):
        # 僅在啟用 LLM 時檢查 LLM 金鑰
        if self.features.enable_llm and not self.llm.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        if not self.embedding.api_key:
            raise ValueError("NVIDIA_API_KEY 未配置")

        total = self.spiral.case_weight + self.spiral.rpcase_weight + self.spiral.pulse_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError("螺旋權重總和需為 1.0")

    # --------- Header ----------
    def _auth_header(self, key: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    # --------- LLM Client ----------
    def get_llm_client(self):
        """
        回傳一個極輕量的 OpenAI-compatible 非同步 client。
        若 features.enable_llm=False，則回傳 None 讓上層走 fallback。
        """
        if not self.features.enable_llm:
            return None
        if self._llm_client is not None:
            return self._llm_client

        # 延遲載入 httpx，避免在未用到時增加依賴
        import httpx
        from asyncio import sleep

        class _LLMClient:
            def __init__(self, cfg: "SCBRConfig"):
                self.cfg = cfg
                self._headers = cfg._auth_header(cfg.llm.api_key)
                self._url = self._build_chat_url(cfg.llm.api_url)
                self._timeout = cfg.llm.timeout
                self._retry = max(0, cfg.llm.retry)

            @staticmethod
            def _build_chat_url(api_url: str) -> str:
                """
                根據提供的 base api_url，在呼叫時才安全地補上 chat completions 路徑。
                - OpenAI 標準：.../v1/chat/completions
                - NVIDIA Integrate：.../v1/llm/chat/completions
                - 若已經是完整路徑，原樣返回。
                """
                u = (api_url or "").strip().rstrip("/")

                # 已經是完整 chat 路徑就直接用
                if u.endswith("/chat/completions") or u.endswith("/llm/chat/completions"):
                    return u

                # NVIDIA Integrate 主機名的判斷
                if "integrate.api.nvidia.com" in u:
                    # 幾種常見情況：
                    # 1) .../v1/llm  -> 補 /chat/completions
                    if re.search(r"/v1/?llm$", u) or u.endswith("/llm"):
                        return f"{u}/chat/completions"
                    # 2) .../v1 -> 補 /llm/chat/completions
                    if re.search(r"/v1$", u):
                        return f"{u}/llm/chat/completions"
                    # 3) 其他（可能只給到主機或沒有 /v1）-> 補 /v1/llm/chat/completions
                    return f"{u}/v1/llm/chat/completions"

                # 其他供應商視為 OpenAI 相容
                if re.search(r"/v1$", u):
                    return f"{u}/chat/completions"
                # 沒帶 /v1 的話自動補上
                return f"{u}/v1/chat/completions"

            async def chat(self, system_prompt: str, user_prompt: str) -> str:
                payload = {
                    "model": self.cfg.llm.model,
                    "temperature": self.cfg.llm.temperature,
                    "max_tokens": self.cfg.llm.max_tokens,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                }
                attempt = 0
                while True:
                    try:
                        async with httpx.AsyncClient(timeout=self._timeout) as client:
                            resp = await client.post(self._url, headers=self._headers, json=payload)
                        resp.raise_for_status()
                        data = resp.json()
                        # OpenAI-compatible 回應結構
                        return data["choices"][0]["message"]["content"]
                    except Exception:
                        if attempt >= self._retry:
                            raise
                        attempt += 1
                        await sleep(0.6 * attempt)

    # --------- Embedding Client ----------
    def get_embed_client(self):
        """
        簡易 OpenAI-compatible embeddings client（供 SearchEngine / SpiralEngine 呼叫）。
        """
        if self._embed_client is not None:
            return self._embed_client

        import httpx
        from asyncio import sleep

        class _EmbedClient:
            def __init__(self, cfg: "SCBRConfig"):
                self.cfg = cfg
                self._headers = cfg._auth_header(cfg.embedding.api_key)
                self._url = cfg.embedding.api_url.rstrip("/") + "/embeddings"
                self._timeout = cfg.embedding.timeout
                self._retry = max(0, cfg.embedding.retry)

            async def embed(self, texts: List[str]) -> List[List[float]]:
                payload = {"model": self.cfg.embedding.model, "input": texts}
                attempt = 0
                while True:
                    try:
                        async with httpx.AsyncClient(timeout=self._timeout) as client:
                            resp = await client.post(self._url, headers=self._headers, json=payload)
                        resp.raise_for_status()
                        data = resp.json()
                        # OpenAI-compatible
                        return [item["embedding"] for item in data["data"]]
                    except Exception:
                        if attempt >= self._retry:
                            raise
                        attempt += 1
                        await sleep(0.6 * attempt)

        self._embed_client = _EmbedClient(self)
        return self._embed_client


# 匯出全域設定
cfg = SCBRConfig()
