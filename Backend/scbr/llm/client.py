# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import json
import hashlib
from typing import List, Optional, Dict, Any
import httpx
import numpy as np

# ---------------------------
# EmbeddingClient
# ---------------------------

class EmbeddingClient:
    """
    NVIDIA Integrate Embeddings API client（含本地退化嵌入）
    - POST {base_url}/v1/embeddings
    payload: {"model": ..., "input": [...], "input_type": "passage"|"query"}
    回傳: {"data":[{"embedding":[...]}...]}
    """
    def __init__(self, model_name: str, base_url: str, api_key: Optional[str] = None, timeout: float = 30.0):
        self.model = model_name
        self.base_url = base_url.rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.base_url = self.base_url + "/v1"
        self.api_key = api_key or os.getenv("EMBEDDING_API_KEY")
        self.timeout = timeout
        self._endpoint = f"{self.base_url}/embeddings"
        self._headers = {"Content-Type": "application/json"}
        if self.api_key:
            self._headers["Authorization"] = f"Bearer {self.api_key}"

    def _fallback_embed(self, texts: List[str], dim: int = 768) -> List[List[float]]:
        """沒有金鑰或 API 失敗時，用可重現 hash 產生固定長度向量。"""
        vecs = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            arr = np.frombuffer(h, dtype=np.uint8).astype(np.float32)
            reps = int(np.ceil(dim / arr.shape[0]))
            arr = np.tile(arr, reps)[:dim] / 255.0
            vecs.append(arr.tolist())
        return vecs

    def embed(self, texts: List[str], input_type: str = "passage") -> List[List[float]]:
        if not texts:
            return []
        if not self.api_key:
            return self._fallback_embed(texts)

        payload = {"model": self.model, "input": texts, "input_type": input_type}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(self._endpoint, headers=self._headers, json=payload)
                if r.status_code >= 400:
                    # 把伺服器回應丟進錯誤，方便排查
                    raise RuntimeError(f"Embedding API {r.status_code}: {r.text}")
                data = r.json()
                embs = [item["embedding"] for item in data.get("data", [])]
                if len(embs) != len(texts):
                    raise RuntimeError(f"Embedding count mismatch: got {len(embs)} vs {len(texts)}")
                return embs
        except Exception:
            # 任意錯誤 → 退化嵌入，確保流程不中斷
            return self._fallback_embed(texts)

# ---------------------------
# LLMClient
# ---------------------------

class LLMClient:
    """
    NVIDIA Integrate Chat Completions API client（含本地退化回覆）
    - POST {base_url}/v1/chat/completions
    payload: {"model": ..., "messages":[{"role":"system/user/assistant","content":...}], "temperature":...}
    回傳: {"choices":[{"message":{"content":"..."}}], ...}
    """
    def __init__(self, model_name: str, base_url: str, api_key: Optional[str] = None, timeout: float = 60.0):
        self.model = model_name
        self.base_url = base_url.rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.base_url = self.base_url + "/v1"
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.timeout = timeout
        self._endpoint = f"{self.base_url}/chat/completions"
        self._headers = {"Content-Type": "application/json"}
        if self.api_key:
            self._headers["Authorization"] = f"Bearer {self.api_key}"

    def _fallback_reply(self, messages: List[Dict[str, str]]) -> str:
        """沒有金鑰或 API 失敗時的簡單模板回覆（確保系統可用）。"""
        # 取最後一則 user 內容做回應
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "")
                break
        return f"（本地模擬回覆）根據當前資訊初步建議：\n- 先彙整主訴與症狀，辨證論治可考慮心脾兩虛或肝鬱化火；\n- 請補充舌脈與伴隨症狀以便進一步推斷。\n（用戶輸入摘要：{user_msg[:80]}…）"

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 512) -> str:
        """
        :param messages: [{"role":"system/user/assistant","content":"..."}...]
        :return: 模型回覆文字
        """
        if not self.api_key:
            return self._fallback_reply(messages)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(self._endpoint, headers=self._headers, json=payload)
                if r.status_code >= 400:
                    raise RuntimeError(f"LLM API {r.status_code}: {r.text}")
                data = r.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content or self._fallback_reply(messages)
        except Exception:
            return self._fallback_reply(messages)
