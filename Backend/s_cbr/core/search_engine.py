# -*- coding: utf-8 -*-
"""
SearchEngine: 通用 Hybrid 搜尋（Weaviate）
- 支援 Case / PulsePJ / RPCase
- 自動選擇 BM25 欄位：bm25_cjk > bm25_text（0 筆會 fallback）
- 有向量 → Hybrid；無向量 → BM25-only
- 回傳欄位 = 白名單 ∩ 實際 schema
"""

import os
import logging
from typing import Any, Dict, List, Optional

try:
    import weaviate
except Exception:
    weaviate = None

logger = logging.getLogger("s_cbr.SearchEngine")
logger.setLevel(logging.INFO)


class SearchEngine:
    """ 與 Weaviate 溝通的檢索層。 """

    ALLOW: Dict[str, List[str]] = {
        "TCMCase": [  # 改為 TCMCase
            # 基本資訊
            "case_id", "patient_id", "visit_date", "age", "gender",
            # 向量搜索欄位
            "full_text",
            # BM25 欄位
            "jieba_tokens", "syndrome_terms", "zangfu_terms", 
            "symptom_terms", "pulse_terms", "tongue_terms", "treatment_terms",
            # 結構化欄位
            "chief_complaint", "diagnosis", "treatment_principle", "suggestion",
            # 原始資料
            "raw_data", "created_at", "updated_at"
        ],
        # RPCase 與其他來源已不使用於整改版
    }

    def __init__(self, config: Any = None, weaviate_client: Any = None):
        self.config = config
        self.client = weaviate_client or self._build_client(config)
        self.weaviate_client = self.client
        logger.info("[SearchEngine] Connected to Weaviate")

    # ---------- client ----------
    def _build_client(self, cfg):
        if weaviate is None:
            raise RuntimeError("請先安裝 weaviate-client：pip install weaviate-client")

        url = (
            getattr(cfg, "WEAVIATE_URL", None)
            or getattr(getattr(cfg, "weaviate", None), "url", None)
            or os.getenv("WEAVIATE_URL")
            or "http://localhost:8080"
        )
        api_key = (
            getattr(cfg, "WV_API_KEY", None)
            or getattr(getattr(cfg, "weaviate", None), "api_key", None)
            or os.getenv("WV_API_KEY")
            or os.getenv("WEAVIATE_API_KEY")  # 你在 config.py 用的是這個名字
            or "key-admin"
        )

        client = weaviate.Client(
            url=url,
            additional_headers={"Authorization": f"Bearer {api_key}"},
            timeout_config=(5, 60),
        )

        # 健檢：不同版本最通用的是 schema.get()
        try:
            _ = client.schema.get()
        except Exception as e:
            logger.error(f"[SearchEngine] Weaviate 連線/健檢失敗：{e}")
            raise
        return client

    # ---------- schema/欄位 ----------
    def _schema_props(self, index: str) -> List[str]:
        try:
            sch = self.weaviate_client.schema.get()
            for c in sch.get("classes", []):
                if c.get("class") == index:
                    return [p.get("name") for p in c.get("properties", [])]
        except Exception:
            pass
        return []

    def _pick_sparse_prop(self, index: str) -> str:
        names = set(self._schema_props(index))
        # 優先順序：bm25_cjk > bm25_text > full_text > jieba_tokens > chief_complaint
        for cand in ["bm25_cjk", "bm25_text", "full_text", "jieba_tokens", "chief_complaint"]:
            if cand in names:
                return cand
        return "bm25_text"

    def _candidate_sparse_props(self, index: str) -> List[str]:
        """回傳此 index 可用的 BM25 欄位候選清單（依優先順序）。"""
        names = set(self._schema_props(index))
        order = [
            "bm25_cjk", "bm25_text", "full_text", "jieba_tokens",
            "chief_complaint", "symptom_terms", "syndrome_terms",
        ]
        return [n for n in order if n in names]

    # ---------- 主入口 ----------
    async def hybrid_search(
        self,
        index: str,
        *,
        text: str,
        vector: Optional[List[float]] = None,
        alpha: float = 0.5,
        limit: int = 10,
        search_fields: Optional[List[str]] = None,
        return_props: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        有向量 → Hybrid；無向量 → BM25-only
        search_fields 預設自動選 bm25_cjk / bm25_text
        return_props = 白名單 ∩ 實際 schema
        0 筆且用 bm25_cjk → fallback bm25_text 再試
        """
        # 1) BM25 欄位
        fields = list(search_fields or [self._pick_sparse_prop(index)])

        # 2) 回傳欄位：白名單 → 與 schema 交集
        allow = set(self.ALLOW.get(index, []))
        if not return_props:
            props = list(allow)
        else:
            props = [p for p in return_props if p in allow]

        real = set(self._schema_props(index))
        props = [p for p in props if p in real]
        if not props:
            fallback = {
                "TCMCase": ["case_id", "chief_complaint", "diagnosis", "full_text"],
                "PulsePJ": ["pid", "name", "category", "main_disease", "search_text"],
                "RPCase": ["rid", "final_diagnosis", "search_text"],
            }
            props = [p for p in fallback.get(index, []) if p in real]

        qdim = len(vector) if vector else 0
        mode = "HYBRID" if qdim > 0 else "BM25-only"

        logger.info(
            f"🔎 {index} 啟動檢索: Mode={mode}, α={alpha:.2f}, "
            f"查詢字串長度={len(text)} ({text[:20]}...)"
        )

        # 3) 執行查詢
        def _do(flds: List[str]) -> List[Dict[str, Any]]:
            # 查詢前紀錄這次實際使用的欄位
            logger.info(f"🔎 {index} {mode} α={alpha}, qdim={qdim}, fields={flds}, props={props}")
            q = self.weaviate_client.query.get(index, props)\
                .with_additional(["score", "distance"])\
                .with_limit(limit)
            if vector and len(vector) > 0:
                q = q.with_hybrid(query=text, alpha=alpha, vector=vector, properties=flds)
            else:
                q = q.with_hybrid(query=text, alpha=1.0, properties=flds)  # 純 BM25
            try:
                resp = q.do()
                items = resp.get("data", {}).get("Get", {}).get(index, []) or []
            except Exception as e:
                logger.error(f"[SearchEngine] {index} query error: {e}")
                items = []
            logger.info(f"📊 {index} 搜索: {len(items)} 個結果")
            return items

        hits = _do(fields)
        if not hits:
            # 動態 fallback：嘗試其他存在於 schema 的候選欄位
            tried = set(fields)
            for alt in self._candidate_sparse_props(index):
                if alt in tried:
                    continue
                logger.info(f"[SearchEngine] {index} 無結果，改用 {alt} 重試")
                hits = _do([alt])
                if hits:
                    break

        # 4) 正規化分數
        out: List[Dict[str, Any]] = []
        for h in hits:
            add = h.get("_additional") or {}
            s = add.get("score")
            try:
                score = float(s) if s is not None else 0.0
            except Exception:
                score = 0.0
            h["_confidence"] = score
            h["_attr_score"] = 0.0
            h["_final_score"] = score
            # 🚨 修正：確保 'score' 字段也存在，以兼容日誌和 L2 邏輯
            h["score"] = score 
            out.append(h)
        return out
    
    async def intelligent_hybrid_search(
        self,
        index: str,
        *,
        text: str,
        vector: Optional[List[float]] = None,
        alpha: float = 0.5,
        limit: int = 10,
        search_fields: Optional[List[str]] = None,
        return_props: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        智能混合檢索（為 Agentic 模式優化）
        
        與 hybrid_search 相似，但添加了額外的智能化處理：
        1. 更詳細的日誌記錄
        2. 更好的錯誤處理
        3. 為 Agentic 決策提供更多元數據
        
        Args:
            index: Weaviate 索引名稱
            text: 查詢文本
            vector: 查詢向量（可選）
            alpha: 混合檢索權重（0.0-1.0）
            limit: 返回數量
            search_fields: BM25 搜索欄位（可選）
            return_props: 返回欄位（可選）
        
        Returns:
            檢索結果列表，每個結果包含額外的元數據
        """
        # 直接調用原有的 hybrid_search，但添加額外的智能化處理
        logger.info(
            f"[SearchEngine] 智能檢索啟動 - "
            f"Index: {index}, Alpha: {alpha:.2f}, "
            f"向量: {'是' if vector else '否'}, Limit: {limit}"
        )
        
        # 調用原有方法
        results = await self.hybrid_search(
            index=index,
            text=text,
            vector=vector,
            alpha=alpha,
            limit=limit,
            search_fields=search_fields,
            return_props=return_props
        )
        
        # 為每個結果添加額外的元數據（用於 Agentic 決策）
        for result in results:
            # 確保有統一的分數欄位
            if "_final_score" in result and "score" not in result:
                result["score"] = result["_final_score"]
            
            # 添加 Agentic 專用的元數據
            result["_agentic_metadata"] = {
                "alpha_used": alpha,
                "retrieval_mode": "hybrid" if vector else "bm25_only",
                "search_fields_used": search_fields or [self._pick_sparse_prop(index)]
            }
        
        logger.info(
            f"[SearchEngine] 智能檢索完成 - "
            f"返回 {len(results)} 個結果"
        )
        
        return results
