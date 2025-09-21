"""
螺旋記憶庫 v2.0

管理S-CBR系統的多輪記憶存儲與檢索
支援會話學習記錄與知識積累

版本：v2.0 - 螺旋互動版
更新：多輪記憶存儲與會話數據整合
"""

from typing import Dict, Any, List, Optional, Union
import logging
import json
import uuid
from datetime import datetime, timedelta

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
    from ..utils.api_manager import SCBRAPIManager
    # Weaviate 向量數據庫（如果可用）
    import weaviate
    WEAVIATE_AVAILABLE = True
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    SCBRAPIManager = None
    WEAVIATE_AVAILABLE = False
    weaviate = None

class SpiralMemory:
    """
    螺旋記憶庫 v2.0
    
    v2.0 特色：
    - 會話級別記憶管理
    - 多輪推理學習記錄
    - 向量化記憶存儲
    - 智能記憶檢索
    - 記憶統計與分析
    """
    
    def __init__(self, weaviate_url: str = "http://localhost:8080"):
        """初始化螺旋記憶庫 v2.0"""
        self.logger = SpiralLogger.get_logger("SpiralMemory") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("SpiralMemory")
        self.version = "2.0"
        
        # 初始化相關組件
        self.api_manager = SCBRAPIManager() if SCBRAPIManager else None
        
        # 初始化向量數據庫連接
        self.weaviate_client = None
        self.memory_schema_created = False
        
        if WEAVIATE_AVAILABLE:
            try:
                self.weaviate_client = weaviate.Client(url=weaviate_url)
                self._initialize_memory_schema()
                self.logger.info("Weaviate 向量數據庫連接成功")
            except Exception as e:
                self.logger.warning(f"Weaviate 連接失敗，使用內存存儲: {str(e)}")
                self.weaviate_client = None
        
        # 內存存儲（降級方案）
        self.in_memory_store = {
            "session_memories": {},
            "case_memories": {},
            "diagnostic_memories": {},
            "treatment_memories": {},
            "learning_records": []
        }
        
        # v2.0 記憶參數
        self.memory_config = {
            "max_session_memories": 1000,
            "max_case_memories": 5000,
            "memory_retention_days": 30,
            "learning_record_limit": 2000,
            "similarity_threshold": 0.7
        }
        
        self.logger.info(f"螺旋記憶庫 v{self.version} 初始化完成")
    
    async def store_session_memory_v2(self, session_learning: Dict[str, Any]) -> bool:
        """
        存儲會話記憶 v2.0
        
        Args:
            session_learning: 會話學習記錄
            
        Returns:
            bool: 存儲是否成功
        """
        try:
            session_id = session_learning.get("session_id", "")
            memory_id = str(uuid.uuid4())
            
            self.logger.info(f"存儲會話記憶 v2.0 - Session: {session_id}")
            
            # 構建記憶對象
            memory_object = {
                "id": memory_id,
                "session_id": session_id,
                "memory_type": "session_learning",
                "content": session_learning,
                "timestamp": datetime.now().isoformat(),
                "version": self.version
            }
            
            # 添加向量化特徵
            memory_vector = await self._vectorize_session_memory(session_learning)
            memory_object["vector"] = memory_vector
            
            # 存儲到向量數據庫（如果可用）
            if self.weaviate_client:
                success = await self._store_to_weaviate(memory_object, "SessionMemory")
                if success:
                    self.logger.info(f"會話記憶存入 Weaviate: {memory_id}")
                    return True
            
            # 降級到內存存儲
            self.in_memory_store["session_memories"][memory_id] = memory_object
            self.logger.info(f"會話記憶存入內存: {memory_id}")
            
            # 定期清理舊記憶
            await self._cleanup_old_memories()
            
            return True
            
        except Exception as e:
            self.logger.error(f"存儲會話記憶失敗: {str(e)}")
            return False
    
    async def store_case_memory_v2(self, case_data: Dict[str, Any], usage_context: Dict[str, Any]) -> bool:
        """
        存儲案例記憶 v2.0
        
        Args:
            case_data: 案例數據
            usage_context: 使用上下文（會話信息、效果反饋等）
            
        Returns:
            bool: 存儲是否成功
        """
        try:
            case_id = case_data.get("id", str(uuid.uuid4()))
            memory_id = str(uuid.uuid4())
            
            self.logger.info(f"存儲案例記憶 v2.0 - Case: {case_id}")
            
            # 構建案例記憶對象
            case_memory = {
                "id": memory_id,
                "case_id": case_id,
                "memory_type": "case_usage",
                "case_data": case_data,
                "usage_context": usage_context,
                "usage_count": 1,
                "effectiveness_scores": [usage_context.get("effectiveness", 0.7)],
                "first_used": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat(),
                "version": self.version
            }
            
            # 檢查是否已存在該案例記憶
            existing_memory = await self._find_existing_case_memory(case_id)
            if existing_memory:
                # 更新現有記憶
                return await self._update_case_memory(existing_memory, usage_context)
            
            # 向量化案例記憶
            case_vector = await self._vectorize_case_memory(case_data, usage_context)
            case_memory["vector"] = case_vector
            
            # 存儲到數據庫
            if self.weaviate_client:
                success = await self._store_to_weaviate(case_memory, "CaseMemory")
                if success:
                    return True
            
            # 降級到內存存儲
            self.in_memory_store["case_memories"][memory_id] = case_memory
            return True
            
        except Exception as e:
            self.logger.error(f"存儲案例記憶失敗: {str(e)}")
            return False
    
    async def store_diagnostic_memory_v2(self, diagnostic_data: Dict[str, Any], session_context: Dict[str, Any]) -> bool:
        """
        存儲診斷記憶 v2.0
        
        Args:
            diagnostic_data: 診斷數據
            session_context: 會話上下文
            
        Returns:
            bool: 存儲是否成功
        """
        try:
            memory_id = str(uuid.uuid4())
            session_id = session_context.get("session_id", "")
            
            self.logger.info(f"存儲診斷記憶 v2.0 - Session: {session_id}")
            
            # 構建診斷記憶對象
            diagnostic_memory = {
                "id": memory_id,
                "session_id": session_id,
                "memory_type": "diagnostic_pattern",
                "diagnostic_data": diagnostic_data,
                "session_context": session_context,
                "diagnostic_confidence": diagnostic_data.get("diagnostic_confidence", 0.7),
                "timestamp": datetime.now().isoformat(),
                "version": self.version
            }
            
            # 向量化診斷記憶
            diagnostic_vector = await self._vectorize_diagnostic_memory(diagnostic_data, session_context)
            diagnostic_memory["vector"] = diagnostic_vector
            
            # 存儲處理
            if self.weaviate_client:
                success = await self._store_to_weaviate(diagnostic_memory, "DiagnosticMemory")
                if success:
                    return True
            
            # 內存存儲
            self.in_memory_store["diagnostic_memories"][memory_id] = diagnostic_memory
            return True
            
        except Exception as e:
            self.logger.error(f"存儲診斷記憶失敗: {str(e)}")
            return False
    
    async def retrieve_session_memories_v2(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        檢索會話記憶 v2.0
        
        Args:
            session_id: 會話ID
            limit: 返回數量限制
            
        Returns:
            List[Dict[str, Any]]: 會話記憶列表
        """
        try:
            self.logger.info(f"檢索會話記憶 v2.0 - Session: {session_id}")
            
            # 從向量數據庫檢索
            if self.weaviate_client:
                memories = await self._retrieve_from_weaviate(
                    "SessionMemory", 
                    {"session_id": session_id}, 
                    limit
                )
                if memories:
                    return memories
            
            # 從內存存儲檢索
            session_memories = []
            for memory_id, memory in self.in_memory_store["session_memories"].items():
                if memory.get("session_id") == session_id:
                    session_memories.append(memory)
            
            # 按時間戳排序，返回最近的記憶
            session_memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return session_memories[:limit]
            
        except Exception as e:
            self.logger.error(f"檢索會話記憶失敗: {str(e)}")
            return []
    
    async def find_similar_memories_v2(self, 
                                     query_vector: List[float], 
                                     memory_type: str = "all",
                                     limit: int = 5,
                                     similarity_threshold: float = None) -> List[Dict[str, Any]]:
        """
        查找相似記憶 v2.0
        
        Args:
            query_vector: 查詢向量
            memory_type: 記憶類型（all, session, case, diagnostic）
            limit: 返回數量限制
            similarity_threshold: 相似度閾值
            
        Returns:
            List[Dict[str, Any]]: 相似記憶列表
        """
        try:
            if similarity_threshold is None:
                similarity_threshold = self.memory_config["similarity_threshold"]
            
            self.logger.info(f"查找相似記憶 v2.0 - 類型: {memory_type}")
            
            # 向量數據庫相似性搜索
            if self.weaviate_client:
                similar_memories = await self._vector_similarity_search(
                    query_vector, memory_type, limit, similarity_threshold
                )
                if similar_memories:
                    return similar_memories
            
            # 內存存儲相似性搜索
            return await self._in_memory_similarity_search(
                query_vector, memory_type, limit, similarity_threshold
            )
            
        except Exception as e:
            self.logger.error(f"查找相似記憶失敗: {str(e)}")
            return []
    
    async def get_memory_stats_v2(self) -> Dict[str, Any]:
        """
        獲取記憶統計 v2.0
        
        Returns:
            Dict[str, Any]: 記憶統計信息
        """
        try:
            self.logger.info("獲取記憶統計 v2.0")
            
            # 從向量數據庫獲取統計
            if self.weaviate_client:
                weaviate_stats = await self._get_weaviate_stats()
                if weaviate_stats:
                    return weaviate_stats
            
            # 內存存儲統計
            memory_stats = {
                "total_memories": sum(len(store) for store in self.in_memory_store.values()),
                "session_memories_count": len(self.in_memory_store["session_memories"]),
                "case_memories_count": len(self.in_memory_store["case_memories"]),
                "diagnostic_memories_count": len(self.in_memory_store["diagnostic_memories"]),
                "treatment_memories_count": len(self.in_memory_store["treatment_memories"]),
                "learning_records_count": len(self.in_memory_store["learning_records"]),
                "storage_type": "in_memory",
                "last_updated": datetime.now().isoformat(),
                "version": self.version
            }
            
            # 計算平均會話歷史
            memory_stats["average_session_history"] = await self._calculate_average_session_history()
            
            # 記憶質量分析
            memory_stats["memory_quality"] = await self._analyze_memory_quality()
            
            return memory_stats
            
        except Exception as e:
            self.logger.error(f"獲取記憶統計失敗: {str(e)}")
            return {
                "total_memories": 0,
                "storage_type": "error",
                "error": str(e),
                "version": self.version
            }
    
    async def store_learning_record_v2(self, learning_data: Dict[str, Any]) -> bool:
        """
        存儲學習記錄 v2.0
        
        Args:
            learning_data: 學習數據
            
        Returns:
            bool: 存儲是否成功
        """
        try:
            record_id = str(uuid.uuid4())
            
            learning_record = {
                "id": record_id,
                "learning_data": learning_data,
                "timestamp": datetime.now().isoformat(),
                "version": self.version
            }
            
            # 向量數據庫存儲
            if self.weaviate_client:
                success = await self._store_to_weaviate(learning_record, "LearningRecord")
                if success:
                    return True
            
            # 內存存儲
            self.in_memory_store["learning_records"].append(learning_record)
            
            # 限制學習記錄數量
            if len(self.in_memory_store["learning_records"]) > self.memory_config["learning_record_limit"]:
                self.in_memory_store["learning_records"] = self.in_memory_store["learning_records"][-self.memory_config["learning_record_limit"]:]
            
            return True
            
        except Exception as e:
            self.logger.error(f"存儲學習記錄失敗: {str(e)}")
            return False
    
    async def cleanup_expired_memories_v2(self) -> Dict[str, int]:
        """
        清理過期記憶 v2.0
        
        Returns:
            Dict[str, int]: 清理統計
        """
        try:
            self.logger.info("清理過期記憶 v2.0")
            
            cleanup_stats = {
                "session_memories_cleaned": 0,
                "case_memories_cleaned": 0,
                "diagnostic_memories_cleaned": 0,
                "total_cleaned": 0
            }
            
            # 計算過期時間
            expiry_date = datetime.now() - timedelta(days=self.memory_config["memory_retention_days"])
            expiry_timestamp = expiry_date.isoformat()
            
            # 向量數據庫清理
            if self.weaviate_client:
                weaviate_cleanup = await self._cleanup_weaviate_memories(expiry_timestamp)
                if weaviate_cleanup:
                    return weaviate_cleanup
            
            # 內存存儲清理
            cleanup_stats = await self._cleanup_in_memory_store(expiry_timestamp)
            
            self.logger.info(f"記憶清理完成: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"清理過期記憶失敗: {str(e)}")
            return {"error": str(e), "total_cleaned": 0}
    
    # 輔助方法實現
    def _initialize_memory_schema(self):
        """初始化記憶數據結構"""
        if not self.weaviate_client:
            return
        
        try:
            # 檢查 schema 是否已存在
            existing_schema = self.weaviate_client.schema.get()
            class_names = [cls["class"] for cls in existing_schema.get("classes", [])]
            
            # 定義記憶類別 schema
            memory_classes = [
                {
                    "class": "SessionMemory",
                    "description": "會話學習記憶",
                    "properties": [
                        {"name": "session_id", "dataType": ["string"]},
                        {"name": "memory_type", "dataType": ["string"]},
                        {"name": "content", "dataType": ["text"]},
                        {"name": "timestamp", "dataType": ["date"]}
                    ]
                },
                {
                    "class": "CaseMemory",
                    "description": "案例使用記憶",
                    "properties": [
                        {"name": "case_id", "dataType": ["string"]},
                        {"name": "usage_count", "dataType": ["int"]},
                        {"name": "effectiveness_score", "dataType": ["number"]},
                        {"name": "last_used", "dataType": ["date"]}
                    ]
                },
                {
                    "class": "DiagnosticMemory",
                    "description": "診斷模式記憶",
                    "properties": [
                        {"name": "session_id", "dataType": ["string"]},
                        {"name": "diagnostic_confidence", "dataType": ["number"]},
                        {"name": "timestamp", "dataType": ["date"]}
                    ]
                },
                {
                    "class": "LearningRecord",
                    "description": "學習記錄",
                    "properties": [
                        {"name": "learning_type", "dataType": ["string"]},
                        {"name": "timestamp", "dataType": ["date"]}
                    ]
                }
            ]
            
            # 創建不存在的 schema
            for memory_class in memory_classes:
                if memory_class["class"] not in class_names:
                    self.weaviate_client.schema.create_class(memory_class)
                    self.logger.info(f"創建記憶 schema: {memory_class['class']}")
            
            self.memory_schema_created = True
            
        except Exception as e:
            self.logger.error(f"初始化記憶 schema 失敗: {str(e)}")
            self.memory_schema_created = False
    
    async def _vectorize_session_memory(self, session_learning: Dict[str, Any]) -> List[float]:
        """向量化會話記憶"""
        # 簡化實現：基於關鍵信息生成向量
        try:
            # 提取關鍵特徵
            features = []
            features.append(session_learning.get("total_rounds", 1) / 10)  # 標準化輪次
            features.append(session_learning.get("final_effectiveness", 0.7))
            features.append(len(session_learning.get("used_cases", [])) / 10)  # 標準化案例數
            features.append(session_learning.get("learning_value", 0.7))
            
            # 填充到固定長度（128維）
            while len(features) < 128:
                features.append(0.0)
            
            return features[:128]
            
        except Exception:
            # 降級：返回隨機向量
            import random
            return [random.random() for _ in range(128)]
    
    async def _vectorize_case_memory(self, case_data: Dict[str, Any], usage_context: Dict[str, Any]) -> List[float]:
        """向量化案例記憶"""
        try:
            features = []
            features.append(case_data.get("similarity", 0.7))
            features.append(case_data.get("quality_score", 0.7))
            features.append(usage_context.get("effectiveness", 0.7))
            features.append(usage_context.get("round", 1) / 10)
            
            # 症狀特徵（簡化）
            symptoms = case_data.get("symptoms", [])
            symptom_vector = [1.0 if i < len(symptoms) else 0.0 for i in range(20)]
            features.extend(symptom_vector)
            
            # 填充到128維
            while len(features) < 128:
                features.append(0.0)
            
            return features[:128]
            
        except Exception:
            import random
            return [random.random() for _ in range(128)]
    
    async def _vectorize_diagnostic_memory(self, diagnostic_data: Dict[str, Any], session_context: Dict[str, Any]) -> List[float]:
        """向量化診斷記憶"""
        try:
            features = []
            features.append(diagnostic_data.get("diagnostic_confidence", 0.7))
            features.append(session_context.get("round", 1) / 10)
            features.append(len(session_context.get("used_cases", [])) / 10)
            
            # 診斷特徵
            syndrome = diagnostic_data.get("syndrome_differentiation", "")
            syndrome_features = [1.0 if keyword in syndrome else 0.0 for keyword in 
                               ["氣虛", "血瘀", "陰虛", "陽虛", "氣滯", "痰濕", "熱證", "寒證"]]
            features.extend(syndrome_features)
            
            # 填充到128維
            while len(features) < 128:
                features.append(0.0)
            
            return features[:128]
            
        except Exception:
            import random
            return [random.random() for _ in range(128)]
    
    async def _store_to_weaviate(self, memory_object: Dict[str, Any], class_name: str) -> bool:
        """存儲到 Weaviate"""
        if not self.weaviate_client or not self.memory_schema_created:
            return False
        
        try:
            # 準備數據
            properties = memory_object.copy()
            vector = properties.pop("vector", [])
            
            # 存儲到 Weaviate
            result = self.weaviate_client.data_object.create(
                data_object=properties,
                class_name=class_name,
                vector=vector
            )
            
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Weaviate 存儲失敗: {str(e)}")
            return False
    
    async def _retrieve_from_weaviate(self, class_name: str, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """從 Weaviate 檢索"""
        if not self.weaviate_client:
            return []
        
        try:
            # 構建查詢
            query = (
                self.weaviate_client.query
                .get(class_name)
                .with_limit(limit)
            )
            
            # 添加過濾條件
            if filters:
                where_filter = {}
                for key, value in filters.items():
                    where_filter = {
                        "path": [key],
                        "operator": "Equal",
                        "valueString": value
                    }
                query = query.with_where(where_filter)
            
            # 執行查詢
            result = query.do()
            
            if result and "data" in result and "Get" in result["data"]:
                return result["data"]["Get"][class_name]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Weaviate 檢索失敗: {str(e)}")
            return []
    
    async def _vector_similarity_search(self, query_vector: List[float], memory_type: str, limit: int, threshold: float) -> List[Dict[str, Any]]:
        """向量相似性搜索"""
        if not self.weaviate_client:
            return []
        
        try:
            # 確定搜索的類別
            class_names = []
            if memory_type == "all":
                class_names = ["SessionMemory", "CaseMemory", "DiagnosticMemory"]
            elif memory_type == "session":
                class_names = ["SessionMemory"]
            elif memory_type == "case":
                class_names = ["CaseMemory"]
            elif memory_type == "diagnostic":
                class_names = ["DiagnosticMemory"]
            
            similar_memories = []
            
            for class_name in class_names:
                # 向量搜索
                query = (
                    self.weaviate_client.query
                    .get(class_name)
                    .with_near_vector({"vector": query_vector})
                    .with_limit(limit)
                    .with_additional(["certainty"])
                )
                
                result = query.do()
                
                if result and "data" in result and "Get" in result["data"]:
                    memories = result["data"]["Get"][class_name]
                    # 過濾相似度閾值
                    for memory in memories:
                        if memory.get("_additional", {}).get("certainty", 0) >= threshold:
                            similar_memories.append(memory)
            
            # 按相似度排序
            similar_memories.sort(key=lambda x: x.get("_additional", {}).get("certainty", 0), reverse=True)
            
            return similar_memories[:limit]
            
        except Exception as e:
            self.logger.error(f"向量相似性搜索失敗: {str(e)}")
            return []
    
    async def _in_memory_similarity_search(self, query_vector: List[float], memory_type: str, limit: int, threshold: float) -> List[Dict[str, Any]]:
        """內存相似性搜索"""
        try:
            similar_memories = []
            
            # 確定搜索範圍
            search_stores = []
            if memory_type == "all":
                search_stores = ["session_memories", "case_memories", "diagnostic_memories"]
            elif memory_type == "session":
                search_stores = ["session_memories"]
            elif memory_type == "case":
                search_stores = ["case_memories"]
            elif memory_type == "diagnostic":
                search_stores = ["diagnostic_memories"]
            
            # 搜索每個存儲
            for store_name in search_stores:
                store = self.in_memory_store[store_name]
                for memory_id, memory in store.items():
                    memory_vector = memory.get("vector", [])
                    if memory_vector:
                        # 計算餘弦相似度
                        similarity = self._calculate_cosine_similarity(query_vector, memory_vector)
                        if similarity >= threshold:
                            memory_copy = memory.copy()
                            memory_copy["similarity"] = similarity
                            similar_memories.append(memory_copy)
            
            # 按相似度排序
            similar_memories.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            
            return similar_memories[:limit]
            
        except Exception as e:
            self.logger.error(f"內存相似性搜索失敗: {str(e)}")
            return []
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """計算餘弦相似度"""
        try:
            # 確保向量長度相同
            min_len = min(len(vec1), len(vec2))
            vec1 = vec1[:min_len]
            vec2 = vec2[:min_len]
            
            # 計算點積
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # 計算向量的模
            norm_vec1 = sum(a * a for a in vec1) ** 0.5
            norm_vec2 = sum(b * b for b in vec2) ** 0.5
            
            # 避免除零
            if norm_vec1 == 0 or norm_vec2 == 0:
                return 0.0
            
            # 餘弦相似度
            similarity = dot_product / (norm_vec1 * norm_vec2)
            
            return max(0.0, min(1.0, similarity))
            
        except Exception:
            return 0.0
    
    async def _find_existing_case_memory(self, case_id: str) -> Optional[Dict[str, Any]]:
        """查找已存在的案例記憶"""
        # 從內存存儲查找
        for memory_id, memory in self.in_memory_store["case_memories"].items():
            if memory.get("case_id") == case_id:
                return memory
        
        return None
    
    async def _update_case_memory(self, existing_memory: Dict[str, Any], usage_context: Dict[str, Any]) -> bool:
        """更新案例記憶"""
        try:
            # 更新使用次數
            existing_memory["usage_count"] = existing_memory.get("usage_count", 0) + 1
            
            # 更新效果評分
            effectiveness_scores = existing_memory.get("effectiveness_scores", [])
            effectiveness_scores.append(usage_context.get("effectiveness", 0.7))
            existing_memory["effectiveness_scores"] = effectiveness_scores
            
            # 更新最後使用時間
            existing_memory["last_used"] = datetime.now().isoformat()
            
            return True
            
        except Exception as e:
            self.logger.error(f"更新案例記憶失敗: {str(e)}")
            return False
    
    async def _calculate_average_session_history(self) -> float:
        """計算平均會話歷史"""
        try:
            session_memories = self.in_memory_store["session_memories"]
            if not session_memories:
                return 0.0
            
            total_rounds = 0
            session_count = 0
            
            for memory in session_memories.values():
                content = memory.get("content", {})
                rounds = content.get("total_rounds", 1)
                total_rounds += rounds
                session_count += 1
            
            return total_rounds / session_count if session_count > 0 else 0.0
            
        except Exception:
            return 0.0
    
    async def _analyze_memory_quality(self) -> Dict[str, float]:
        """分析記憶質量"""
        try:
            quality_analysis = {
                "session_memory_quality": 0.8,
                "case_memory_quality": 0.75,
                "diagnostic_memory_quality": 0.85,
                "overall_quality": 0.8
            }
            
            # 簡化實現：基於記憶數量和時間分佈
            total_memories = sum(len(store) for store in self.in_memory_store.values())
            
            if total_memories > 100:
                quality_analysis["overall_quality"] = 0.85
            elif total_memories > 50:
                quality_analysis["overall_quality"] = 0.8
            else:
                quality_analysis["overall_quality"] = 0.75
            
            return quality_analysis
            
        except Exception:
            return {"overall_quality": 0.7}
    
    async def _cleanup_old_memories(self):
        """清理舊記憶"""
        try:
            # 檢查記憶數量限制
            for store_name, store in self.in_memory_store.items():
                if store_name == "learning_records":
                    continue  # 學習記錄已單獨處理
                
                max_memories = {
                    "session_memories": self.memory_config["max_session_memories"],
                    "case_memories": self.memory_config["max_case_memories"],
                    "diagnostic_memories": 1000,
                    "treatment_memories": 1000
                }.get(store_name, 1000)
                
                if len(store) > max_memories:
                    # 按時間戳排序，保留最新的記憶
                    sorted_memories = sorted(
                        store.items(), 
                        key=lambda x: x[1].get("timestamp", ""), 
                        reverse=True
                    )
                    
                    # 保留前 max_memories 個記憶
                    kept_memories = dict(sorted_memories[:max_memories])
                    self.in_memory_store[store_name] = kept_memories
                    
                    self.logger.info(f"清理 {store_name}: {len(store)} -> {len(kept_memories)}")
                    
        except Exception as e:
            self.logger.error(f"清理舊記憶失敗: {str(e)}")
    
    async def _get_weaviate_stats(self) -> Optional[Dict[str, Any]]:
        """獲取 Weaviate 統計"""
        if not self.weaviate_client:
            return None
        
        try:
            # 獲取各類別的數量
            stats = {"storage_type": "weaviate"}
            
            class_names = ["SessionMemory", "CaseMemory", "DiagnosticMemory", "LearningRecord"]
            total_count = 0
            
            for class_name in class_names:
                try:
                    result = (
                        self.weaviate_client.query
                        .aggregate(class_name)
                        .with_meta_count()
                        .do()
                    )
                    
                    count = result["data"]["Aggregate"][class_name][0]["meta"]["count"]
                    stats[f"{class_name.lower()}_count"] = count
                    total_count += count
                    
                except Exception:
                    stats[f"{class_name.lower()}_count"] = 0
            
            stats["total_memories"] = total_count
            stats["last_updated"] = datetime.now().isoformat()
            stats["version"] = self.version
            
            return stats
            
        except Exception as e:
            self.logger.error(f"獲取 Weaviate 統計失敗: {str(e)}")
            return None
    
    async def _cleanup_weaviate_memories(self, expiry_timestamp: str) -> Optional[Dict[str, int]]:
        """清理 Weaviate 中的過期記憶"""
        if not self.weaviate_client:
            return None
        
        try:
            cleanup_stats = {
                "session_memories_cleaned": 0,
                "case_memories_cleaned": 0,
                "diagnostic_memories_cleaned": 0,
                "total_cleaned": 0
            }
            
            class_names = ["SessionMemory", "CaseMemory", "DiagnosticMemory"]
            
            for class_name in class_names:
                # 構建刪除查詢
                where_filter = {
                    "path": ["timestamp"],
                    "operator": "LessThan",
                    "valueString": expiry_timestamp
                }
                
                # 執行批量刪除
                result = (
                    self.weaviate_client.batch
                    .delete_objects(
                        class_name=class_name,
                        where=where_filter
                    )
                )
                
                deleted_count = result.get("results", {}).get("successful", 0)
                cleanup_stats[f"{class_name.lower()}_cleaned"] = deleted_count
                cleanup_stats["total_cleaned"] += deleted_count
            
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"Weaviate 記憶清理失敗: {str(e)}")
            return None
    
    async def _cleanup_in_memory_store(self, expiry_timestamp: str) -> Dict[str, int]:
        """清理內存存儲中的過期記憶"""
        cleanup_stats = {
            "session_memories_cleaned": 0,
            "case_memories_cleaned": 0,
            "diagnostic_memories_cleaned": 0,
            "total_cleaned": 0
        }
        
        try:
            for store_name, store in self.in_memory_store.items():
                if store_name == "learning_records":
                    continue
                
                # 過濾過期記憶
                original_count = len(store)
                filtered_store = {
                    memory_id: memory for memory_id, memory in store.items()
                    if memory.get("timestamp", "") > expiry_timestamp
                }
                
                self.in_memory_store[store_name] = filtered_store
                cleaned_count = original_count - len(filtered_store)
                
                if store_name in ["session_memories", "case_memories", "diagnostic_memories"]:
                    cleanup_stats[f"{store_name}_cleaned"] = cleaned_count
                
                cleanup_stats["total_cleaned"] += cleaned_count
            
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"內存記憶清理失敗: {str(e)}")
            return cleanup_stats
    
    # 向後兼容方法（v1.0）
    async def store_memory(self, memory_data: Dict[str, Any], memory_type: str = "general") -> bool:
        """向後兼容的記憶存儲"""
        if memory_type == "session":
            return await self.store_session_memory_v2(memory_data)
        else:
            return await self.store_learning_record_v2(memory_data)
    
    async def retrieve_memories(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """向後兼容的記憶檢索"""
        # 簡化實現：返回最近的會話記憶
        all_session_memories = []
        for memory in self.in_memory_store["session_memories"].values():
            all_session_memories.append(memory)
        
        # 按時間排序
        all_session_memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_session_memories[:limit]
    
    async def get_memory_statistics(self) -> Dict[str, Any]:
        """向後兼容的記憶統計"""
        return await self.get_memory_stats_v2()

# 向後兼容的類別名稱
SpiralMemoryV2 = SpiralMemory

__all__ = ["SpiralMemory", "SpiralMemoryV2"]