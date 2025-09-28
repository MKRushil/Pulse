# -*- coding: utf-8 -*-
"""
PulsePJV 脈診知識檢索器
"""

from .vector_client import VectorClient
from typing import List, Dict, Any

class PulseRetriever:
    def __init__(self, client: VectorClient):
        self.client = client

    async def search_pulse_patterns(self, query: str) -> List[Dict[str, Any]]:
        return await self.client.search("PulsePJV", query, None, limit=10)
