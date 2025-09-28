# -*- coding: utf-8 -*-
"""
Case 案例檢索器
"""

from .vector_client import VectorClient
from typing import List, Dict, Any
from ..utils.logger import get_logger

logger = get_logger("CaseRetriever")

class CaseRetriever:
    def __init__(self, config):
        self.client = VectorClient(config)

    async def hybrid_search(self, query: str, vector: List[float] = None, limit: int = 20) -> List[Dict[str, Any]]:
        return await self.client.search("Case", query, vector, limit)
