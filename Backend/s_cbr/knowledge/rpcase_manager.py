# -*- coding: utf-8 -*-
"""
RPCase 回饋案例管理
"""

from typing import Dict, Any
import uuid
from .vector_client import VectorClient

class RPCaseManager:
    def __init__(self, client: VectorClient):
        self.client = client

    async def search_feedback_cases(self, query: str, vector=None, limit=5):
        return await self.client.search("RPCase", query, vector, limit)

    async def save_case(self, data: Dict[str, Any]):
        data["rpcase_id"] = f"RPC_{uuid.uuid4().hex[:8]}"
        await self.client.insert("RPCase", data)
