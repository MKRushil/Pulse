# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, List
import hashlib
import logging
import os

logger = logging.getLogger(__name__)

# 🔧 從 config.py 讀取配置
try:
    import sys
    import os as os_module
    
    # 添加 Backend 路徑
    backend_path = os_module.path.join(os_module.path.dirname(__file__), '..')
    if backend_path not in sys.path:
        sys.path.append(backend_path)
    
    from config import NVIDIA_API_KEY, EMBEDDING_NV_MODEL_NAME
    logger.info(f"✅ 從 config.py 載入 NVIDIA API Key: {'有' if NVIDIA_API_KEY else '無'}")
except ImportError as e:
    logger.warning(f"無法從 config.py 載入配置: {e}")
    # 降級到環境變數
    NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
    EMBEDDING_NV_MODEL_NAME = "nvidia/nv-embedqa-e5-v5"

NVIDIA_API_BASE = "https://integrate.api.nvidia.com/v1"

def _deterministic_vector(seed: str, dim: int = 384) -> List[float]:
    """備用的確定性向量生成（向後相容）"""
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

def _call_nvidia_embedding_sync(text: str, input_type: str = "passage") -> List[float]:
    """同步調用 NVIDIA Embedding API"""
    import requests
    
    try:
        payload = {
            "input": [text],
            "model": EMBEDDING_NV_MODEL_NAME,
            "input_type": input_type,
            "encoding_format": "float"
        }
        
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        logger.debug(f"調用 NVIDIA API: {NVIDIA_API_BASE}/embeddings")
        logger.debug(f"模型: {EMBEDDING_NV_MODEL_NAME}, 文本長度: {len(text)}")
        
        response = requests.post(
            f"{NVIDIA_API_BASE}/embeddings",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            vector = result["data"][0]["embedding"]
            logger.info(f"✅ NVIDIA Embedding 成功生成 {len(vector)} 維向量")
            return vector
        else:
            logger.error(f"❌ NVIDIA Embedding API 錯誤: {response.status_code}")
            logger.error(f"錯誤詳情: {response.text}")
            raise Exception(f"NVIDIA API 錯誤: {response.status_code}")
            
    except Exception as e:
        logger.error(f"NVIDIA Embedding 調用失敗: {e}")
        raise

def generate_embedding(text: str, input_type: str = "passage") -> List[float]:
    """
    生成向量 - 新版 (支持 NVIDIA API)
    
    Args:
        text: 輸入文本
        input_type: "passage" (存儲用) 或 "query" (檢索用)
    
    Returns:
        List[float]: 向量表示
    """
    if not text or not text.strip():
        text = "（無敘述）"
    
    # 🔧 檢查是否有 NVIDIA API Key
    if NVIDIA_API_KEY and len(NVIDIA_API_KEY) > 10:
        try:
            logger.debug(f"嘗試使用 NVIDIA API 生成向量: {text[:50]}...")
            return _call_nvidia_embedding_sync(text, input_type)
        except Exception as e:
            logger.warning(f"NVIDIA API 失敗，降級到本地向量: {e}")
    else:
        logger.debug(f"NVIDIA_API_KEY 無效 (長度: {len(NVIDIA_API_KEY or '')}), 使用本地向量")
    
    # 🔧 降級到確定性向量 (向後相容)
    seed = f"{input_type}|{text}"
    logger.debug(f"使用確定性向量: {seed[:50]}...")
    return _deterministic_vector(seed, dim=384)

def generate_embedding_safe(text_or_list: Any, *, input_type: str = "passage") -> List[float]:
    """保證輸入非空的安全版本"""
    if isinstance(text_or_list, str):
        payload = text_or_list.strip() or "（無敘述）"
    elif isinstance(text_or_list, (list, tuple)):
        xs = [str(x).strip() for x in text_or_list if isinstance(x, str) and str(x).strip()]
        payload = xs[0] if xs else "（無敘述）"
    else:
        payload = "（無敘述）"
    return generate_embedding(payload, input_type=input_type)
