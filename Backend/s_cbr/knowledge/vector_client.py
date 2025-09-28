# -*- coding: utf-8 -*-
"""
向量數據庫客戶端
"""

from typing import List, Dict, Any, Optional
import weaviate
from ..config import SCBRConfig
from ..utils.logger import get_logger

logger = get_logger("VectorClient")

class VectorClient:
    def __init__(self, config: SCBRConfig):
        self.config = config
        self._init_client()

    def _init_client(self):
        """初始化 Weaviate 客戶端"""
        try:
            weaviate_config = self.config.weaviate
            if weaviate_config.api_key:
                auth_config = weaviate.AuthApiKey(api_key=weaviate_config.api_key)
                self.client = weaviate.Client(
                    url=weaviate_config.url,
                    auth_client_secret=auth_config
                )
            else:
                self.client = weaviate.Client(url=weaviate_config.url)
            logger.info("向量客戶端初始化成功")
        except Exception as e:
            logger.error(f"向量客戶端初始化失敗: {e}")
            self.client = None

    async def search(self, class_name: str, query: str, 
                    vector: Optional[List[float]] = None, 
                    limit: int = 10) -> List[Dict[str, Any]]:
        """搜索向量"""
        if not self.client:
            return []
        
        try:
            query_builder = self.client.query.get(class_name).with_additional(["score"])
            
            if vector:
                query_builder = query_builder.with_near_vector({"vector": vector})
            else:
                query_builder = query_builder.with_bm25(query=query)
            
            result = query_builder.with_limit(limit).do()
            return result.get("data", {}).get("Get", {}).get(class_name, [])
        except Exception as e:
            logger.error(f"搜索失敗: {e}")
            return []

    async def insert(self, class_name: str, data: Dict[str, Any]):
        """插入數據"""
        if not self.client:
            return
        
        try:
            self.client.data_object.create(data, class_name)
            logger.info(f"數據插入成功: {class_name}")
        except Exception as e:
            logger.error(f"數據插入失敗: {e}")
