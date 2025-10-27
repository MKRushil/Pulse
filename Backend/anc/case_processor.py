# -*- coding: utf-8 -*-
"""
TCM Case Processor
病例處理核心邏輯: 保存 JSON + 向量化 + 上傳
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import weaviate
from weaviate.classes.query import Filter

from .config import (
    RAW_CASES_DIR,
    PROCESS_LOGS_DIR,
    WEAVIATE_URL,
    WEAVIATE_API_KEY,
    CASE_COLLECTION_NAME,
    AUTO_VECTORIZE,
    TCM_DICT_PATH
)
from .schema import TCMCaseInput, TCMCaseData, create_tcm_case_collection, _to_rfc3339
from .jieba_processor import get_jieba_processor
from .vectorizer import get_vectorizer


class CaseProcessor:
    """病例處理器 - 負責保存、正規化、向量化與上傳"""
    
    def __init__(self):
        self.weaviate_client = None
        self.collection = None
        self.jieba = None
        self.vectorizer = None
        
        try:
            self.jieba = get_jieba_processor(TCM_DICT_PATH)
            self.vectorizer = get_vectorizer()
            self._init_weaviate()
        except Exception as e:
            print(f"❌ CaseProcessor 初始化失敗: {e}")
            import traceback
            traceback.print_exc()

    def __del__(self):
        """清理資源"""
        try:
            if hasattr(self, 'weaviate_client') and self.weaviate_client:
                self.weaviate_client.close()
        except Exception:
            pass
    
    def _init_weaviate(self):
        """初始化 Weaviate 連接"""
        try:
            from weaviate.auth import AuthApiKey
            
            host = WEAVIATE_URL.replace("http://", "").replace("https://", "").split(":")[0]
            port = int(WEAVIATE_URL.split(":")[-1]) if ":" in WEAVIATE_URL else 8080
            
            if WEAVIATE_API_KEY:
                self.weaviate_client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    auth_credentials=AuthApiKey(WEAVIATE_API_KEY)
                )
                print(f"✅ Weaviate 連接成功 (已認證): {WEAVIATE_URL}")
            else:
                self.weaviate_client = weaviate.connect_to_local(
                    host=host,
                    port=port
                )
                print(f"✅ Weaviate 連接成功 (無認證): {WEAVIATE_URL}")
            
            print(f"⏳ 正在檢查/建立 Collection: {CASE_COLLECTION_NAME}")
            
            self.collection = create_tcm_case_collection(
                self.weaviate_client,
                CASE_COLLECTION_NAME
            )
            
            if self.collection is not None:
                print(f"✅ Collection 已就緒: {self.collection.name}")
            else:
                print(f"❌ Collection 建立失敗!")
                self.weaviate_client = None
            
        except Exception as e:
            print(f"❌ Weaviate 連接失敗: {e}")
            import traceback
            traceback.print_exc()
            self.weaviate_client = None
            self.collection = None
    
    def process_case(
        self,
        case_input: TCMCaseInput,
        save_location: Optional[Path] = None
    ) -> Dict[str, Any]:
        """處理病例完整流程"""
        result = {
            "success": False,
            "case_id": None,
            "json_path": None,
            "vectorized": False,
            "uploaded": False,
            "errors": []
        }
        
        try:
            case_id = self._generate_case_id(case_input)
            result["case_id"] = case_id
            
            print(f"\n{'='*60}")
            print(f"🏥 開始處理病例: {case_id}")
            print(f"{'='*60}")
            
            json_path = self._save_raw_json(case_input, case_id, save_location)
            result["json_path"] = str(json_path)
            print(f"✅ 原始 JSON 已保存: {json_path}")
            
            full_text = TCMCaseData._build_full_text(case_input)
            jieba_analysis = self.jieba.analyze_case(full_text)
            
            print(f"✅ Jieba 分詞完成:")
            print(f"   - 總詞數: {len(jieba_analysis['all_tokens'])}")
            print(f"   - 證型: {len(jieba_analysis['syndrome'])} 個")
            print(f"   - 臟腑: {len(jieba_analysis['zangfu'])} 個")
            print(f"   - 症狀: {len(jieba_analysis['symptom'])} 個")
            print(f"   - 治法: {len(jieba_analysis['treatment'])} 個")
            
            if AUTO_VECTORIZE:
                try:
                    print("⏳ 正在生成 1024 維向量...")
                    embedding = self.vectorizer.encode(full_text)
                    result["vectorized"] = True
                    print(f"✅ 向量化成功 (維度: {len(embedding)})")
                except Exception as e:
                    error_msg = f"向量化失敗: {e}"
                    result["errors"].append(error_msg)
                    print(f"❌ {error_msg}")
                    embedding = [0.0] * 1024
            else:
                embedding = [0.0] * 1024
            
            if self.weaviate_client is None:
                error_msg = "Weaviate 客戶端未初始化"
                result["errors"].append(error_msg)
                print(f"⚠️ {error_msg}")
            elif self.collection is None:
                error_msg = "Collection 未初始化"
                result["errors"].append(error_msg)
                print(f"⚠️ {error_msg}")
            else:
                try:
                    data_obj, vector = TCMCaseData.prepare_for_upload(
                        case_input,
                        case_id,
                        jieba_analysis,
                        embedding
                    )
                    
                    existing = self._check_existing(case_id)
                    
                    if existing:
                        print(f"⚠️ 病例 {case_id} 已存在，進行更新...")
                        self._update_case(existing, data_obj, vector)
                    else:
                        print(f"⏳ 正在上傳到 Weaviate...")
                        self._upload_case(data_obj, vector)
                    
                    result["uploaded"] = True
                    print(f"✅ 成功上傳到向量資料庫")
                    
                except Exception as e:
                    error_msg = f"Weaviate 上傳失敗: {e}"
                    result["errors"].append(error_msg)
                    print(f"❌ {error_msg}")
                    import traceback
                    traceback.print_exc()
            
            self._log_process(case_id, result)
            
            result["success"] = True
            print(f"\n{'='*60}")
            print(f"✅ 病例處理完成: {case_id}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            error_msg = f"處理失敗: {str(e)}"
            result["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def _generate_case_id(self, case_input: TCMCaseInput) -> str:
        """生成病例唯一 ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        patient_id = case_input.basic.idLast4
        return f"CASE_{timestamp}_{patient_id}_{short_uuid}"
    
    def _save_raw_json(
        self,
        case_input: TCMCaseInput,
        case_id: str,
        save_location: Optional[Path] = None
    ) -> Path:
        """保存原始 JSON 檔案"""
        if save_location:
            save_dir = save_location
        else:
            date_str = datetime.now().strftime("%Y%m")
            save_dir = RAW_CASES_DIR / date_str
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{case_id}.json"
        filepath = save_dir / filename
        
        case_data = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(),
            "data": case_input.model_dump()
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def _check_existing(self, case_id: str) -> Optional[str]:
        """檢查病例是否已存在"""
        try:
            response = self.collection.query.fetch_objects(
                filters=Filter.by_property("case_id").equal(case_id),
                limit=1
            )
            
            if response.objects and len(response.objects) > 0:
                return response.objects[0].uuid
            return None
            
        except Exception as e:
            print(f"⚠️ 檢查現有病例時出錯: {e}")
            return None
    
    def _upload_case(self, data_obj: Dict[str, Any], vector: list):
        """上傳新病例到 Weaviate"""
        self.collection.data.insert(
            properties=data_obj,
            vector=vector
        )
    
    def _update_case(self, uuid: str, data_obj: Dict[str, Any], vector: list):
        """更新現有病例"""
        # 更新 updated_at - 使用 RFC3339 格式
        data_obj["updated_at"] = _to_rfc3339(datetime.now(timezone.utc))
        
        self.collection.data.update(
            uuid=uuid,
            properties=data_obj,
            vector=vector
        )
    
    def _log_process(self, case_id: str, result: Dict[str, Any]):
        """記錄處理日誌"""
        PROCESS_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        log_file = PROCESS_LOGS_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "case_id": case_id,
            "result": result
        }
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ 寫入日誌失敗: {e}")
    
    def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """根據 case_id 查詢病例"""
        if self.collection is None:
            return None
        
        try:
            response = self.collection.query.fetch_objects(
                filters=Filter.by_property("case_id").equal(case_id),
                limit=1
            )
            
            if response.objects and len(response.objects) > 0:
                obj = response.objects[0]
                raw_data = json.loads(obj.properties.get("raw_data", "{}"))
                return {
                    "case_id": obj.properties.get("case_id"),
                    "patient_id": obj.properties.get("patient_id"),
                    "visit_date": obj.properties.get("visit_date"),
                    "chief_complaint": obj.properties.get("chief_complaint"),
                    "diagnosis": obj.properties.get("diagnosis"),
                    "data": raw_data,
                    "created_at": obj.properties.get("created_at"),
                }
            
            return None
            
        except Exception as e:
            print(f"❌ 查詢失敗: {e}")
            return None
    
    def search_cases(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> list:
        """混合搜索病例"""
        if self.collection is None:
            return []
        
        try:
            query_vector = self.vectorizer.encode(query)
            
            weaviate_filter = None
            if filters:
                filter_conditions = []
                if "gender" in filters:
                    filter_conditions.append(
                        Filter.by_property("gender").equal(filters["gender"])
                    )
                if "age_min" in filters:
                    filter_conditions.append(
                        Filter.by_property("age").greater_or_equal(filters["age_min"])
                    )
                if "age_max" in filters:
                    filter_conditions.append(
                        Filter.by_property("age").less_or_equal(filters["age_max"])
                    )
                
                if filter_conditions:
                    weaviate_filter = filter_conditions[0]
                    for cond in filter_conditions[1:]:
                        weaviate_filter = weaviate_filter & cond
            
            response = self.collection.query.hybrid(
                query=query,
                vector=query_vector,
                alpha=0.7,
                limit=limit,
                filters=weaviate_filter,
                return_metadata=["score", "distance"]
            )
            
            results = []
            for obj in response.objects:
                results.append({
                    "case_id": obj.properties.get("case_id"),
                    "patient_id": obj.properties.get("patient_id"),
                    "chief_complaint": obj.properties.get("chief_complaint"),
                    "diagnosis": obj.properties.get("diagnosis"),
                    "score": obj.metadata.score if hasattr(obj.metadata, 'score') else None,
                    "distance": obj.metadata.distance if hasattr(obj.metadata, 'distance') else None,
                })
            
            return results
            
        except Exception as e:
            print(f"❌ 搜索失敗: {e}")
            return []


# ==================== 單例模式 (帶狀態檢查) ====================
_processor_instance = None

def get_case_processor() -> CaseProcessor:
    """
    獲取全局病例處理器實例
    
    使用單例模式以複用:
    - Weaviate 連接
    - NVIDIA Vectorizer
    - Jieba 處理器
    
    包含自動狀態檢查與恢復機制
    """
    global _processor_instance
    
    need_init = (
        _processor_instance is None or
        _processor_instance.weaviate_client is None or
        _processor_instance.collection is None or
        _processor_instance.jieba is None or
        _processor_instance.vectorizer is None
    )
    
    if need_init:
        if _processor_instance is not None:
            print("⚠️ 檢測到 CaseProcessor 狀態異常,正在重新初始化...")
            try:
                if hasattr(_processor_instance, 'weaviate_client') and _processor_instance.weaviate_client:
                    _processor_instance.weaviate_client.close()
            except:
                pass
        
        _processor_instance = CaseProcessor()
    
    return _processor_instance


def reset_case_processor():
    """重置病例處理器 (用於測試或強制重新初始化)"""
    global _processor_instance
    if _processor_instance is not None:
        try:
            _processor_instance.weaviate_client.close()
        except:
            pass
    _processor_instance = None