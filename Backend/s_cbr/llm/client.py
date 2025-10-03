# -*- coding: utf-8 -*-
"""
統一的 LLM 客戶端
"""

import aiohttp
import json
from typing import List, Dict, Optional
from ..config import SCBRConfig
from ..utils.logger import get_logger

logger = get_logger("LLMClient")

class LLMClient:
    """統一的 LLM 客戶端"""
    
    def __init__(self, config: SCBRConfig):
        self.config = config
        self.url = self._build_url(config.llm.api_url)
        self.headers = {
            "Authorization": f"Bearer {config.llm.api_key}",
            "Content-Type": "application/json"
        }
        self.model = config.llm.model
        self.max_tokens = config.llm.max_tokens
        self.timeout = config.llm.timeout
        
    def _build_url(self, base_url: str) -> str:
        """構建完整 URL"""
        base = base_url.rstrip("/")
        
        if base.endswith("/chat/completions"):
            return base
        
        if "nvidia" in base:
            if "/v1" in base:
                return f"{base}/chat/completions"
            return f"{base}/v1/chat/completions"
        
        return f"{base}/chat/completions"
    
    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None
    ) -> str:
        """執行聊天完成"""
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": temperature or self.config.llm.temperature
        }
        
        logger.debug(f"發送 LLM 請求: model={self.model}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"LLM API 錯誤 {response.status}: {error_text}")
                        # Return fallback instead of raising
                        return self._get_fallback_response()
                    
                    data = await response.json()
                    
                    if "choices" in data and data["choices"]:
                        content = data["choices"][0]["message"]["content"]
                        logger.debug(f"LLM 響應成功")
                        return content
                    else:
                        logger.error(f"LLM 響應格式錯誤")
                        return self._get_fallback_response()
                    
        except Exception as e:
            logger.error(f"LLM 處理錯誤: {e}")
            return self._get_fallback_response()
    
    def _get_fallback_response(self) -> str:
        """獲取備用響應"""
        return "診斷結果：證型待定。\n建議：調整作息，保持情緒穩定，清淡飲食。"