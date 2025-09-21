"""
脈診知識庫 v2.0

管理 S-CBR 系統中的脈診相關數據與檢索
支援脈診模式匹配與診斷輔助

版本：v2.0 - 螺旋互動版
更新：脈診數據向量化與智能檢索
"""

from typing import Dict, Any, List, Optional
import logging
import json
import uuid
from datetime import datetime

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

class PulseRepository:
    """
    脈診知識庫 v2.0
    
    v2.0 特色：
    - 脈診模式智能匹配
    - 向量化脈診存儲
    - 症狀脈象關聯分析
    - 脈診診斷輔助
    """
    
    def __init__(self, weaviate_url: str = "http://localhost:8080"):
        """初始化脈診知識庫 v2.0"""
        self.logger = SpiralLogger.get_logger("PulseRepository") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("PulseRepository")
        self.version = "2.0"
        
        # 初始化相關組件
        self.api_manager = SCBRAPIManager() if SCBRAPIManager else None
        
        # 初始化向量數據庫連接
        self.weaviate_client = None
        self.pulse_schema_created = False
        
        if WEAVIATE_AVAILABLE:
            try:
                self.weaviate_client = weaviate.Client(url=weaviate_url)
                self._initialize_pulse_schema()
                self.logger.info("Weaviate 脈診數據庫連接成功")
            except Exception as e:
                self.logger.warning(f"Weaviate 連接失敗，使用內存存儲: {str(e)}")
                self.weaviate_client = None
        
        # 內存存儲（降級方案）
        self.pulse_data_store = {
            "pulse_patterns": {},
            "pulse_symptoms": {},
            "pulse_diagnoses": {},
            "pulse_treatments": {}
        }
        
        # v2.0 脈診參數
        self.pulse_config = {
            "max_pulse_patterns": 2000,
            "similarity_threshold": 0.75,
            "pulse_weight": 0.6,
            "symptom_weight": 0.4
        }
        
        # 載入預設脈診數據
        self._load_default_pulse_data()
        
        self.logger.info(f"脈診知識庫 v{self.version} 初始化完成")
    
    async def search_similar_pulses_v2(self, pulse_description: str, symptoms: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索相似脈診 v2.0
        
        Args:
            pulse_description: 脈診描述
            symptoms: 伴隨症狀列表
            limit: 返回數量限制
            
        Returns:
            List[Dict[str, Any]]: 相似脈診列表
        """
        try:
            self.logger.info(f"搜索相似脈診 v2.0 - 描述: {pulse_description}")
            
            # 構建查詢向量
            query_vector = await self._vectorize_pulse_query(pulse_description, symptoms or [])
            
            # 從向量數據庫搜索
            if self.weaviate_client:
                similar_pulses = await self._search_pulse_weaviate(query_vector, limit)
                if similar_pulses:
                    return similar_pulses
            
            # 降級到內存搜索
            return await self._search_pulse_memory(pulse_description, symptoms or [], limit)
            
        except Exception as e:
            self.logger.error(f"搜索相似脈診失敗: {str(e)}")
            return []
    
    async def get_pulse_diagnosis_v2(self, pulse_pattern: Dict[str, Any], patient_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        獲取脈診診斷 v2.0
        
        Args:
            pulse_pattern: 脈診模式
            patient_context: 患者上下文
            
        Returns:
            Dict[str, Any]: 診斷結果
        """
        try:
            self.logger.info("獲取脈診診斷 v2.0")
            
            # 分析脈診模式
            pulse_analysis = await self._analyze_pulse_pattern(pulse_pattern)
            
            # 結合患者上下文
            if patient_context:
                pulse_analysis = await self._integrate_patient_context(pulse_analysis, patient_context)
            
            # 生成診斷建議
            diagnosis = await self._generate_pulse_diagnosis(pulse_analysis)
            
            return {
                "pulse_analysis": pulse_analysis,
                "primary_diagnosis": diagnosis.get("primary", ""),
                "secondary_diagnoses": diagnosis.get("secondary", []),
                "confidence": diagnosis.get("confidence", 0.7),
                "recommendations": diagnosis.get("recommendations", []),
                "version": self.version
            }
            
        except Exception as e:
            self.logger.error(f"獲取脈診診斷失敗: {str(e)}")
            return {"error": str(e), "confidence": 0.0}
    
    async def store_pulse_pattern_v2(self, pulse_data: Dict[str, Any]) -> bool:
        """
        存儲脈診模式 v2.0
        
        Args:
            pulse_data: 脈診數據
            
        Returns:
            bool: 存儲是否成功
        """
        try:
            pulse_id = str(uuid.uuid4())
            
            pulse_record = {
                "id": pulse_id,
                "pulse_pattern": pulse_data.get("pattern", ""),
                "symptoms": pulse_data.get("symptoms", []),
                "diagnosis": pulse_data.get("diagnosis", ""),
                "treatment": pulse_data.get("treatment", ""),
                "effectiveness": pulse_data.get("effectiveness", 0.7),
                "timestamp": datetime.now().isoformat(),
                "version": self.version
            }
            
            # 向量化脈診數據
            pulse_vector = await self._vectorize_pulse_data(pulse_data)
            pulse_record["vector"] = pulse_vector
            
            # 存儲到向量數據庫
            if self.weaviate_client:
                success = await self._store_pulse_weaviate(pulse_record)
                if success:
                    return True
            
            # 降級到內存存儲
            self.pulse_data_store["pulse_patterns"][pulse_id] = pulse_record
            return True
            
        except Exception as e:
            self.logger.error(f"存儲脈診模式失敗: {str(e)}")
            return False
    
    async def get_pulse_statistics_v2(self) -> Dict[str, Any]:
        """
        獲取脈診統計 v2.0
        
        Returns:
            Dict[str, Any]: 脈診統計信息
        """
        try:
            stats = {
                "total_pulse_patterns": len(self.pulse_data_store["pulse_patterns"]),
                "total_symptoms": len(self.pulse_data_store["pulse_symptoms"]),
                "total_diagnoses": len(self.pulse_data_store["pulse_diagnoses"]),
                "total_treatments": len(self.pulse_data_store["pulse_treatments"]),
                "storage_type": "in_memory",
                "version": self.version,
                "last_updated": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"獲取脈診統計失敗: {str(e)}")
            return {"error": str(e)}
    
    def _load_default_pulse_data(self):
        """載入預設脈診數據"""
        try:
            # 預設脈診模式
            default_pulses = [
                {
                    "id": "pulse_001",
                    "pattern": "浮脈",
                    "description": "脈搏浮於皮表，輕按即得",
                    "symptoms": ["表證", "風寒感冒"],
                    "diagnosis": "表證",
                    "treatment": "發表解肌"
                },
                {
                    "id": "pulse_002", 
                    "pattern": "沉脈",
                    "description": "脈搏沉於筋骨，重按方得",
                    "symptoms": ["裡證", "腎陽虛"],
                    "diagnosis": "裡證",
                    "treatment": "溫補腎陽"
                },
                {
                    "id": "pulse_003",
                    "pattern": "數脈",
                    "description": "脈搏快速，每分鐘90次以上",
                    "symptoms": ["熱證", "炎症"],
                    "diagnosis": "熱證",
                    "treatment": "清熱瀉火"
                },
                {
                    "id": "pulse_004",
                    "pattern": "遲脈",
                    "description": "脈搏緩慢，每分鐘60次以下",
                    "symptoms": ["寒證", "氣虛"],
                    "diagnosis": "寒證",
                    "treatment": "溫陽散寒"
                },
                {
                    "id": "pulse_005",
                    "pattern": "弦脈",
                    "description": "脈如按琴弦，直長而緊",
                    "symptoms": ["肝膽疾病", "高血壓"],
                    "diagnosis": "肝陽上亢",
                    "treatment": "平肝潛陽"
                },
                {
                    "id": "pulse_006",
                    "pattern": "滑脈",
                    "description": "脈搏流利，如盤走珠",
                    "symptoms": ["痰濕", "妊娠"],
                    "diagnosis": "痰濕內阻",
                    "treatment": "化痰除濕"
                },
                {
                    "id": "pulse_007",
                    "pattern": "澀脈",
                    "description": "脈搏艱澀不暢，如刀刮竹",
                    "symptoms": ["血瘀", "氣滞"],
                    "diagnosis": "血瘀氣滞",
                    "treatment": "活血化瘀"
                },
                {
                    "id": "pulse_008",
                    "pattern": "洪脈",
                    "description": "脈搏洪大有力，如潮水湧來",
                    "symptoms": ["陽明熱盛", "高熱"],
                    "diagnosis": "陽明腑實",
                    "treatment": "瀉熱通腑"
                },
                {
                    "id": "pulse_009",
                    "pattern": "細脈",
                    "description": "脈搏細小如線，但應指明顯",
                    "symptoms": ["氣血不足", "陰虛"],
                    "diagnosis": "氣血兩虛",
                    "treatment": "益氣養血"
                },
                {
                    "id": "pulse_010",
                    "pattern": "緊脈",
                    "description": "脈搏緊張有力，如繩索牽拉",
                    "symptoms": ["寒邪束表", "疼痛"],
                    "diagnosis": "寒邪外束",
                    "treatment": "溫經散寒"
                }
            ]
            
            for pulse in default_pulses:
                self.pulse_data_store["pulse_patterns"][pulse["id"]] = pulse
            
            self.logger.info(f"載入預設脈診數據: {len(default_pulses)} 種脈象")
            
        except Exception as e:
            self.logger.error(f"載入預設脈診數據失敗: {str(e)}")
    
    async def _vectorize_pulse_query(self, pulse_description: str, symptoms: List[str]) -> List[float]:
        """向量化脈診查詢"""
        try:
            features = []
            
            # 脈診特徵
            pulse_features = {
                "浮": 1.0 if "浮" in pulse_description else 0.0,
                "沉": 1.0 if "沉" in pulse_description else 0.0,
                "數": 1.0 if "數" in pulse_description else 0.0,
                "遲": 1.0 if "遲" in pulse_description else 0.0,
                "弦": 1.0 if "弦" in pulse_description else 0.0,
                "滑": 1.0 if "滑" in pulse_description else 0.0,
                "澀": 1.0 if "澀" in pulse_description else 0.0,
                "洪": 1.0 if "洪" in pulse_description else 0.0,
                "細": 1.0 if "細" in pulse_description else 0.0,
                "緊": 1.0 if "緊" in pulse_description else 0.0
            }
            features.extend(pulse_features.values())
            
            # 症狀特徵
            symptom_features = {
                "發熱": 1.0 if any("熱" in s for s in symptoms) else 0.0,
                "畏寒": 1.0 if any("寒" in s for s in symptoms) else 0.0,
                "頭痛": 1.0 if any("痛" in s for s in symptoms) else 0.0,
                "疲勞": 1.0 if any("疲" in s or "乏" in s for s in symptoms) else 0.0,
                "咳嗽": 1.0 if any("咳" in s for s in symptoms) else 0.0,
                "胸悶": 1.0 if any("胸" in s for s in symptoms) else 0.0
            }
            features.extend(symptom_features.values())
            
            # 填充到128維
            while len(features) < 128:
                features.append(0.0)
            
            return features[:128]
            
        except Exception:
            import random
            return [random.random() for _ in range(128)]
    
    async def _vectorize_pulse_data(self, pulse_data: Dict[str, Any]) -> List[float]:
        """向量化脈診數據"""
        try:
            pattern = pulse_data.get("pattern", "")
            symptoms = pulse_data.get("symptoms", [])
            
            return await self._vectorize_pulse_query(pattern, symptoms)
            
        except Exception:
            import random
            return [random.random() for _ in range(128)]
    
    async def _search_pulse_memory(self, pulse_description: str, symptoms: List[str], limit: int) -> List[Dict[str, Any]]:
        """內存脈診搜索"""
        try:
            results = []
            
            for pulse_id, pulse_data in self.pulse_data_store["pulse_patterns"].items():
                # 計算相似度
                similarity = self._calculate_pulse_similarity(
                    pulse_description, symptoms, pulse_data
                )
                
                if similarity > self.pulse_config["similarity_threshold"]:
                    pulse_result = pulse_data.copy()
                    pulse_result["similarity"] = similarity
                    results.append(pulse_result)
            
            # 按相似度排序
            results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            return results[:limit]
            
        except Exception as e:
            self.logger.error(f"內存脈診搜索失敗: {str(e)}")
            return []
    
    def _calculate_pulse_similarity(self, query_pulse: str, query_symptoms: List[str], pulse_data: Dict[str, Any]) -> float:
        """計算脈診相似度"""
        try:
            pulse_score = 0.0
            symptom_score = 0.0
            
            # 脈象匹配
            pattern = pulse_data.get("pattern", "")
            if query_pulse and pattern:
                if query_pulse in pattern or pattern in query_pulse:
                    pulse_score = 1.0
                else:
                    # 簡化相似度計算
                    pulse_score = 0.5 if len(set(query_pulse) & set(pattern)) > 0 else 0.0
            
            # 症狀匹配
            pulse_symptoms = pulse_data.get("symptoms", [])
            if query_symptoms and pulse_symptoms:
                matches = sum(1 for qs in query_symptoms for ps in pulse_symptoms if qs in ps or ps in qs)
                symptom_score = matches / max(len(query_symptoms), len(pulse_symptoms))
            
            # 加權計算總相似度
            total_similarity = (
                pulse_score * self.pulse_config["pulse_weight"] +
                symptom_score * self.pulse_config["symptom_weight"]
            )
            
            return min(1.0, total_similarity)
            
        except Exception:
            return 0.0
    
    async def _analyze_pulse_pattern(self, pulse_pattern: Dict[str, Any]) -> Dict[str, Any]:
        """分析脈診模式"""
        try:
            analysis = {
                "pattern_type": pulse_pattern.get("pattern", "未知"),
                "strength": pulse_pattern.get("strength", "中等"),
                "rhythm": pulse_pattern.get("rhythm", "規律"),
                "characteristics": []
            }
            
            # 分析脈診特徵
            pattern = pulse_pattern.get("pattern", "")
            if "浮" in pattern:
                analysis["characteristics"].append("表證")
            if "沉" in pattern:
                analysis["characteristics"].append("裡證")
            if "數" in pattern:
                analysis["characteristics"].append("熱證")
            if "遲" in pattern:
                analysis["characteristics"].append("寒證")
            if "弦" in pattern:
                analysis["characteristics"].append("肝膽病變")
            if "滑" in pattern:
                analysis["characteristics"].append("痰濕")
            if "澀" in pattern:
                analysis["characteristics"].append("血瘀")
            if "洪" in pattern:
                analysis["characteristics"].append("陽明熱盛")
            if "細" in pattern:
                analysis["characteristics"].append("氣血不足")
            if "緊" in pattern:
                analysis["characteristics"].append("寒邪")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"分析脈診模式失敗: {str(e)}")
            return {"pattern_type": "分析失敗", "characteristics": []}
    
    async def _integrate_patient_context(self, pulse_analysis: Dict[str, Any], patient_context: Dict[str, Any]) -> Dict[str, Any]:
        """整合患者上下文"""
        try:
            # 結合患者年齡、性別、症狀等信息調整脈診分析
            age = patient_context.get("age", 0)
            gender = patient_context.get("gender", "")
            symptoms = patient_context.get("symptoms", [])
            
            # 根據年齡調整
            if age > 60:
                pulse_analysis["age_consideration"] = "老年患者，脈象可能較弱"
            elif age < 18:
                pulse_analysis["age_consideration"] = "青少年患者，脈象可能較快"
            
            # 根據性別調整
            if gender == "女性":
                pulse_analysis["gender_consideration"] = "女性患者，需考慮月經週期影響"
            
            # 結合症狀
            pulse_analysis["symptom_correlation"] = symptoms
            
            return pulse_analysis
            
        except Exception as e:
            self.logger.error(f"整合患者上下文失敗: {str(e)}")
            return pulse_analysis
    
    async def _generate_pulse_diagnosis(self, pulse_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成脈診診斷"""
        try:
            characteristics = pulse_analysis.get("characteristics", [])
            
            diagnosis = {
                "primary": "",
                "secondary": [],
                "confidence": 0.7,
                "recommendations": []
            }
            
            # 根據脈診特徵生成診斷
            if "表證" in characteristics:
                diagnosis["primary"] = "外感風寒"
                diagnosis["recommendations"].append("發表解肌")
            elif "裡證" in characteristics:
                diagnosis["primary"] = "內傷雜病"
                diagnosis["recommendations"].append("調理臟腑")
            elif "熱證" in characteristics:
                diagnosis["primary"] = "熱性病變"
                diagnosis["recommendations"].append("清熱瀉火")
            elif "寒證" in characteristics:
                diagnosis["primary"] = "寒性病變"
                diagnosis["recommendations"].append("溫陽散寒")
            elif "肝膽病變" in characteristics:
                diagnosis["primary"] = "肝膽疾患"
                diagnosis["recommendations"].append("疏肝利膽")
            elif "痰濕" in characteristics:
                diagnosis["primary"] = "痰濕內阻"
                diagnosis["recommendations"].append("化痰除濕")
            elif "血瘀" in characteristics:
                diagnosis["primary"] = "血瘀氣滞"
                diagnosis["recommendations"].append("活血化瘀")
            elif "氣血不足" in characteristics:
                diagnosis["primary"] = "氣血兩虛"
                diagnosis["recommendations"].append("益氣養血")
            else:
                diagnosis["primary"] = "需進一步診察"
                diagnosis["confidence"] = 0.5
            
            return diagnosis
            
        except Exception as e:
            self.logger.error(f"生成脈診診斷失敗: {str(e)}")
            return {"primary": "診斷失敗", "confidence": 0.0, "recommendations": []}
    
    def _initialize_pulse_schema(self):
        """初始化脈診數據結構"""
        if not self.weaviate_client:
            return
        
        try:
            # 檢查 schema 是否已存在
            existing_schema = self.weaviate_client.schema.get()
            class_names = [cls["class"] for cls in existing_schema.get("classes", [])]
            
            # 定義脈診類別 schema
            pulse_class = {
                "class": "PulsePattern",
                "description": "脈診模式數據",
                "properties": [
                    {"name": "pattern", "dataType": ["string"]},
                    {"name": "symptoms", "dataType": ["string[]"]},
                    {"name": "diagnosis", "dataType": ["string"]},
                    {"name": "treatment", "dataType": ["string"]},
                    {"name": "effectiveness", "dataType": ["number"]},
                    {"name": "timestamp", "dataType": ["date"]}
                ]
            }
            
            if "PulsePattern" not in class_names:
                self.weaviate_client.schema.create_class(pulse_class)
                self.logger.info("創建脈診 schema: PulsePattern")
            
            self.pulse_schema_created = True
            
        except Exception as e:
            self.logger.error(f"初始化脈診 schema 失敗: {str(e)}")
            self.pulse_schema_created = False
    
    async def _store_pulse_weaviate(self, pulse_record: Dict[str, Any]) -> bool:
        """存儲到 Weaviate"""
        if not self.weaviate_client or not self.pulse_schema_created:
            return False
        
        try:
            properties = pulse_record.copy()
            vector = properties.pop("vector", [])
            
            result = self.weaviate_client.data_object.create(
                data_object=properties,
                class_name="PulsePattern",
                vector=vector
            )
            
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Weaviate 脈診存儲失敗: {str(e)}")
            return False
    
    async def _search_pulse_weaviate(self, query_vector: List[float], limit: int) -> List[Dict[str, Any]]:
        """從 Weaviate 搜索脈診"""
        if not self.weaviate_client:
            return []
        
        try:
            query = (
                self.weaviate_client.query
                .get("PulsePattern")
                .with_near_vector({"vector": query_vector})
                .with_limit(limit)
                .with_additional(["certainty"])
            )
            
            result = query.do()
            
            if result and "data" in result and "Get" in result["data"]:
                return result["data"]["Get"]["PulsePattern"]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Weaviate 脈診搜索失敗: {str(e)}")
            return []

# 向後兼容的類別名稱
PulseRepositoryV2 = PulseRepository

__all__ = ["PulseRepository", "PulseRepositoryV2"]
