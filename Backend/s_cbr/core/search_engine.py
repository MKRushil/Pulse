# -*- coding: utf-8 -*-
"""
統一搜索引擎 v2.1
整合 BM25 關鍵字搜索和向量語義搜索
"""

import asyncio
from typing import Dict, Any, List, Optional
import weaviate
from ..config import SCBRConfig
from ..utils.logger import get_logger
from ..utils.text_processor import TextProcessor

logger = get_logger("SearchEngine")

# 轉 float（容錯：字串、None、空白）
def _to_float(v, default: float = 0.0) -> float:
    try:
        if v is None:
            return float(default)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            return float(v.strip())
    except Exception:
        pass
    return float(default)

# 放在檔案頂部 _to_float 之後，加一個小工具算 L2 範數（避免印整條向量）
def _l2_norm(vec) -> float:
    try:
        s = 0.0
        for v in (vec or []):
            fv = float(v)
            s += fv * fv
        return s ** 0.5
    except Exception:
        return 0.0


async def hybrid_search(
    self,
    class_name: str,
    query_text: str,
    query_vector: Optional[List[float]] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    if not self.weaviate_client:
        return []
    try:
        processed_text = self.text_processor.segment_text(query_text) if query_text else ""

        # 多帶幾個 _additional，方便觀察
        query_builder = (
            self.weaviate_client
            .query
            .get(class_name)
            .with_additional(["id", "score", "distance"])
        )

        qlen = len(query_vector) if isinstance(query_vector, list) else 0
        alpha = self.config.search.hybrid_alpha

        if qlen > 0 and _to_float(alpha, 0.0) > 0.0:
            # ★ 明確記錄：真的走混合（含向量），印維度與範數
            logger.info(f"🔎 {class_name} HYBRID α={alpha}, qdim={qlen}, ‖v‖₂={_l2_norm(query_vector):.4f}")
            query_builder = query_builder.with_hybrid(
                query=processed_text,
                vector=query_vector,
                alpha=alpha,
                properties=self.config.search.search_fields
            )
        else:
            # ★ 若向量為空或 alpha=0，走 BM25-only
            logger.info(f"🔎 {class_name} BM25-only α={alpha}, qdim={qlen}")
            query_builder = query_builder.with_hybrid(
                query=processed_text,
                alpha=0.0,
                properties=self.config.search.search_fields
            )

        result = query_builder.with_limit(limit).do()

        if isinstance(result, dict) and "errors" in result:
            logger.error(f"GraphQL 錯誤: {result['errors']}")
            return []

        # ★ 兼容 {"data":{"Get":...}} 或 {"Get":...}
        get_section = {}
        if isinstance(result, dict):
            get_section = result.get("data", {}).get("Get") or result.get("Get") or {}
        results = get_section.get(class_name) or []
        if not isinstance(results, list):
            results = []

        # ★ 統一轉成 _confidence（用你既有的 _calculate_confidence）
        ranked: List[Dict[str, Any]] = []
        for item in results:
            addi = item.get("_additional") or {}
            score = _to_float(addi.get("score"), 0.0)
            distance = _to_float(addi.get("distance"), float("inf"))
            item["_confidence"] = self._calculate_confidence(score, distance)
            ranked.append(item)

        logger.info(f"📊 {class_name} 搜索: {len(ranked)} 個結果")
        return ranked

    except Exception as e:
        logger.error(f"❌ 混合搜索失敗 ({class_name}): {e}")
        return []



class SearchEngine:
    def __init__(self, config: SCBRConfig):
        self.config = config
        self.text_processor = TextProcessor(config.text_processor)
        self._init_weaviate_client()
        logger.info("搜索引擎初始化完成")

    def _init_weaviate_client(self):
        """初始化 Weaviate 客戶端"""
        try:
            weaviate_config = self.config.weaviate
            if weaviate_config.api_key:
                auth_config = weaviate.AuthApiKey(api_key=weaviate_config.api_key)
                self.weaviate_client = weaviate.Client(
                    url=weaviate_config.url,
                    auth_client_secret=auth_config,
                    timeout_config=(weaviate_config.timeout, weaviate_config.timeout)
                )
            else:
                self.weaviate_client = weaviate.Client(
                    url=weaviate_config.url,
                    timeout_config=(weaviate_config.timeout, weaviate_config.timeout)
                )
            logger.info(f"✅ Weaviate 連接成功: {weaviate_config.url}")
        except Exception as e:
            logger.error(f"❌ Weaviate 客戶端初始化失敗: {e}")
            self.weaviate_client = None

    async def hybrid_search(self, class_name: str, query_text: str, 
                           query_vector: Optional[List[float]] = None,
                           limit: int = 10) -> List[Dict[str, Any]]:
        """執行混合搜索"""
        if not self.weaviate_client:
            return []

        try:
            # 處理查詢文本
            processed_text = self.text_processor.segment_text(query_text) if query_text else ""
            
            # 構建查詢
            query_builder = self.weaviate_client.query.get(class_name).with_additional(["score", "distance"])
            
            if query_vector and len(query_vector) > 0:
                # 混合搜索
                query_builder = query_builder.with_hybrid(
                    query=processed_text,
                    vector=query_vector,
                    alpha=self.config.search.hybrid_alpha,
                    properties=self.config.search.search_fields
                )
            else:
                # 純 BM25 搜索
                query_builder = query_builder.with_hybrid(
                    query=processed_text,
                    alpha=0.0,
                    properties=self.config.search.search_fields
                )
            
            result = query_builder.with_limit(limit).do()
            
            if isinstance(result, dict) and "errors" in result:
                logger.error(f"GraphQL 錯誤: {result['errors']}")
                return []

            #  兼容 {"data":{"Get":...}} 與 {"Get":...}
            get_section = {}
            if isinstance(result, dict):
                get_section = result.get("data", {}).get("Get") or result.get("Get") or {}
            results = get_section.get(class_name) or []
            if not isinstance(results, list):
                results = []

            #  處理結果（先把型別統一成 float，再算信心分數）
            for item in results:
                addi = item.get("_additional") or {}
                score = _to_float(addi.get("score"), default=0.0)
                distance = _to_float(addi.get("distance"), default=float("inf"))
                item["_confidence"] = self._calculate_confidence(score, distance)
            
            logger.info(f"📊 {class_name} 搜索: {len(results)} 個結果")
            return results
            
        except Exception as e:
            logger.error(f"❌ 混合搜索失敗 ({class_name}): {e}")
            return []

    def _calculate_confidence(self, score: float | None, distance: float | None) -> float:
        """計算置信度分數（容錯型別與缺值）"""
        import math
        s = _to_float(score, default=0.0)
        d = _to_float(distance, default=float("inf"))

        if s > 0.0:
            # 保留你原本的 logistic 形狀，但已確保為 float
            return 1.0 / (1.0 + math.exp(-1.2 * (s - 0.10)))

        # 距離越小越好 → 轉為 [0,1] 信心
        if math.isfinite(d):
            return 1.0 / (1.0 + max(d, 1e-9))

        # 都不可用時給 0
        return 0.0

