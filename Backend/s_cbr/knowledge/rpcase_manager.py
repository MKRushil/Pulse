"""
RPCase 回饋案例管理器 v2.0

管理螺旋推理回饋案例的儲存、檢索和向量化
- 支援 Weaviate 向量資料庫
- 與 Case、PulsePJ 並列的第三個知識庫
- 提供案例儲存、相似度檢索等功能
"""

import weaviate
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

try:
    from ..utils.spiral_logger import SpiralLogger
    logger = SpiralLogger.get_logger("RPCaseManager")
except ImportError:
    logger = logging.getLogger("RPCaseManager")

try:
    from ..config.scbr_config import SCBRConfig
except ImportError:
    logger.warning("無法載入 SCBRConfig，使用預設配置")
    SCBRConfig = None

class RPCaseManager:
    """
    RPCase 回饋案例管理器
    
    負責管理螺旋推理產生的回饋案例：
    - 案例向量化與儲存
    - 相似案例檢索
    - 案例統計與分析
    - 案例品質評估
    """
    
    def __init__(self, weaviate_client: Optional[weaviate.Client] = None):
        """初始化 RPCase 管理器"""
        self.logger = logger
        self.config = SCBRConfig() if SCBRConfig else None
        
        # Weaviate 客戶端
        if weaviate_client:
            self.client = weaviate_client
        else:
            self.client = self._init_weaviate_client()
        
        # 初始化 Schema
        self._ensure_rpcase_schema()
        
        self.logger.info("RPCase 管理器 v2.0 初始化完成")
    
    def _init_weaviate_client(self) -> Optional[weaviate.Client]:
        """初始化 Weaviate 客戶端"""
        try:
            if self.config:
                db_config = self.config.get_database_config()
                weaviate_url = db_config.weaviate_url
                timeout = db_config.weaviate_timeout
            else:
                weaviate_url = "http://localhost:8080"
                timeout = 30
            
            client = weaviate.Client(
                url=weaviate_url,
                timeout_config=(timeout, timeout)
            )
            
            # 測試連接
            client.schema.get()
            self.logger.info(f"✅ Weaviate 客戶端連接成功: {weaviate_url}")
            return client
            
        except Exception as e:
            self.logger.error(f"❌ Weaviate 客戶端初始化失敗: {e}")
            return None
    
    def _ensure_rpcase_schema(self):
        """確保 RPCase Schema 存在"""
        if not self.client:
            self.logger.warning("Weaviate 客戶端不可用，跳過 Schema 檢查")
            return
        
        try:
            # 檢查 Schema 是否存在
            schema = self.client.schema.get()
            existing_classes = [cls['class'] for cls in schema.get('classes', [])]
            
            if 'RPCase' not in existing_classes:
                self.logger.info("創建 RPCase Schema...")
                self._create_rpcase_schema()
            else:
                self.logger.info("RPCase Schema 已存在")
                
        except Exception as e:
            self.logger.error(f"RPCase Schema 檢查失敗: {e}")
    
    def _create_rpcase_schema(self):
        """創建 RPCase Schema"""
        rpcase_schema = {
            "class": "RPCase",
            "description": "螺旋推理回饋案例知識庫",
            "vectorizer": "none",  # 使用外部向量
            "properties": [
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
                {"name": "source_type", "dataType": ["string"], "description": "來源類型"}
            ]
        }
        
        try:
            self.client.schema.create_class(rpcase_schema)
            self.logger.info("✅ RPCase Schema 創建成功")
        except Exception as e:
            self.logger.error(f"RPCase Schema 創建失敗: {e}")
            raise
    
    async def save_rpcase(self, rpcase_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        儲存回饋案例到 RPCase 知識庫
        
        Args:
            rpcase_data: 回饋案例數據
            
        Returns:
            Dict: 儲存結果
        """
        if not self.client:
            raise Exception("Weaviate 客戶端不可用")
        
        try:
            # 生成向量 (這裡需要實現向量化邏輯)
            vector = await self._generate_case_vector(rpcase_data)
            
            # 準備數據對象
            data_object = {
                "rpcase_id": rpcase_data.get("rpcase_id"),
                "original_question": rpcase_data.get("original_question", ""),
                "patient_context": rpcase_data.get("patient_context", ""),
                "spiral_rounds": int(rpcase_data.get("spiral_rounds", 1)),
                "used_cases": rpcase_data.get("used_cases", []),
                "final_diagnosis": rpcase_data.get("final_diagnosis", ""),
                "treatment_plan": rpcase_data.get("treatment_plan", ""),
                "reasoning_process": rpcase_data.get("reasoning_process", ""),
                "user_feedback": rpcase_data.get("user_feedback", ""),
                "effectiveness_score": float(rpcase_data.get("effectiveness_score", 0.8)),
                "confidence_score": float(rpcase_data.get("confidence_score", 0.8)),
                "safety_score": float(rpcase_data.get("safety_score", 0.8)),
                "session_id": rpcase_data.get("session_id", ""),
                "conversation_history": rpcase_data.get("conversation_history", ""),
                "created_timestamp": rpcase_data.get("created_timestamp", datetime.now().isoformat()),
                "updated_timestamp": rpcase_data.get("updated_timestamp", datetime.now().isoformat()),
                "tags": rpcase_data.get("tags", []),
                "complexity_level": int(rpcase_data.get("complexity_level", 1)),
                "success_rate": float(rpcase_data.get("success_rate", 1.0)),
                "reuse_count": int(rpcase_data.get("reuse_count", 0)),
                "source_type": rpcase_data.get("source_type", "spiral_feedback")
            }
            
            # 儲存到 Weaviate
            result = self.client.data_object.create(
                data_object=data_object,
                class_name="RPCase",
                vector=vector
            )
            
            self.logger.info(f"✅ RPCase 儲存成功: {rpcase_data.get('rpcase_id')}")
            
            return {
                "success": True,
                "rpcase_id": rpcase_data.get("rpcase_id"),
                "weaviate_id": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"RPCase 儲存失敗: {str(e)}")
            raise
    
    async def _generate_case_vector(self, rpcase_data: Dict[str, Any]) -> List[float]:
        """
        生成案例向量
        
        TODO: 實現向量化邏輯
        - 可以使用 OpenAI Embeddings
        - 或其他向量化模型
        - 結合診斷、治療方案、推理過程等文本
        """
        try:
            # 合併關鍵文本用於向量化
            text_content = " ".join([
                rpcase_data.get("original_question", ""),
                rpcase_data.get("final_diagnosis", ""),
                rpcase_data.get("treatment_plan", ""),
                rpcase_data.get("reasoning_process", "")[:500]  # 限制長度
            ])
            
            # 暫時返回隨機向量 (生產環境需要實際實現)
            import random
            vector_dim = 1536  # OpenAI embedding dimension
            vector = [random.random() for _ in range(vector_dim)]
            
            self.logger.debug(f"為案例生成 {vector_dim} 維向量")
            return vector
            
        except Exception as e:
            self.logger.error(f"向量生成失敗: {str(e)}")
            # 返回零向量作為降級
            return [0.0] * 1536
    
    async def search_similar_rpcases(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        檢索相似的回饋案例
        
        Args:
            query_text: 查詢文本
            limit: 返回數量限制
            
        Returns:
            List[Dict]: 相似案例列表
        """
        if not self.client:
            return []
        
        try:
            # 生成查詢向量
            query_vector = await self._generate_query_vector(query_text)
            
            # 向量搜尋
            result = (
                self.client.query
                .get("RPCase", [
                    "rpcase_id", "original_question", "final_diagnosis",
                    "treatment_plan", "effectiveness_score", "confidence_score",
                    "spiral_rounds", "created_timestamp", "tags"
                ])
                .with_near_vector({
                    "vector": query_vector,
                    "certainty": 0.7  # 相似度閾值
                })
                .with_limit(limit)
                .do()
            )
            
            cases = result.get("data", {}).get("Get", {}).get("RPCase", [])
            self.logger.info(f"檢索到 {len(cases)} 個相似的回饋案例")
            
            return cases
            
        except Exception as e:
            self.logger.error(f"相似案例檢索失敗: {str(e)}")
            return []
    
    async def _generate_query_vector(self, query_text: str) -> List[float]:
        """生成查詢向量"""
        # 暫時實現，實際應該使用與儲存時相同的向量化方法
        import random
        return [random.random() for _ in range(1536)]
    
    def get_rpcase_stats(self) -> Dict[str, Any]:
        """獲取 RPCase 統計資訊"""
        if not self.client:
            return {"error": "Weaviate 客戶端不可用"}
        
        try:
            # 獲取案例總數
            result = (
                self.client.query
                .aggregate("RPCase")
                .with_meta_count()
                .do()
            )
            
            total_cases = result.get("data", {}).get("Aggregate", {}).get("RPCase", [{}])[0].get("meta", {}).get("count", 0)
            
            # 獲取平均評分等統計
            stats_result = (
                self.client.query
                .aggregate("RPCase")
                .with_fields("effectiveness_score { mean } confidence_score { mean } safety_score { mean }")
                .do()
            )
            
            aggregates = stats_result.get("data", {}).get("Aggregate", {}).get("RPCase", [{}])[0]
            
            return {
                "total_rpcases": total_cases,
                "avg_effectiveness": aggregates.get("effectiveness_score", {}).get("mean", 0.0),
                "avg_confidence": aggregates.get("confidence_score", {}).get("mean", 0.0),
                "avg_safety": aggregates.get("safety_score", {}).get("mean", 0.0),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"RPCase 統計獲取失敗: {str(e)}")
            return {"error": str(e)}

# 導出
__all__ = ["RPCaseManager"]
