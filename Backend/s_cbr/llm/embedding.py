# -*- coding: utf-8 -*-
"""
向量嵌入服務封裝（健壯版）
- 相容常見回傳格式：
  1) {"data":[{"embedding":[...]}]}            # OpenAI / NVIDIA integrate
  2) {"embedding":[...]} / {"vector":[...]}    # 自架 / 代理層
  3) {"output":{"embedding":[...]}}            # 部分 SDK
  4) {"embeddings":[...]} 或 [[...]]           # 有些庫
  5) 直接回 list[float]                        # 本地模型
- 對 HTTP 與 JSON 解析做完整錯誤處理與可診斷訊息
"""

from typing import Any, Mapping, Sequence, List
import math
import json
import aiohttp
import logging
from ..config import SCBRConfig

logger = logging.getLogger("s_cbr.embedding")

def _to_float_list(x: Sequence[Any]) -> List[float]:
    out: List[float] = []
    for v in x:
        try:
            fv = float(v)
        except Exception:
            raise ValueError(f"Embedding contains non-numeric value: {type(v).__name__}")
        if not math.isfinite(fv):
            raise ValueError("Embedding contains non-finite value (NaN/Inf)")
        out.append(fv)
    if not out:
        raise ValueError("Empty embedding vector")
    return out

def _extract_embedding(payload: Any) -> List[float] | None:
    # 5) raw list
    if isinstance(payload, (list, tuple)):
        if payload and isinstance(payload[0], (int, float)):
            return _to_float_list(payload)

    if isinstance(payload, Mapping):
        # 1) OpenAI/NVIDIA
        data = payload.get("data")
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, Mapping):
                emb = first.get("embedding")
                if isinstance(emb, (list, tuple)):
                    return _to_float_list(emb)

        # 2) {"embedding": [...]}
        emb = payload.get("embedding")
        if isinstance(emb, (list, tuple)):
            return _to_float_list(emb)

        # 2’) {"vector": [...]}
        vec = payload.get("vector")
        if isinstance(vec, (list, tuple)):
            return _to_float_list(vec)

        # 3) {"output":{"embedding":[...]}}
        out = payload.get("output")
        if isinstance(out, Mapping):
            emb2 = out.get("embedding")
            if isinstance(emb2, (list, tuple)):
                return _to_float_list(emb2)

        # 4) {"embeddings":[...]} 或 [[...]]
        embs = payload.get("embeddings")
        if isinstance(embs, (list, tuple)) and embs:
            if isinstance(embs[0], (int, float)):
                return _to_float_list(embs)
            if isinstance(embs[0], (list, tuple)):
                return _to_float_list(embs[0])

    return None

class EmbedClient:
    def __init__(self, config: SCBRConfig):
        self.url = (config.embedding.api_url or "").rstrip("/")
        self.key = config.embedding.api_key
        self.model = config.embedding.model

    async def embed(self, text: str) -> list[float]:
        """
        呼叫 {api_url}/embeddings，body: {"model": "...", "input": [text]}
        - 成功時回傳 list[float]
        - 失敗時丟出帶型別與 keys 的 ValueError（避免 KeyError: 'data'）
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("embed(text) 參數必須是非空字串")

        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"

        payload = {
            "model": self.model,
            "input": [text],
            "input_type": "query"   # ★ 新增：查詢階段用 query
        }

        url = f"{self.url}/embeddings" if self.url else "/embeddings"
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.post(url, json=payload, headers=headers) as resp:
                raw_text = await resp.text()
                if resp.status < 200 or resp.status >= 300:
                    # 儘量解析 JSON 錯誤，否則直接附原文
                    try:
                        err_obj = json.loads(raw_text)
                    except Exception:
                        err_obj = {"raw": raw_text}
                    raise ValueError(
                        f"Embedding HTTP {resp.status} at {url}; error={err_obj}"
                    )
                try:
                    data = json.loads(raw_text)
                except Exception as je:
                    raise ValueError(f"Embedding response is not valid JSON: {je}; raw={raw_text[:200]}")

        # 診斷列印（可視需要降級到 debug）
        try:
            keys = list(data.keys()) if isinstance(data, Mapping) else None
            logger.debug(f"[embed] url={url} payload_keys={keys}")
        except Exception:
            pass

        vec = _extract_embedding(data)
        if vec is None:
            tname = type(data).__name__
            keys = list(data.keys()) if isinstance(data, Mapping) else None
            raise ValueError(f"Unexpected embedding payload shape (type={tname}, keys={keys})")

        return vec


