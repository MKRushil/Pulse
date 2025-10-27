# -*- coding: utf-8 -*-
"""
Backend/s_cbr/core/rpcase_manager.py
RPCase 分級管理器 - Quarantine → Active → Deprecated
兼容 Weaviate v3 和 v4 API
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import hashlib
import json
from ..utils.logger import get_logger

logger = get_logger("RPCaseManager")

@dataclass
class RPCaseStatus:
    """RPCase 狀態"""
    QUARANTINE = "quarantine"  # 檢疫區
    ACTIVE = "active"          # 活躍庫
    DEPRECATED = "deprecated"  # 已淘汰

@dataclass
class RPCaseRecord:
    """RPCase 記錄"""
    rid: str
    session_id: str
    final_diagnosis: str
    symptom_tags: List[str]
    pulse_tags: List[str]
    conversation_rounds: int
    convergence_score: float
    created_at: datetime
    status: str
    
    # 統計資訊
    hit_count: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0
    last_hit_at: Optional[datetime] = None
    
    # 相似度哈希（用於去重）
    content_hash: str = ""

@dataclass
class WritebackCriteria:
    """寫回標準"""
    min_convergence: float = 0.90
    min_coverage: float = 0.70
    min_stability: float = 0.80
    min_rounds: int = 2
    max_primary_change: float = 0.05  # 主證變化 < 5%
    min_confidence_gap: float = 0.15  # 主次證分差 > 15%

class RPCaseManager:
    """RPCase 分級管理器 - 兼容 Weaviate v3/v4"""
    
    def __init__(
        self,
        weaviate_client,
        config,
        criteria: WritebackCriteria = None
    ):
        self.client = weaviate_client
        self.config = config
        self.criteria = criteria or WritebackCriteria()
        self.collection_name = "RPCase"
        
        # 檢測 Weaviate 版本並設置兼容模式
        self.use_v4_api = self._detect_weaviate_version()
        
        # 確保 Collection 存在
        try:
            self._ensure_collection()
        except Exception as e:
            logger.error(f"初始化 RPCase Collection 失敗: {e}")
            raise
        
        # 內存緩存（加速查詢）
        self._cache: Dict[str, RPCaseRecord] = {}
        
        logger.info("✅ RPCase 分級管理器初始化")
        logger.info(f"   Weaviate API: {'v4' if self.use_v4_api else 'v3'}")
        logger.info(f"   寫回標準: Conv≥{self.criteria.min_convergence}, Cov≥{self.criteria.min_coverage}")
    
    # ==================== 版本檢測 ====================
    def _detect_weaviate_version(self) -> bool:
        """
        檢測 Weaviate 客戶端版本
        
        Returns:
            True: v4 API (使用 collections)
            False: v3 API (使用 schema)
        """
        # 檢查是否有 collections 屬性（v4）
        if hasattr(self.client, 'collections'):
            logger.info("檢測到 Weaviate v4 API")
            return True
        # 檢查是否有 schema 屬性（v3）
        elif hasattr(self.client, 'schema'):
            logger.info("檢測到 Weaviate v3 API")
            return False
        else:
            logger.warning("無法檢測 Weaviate 版本，默認使用 v3 API")
            return False
    
    # ==================== Collection 管理 ====================
    def _ensure_collection(self):
        """確保 RPCase Collection 存在（兼容 v3 和 v4）"""
        
        if self.use_v4_api:
            # ===== Weaviate v4 API =====
            try:
                if not self.client.collections.exists(self.collection_name):
                    self.client.collections.create(
                        name=self.collection_name,
                        properties=[
                            {"name": "rid", "dataType": ["text"]},
                            {"name": "session_id", "dataType": ["text"]},
                            {"name": "final_diagnosis", "dataType": ["text"]},
                            {"name": "symptom_tags", "dataType": ["text[]"]},
                            {"name": "pulse_tags", "dataType": ["text[]"]},
                            {"name": "conversation_rounds", "dataType": ["int"]},
                            {"name": "convergence_score", "dataType": ["number"]},
                            {"name": "created_at", "dataType": ["date"]},
                            {"name": "status", "dataType": ["text"]},
                            {"name": "hit_count", "dataType": ["int"]},
                            {"name": "positive_feedback", "dataType": ["int"]},
                            {"name": "negative_feedback", "dataType": ["int"]},
                            {"name": "last_hit_at", "dataType": ["date"]},
                            {"name": "content_hash", "dataType": ["text"]},
                            {"name": "search_text", "dataType": ["text"]},
                            {"name": "bm25_text", "dataType": ["text"]},
                        ]
                    )
                    logger.info("✅ 創建 RPCase Collection (v4)")
                else:
                    logger.info("✅ RPCase Collection 已存在 (v4)")
            except Exception as e:
                logger.error(f"❌ 創建 RPCase Collection 失敗 (v4): {e}")
                raise
        else:
            # ===== Weaviate v3 API =====
            try:
                # 檢查 class 是否存在
                schema = self.client.schema.get()
                class_exists = any(
                    c.get("class") == self.collection_name 
                    for c in schema.get("classes", [])
                )
                
                if not class_exists:
                    # 創建 class schema
                    class_obj = {
                        "class": self.collection_name,
                        "description": "RPCase - 反饋案例庫",
                        "properties": [
                            {"name": "rid", "dataType": ["text"], "description": "RPCase ID"},
                            {"name": "session_id", "dataType": ["text"]},
                            {"name": "final_diagnosis", "dataType": ["text"]},
                            {"name": "symptom_tags", "dataType": ["text[]"]},
                            {"name": "pulse_tags", "dataType": ["text[]"]},
                            {"name": "conversation_rounds", "dataType": ["int"]},
                            {"name": "convergence_score", "dataType": ["number"]},
                            {"name": "created_at", "dataType": ["date"]},
                            {"name": "status", "dataType": ["text"]},
                            {"name": "hit_count", "dataType": ["int"]},
                            {"name": "positive_feedback", "dataType": ["int"]},
                            {"name": "negative_feedback", "dataType": ["int"]},
                            {"name": "last_hit_at", "dataType": ["date"]},
                            {"name": "content_hash", "dataType": ["text"]},
                            {"name": "search_text", "dataType": ["text"]},
                            {"name": "bm25_text", "dataType": ["text"]},
                        ],
                        "vectorizer": "none"  # 使用外部向量
                    }
                    
                    self.client.schema.create_class(class_obj)
                    logger.info("✅ 創建 RPCase Collection (v3)")
                else:
                    logger.info("✅ RPCase Collection 已存在 (v3)")
                    
            except Exception as e:
                logger.error(f"❌ 創建 RPCase Collection 失敗 (v3): {e}")
                raise
    
    # ==================== 寫回判定 ====================
    def should_writeback(
        self,
        session_data: Dict[str, Any],
        convergence_metrics: Dict[str, float],
        syndrome_history: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """
        判定是否符合寫回條件
        
        Returns:
            (是否寫回, 原因說明)
        """
        # 1. 收斂度檢查
        conv = convergence_metrics.get("overall_convergence", 0.0)
        if conv < self.criteria.min_convergence:
            return False, f"收斂度不足 ({conv:.2f} < {self.criteria.min_convergence})"
        
        # 2. 覆蓋率檢查
        cov = convergence_metrics.get("evidence_coverage", 0.0)
        if cov < self.criteria.min_coverage:
            return False, f"覆蓋率不足 ({cov:.2f} < {self.criteria.min_coverage})"
        
        # 3. 穩定度檢查
        stab = convergence_metrics.get("case_stability", 0.0)
        if stab < self.criteria.min_stability:
            return False, f"穩定度不足 ({stab:.2f} < {self.criteria.min_stability})"
        
        # 4. 輪次檢查
        rounds = session_data.get("round", 1)
        if rounds < self.criteria.min_rounds:
            return False, f"輪次不足 ({rounds} < {self.criteria.min_rounds})"
        
        # 5. 主證穩定性檢查（連續2輪）
        if len(syndrome_history) >= 2:
            last_two = syndrome_history[-2:]
            
            # 檢查主證是否一致
            primary_syndromes = [
                h.get("primary_syndrome") 
                for h in last_two
            ]
            
            if len(set(primary_syndromes)) > 1:
                return False, "主證在最後2輪不一致"
            
            # 檢查分數變化
            scores = [h.get("score", 0) for h in last_two]
            if len(scores) == 2:
                score_change = abs(scores[1] - scores[0])
                if score_change > self.criteria.max_primary_change:
                    return False, f"主證分數變化過大 ({score_change:.2f} > {self.criteria.max_primary_change})"
        
        # 6. 主次證分差檢查
        primary_score = session_data.get("primary_score", 0.0)
        secondary_score = session_data.get("secondary_score", 0.0)
        
        if secondary_score > 0:
            gap = primary_score - secondary_score
            if gap < self.criteria.min_confidence_gap:
                return False, f"主次證分差不足 ({gap:.2f} < {self.criteria.min_confidence_gap})"
        
        # 全部通過
        return True, "符合所有寫回標準"
    
    # ==================== 寫入 Quarantine ====================
    async def save_to_quarantine(
        self,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        保存到檢疫區
        
        Returns:
            {"success": bool, "case_id": str, "message": str}
        """
        try:
            # 1. 生成 RPCase ID
            rid = self._generate_rid(session_data["session_id"])
            
            # 2. 提取資訊
            final_diagnosis = session_data.get("diagnosis", "")
            symptom_tags = self._extract_symptoms(session_data)
            pulse_tags = self._extract_pulse_tags(session_data)
            
            # 3. 計算內容哈希（用於去重）
            content_hash = self._calculate_content_hash(
                final_diagnosis, symptom_tags, pulse_tags
            )
            
            # 4. 檢查是否有近重複
            similar_case = await self._find_similar_case(
                content_hash, symptom_tags
            )
            
            if similar_case:
                logger.info(f"🔍 發現相似案例: {similar_case.get('rid', 'unknown')}")
                
                # 比較評分
                similar_score = similar_case.get("convergence_score", 0)
                current_score = session_data.get("convergence_score", 0)
                
                if current_score > similar_score:
                    # 新案例更好，升級版本
                    await self._upgrade_case(similar_case["rid"], rid)
                    logger.info(f"✅ 升級案例版本: {similar_case['rid']} → {rid}")
                else:
                    # 舊案例更好，拒絕寫入
                    return {
                        "success": False,
                        "case_id": similar_case["rid"],
                        "message": "已存在更優質的相似案例"
                    }
            
            # 5. 構建 RPCase 資料
            rpcase_data = {
                "rid": rid,
                "session_id": session_data["session_id"],
                "final_diagnosis": final_diagnosis,
                "symptom_tags": symptom_tags,
                "pulse_tags": pulse_tags,
                "conversation_rounds": session_data.get("round", 1),
                "convergence_score": session_data.get("convergence_score", 0),
                "created_at": datetime.now().isoformat(),
                "status": RPCaseStatus.QUARANTINE,
                "hit_count": 0,
                "positive_feedback": 0,
                "negative_feedback": 0,
                "last_hit_at": None,
                "content_hash": content_hash,
                "search_text": self._build_search_text(session_data),
                "bm25_text": " ".join(symptom_tags + pulse_tags)
            }
            
            # 6. 儲存到 Weaviate（兼容 v3 和 v4）
            if self.use_v4_api:
                # v4 API
                collection = self.client.collections.get(self.collection_name)
                collection.data.insert(properties=rpcase_data)
            else:
                # v3 API
                self.client.data_object.create(
                    data_object=rpcase_data,
                    class_name=self.collection_name
                )
            
            # 7. 加入緩存
            self._cache[rid] = RPCaseRecord(**rpcase_data)
            
            logger.info(f"✅ RPCase 寫入檢疫區: {rid}")
            logger.info(f"   診斷: {final_diagnosis}")
            logger.info(f"   症狀: {len(symptom_tags)} 個")
            logger.info(f"   收斂度: {rpcase_data['convergence_score']:.2f}")
            
            return {
                "success": True,
                "case_id": rid,
                "message": "已寫入檢疫區，等待驗證"
            }
            
        except Exception as e:
            logger.error(f"❌ RPCase 寫入失敗: {e}")
            return {
                "success": False,
                "case_id": None,
                "message": str(e)
            }
    
    # ==================== 升級到 Active ====================
    async def promote_to_active(self, rid: str) -> bool:
        """
        將案例從 Quarantine 升級到 Active
        
        條件：
        - 命中次數 ≥ 3
        - 正面反饋率 ≥ 80%
        """
        try:
            # 1. 查詢案例
            case = await self._get_case(rid)
            if not case:
                logger.warning(f"案例不存在: {rid}")
                return False
            
            # 2. 檢查狀態
            if case.get("status") != RPCaseStatus.QUARANTINE:
                logger.warning(f"案例狀態不是 QUARANTINE: {rid} ({case.get('status')})")
                return False
            
            # 3. 檢查升級條件
            hit_count = case.get("hit_count", 0)
            positive = case.get("positive_feedback", 0)
            negative = case.get("negative_feedback", 0)
            
            total_feedback = positive + negative
            
            if hit_count < 3:
                logger.info(f"⏳ 案例命中不足: {rid} ({hit_count}/3)")
                return False
            
            if total_feedback == 0:
                positive_rate = 0.0
            else:
                positive_rate = positive / total_feedback
            
            if positive_rate < 0.80:
                logger.info(f"⏳ 正面反饋率不足: {rid} ({positive_rate:.0%} < 80%)")
                return False
            
            # 4. 更新狀態
            await self._update_case_status(rid, RPCaseStatus.ACTIVE)
            
            logger.info(f"⬆️  案例升級到 Active: {rid}")
            logger.info(f"   命中: {hit_count} 次, 正面反饋: {positive_rate:.0%}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 升級案例失敗: {e}")
            return False
    
    # ==================== 降級到 Deprecated ====================
    async def deprecate_case(self, rid: str, reason: str = "") -> bool:
        """
        將案例降級到 Deprecated
        
        觸發條件：
        - 6個月無命中
        - 負面反饋 > 50%
        """
        try:
            await self._update_case_status(rid, RPCaseStatus.DEPRECATED)
            
            logger.info(f"⬇️  案例降級到 Deprecated: {rid}")
            logger.info(f"   原因: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 降級案例失敗: {e}")
            return False
    
    # ==================== 記錄命中 ====================
    async def record_hit(self, rid: str, positive: bool = True):
        """記錄案例命中與反饋"""
        try:
            case = await self._get_case(rid)
            if not case:
                return
            
            # 更新統計
            updates = {
                "hit_count": case.get("hit_count", 0) + 1,
                "last_hit_at": datetime.now().isoformat()
            }
            
            if positive:
                updates["positive_feedback"] = case.get("positive_feedback", 0) + 1
            else:
                updates["negative_feedback"] = case.get("negative_feedback", 0) + 1
            
            await self._update_case_properties(rid, updates)
            
            logger.info(f"📊 記錄命中: {rid} (正面={positive})")
            
        except Exception as e:
            logger.error(f"記錄命中失敗: {e}")
    
    # ==================== 定期維護任務 ====================
    async def run_maintenance(self):
        """
        運行定期維護任務
        
        1. 檢查 Quarantine 案例是否可升級
        2. 檢查 Active 案例是否應淘汰
        3. 清理 Deprecated 案例
        """
        logger.info("🔧 開始 RPCase 維護任務")
        
        try:
            # 1. 升級檢查
            quarantine_cases = await self._get_cases_by_status(RPCaseStatus.QUARANTINE)
            for case in quarantine_cases:
                await self.promote_to_active(case.get("rid", ""))
            
            # 2. 淘汰檢查
            active_cases = await self._get_cases_by_status(RPCaseStatus.ACTIVE)
            now = datetime.now()
            
            for case in active_cases:
                last_hit = case.get("last_hit_at")
                
                # 6個月無命中
                if last_hit:
                    try:
                        last_hit_date = datetime.fromisoformat(last_hit)
                        if (now - last_hit_date).days > 180:
                            await self.deprecate_case(
                                case.get("rid", ""),
                                reason="6個月無命中"
                            )
                    except Exception:
                        pass
                
                # 負面反饋過多
                positive = case.get("positive_feedback", 0)
                negative = case.get("negative_feedback", 0)
                total = positive + negative
                
                if total >= 10 and negative / total > 0.5:
                    await self.deprecate_case(
                        case.get("rid", ""),
                        reason="負面反饋超過50%"
                    )
            
            logger.info("✅ RPCase 維護任務完成")
            
        except Exception as e:
            logger.error(f"❌ 維護任務失敗: {e}")
    
    # ==================== 內部方法 ====================
    async def _get_case(self, rid: str) -> Optional[Dict]:
        """獲取案例詳情（兼容 v3 和 v4）"""
        try:
            if self.use_v4_api:
                # v4 API
                collection = self.client.collections.get(self.collection_name)
                result = collection.query.fetch_object_by_id(rid)
                return result.properties if result else None
            else:
                # v3 API
                result = self.client.data_object.get_by_id(
                    rid,
                    class_name=self.collection_name
                )
                return result.get("properties") if result else None
        except Exception as e:
            logger.error(f"獲取案例失敗: {e}")
            return None
    
    async def _update_case_status(self, rid: str, new_status: str):
        """更新案例狀態"""
        await self._update_case_properties(rid, {"status": new_status})
    
    async def _update_case_properties(self, rid: str, properties: Dict[str, Any]):
        """更新案例屬性（兼容 v3 和 v4）"""
        try:
            if self.use_v4_api:
                # v4 API
                collection = self.client.collections.get(self.collection_name)
                collection.data.update(
                    uuid=rid,
                    properties=properties
                )
            else:
                # v3 API
                self.client.data_object.update(
                    uuid=rid,
                    class_name=self.collection_name,
                    data_object=properties
                )
        except Exception as e:
            logger.error(f"更新案例失敗: {e}")
            raise
    
    async def _find_similar_case(
        self,
        content_hash: str,
        symptoms: List[str]
    ) -> Optional[Dict]:
        """查找相似案例（兼容 v3 和 v4）"""
        try:
            if self.use_v4_api:
                # v4 API
                collection = self.client.collections.get(self.collection_name)
                result = collection.query.fetch_objects(
                    filters={
                        "path": ["content_hash"],
                        "operator": "Equal",
                        "valueText": content_hash
                    },
                    limit=1
                )
                return result.objects[0].properties if result.objects else None
            else:
                # v3 API
                results = self.client.query.get(
                    self.collection_name,
                    ["rid", "content_hash", "convergence_score", "status"]
                ).with_where({
                    "path": ["content_hash"],
                    "operator": "Equal",
                    "valueText": content_hash
                }).with_limit(1).do()
                
                items = results.get("data", {}).get("Get", {}).get(self.collection_name, [])
                return items[0] if items else None
                
        except Exception as e:
            logger.warning(f"查找相似案例失敗: {e}")
            return None
    
    async def _get_cases_by_status(self, status: str) -> List[Dict]:
        """按狀態查詢案例（兼容 v3 和 v4）"""
        try:
            if self.use_v4_api:
                # v4 API
                collection = self.client.collections.get(self.collection_name)
                result = collection.query.fetch_objects(
                    filters={
                        "path": ["status"],
                        "operator": "Equal",
                        "valueText": status
                    },
                    limit=100
                )
                return [obj.properties for obj in result.objects]
            else:
                # v3 API
                results = self.client.query.get(
                    self.collection_name,
                    ["rid", "status", "hit_count", "positive_feedback", 
                     "negative_feedback", "last_hit_at", "convergence_score"]
                ).with_where({
                    "path": ["status"],
                    "operator": "Equal",
                    "valueText": status
                }).with_limit(100).do()
                
                return results.get("data", {}).get("Get", {}).get(self.collection_name, [])
                
        except Exception as e:
            logger.error(f"查詢案例失敗: {e}")
            return []
    
    async def _upgrade_case(self, old_rid: str, new_rid: str):
        """升級案例版本"""
        # 舊案例降級
        await self.deprecate_case(old_rid, reason=f"被新版本取代: {new_rid}")
    
    # ==================== 輔助方法 ====================
    def _generate_rid(self, session_id: str) -> str:
        """生成 RPCase ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"RP_{timestamp}_{session_id[:8]}"
    
    def _calculate_content_hash(
        self,
        diagnosis: str,
        symptoms: List[str],
        pulse_tags: List[str]
    ) -> str:
        """計算內容哈希"""
        content = f"{diagnosis}|{','.join(sorted(symptoms))}|{','.join(sorted(pulse_tags))}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _extract_symptoms(self, data: Dict) -> List[str]:
        """提取症狀標籤"""
        symptoms = []
        
        # 從對話歷史提取
        if "conversation_history" in data:
            for msg in data["conversation_history"]:
                if msg.get("from") == "user":
                    text = msg.get("text", "")
                    # 簡單關鍵詞提取
                    for keyword in ["失眠", "多夢", "心悸", "口乾", "咳嗽", "發熱", 
                                   "頭暈", "乏力", "腹痛", "便秘", "腹瀉"]:
                        if keyword in text and keyword not in symptoms:
                            symptoms.append(keyword)
        
        # 從診斷結果提取
        if "primary" in data and data["primary"]:
            primary_symptoms = data["primary"].get("primary_symptoms", [])
            if isinstance(primary_symptoms, list):
                symptoms.extend(primary_symptoms)
            
            hits = data["primary"].get("_hits", [])
            if isinstance(hits, list):
                symptoms.extend(hits)
        
        return list(set(symptoms))[:10]
    
    def _extract_pulse_tags(self, data: Dict) -> List[str]:
        """提取脈象標籤"""
        pulse_tags = []
        
        if "primary" in data and data["primary"]:
            pulse = data["primary"].get("pulse", "")
            if isinstance(pulse, str) and pulse:
                # 分割脈象（支持頓號、逗號）
                pulse_tags = pulse.replace("、", ",").split(",")
                pulse_tags = [p.strip() for p in pulse_tags if p.strip()][:3]
            elif isinstance(pulse, list):
                pulse_tags = pulse[:3]
        
        return pulse_tags
    
    def _build_search_text(self, data: Dict) -> str:
        """構建搜索文本"""
        parts = []
        
        if "diagnosis" in data:
            parts.append(str(data["diagnosis"]))
        
        symptoms = self._extract_symptoms(data)
        if symptoms:
            parts.append(" ".join(symptoms))
        
        pulse_tags = self._extract_pulse_tags(data)
        if pulse_tags:
            parts.append(" ".join(pulse_tags))
        
        return " ".join(parts)
    
    def clear_cache(self):
        """清除內存緩存"""
        self._cache.clear()
        logger.info("🗑️  清除 RPCase 緩存")
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        try:
            stats = {
                "quarantine_count": 0,
                "active_count": 0,
                "deprecated_count": 0,
                "total_count": 0
            }
            
            # 統計各狀態的案例數
            if self.use_v4_api:
                collection = self.client.collections.get(self.collection_name)
                # v4 API 統計邏輯
                # 簡化版：直接返回概估值
                stats["total_count"] = len(self._cache)
            else:
                # v3 API
                for status in [RPCaseStatus.QUARANTINE, RPCaseStatus.ACTIVE, RPCaseStatus.DEPRECATED]:
                    count = len(self._get_cases_by_status(status))
                    if status == RPCaseStatus.QUARANTINE:
                        stats["quarantine_count"] = count
                    elif status == RPCaseStatus.ACTIVE:
                        stats["active_count"] = count
                    elif status == RPCaseStatus.DEPRECATED:
                        stats["deprecated_count"] = count
                
                stats["total_count"] = (
                    stats["quarantine_count"] +
                    stats["active_count"] +
                    stats["deprecated_count"]
                )
            
            return stats
            
        except Exception as e:
            logger.error(f"獲取統計失敗: {e}")
            return {
                "quarantine_count": 0,
                "active_count": 0,
                "deprecated_count": 0,
                "total_count": 0,
                "error": str(e)
            }