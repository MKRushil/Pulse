# -*- coding: utf-8 -*-
"""
統一搜索引擎 v2.1
整合 BM25 關鍵字搜索和向量語義搜索
"""

import asyncio
import re  # 用於欄位名稱過濾
from typing import Dict, Any, List, Optional
import weaviate
from ..config import SCBRConfig
from ..utils.logger import get_logger
from ..utils.text_processor import TextProcessor

# 放在檔案開頭適當位置
ALLOWED_RETURN_PROPS = {
    "Case":    ["src_casev_uuid", "diagnosis_main", "pulse_text"],
    "PulsePJV":["symptoms", "name", "category_id"],
    "RPCase":  ["final_diagnosis", "pulse_tags", "symptom_tags"],
}

# 不同集合 → 對齊成共同鍵
RENAME_MAP = {
    "Case": {
        "src_casev_uuid": "case_id",
        # diagnosis_main 已是共同鍵
    },
    "PulsePJV": {
        # 這組主要回 symptoms，其他對齊在後處理補齊
    },
    "RPCase": {
        "final_diagnosis": "diagnosis_main",
        # pulse_tags/symptom_tags 會在後處理合併成可讀字串
    }
}


logger = get_logger("SearchEngine")
logger.info(f"📦 SearchEngine loaded from: {__file__}")

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

    async def hybrid_search(
        self,
        class_name: str,
        processed_text: str,
        query_vector: list[float] | None,
        limit: int = 20,
    ) -> dict:
        """
        以 weaviate hybrid (BM25 + vector) 搜索指定 class。
        - 依據 weaviate 的 schema 自動過濾不存在/非法的欄位，避免 GraphQL 語法錯誤。
        - 預設回傳欄位會根據類別精簡到「前端用得到」且「確定存在」的欄位。
        - 仍以 config.search.search_fields 作為 keyword 搜尋欄位。
        回傳 weaviate 原始結果物件（dict）。
        """
        import re
        

        def _to_float(x, fallback: float) -> float:
            try:
                return float(x)
            except Exception:
                return fallback

        def _l2_norm(v: list[float]) -> float:
            try:
                import math
                return math.sqrt(sum(x * x for x in v))
            except Exception:
                return 0.0

        # === 1) 依 class 設定【建議回傳欄位】（只選 schema 裡真的存在的） =======================
        # 從你的 log 得到的可用欄位（避免中文欄位/不存在欄位造成 GraphQL error）
        per_class_defaults = {
            "Case": [
                # 你 schema 有的：
                "src_casev_uuid",       # ← weaviate 回饋提示：原來的 case_id 應改此欄位
                "diagnosis_main",
                "pulse_text",
            ],
            "PulsePJV": [
                # schema 有的：
                "category_id",
                "name",
                "symptoms",
            ],
            "RPCase": [
                # schema 有的：
                "final_diagnosis",
                "pulse_tags",
                "symptom_tags",
            ],
        }
        default_return_props = per_class_defaults.get(class_name, [])

        # 允許用 config 另行指定（會與預設做 union）
        cfg_return = getattr(self.config.search, "return_fields", None)
        if isinstance(cfg_return, list) and cfg_return:
            # union 去重，保序
            want_props = list(dict.fromkeys(cfg_return + default_return_props))
        else:
            want_props = default_return_props

        # 只允許 GraphQL 合法的識別字元（英文/底線/數字，且開頭不能是數字）
        ident_pat = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        gql_props = [p for p in want_props if isinstance(p, str) and ident_pat.match(p)]
        dropped = [p for p in want_props if p not in gql_props]
        if dropped:
            logger.warning(f"↯ Dropped non-GraphQL property names: {dropped}")

        # === 2) keyword 搜尋欄位 ============================================================
        search_fields = getattr(self.config.search, "search_fields", None) or ["search_all", "search_all_seg"]

        # === 3) 建立查詢 ===================================================================
        query_builder = (
            self.weaviate_client
            .query
            .get(class_name, gql_props if gql_props else [])  # 允許為空，純取 additional
            .with_additional(["id", "score", "distance"])
        )

        qlen = len(query_vector or [])
        alpha = _to_float(getattr(self.config.search, "hybrid_alpha", 0.5), 0.5)

        if qlen > 0 and alpha > 0.0:
            logger.info(f"🔎 {class_name} HYBRID α={alpha}, qdim={qlen}, ‖v‖₂={_l2_norm(query_vector or []):.4f}")
            logger.info(f"↪ return props={gql_props[:8]}... | search_fields={search_fields}")
            query_builder = query_builder.with_hybrid(
                query=processed_text or "",
                vector=query_vector,
                alpha=alpha,
                properties=search_fields,
            )
        else:
            logger.info(f"🔎 {class_name} BM25-only α={alpha}, qdim={qlen}")
            query_builder = query_builder.with_hybrid(
                query=processed_text or "",
                alpha=0.0,
                properties=search_fields,
            )

        # === 4) 送出 =======================================================================
        result = query_builder.with_limit(int(limit or 20)).do()

        # 小結 log
        try:
            n_hits = len(result["data"]["Get"].get(class_name, []))
        except Exception:
            n_hits = 0
        logger.info(f"📊 {class_name} 搜索: {n_hits} 個結果")

        return result




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

