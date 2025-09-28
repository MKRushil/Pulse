# -*- coding: utf-8 -*-
"""
LLM 客戶端封裝
"""

import aiohttp
from ..config import SCBRConfig

class LLMClient:
    def __init__(self, config: SCBRConfig):
        self.url = config.llm.api_url
        self.key = config.llm.api_key

    async def chat(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.key}"}
        payload = {"model": "", "messages":[{"role":"user","content":prompt}]}
        async with aiohttp.ClientSession() as sess:
            resp = await sess.post(self.url, json=payload, headers=headers)
            data = await resp.json()
            return data["choices"][0]["message"]["content"]
