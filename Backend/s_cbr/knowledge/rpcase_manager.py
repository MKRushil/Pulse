# -*- coding: utf-8 -*-
"""
RPCase 回饋案例管理器 v2.0（保留舊版架構，補欄位 / jieba / 連線強化）

修改點（不改你的流程與函式介面）：
1) Weaviate 連線支援 API Key（SCBRConfig 或環境變數 WV_API_KEY）
2) 載入 jieba 詞庫 Backend/prompt/tcm_userdict_jieba_v2.txt
3) RPCase Schema 新增/補齊欄位：
   - 檢索專用：search_all, search_all_seg
   - 槽位：symptom_tags[], observation_tags[], pulse_tags[], age_range, gender, duration, triggers[]
   - 溯源：source_case_ids[], source_pulse_ids[]
   - 向量/版本：embedding_model, embed_dim, model_version
   - 品質/治理：trust_score, feedback_count, disagreement_count, reuse_count, review_status, safety_flag, safety_notes, conversation_summary
   - 原有欄位保留：original_question, patient_context, final_diagnosis, treatment_plan, reasoning_process, conversation_log, effectiveness_score/confidence_score/safety_score, ...
"""

import os
import re
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

import weaviate
import jieba

try:
    from ..utils.spiral_logger import SpiralLogger
    logger = SpiralLogger.get_logger("RPCaseManager")
except ImportError:
    logger = logging.getLogger("RPCaseManager")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

try:
    from ..config.scbr_config import SCBRConfig
except ImportError:
    logger.warning("無法載入 SCBRConfig，使用預設配置")
    SCBRConfig = None


# -----------------------------
# jieba：載入專用詞庫
# -----------------------------
def _backend_root() -> str:
    # 本檔位於 Backend/s_cbr/knowledge/rpcase_manager.py
    # 上兩層就是 Backend 根目錄
    here = os.path.abspath(__file__)
    return os.path.dirname(os.path.dirname(os.path.dirname(here)))  # -> Backend

USERDICT_PATH = os.path.join(_backend_root(), "prompt", "tcm_userdict_jieba_v2.txt")

def _normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.strip()

    # 全形 -> 半形
    def to_half_width(u: str) -> str:
        res = []
        for ch in u:
            code = ord(ch)
            if code == 0x3000:
                code = 32
            elif 0xFF01 <= code <= 0xFF5E:
                code -= 0xFEE0
            res.append(chr(code))
        return "".join(res)

    s = to_half_width(s)
    s = re.sub(r"[，。、《》〈〉（）()；、：:,.!?;\"'\\/\[\]{}]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def _seg_text(s: str) -> str:
    s = _normalize_text(s)
    if not s:
        return ""
    toks = jieba.cut(s, HMM=True)
    return " ".join([t for t in toks if t.strip()])


# 嘗試載入自訂詞庫
try:
    if os.path.exists(USERDICT_PATH):
        with open(USERDICT_PATH, "r", encoding="utf-8") as f:
            jieba.load_userdict(f)
        logger.info(f"[jieba] 已載入詞庫：{USERDICT_PATH}")
    else:
        logger.info(f"[jieba] 找不到自訂詞庫，改用內建詞庫：{USERDICT_PATH}")
except Exception as _e:
    logger.warning(f"[jieba] 載入詞庫失敗：{_e}，改用內建詞庫。")


class RPCaseManager:
    """
    RPCase 回饋案例管理器（保留舊版介面）
    - 案例向量化與儲存
    - 相似案例檢索
    - 統計與品質欄位
    """

    def __init__(self, weaviate_client: Optional[weaviate.Client] = None):
        self.logger = logger
        self.config = SCBRConfig() if SCBRConfig else None

        # Weaviate 客戶端
        if weaviate_client:
            self.client = weaviate_client
        else:
            self.client = self._init_weaviate_client()

        # 初始化 / 補齊 Schema
        self._ensure_rpcase_schema()
        self.logger.info("RPCase 管理器 v2.0 初始化完成")

    # -----------------------------
    # Weaviate 連線（加入 API Key）
    # -----------------------------
    def _init_weaviate_client(self) -> Optional[weaviate.Client]:
        try:
            if self.config:
                db_config = self.config.get_database_config()
                weaviate_url = getattr(db_config, "weaviate_url", "http://localhost:8080")
                timeout = getattr(db_config, "weaviate_timeout", 30)
                api_key = getattr(db_config, "weaviate_api_key", None) or os.getenv("WV_API_KEY")
            else:
                weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
                timeout = int(os.getenv("WEAVIATE_TIMEOUT", "30"))
                api_key = os.getenv("WV_API_KEY")

            if api_key:
                # v3 client：AuthApiKey 或 additional_headers 皆可
                try:
                    client = weaviate.Client(
                        url=weaviate_url,
                        auth_client_secret=weaviate.AuthApiKey(api_key),
                        timeout_config=(timeout, timeout),
                    )
                except Exception:
                    client = weaviate.Client(
                        url=weaviate_url,
                        additional_headers={"Authorization": f"Bearer {api_key}"},
                        timeout_config=(timeout, timeout),
                    )
            else:
                client = weaviate.Client(url=weaviate_url, timeout_config=(timeout, timeout))

            # 健康檢查
            client.schema.get()
            self.logger.info(f"✅ Weaviate 客戶端連接成功: {weaviate_url}")
            return client

        except Exception as e:
            self.logger.error(f"❌ Weaviate 客戶端初始化失敗: {e}")
            return None

    # -----------------------------
    # Schema：建立或補欄位
    # -----------------------------
    def _ensure_rpcase_schema(self):
        if not self.client:
            self.logger.warning("Weaviate 客戶端不可用，跳過 Schema 檢查")
            return

        try:
            schema = self.client.schema.get()
            class_names = [c["class"] for c in schema.get("classes", [])]

            if "RPCase" not in class_names:
                self.logger.info("創建 RPCase Schema...")
                self._create_rpcase_schema()
            else:
                self.logger.info("RPCase Schema 已存在，檢查缺欄位...")
                self._ensure_missing_properties()
        except Exception as e:
            self.logger.error(f"RPCase Schema 檢查失敗: {e}")

    def _create_rpcase_schema(self):
        """創建 RPCase（含你要求的新增欄位）"""
        rpcase_schema = {
            "class": "RPCase",
            "description": "螺旋推理回饋案例知識庫",
            "vectorizer": "none",  # 使用外部向量
            "properties": [
                # 原有
                {"name": "rpcase_id", "dataType": ["string"], "description": "回饋案例ID"},
                {"name": "original_question", "dataType": ["text"], "description": "原始問題"},
                {"name": "patient_context", "dataType": ["text"], "description": "患者上下文"},
                {"name": "spiral_rounds", "dataType": ["int"], "description": "螺旋推理輪數"},
                {"name": "used_cases", "dataType": ["string[]"], "description": "使用的案例ID列表"},
                {"name": "final_diagnosis", "dataType": ["text"], "description": "最終診斷"},
                {"name": "treatment_plan", "dataType": ["text"], "description": "治療方案"},
                {"name": "reasoning_process", "dataType": ["text"], "description": "推理過程"},
                {"name": "user_feedback", "dataType": ["text"], "description": "用戶回饋"},
                {"name": "effectiveness_score", "dataType": ["number"], "description": "有效性評分"},
                {"name": "confidence_score", "dataType": ["number"], "description": "信心度評分"},
                {"name": "safety_score", "dataType": ["number"], "description": "安全性評分"},
                {"name": "session_id", "dataType": ["string"], "description": "會話ID"},
                {"name": "conversation_history", "dataType": ["text"], "description": "對話歷史"},
                {"name": "created_timestamp", "dataType": ["string"], "description": "創建時間"},
                {"name": "updated_timestamp", "dataType": ["string"], "description": "更新時間"},
                {"name": "tags", "dataType": ["string[]"], "description": "標籤"},
                {"name": "complexity_level", "dataType": ["int"], "description": "複雜度等級"},
                {"name": "success_rate", "dataType": ["number"], "description": "成功率"},
                {"name": "reuse_count", "dataType": ["int"], "description": "重用次數"},
                {"name": "source_type", "dataType": ["string"], "description": "來源類型"},

                # === 新增：檢索專用 ===
                {"name": "search_all", "dataType": ["text"], "description": "檢索用原文彙總"},
                {"name": "search_all_seg", "dataType": ["text"], "description": "jieba 切詞結果（空白分隔）"},

                # === 新增：槽位 ===
                {"name": "symptom_tags", "dataType": ["text[]"], "description": "症狀標籤"},
                {"name": "observation_tags", "dataType": ["text[]"], "description": "觀察域標籤"},
                {"name": "pulse_tags", "dataType": ["text[]"], "description": "脈象標籤"},
                {"name": "age_range", "dataType": ["text"], "description": "年齡區間"},
                {"name": "gender", "dataType": ["text"], "description": "性別"},
                {"name": "duration", "dataType": ["text"], "description": "病程長短"},
                {"name": "triggers", "dataType": ["text[]"], "description": "誘因"},

                # === 新增：溯源 ===
                {"name": "source_case_ids", "dataType": ["text[]"], "description": "來源 Case IDs"},
                {"name": "source_pulse_ids", "dataType": ["text[]"], "description": "來源 PulsePJV IDs"},

                # === 新增：向量/版本 ===
                {"name": "embedding_model", "dataType": ["text"], "description": "向量模型名"},
                {"name": "embed_dim", "dataType": ["int"], "description": "向量維度"},
                {"name": "model_version", "dataType": ["text"], "description": "SCBR 模型版本"},

                # === 新增：品質/治理 ===
                {"name": "trust_score", "dataType": ["number"], "description": "可信加權"},
                {"name": "feedback_count", "dataType": ["int"], "description": "回饋次數"},
                {"name": "disagreement_count", "dataType": ["int"], "description": "不一致次數"},
                {"name": "review_status", "dataType": ["text"], "description": "review 狀態"},
                {"name": "safety_flag", "dataType": ["boolean"], "description": "安全標記"},
                {"name": "safety_notes", "dataType": ["text"], "description": "安全備註"},
                {"name": "conversation_summary", "dataType": ["text"], "description": "對話摘要（壓縮）"},
            ],
        }

        try:
            self.client.schema.create_class(rpcase_schema)
            self.logger.info("✅ RPCase Schema 創建成功")
        except Exception as e:
            self.logger.error(f"RPCase Schema 創建失敗: {e}")
            raise

    def _ensure_missing_properties(self):
        """如果類別存在，補齊缺欄位（不改動已存在欄位）"""
        try:
            schema = self.client.schema.get()
            classes = {c["class"]: c for c in schema.get("classes", [])}
            props_exist = {p["name"] for p in classes["RPCase"].get("properties", [])}

            # 只列出需要新增的（與 _create_rpcase_schema 同步）
            needed = [
                "search_all", "search_all_seg",
                "symptom_tags", "observation_tags", "pulse_tags",
                "age_range", "gender", "duration", "triggers",
                "source_case_ids", "source_pulse_ids",
                "embedding_model", "embed_dim", "model_version",
                "trust_score", "feedback_count", "disagreement_count",
                "review_status", "safety_flag", "safety_notes", "conversation_summary",
            ]

            # 對應 dataType
            dtype_map = {
                "search_all": ["text"],
                "search_all_seg": ["text"],
                "symptom_tags": ["text[]"],
                "observation_tags": ["text[]"],
                "pulse_tags": ["text[]"],
                "age_range": ["text"],
                "gender": ["text"],
                "duration": ["text"],
                "triggers": ["text[]"],
                "source_case_ids": ["text[]"],
                "source_pulse_ids": ["text[]"],
                "embedding_model": ["text"],
                "embed_dim": ["int"],
                "model_version": ["text"],
                "trust_score": ["number"],
                "feedback_count": ["int"],
                "disagreement_count": ["int"],
                "review_status": ["text"],
                "safety_flag": ["boolean"],
                "safety_notes": ["text"],
                "conversation_summary": ["text"],
            }

            for name in needed:
                if name not in props_exist:
                    self.client.schema.property.create("RPCase", {
                        "name": name,
                        "dataType": dtype_map[name],
                        "description": name
                    })
                    self.logger.info(f"[schema] 已補欄位：RPCase.{name}")

        except Exception as e:
            self.logger.error(f"補欄位失敗：{e}")

    # -----------------------------
    # 工具：組合 search_all / seg
    # -----------------------------
    def _build_search_fields(self, data: Dict[str, Any]) -> Tuple[str, str]:
        parts: List[str] = [
            data.get("original_question", ""),
            data.get("patient_context", ""),
            data.get("final_diagnosis", ""),
            data.get("treatment_plan", ""),
            data.get("reasoning_process", ""),
            data.get("conversation_summary", ""),
            " ".join(data.get("symptom_tags", []) or []),
            " ".join(data.get("observation_tags", []) or []),
            " ".join(data.get("pulse_tags", []) or []),
            data.get("duration", "") or "",
            data.get("age_range", "") or "",
            data.get("gender", "") or "",
        ]
        s_all = "；".join([p for p in parts if p])
        s_seg = _seg_text(s_all)
        return s_all, s_seg

    # -----------------------------
    # === 以下為你原本的流程/介面 ===
    # -----------------------------
    async def save_rpcase(self, rpcase_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        儲存回饋案例到 RPCase 知識庫
        （保留你的介面；新增：自動回填 search_all / search_all_seg 與治理欄位）
        """
        if not self.client:
            raise Exception("Weaviate 客戶端不可用")

        try:
            # 1) 生成向量（沿用你原本的做法，不強改）
            vector = await self._generate_case_vector(rpcase_data)

            # 2) 檢索欄位
            s_all, s_seg = self._build_search_fields(rpcase_data)

            # 3) 準備資料（保留原欄位，加上你要求的新增欄位，若未給則設預設值）
            data_object = {
                # 原有
                "rpcase_id": rpcase_data.get("rpcase_id") or str(uuid.uuid4()),
                "original_question": rpcase_data.get("original_question", ""),
                "patient_context": rpcase_data.get("patient_context", ""),
                "spiral_rounds": int(rpcase_data.get("spiral_rounds", 1)),
                "used_cases": rpcase_data.get("used_cases", []),
                "final_diagnosis": rpcase_data.get("final_diagnosis", ""),
                "treatment_plan": rpcase_data.get("treatment_plan", ""),
                "reasoning_process": rpcase_data.get("reasoning_process", ""),
                "user_feedback": rpcase_data.get("user_feedback", ""),
                "effectiveness_score": float(rpcase_data.get("effectiveness_score", 0.0)),
                "confidence_score": float(rpcase_data.get("confidence_score", 0.0)),
                "safety_score": float(rpcase_data.get("safety_score", 0.0)),
                "session_id": rpcase_data.get("session_id", ""),
                "conversation_history": rpcase_data.get("conversation_history", ""),
                "created_timestamp": rpcase_data.get("created_timestamp", datetime.now().isoformat()),
                "updated_timestamp": rpcase_data.get("updated_timestamp", datetime.now().isoformat()),
                "tags": rpcase_data.get("tags", []),
                "complexity_level": int(rpcase_data.get("complexity_level", 1)),
                "success_rate": float(rpcase_data.get("success_rate", 0.0)),
                "reuse_count": int(rpcase_data.get("reuse_count", 0)),
                "source_type": rpcase_data.get("source_type", "spiral_feedback"),

                # 新增：檢索專用
                "search_all": s_all,
                "search_all_seg": s_seg,

                # 新增：槽位
                "symptom_tags": rpcase_data.get("symptom_tags", []),
                "observation_tags": rpcase_data.get("observation_tags", []),
                "pulse_tags": rpcase_data.get("pulse_tags", []),
                "age_range": rpcase_data.get("age_range", ""),
                "gender": rpcase_data.get("gender", ""),
                "duration": rpcase_data.get("duration", ""),
                "triggers": rpcase_data.get("triggers", []),

                # 新增：溯源
                "source_case_ids": rpcase_data.get("source_case_ids", []),
                "source_pulse_ids": rpcase_data.get("source_pulse_ids", []),

                # 新增：向量/版本（embed_dim 以實際長度填入；你之後切到 1024D 會自動正確）
                "embedding_model": rpcase_data.get("embedding_model", ""),
                "embed_dim": rpcase_data.get("embed_dim", len(vector) if isinstance(vector, list) else 0),
                "model_version": rpcase_data.get("model_version", ""),

                # 新增：品質/治理
                "trust_score": float(rpcase_data.get("trust_score", 0.0)),
                "feedback_count": int(rpcase_data.get("feedback_count", 0)),
                "disagreement_count": int(rpcase_data.get("disagreement_count", 0)),
                "review_status": rpcase_data.get("review_status", "draft"),
                "safety_flag": bool(rpcase_data.get("safety_flag", False)),
                "safety_notes": rpcase_data.get("safety_notes", ""),
                "conversation_summary": rpcase_data.get("conversation_summary", ""),
            }

            # 4) 寫入 Weaviate（vectorizer=none → 帶 vector）
            result = self.client.data_object.create(
                data_object=data_object,
                class_name="RPCase",
                vector=vector
            )

            self.logger.info(f"✅ RPCase 儲存成功: {data_object['rpcase_id']}")
            return {
                "success": True,
                "rpcase_id": data_object["rpcase_id"],
                "weaviate_id": result,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"RPCase 儲存失敗: {str(e)}")
            raise

    # ==== 下面這些函式維持你的舊版介面 ====

    async def _generate_case_vector(self, rpcase_data: Dict[str, Any]) -> List[float]:
        """
        生成案例向量（保留你舊版 placeholder，不做變更）
        之後你改成 NVIDIA 1024D 時，這裡回傳 1024 維即可，embed_dim 會自動跟著更新。
        """
        try:
            # 舊版：合併文本 → 產生隨機向量（佔位）
            text_content = " ".join([
                rpcase_data.get("original_question", ""),
                rpcase_data.get("final_diagnosis", ""),
                rpcase_data.get("treatment_plan", ""),
                rpcase_data.get("reasoning_process", "")[:500]
            ])
            import random
            vector_dim = 1536  # <— 你目前舊版 placeholder，之後可改 1024
            vector = [random.random() for _ in range(vector_dim)]
            self.logger.debug(f"為案例生成 {vector_dim} 維向量；文本長度={len(text_content)}")
            return vector
        except Exception as e:
            self.logger.error(f"向量生成失敗: {str(e)}")
            return [0.0] * 1536

    async def search_similar_rpcases(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """相似案例檢索（沿用你舊版流程）"""
        if not self.client:
            return []
        try:
            query_vector = await self._generate_query_vector(query_text)
            result = (
                self.client.query
                .get("RPCase", [
                    "rpcase_id", "original_question", "final_diagnosis",
                    "treatment_plan", "effectiveness_score", "confidence_score",
                    "spiral_rounds", "created_timestamp", "tags"
                ])
                .with_near_vector({"vector": query_vector, "certainty": 0.7})
                .with_limit(limit)
                .do()
            )
            return result.get("data", {}).get("Get", {}).get("RPCase", []) or []
        except Exception as e:
            self.logger.error(f"相似案例檢索失敗: {str(e)}")
            return []

    async def _generate_query_vector(self, query_text: str) -> List[float]:
        """生成查詢向量（保留你舊版 placeholder）"""
        import random
        return [random.random() for _ in range(1536)]

    def get_rpcase_stats(self) -> Dict[str, Any]:
        """取得 RPCase 統計（保留你舊版介面；若欄位型態不支援 mean 會回退）"""
        if not self.client:
            return {"error": "Weaviate 客戶端不可用"}
        try:
            # count
            res_cnt = self.client.query.aggregate("RPCase").with_meta_count().do()
            total_cases = (
                res_cnt.get("data", {}).get("Aggregate", {}).get("RPCase", [{}])[0]
                .get("meta", {}).get("count", 0)
            )
            # mean（容錯）
            out = {"total_rpcases": total_cases, "timestamp": datetime.now().isoformat()}
            try:
                res_mean = (
                    self.client.query
                    .aggregate("RPCase")
                    .with_fields("mean { effectiveness_score confidence_score safety_score trust_score }")
                    .do()
                )
                node = res_mean.get("data", {}).get("Aggregate", {}).get("RPCase", [{}])[0]
                mean = node.get("mean", {}) or {}
                out.update({
                    "avg_effectiveness": float(mean.get("effectiveness_score") or 0.0),
                    "avg_confidence": float(mean.get("confidence_score") or 0.0),
                    "avg_safety": float(mean.get("safety_score") or 0.0),
                    "avg_trust": float(mean.get("trust_score") or 0.0),
                })
            except Exception as _e:
                self.logger.warning(f"[stats] 取得 mean 失敗：{_e}")
            return out
        except Exception as e:
            self.logger.error(f"RPCase 統計獲取失敗: {str(e)}")
            return {"error": str(e)}


__all__ = ["RPCaseManager"]
