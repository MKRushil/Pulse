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
        "Case": [
            "case_id", "chiefComplaint", "presentIllness", "search_text",
            "diagnosis_main", "pulse_text", "src_casev_uuid",
        ],
        "PulsePJ": [
            "pid", "name", "category", "main_disease", "search_text", "symptoms", "category_id",
        ],
        "RPCase": [
            "rid", "final_diagnosis", "pulse_tags", "symptom_tags", "search_text",
        ],
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
        if "bm25_cjk" in names:
            return "bm25_cjk"
        if "bm25_text" in names:
            return "bm25_text"
        return "bm25_text"

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
                "Case": ["case_id", "chiefComplaint", "presentIllness", "search_text"],
                "PulsePJ": ["pid", "name", "category", "main_disease", "search_text"],
                "RPCase": ["rid", "final_diagnosis", "search_text"],
            }
            props = [p for p in fallback.get(index, []) if p in real]

        qdim = len(vector) if vector else 0
        mode = "HYBRID" if qdim > 0 else "BM25-only"
        logger.info(f"🔎 {index} {mode} α={alpha}, qdim={qdim}, fields={fields}, props={props}")

        # 3) 執行查詢
        def _do(flds: List[str]) -> List[Dict[str, Any]]:
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
        if not hits and fields == ["bm25_cjk"]:
            logger.info(f"[SearchEngine] {index} 無結果，改用 bm25_text 重試")
            hits = _do(["bm25_text"])

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
            out.append(h)
        return out
