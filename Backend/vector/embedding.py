# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, List
import hashlib

"""
最小可執行的向量生成模組：
- generate_embedding(text, input_type): 提供本地 deterministic stub，避免外網依賴。
- generate_embedding_safe(input, input_type): 清洗空字串/空列表後再呼叫 generate_embedding。

若需接入真實嵌入服務，保留此介面不變，於 generate_embedding 內改為 HTTP 呼叫即可。
"""


def _deterministic_vector(seed: str, dim: int = 384) -> List[float]:
    """以 SHA256 衍生向量，長度 dim，範圍約 [-1, 1)。"""
    out: List[float] = []
    i = 0
    while len(out) < dim:
        h = hashlib.sha256(f"{seed}:{i}".encode("utf-8")).digest()
        for j in range(0, len(h), 4):
            chunk = h[j:j+4]
            if len(chunk) < 4:
                break
            n = int.from_bytes(chunk, byteorder="big", signed=False)
            out.append((n % 2000000) / 1000000.0 - 1.0)
            if len(out) >= dim:
                break
        i += 1
    return out


def generate_embedding(text: str, input_type: str = "passage") -> List[float]:
    """產生向量（本地 stub）。
    後續可替換為真實嵌入 API。
    """
    seed = f"{input_type}|{text}"
    return _deterministic_vector(seed, dim=384)


def generate_embedding_safe(text_or_list: Any, *, input_type: str = "passage") -> List[float]:
    """保證輸入非空：
    - 字串：strip 後若為空→改成『（無敘述）』
    - list：取第一個非空字串；若皆空→『（無敘述）』
    - 其他型別：直接『（無敘述）』
    """
    if isinstance(text_or_list, str):
        payload = text_or_list.strip() or "（無敘述）"
    elif isinstance(text_or_list, (list, tuple)):
        xs = [str(x).strip() for x in text_or_list if isinstance(x, str) and str(x).strip()]
        payload = xs[0] if xs else "（無敘述）"
    else:
        payload = "（無敘述）"
    return generate_embedding(payload, input_type=input_type)

