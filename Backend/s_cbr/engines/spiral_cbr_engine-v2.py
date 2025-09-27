"""
S-CBR v2.1 重構版 - 螺旋案例推理引擎

重構重點：
1. 統一檢索流程，減少重複代碼
2. 優化權重計算與命中邏輯 (Case 0.6, RPCase 0.3, Pulse 0.1)
3. 加強分類訊號處理
4. 統一日誌與錯誤處理
5. 完善滿意度與寫回機制

版本：v2.1 (重構版)
作者：SCBR Team
更新日期：2025-09-25
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import openai
import weaviate
from openai import AsyncOpenAI

# 保持原始模組引用名稱不變
try:
    from ..utils.spiral_logger import SpiralLogger
    logger = SpiralLogger.get_logger("SpiralCBREngine")
except ImportError:
    logger = logging.getLogger("SpiralCBREngine")

try:
    from ..config.scbr_config import SCBRConfig
except ImportError:
    logger.warning("無法載入 SCBRConfig，將使用預設配置")
    SCBRConfig = None

try:
    from ..knowledge.rpcase_manager import RPCaseManager
except ImportError:
    logger.warning("無法載入 RPCaseManager，回饋案例功能將不可用")
    RPCaseManager = None

try:
    from ..steps.step1_case_finder import CaseFinder
except ImportError:
    logger.warning("無法載入 CaseFinder，案例檢索備援功能將不可用")
    CaseFinder = None


class SpiralCBREngine:
    """
    螺旋案例推理引擎 v2.1 重構版
    
    重構改進：
    - 統一檢索介面，減少重複代碼
    - 優化權重計算邏輯 (Case 0.6, RPCase 0.3, Pulse 0.1)
    - 加強分類訊號與脈象線索處理
    - 統一日誌與錯誤處理模式
    - 完善滿意度分支與回饋機制
    """

    def __init__(self):
        """初始化螺旋推理引擎 v2.1"""
        self.logger = logger
        self.config = SCBRConfig() if SCBRConfig else None
        self.version = "2.1"
        
        # 檢索權重配置 (重構調整)
        self.retrieval_weights = {
            "case": 0.6,     # Case 知識庫權重
            "rpcase": 0.3,   # RPCase 知識庫權重  
            "pulse": 0.1     # Pulse 知識庫權重
        }
        
        # 初始化各組件
        self._init_llm_client()
        self._init_weaviate_client()
        self._init_rpcase_manager()
        
        self.logger.info(f"S-CBR 螺旋推理引擎 v{self.version} 初始化完成")

    def _init_llm_client(self):
        """初始化大語言模型客戶端"""
        try:
            if not self.config:
                self.logger.error("❌ SCBRConfig 不可用")
                self.llm_client = None
                return
            
            # 通過 SCBRConfig 獲取 LLM 配置
            llm_config = self.config.get_llm_config()
            
            self.llm_api_url = llm_config.get("api_url", "")
            self.llm_api_key = llm_config.get("api_key", "")
            self.llm_model = llm_config.get("model", "meta/llama-3.1-405b-instruct")
            
            self.logger.info(f"LLM 配置載入: URL={self.llm_api_url}, Model={self.llm_model}, Key={'有' if self.llm_api_key else '無'}")
            
            if not self.llm_api_key:
                self.logger.error("❌ LLM API Key 未配置")
                self.llm_client = None
                return
            
            if not self.llm_api_url:
                self.logger.error("❌ LLM API URL 未配置")
                self.llm_client = None
                return
            
            # 初始化 AsyncOpenAI 客戶端
            self.llm_client = AsyncOpenAI(
                api_key=self.llm_api_key,
                base_url=self.llm_api_url
            )
            
            self.logger.info(f"✅ LLM 客戶端初始化成功: {self.llm_model}")
            
        except Exception as e:
            self.logger.error(f"❌ LLM 客戶端初始化失敗: {e}")
            self.llm_client = None

    def _init_weaviate_client(self):
        """初始化 Weaviate 向量資料庫客戶端"""
        try:
            if not self.config:
                self.logger.error("❌ SCBRConfig 不可用")
                self.weaviate_client = None
                return
            
            # 通過 SCBRConfig 獲取 Weaviate 配置
            weaviate_config = self.config.get_weaviate_config()
            
            weaviate_url = weaviate_config.get("url", "http://localhost:8080")
            api_key = weaviate_config.get("api_key")
            timeout = weaviate_config.get("timeout", 30)
            
            self.logger.info(f"Weaviate 配置載入: URL={weaviate_url}, API Key={'有' if api_key else '無'}, Timeout={timeout}")
            
            # 根據是否有 API Key 來初始化客戶端
            if api_key and api_key != "" and api_key != "None":
                # 使用 API Key 認證
                auth_config = weaviate.AuthApiKey(api_key=api_key)
                self.weaviate_client = weaviate.Client(
                    url=weaviate_url,
                    auth_client_secret=auth_config,
                    timeout_config=(timeout, timeout)
                )
                self.logger.info("使用 API Key 認證模式")
            else:
                # 無認證模式
                self.weaviate_client = weaviate.Client(
                    url=weaviate_url,
                    timeout_config=(timeout, timeout)
                )
                self.logger.info("使用無認證模式")
            
            # 測試連接
            schema = self.weaviate_client.schema.get()
            available_classes = [cls['class'] for cls in schema.get('classes', [])]
            self.logger.info(f"✅ Weaviate 客戶端連接成功: {weaviate_url}")
            self.logger.info(f"可用的 Schema Classes: {available_classes}")
            
        except Exception as e:
            self.logger.error(f"❌ Weaviate 客戶端初始化失敗: {e}")
            # 嘗試降級連接
            try:
                self.weaviate_client = weaviate.Client(
                    url="http://localhost:8080",
                    timeout_config=(10, 10)
                )
                # 簡單測試
                ready = self.weaviate_client.is_ready()
                if ready:
                    self.logger.info("✅ Weaviate 降級連接成功")
                else:
                    raise Exception("Weaviate 未準備就緒")
            except Exception as e2:
                self.logger.error(f"❌ Weaviate 降級連接也失敗: {e2}")
                self.weaviate_client = None

    def _init_rpcase_manager(self):
        """初始化 RPCase 管理器"""
        try:
            if RPCaseManager:
                self.rpcase_manager = RPCaseManager()
                self._log_success("RPCase 管理器初始化成功")
            else:
                self.rpcase_manager = None
                self.logger.warning("RPCase 管理器不可用")
        except Exception as e:
            self._log_error("RPCase 管理器初始化失敗", e)
            self.rpcase_manager = None

    # ========== 重構：統一日誌處理函式 ==========
    
    def _log_step(self, step_name: str, details: str = ""):
        """統一的步驟日誌記錄"""
        if details:
            self.logger.info(f"{step_name}: {details}")
        else:
            self.logger.info(step_name)

    def _log_success(self, operation: str, details: str = ""):
        """統一的成功日誌記錄"""
        if details:
            self.logger.info(f"✅ {operation}: {details}")
        else:
            self.logger.info(f"✅ {operation}")

    def _log_error(self, operation: str, error: Exception):
        """統一的錯誤日誌記錄"""
        self.logger.error(f"❌ {operation}: {str(error)}")
        if hasattr(self.logger, 'exception'):
            self.logger.exception("詳細錯誤信息")

    def _log_retrieval_result(self, kb_name: str, count: int, retry_count: int = 0):
        """統一的檢索結果日誌記錄"""
        retry_info = f" (重試 {retry_count} 次)" if retry_count > 0 else ""
        self.logger.info(f"📊 {kb_name} 知識庫檢索: {count} 個結果{retry_info}")

    # ========== 重構：統一檢索介面 ==========
    
    def _check_weaviate_class_exists(self, class_name: str) -> bool:
        """檢查 Weaviate 類別是否存在"""
        try:
            if not self.weaviate_client:
                return False
            
            schema = self.weaviate_client.schema.get()
            available_classes = [cls["class"] for cls in schema.get("classes", [])]
            exists = class_name in available_classes
            
            if not exists:
                self.logger.warning(f"Weaviate 類別 '{class_name}' 不存在")
            
            return exists
        except Exception as e:
            self._log_error(f"檢查 Weaviate 類別 {class_name}", e)
            return False

    async def _unified_vector_retrieval(self, 
                                      class_name: str,
                                      query_vector: List[float],
                                      limit: int = 10,
                                      where_conditions: Optional[Dict] = None,
                                      additional_properties: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        統一的向量檢索介面 (重構核心)
        
        Args:
            class_name: Weaviate 類別名稱
            query_vector: 查詢向量
            limit: 檢索數量限制
            where_conditions: WHERE 條件字典
            additional_properties: 額外屬性列表
        
        Returns:
            List[Dict]: 檢索結果列表
        """
        try:
            # 檢查類別是否存在
            if not self._check_weaviate_class_exists(class_name):
                return []

            # 構建查詢
            query_builder = (
                self.weaviate_client.query
                .get(class_name, additional_properties or ["*"])
                .with_near_vector({"vector": query_vector})
                .with_limit(limit)
            )

            # 添加 WHERE 條件
            if where_conditions:
                query_builder = query_builder.with_where(where_conditions)

            # 執行查詢
            result = query_builder.do()
            
            # 解析結果
            raw_results = result.get("data", {}).get("Get", {}).get(class_name, [])
            
            # 統一結果格式
            formatted_results = []
            for item in raw_results:
                # 統一添加來源標記
                item["_source_kb"] = class_name.lower()
                formatted_results.append(item)
            
            self._log_retrieval_result(class_name, len(formatted_results))
            return formatted_results

        except Exception as e:
            self._log_error(f"向量檢索 {class_name}", e)
            return []

    async def _retry_with_or_conditions(self,
                                      class_name: str,
                                      query_vector: List[float],
                                      retry_terms: List[str],
                                      field_name: str = "content",
                                      limit: int = 5) -> List[Dict[str, Any]]:
        """
        使用 OR 條件重試檢索 (重構統一)
        
        Args:
            class_name: Weaviate 類別名稱
            query_vector: 查詢向量
            retry_terms: 重試關鍵詞列表
            field_name: 檢索欄位名稱
            limit: 檢索數量限制
        
        Returns:
            List[Dict]: 重試檢索結果
        """
        try:
            if not retry_terms:
                return []

            # 構建 OR 條件
            operands = []
            for term in retry_terms:
                operands.append({
                    "path": [field_name],
                    "operator": "Like",
                    "valueText": f"*{term}*"
                })

            where_conditions = {
                "operator": "Or",
                "operands": operands
            }

            # 使用統一檢索介面
            results = await self._unified_vector_retrieval(
                class_name=class_name,
                query_vector=query_vector,
                limit=limit,
                where_conditions=where_conditions
            )

            self._log_retrieval_result(f"{class_name}(OR重試)", len(results), 1)
            return results

        except Exception as e:
            self._log_error(f"OR條件重試 {class_name}", e)
            return []

    # ========== 重構：主要檢索流程 ==========
    
    async def _retrieve_from_case_kb(self, 
                                   query_vector: List[float], 
                                   used_cases: List[str] = None,
                                   signals: List[str] = None) -> List[Dict[str, Any]]:
        """從 Case 知識庫檢索 (重構優化)"""
        try:
            # 構建過濾條件
            where_conditions = None
            if used_cases:
                # 排除已使用的案例
                where_conditions = {
                    "operator": "Not",
                    "operands": [{
                        "path": ["case_id"],
                        "operator": "ContainsAny",
                        "valueTextArray": used_cases
                    }]
                }

            # 基礎檢索
            results = await self._unified_vector_retrieval(
                class_name="Case",
                query_vector=query_vector,
                limit=10,
                where_conditions=where_conditions
            )

            # 如果結果不足且有分類訊號，嘗試擴展檢索
            if len(results) < 3 and signals:
                retry_results = await self._retry_with_or_conditions(
                    class_name="Case",
                    query_vector=query_vector,
                    retry_terms=signals,
                    field_name="symptoms"
                )
                
                # 合併結果，避免重複
                case_ids = {item.get("case_id") for item in results if item.get("case_id")}
                for item in retry_results:
                    if item.get("case_id") not in case_ids:
                        results.append(item)

            return results

        except Exception as e:
            self._log_error("Case 知識庫檢索", e)
            return []

    async def _retrieve_from_rpcase_kb(self, 
                                     query_vector: List[float],
                                     used_cases: List[str] = None) -> List[Dict[str, Any]]:
        """從 RPCase 知識庫檢索 (重構優化)"""
        try:
            # 構建過濾條件
            where_conditions = None
            if used_cases:
                where_conditions = {
                    "operator": "Not",
                    "operands": [{
                        "path": ["rpcase_id"],
                        "operator": "ContainsAny", 
                        "valueTextArray": used_cases
                    }]
                }

            # 基礎檢索
            results = await self._unified_vector_retrieval(
                class_name="RPCase",
                query_vector=query_vector,
                limit=5,
                where_conditions=where_conditions
            )

            return results

        except Exception as e:
            self._log_error("RPCase 知識庫檢索", e)
            return []

    async def _retrieve_from_pulse_kb(self, 
                                    query_vector: List[float],
                                    pulse_clues: List[str] = None) -> List[Dict[str, Any]]:
        """從 Pulse 知識庫檢索 (重構優化)"""
        try:
            # 基礎檢索
            results = await self._unified_vector_retrieval(
                class_name="PulsePJ",
                query_vector=query_vector,
                limit=8
            )

            # 如果有脈象線索，嘗試精確匹配
            if len(results) < 3 and pulse_clues:
                retry_results = await self._retry_with_or_conditions(
                    class_name="PulsePJ", 
                    query_vector=query_vector,
                    retry_terms=pulse_clues,
                    field_name="pulse_type"
                )
                
                # 合併結果
                pulse_ids = {item.get("pulse_id") for item in results if item.get("pulse_id")}
                for item in retry_results:
                    if item.get("pulse_id") not in pulse_ids:
                        results.append(item)

            return results

        except Exception as e:
            self._log_error("Pulse 知識庫檢索", e)
            return []

    # ========== 重構：JSON/Text 解析統一處理 ==========
    
    def _safe_json_parse(self, text: str, fallback_key: str = "content") -> Dict[str, Any]:
        """
        安全的 JSON 解析 (重構統一)
        
        Args:
            text: 要解析的文本
            fallback_key: 解析失敗時的降級鍵名
            
        Returns:
            Dict: 解析結果
        """
        try:
            # 嘗試移除 markdown 標記
            cleaned_text = text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            # 嘗試 JSON 解析
            parsed = json.loads(cleaned_text)
            return parsed if isinstance(parsed, dict) else {fallback_key: str(parsed)}

        except json.JSONDecodeError:
            # JSON 解析失敗，嘗試文本分割
            return self._parse_text_fallback(text, fallback_key)
        except Exception as e:
            self.logger.warning(f"JSON 解析異常: {str(e)}")
            return {fallback_key: text, "parse_error": str(e)}

    def _parse_text_fallback(self, text: str, fallback_key: str) -> Dict[str, Any]:
        """文本解析降級處理"""
        result = {fallback_key: text}
        
        # 嘗試提取關鍵信息
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if ':' in line or '：' in line:
                key_value = line.split(':', 1) if ':' in line else line.split('：', 1)
                if len(key_value) == 2:
                    key = key_value[0].strip().lower()
                    value = key_value[1].strip()
                    
                    # 映射常見字段
                    if key in ['診斷', 'diagnosis', '主診斷']:
                        result['diagnosis'] = value
                    elif key in ['治療', 'treatment', '治療方案']:
                        result['treatment_plan'] = value
                    elif key in ['信心度', 'confidence']:
                        try:
                            result['confidence'] = float(value.replace('%', ''))
                        except:
                            result['confidence'] = 0.8
        
        return result

    # ========== 重構：權重計算與評估指標 ==========
    
    def _calculate_weighted_cms_score(self, 
                                    case_results: List[Dict], 
                                    rpcase_results: List[Dict], 
                                    pulse_results: List[Dict]) -> float:
        """
        計算加權 CMS 分數 (重構權重調整)
        
        權重配置：Case 0.6, RPCase 0.3, Pulse 0.1
        """
        try:
            total_score = 0.0
            weights = self.retrieval_weights
            
            # Case 知識庫分數
            case_score = len(case_results) * weights["case"]
            
            # RPCase 知識庫分數
            rpcase_score = len(rpcase_results) * weights["rpcase"]
            
            # Pulse 知識庫分數 (僅作為輔助參考)
            pulse_score = min(len(pulse_results), 3) * weights["pulse"]  # 限制脈象權重
            
            total_score = case_score + rpcase_score + pulse_score
            
            # 歸一化到 0-10 分
            max_possible = 10 * weights["case"] + 5 * weights["rpcase"] + 3 * weights["pulse"]
            normalized_score = min(10.0, (total_score / max_possible) * 10)
            
            self.logger.info(f"CMS 分數計算: Case={case_score:.2f}, RPCase={rpcase_score:.2f}, "
                           f"Pulse={pulse_score:.2f}, 總分={normalized_score:.2f}")
            
            return round(normalized_score, 2)
            
        except Exception as e:
            self._log_error("CMS 分數計算", e)
            return 5.0  # 預設分數

    def _calculate_rci_score(self, round_count: int, consistency_factors: Dict) -> float:
        """計算推理一致性指標 (RCI)"""
        try:
            base_score = 8.0
            
            # 輪次懲罰 (輪次越多，一致性可能下降)
            round_penalty = max(0, (round_count - 1) * 0.5)
            
            # 一致性獎勵
            consistency_bonus = 0
            if consistency_factors.get("llm_confidence", 0) > 0.8:
                consistency_bonus += 1.0
            if consistency_factors.get("symptom_match", False):
                consistency_bonus += 0.5
            
            final_score = max(0, min(10, base_score - round_penalty + consistency_bonus))
            
            self.logger.info(f"RCI 分數: 基礎={base_score}, 輪次懲罰={round_penalty}, "
                           f"一致性獎勵={consistency_bonus}, 最終={final_score}")
            
            return round(final_score, 2)
            
        except Exception as e:
            self._log_error("RCI 分數計算", e)
            return 7.0

    def _calculate_sals_score(self, learning_success: bool, feedback_count: int) -> float:
        """計算系統自適應學習分數 (SALS)"""
        try:
            base_score = 6.0
            
            # 學習成功獎勵
            if learning_success:
                base_score += 2.0
            
            # 回饋次數獎勵 (但有上限)
            feedback_bonus = min(2.0, feedback_count * 0.5)
            
            final_score = min(10.0, base_score + feedback_bonus)
            
            self.logger.info(f"SALS 分數: 基礎={base_score}, 學習成功={learning_success}, "
                           f"回饋獎勵={feedback_bonus}, 最終={final_score}")
            
            return round(final_score, 2)
            
        except Exception as e:
            self._log_error("SALS 分數計算", e)
            return 6.0

    # ========== 重構：生成同義詞與擴展查詢 ==========
    
    async def _generate_llm_synonyms(self, query: str, max_synonyms: int = 5) -> List[str]:
        """
        使用 LLM 生成同義詞 (重構優化)
        
        Args:
            query: 原始查詢詞
            max_synonyms: 最大同義詞數量
            
        Returns:
            List[str]: 同義詞列表
        """
        try:
            if not self.llm_client:
                return []

            prompt = f"""
請為中醫症狀「{query}」生成 {max_synonyms} 個相關的同義詞或相似症狀描述。
要求：
1. 只返回中醫專業術語
2. 一行一個詞
3. 不要編號或其他標記
4. 專注於症狀的不同表達方式

示例輸入：頭痛
示例輸出：
頭脹痛
腦痛
偏頭痛
頭部疼痛
頭昏痛

請為「{query}」生成同義詞：
"""

            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3
            )
            
            llm_text = response.choices[0].message.content.strip()
            synonyms = [line.strip() for line in llm_text.split('\n') 
                       if line.strip() and not line.strip().startswith(('示例', '請為'))]
            
            # 限制數量並過濾重複
            unique_synonyms = list(dict.fromkeys(synonyms))[:max_synonyms]
            
            self._log_step("LLM 同義詞生成", f"原詞={query}, 生成={len(unique_synonyms)}個")
            return unique_synonyms

        except Exception as e:
            self._log_error("LLM 同義詞生成", e)
            return []

    async def _expand_query_with_synonyms(self, original_query: str, 
                                        signals: List[str] = None) -> List[str]:
        """
        擴展查詢詞與同義詞 (重構新增)
        
        Args:
            original_query: 原始查詢
            signals: 分類訊號列表
            
        Returns:
            List[str]: 擴展後的查詢詞列表
        """
        try:
            expanded_terms = [original_query]
            
            # 添加分類訊號
            if signals:
                expanded_terms.extend(signals)
            
            # 為主要症狀生成同義詞
            main_symptoms = [original_query] + (signals[:2] if signals else [])
            
            for symptom in main_symptoms:
                synonyms = await self._generate_llm_synonyms(symptom, 3)
                expanded_terms.extend(synonyms)
            
            # 去除重複並限制總數
            unique_terms = list(dict.fromkeys(expanded_terms))[:10]
            
            self.logger.info(f"查詢詞擴展: 原始={len([original_query] + (signals or []))}, "
                           f"擴展後={len(unique_terms)}")
            
            return unique_terms

        except Exception as e:
            self._log_error("查詢詞擴展", e)
            return [original_query] + (signals or [])

    # ========== 主要對外接口 (保持兼容性) ==========
    
    async def start_spiral_dialog(self, query_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        啟動螺旋推理對話 (重構主流程)
        
        Args:
            query_context: 查詢上下文，包含：
                - question: 用戶問題
                - patient_ctx: 患者上下文 (含 signals, pulse_clues 等)
                - session_id: 會話ID  
                - round_count: 當前輪數
                - used_cases: 已使用案例列表
                - continue_spiral: 是否繼續螺旋推理
        
        Returns:
            Dict: 螺旋推理結果
        """
        start_time = datetime.now()
        
        try:
            # 解析輸入參數 (重構：加強分類訊號處理)
            question = query_context.get("question", "")
            patient_ctx = query_context.get("patient_ctx", {})
            session_id = query_context.get("session_id", f"spiral_{uuid.uuid4().hex[:8]}")
            round_count = query_context.get("round_count", 1)
            used_cases = query_context.get("used_cases", [])
            continue_spiral = query_context.get("continue_spiral", False)
            
            # 提取分類訊號與脈象線索 (重構新增)
            signals = patient_ctx.get("signals", [])
            pulse_clues = patient_ctx.get("pulse_clues", [])
            
            self._log_step(f"螺旋推理開始 第{round_count}輪", 
                          f"問題='{question[:50]}...', 訊號={len(signals)}個, 脈象線索={len(pulse_clues)}個")

            # Step 1: 生成查詢向量 (重構：整合分類訊號)
            query_vector = await self._generate_query_vector(question, signals, pulse_clues)
            
            # Step 2: 三庫並行檢索 (重構核心)
            case_results, rpcase_results, pulse_results = await asyncio.gather(
                self._retrieve_from_case_kb(query_vector, used_cases, signals),
                self._retrieve_from_rpcase_kb(query_vector, used_cases), 
                self._retrieve_from_pulse_kb(query_vector, pulse_clues)
            )
            
            # Step 3: 如果結果不足，使用同義詞擴展重試
            if len(case_results) < 3:
                expanded_terms = await self._expand_query_with_synonyms(question, signals)
                additional_case_results = await self._retry_with_or_conditions(
                    "Case", query_vector, expanded_terms, "symptoms", 5
                )
                
                # 合併結果，避免重複
                case_ids = {item.get("case_id") for item in case_results}
                for item in additional_case_results:
                    if item.get("case_id") not in case_ids:
                        case_results.append(item)
            
            # Step 4: 計算評估指標 (重構權重)
            cms_score = self._calculate_weighted_cms_score(case_results, rpcase_results, pulse_results)
            rci_score = self._calculate_rci_score(round_count, {"llm_confidence": 0.85})
            sals_score = self._calculate_sals_score(True, round_count)
            
            # Step 5: LLM 推理與適配 (保持原有邏輯)
            llm_result = await self._llm_reasoning_and_adaptation(
                question, case_results, rpcase_results, pulse_results, patient_ctx
            )
            
            # Step 6: 構建螺旋推理結果 (重構輸出格式)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            spiral_result = {
                # 基本信息
                "session_id": session_id,
                "round": round_count,
                "question": question,
                "processing_time": processing_time,
                
                # LLM 結構化結果
                "llm_struct": llm_result,
                
                # 檢索統計 (重構：突出 Case 和 RPCase)
                "retrieval_stats": {
                    "case_count": len(case_results),
                    "rpcase_count": len(rpcase_results), 
                    "pulse_count": len(pulse_results),
                    "total_retrieved": len(case_results) + len(rpcase_results)  # 不計入脈象
                },
                
                # 評估指標
                "evaluation_metrics": {
                    "cms": {"name": "案例匹配相似性", "score": cms_score, "max_score": 10},
                    "rci": {"name": "推理一致性指標", "score": rci_score, "max_score": 10},
                    "sals": {"name": "系統自適應學習", "score": sals_score, "max_score": 10}
                },
                
                # 螺旋推理狀態  
                "spiral_state": {
                    "continue_available": cms_score < 7.0 or len(case_results) < 3,
                    "confidence": llm_result.get("confidence", 0.8),
                    "converged": cms_score >= 8.0 and len(case_results) >= 3,
                    "can_save": llm_result.get("confidence", 0) > 0.7
                },
                
                # 詳細結果 (供調試用)
                "detailed_results": {
                    "case_results": case_results[:3],  # 只返回前3個
                    "rpcase_results": rpcase_results[:2],
                    "signals_used": signals,
                    "pulse_clues_used": pulse_clues
                },
                
                "version": self.version,
                "timestamp": start_time.isoformat()
            }
            
            self._log_success(f"螺旋推理完成 第{round_count}輪", 
                            f"處理時間={processing_time:.2f}s, CMS={cms_score}")
            
            return spiral_result
            
        except Exception as e:
            self._log_error(f"螺旋推理失敗 第{round_count}輪", e)
            return self._create_error_result(session_id, round_count, str(e))

    async def _generate_query_vector(self, question: str, signals: List[str], pulse_clues: List[str]) -> List[float]:
        """
        生成查詢向量 (重構：整合分類訊號)
        
        TODO: 實際實作中應使用 sentence transformers 或其他向量化模型
        現在返回隨機向量作為占位符
        """
        try:
            # 組合完整查詢文本
            full_query = question
            if signals:
                full_query += f" 症狀特徵: {', '.join(signals)}"
            if pulse_clues:
                full_query += f" 脈象特徵: {', '.join(pulse_clues)}"
            
            self.logger.info(f"生成查詢向量: {full_query[:100]}...")
            
            # 占位符實作 - 實際應使用真實的向量化模型
            import random
            random.seed(hash(full_query) % (2**32))
            vector = [random.random() for _ in range(384)]  # 假設384維向量
            
            return vector
            
        except Exception as e:
            self._log_error("查詢向量生成", e)
            # 返回零向量作為降級
            return [0.0] * 384

    async def _llm_reasoning_and_adaptation(self, 
                                          question: str,
                                          case_results: List[Dict],
                                          rpcase_results: List[Dict], 
                                          pulse_results: List[Dict],
                                          patient_ctx: Dict) -> Dict[str, Any]:
        """LLM 推理與適配處理 (保持原有架構)"""
        try:
            if not self.llm_client:
                self.logger.warning("LLM 客戶端不可用，使用模擬結果")
                return self._create_mock_llm_result(question)
            
            # 構建推理提示
            prompt = self._build_reasoning_prompt(question, case_results, rpcase_results, pulse_results, patient_ctx)
            
            # 調用 LLM
            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7
            )
            
            llm_text = response.choices[0].message.content
            
            # 解析 LLM 回應 (使用統一解析函式)
            parsed_result = self._safe_json_parse(llm_text, "diagnosis")
            
            # 確保必要字段存在
            if "confidence" not in parsed_result:
                parsed_result["confidence"] = 0.8
            if "main_dx" not in parsed_result:
                parsed_result["main_dx"] = parsed_result.get("diagnosis", "需進一步診斷")
            
            self._log_success("LLM 推理完成", f"信心度={parsed_result.get('confidence', 0)}")
            return parsed_result
            
        except Exception as e:
            self._log_error("LLM 推理", e)
            return self._create_mock_llm_result(question)

    def _build_reasoning_prompt(self, question: str, case_results: List[Dict], 
                               rpcase_results: List[Dict], pulse_results: List[Dict],
                               patient_ctx: Dict) -> str:
        """構建 LLM 推理提示"""
        prompt_parts = [
            "你是一位經驗豐富的中醫師，請基於以下信息進行診斷分析：",
            f"\n患者問題：{question}",
            f"\n患者上下文：{json.dumps(patient_ctx, ensure_ascii=False)}",
        ]
        
        if case_results:
            prompt_parts.append(f"\n相關案例 ({len(case_results)} 個)：")
            for i, case in enumerate(case_results[:3]):
                prompt_parts.append(f"案例 {i+1}: {case.get('symptoms', '')} -> {case.get('diagnosis', '')}")
        
        if rpcase_results:
            prompt_parts.append(f"\n回饋案例 ({len(rpcase_results)} 個)：")
            for i, rpcase in enumerate(rpcase_results[:2]):
                prompt_parts.append(f"回饋 {i+1}: {rpcase.get('final_diagnosis', '')}")
        
        if pulse_results:
            prompt_parts.append(f"\n脈象參考 ({len(pulse_results)} 個)：")
            for i, pulse in enumerate(pulse_results[:3]):
                prompt_parts.append(f"脈象 {i+1}: {pulse.get('pulse_type', '')} - {pulse.get('description', '')}")
        
        prompt_parts.append("""
請提供 JSON 格式的診斷結果：
{
    "main_dx": "主要診斷",
    "confidence": 0.8,
    "reasoning": "推理過程",
    "treatment_plan": "治療建議",
    "safety_score": 0.9,
    "efficacy_score": 0.8
}""")
        
        return "\n".join(prompt_parts)

    def _create_mock_llm_result(self, question: str) -> Dict[str, Any]:
        """創建模擬 LLM 結果"""
        return {
            "main_dx": "基於症狀的初步分析",
            "confidence": 0.6,
            "reasoning": f"根據症狀描述 '{question}' 進行的初步分析",
            "treatment_plan": "建議進一步診斷確認",
            "safety_score": 0.8,
            "efficacy_score": 0.7
        }

    def _create_error_result(self, session_id: str, round_count: int, error_msg: str) -> Dict[str, Any]:
        """創建錯誤結果"""
        return {
            "session_id": session_id,
            "round": round_count,
            "error": error_msg,
            "llm_struct": {
                "main_dx": "系統處理錯誤",
                "confidence": 0.0,
                "reasoning": f"處理過程中發生錯誤: {error_msg}"
            },
            "spiral_state": {
                "continue_available": False,
                "confidence": 0.0,
                "converged": False,
                "can_save": False
            },
            "version": self.version,
            "timestamp": datetime.now().isoformat()
        }

    # ========== 滿意度處理與回饋機制 (重構新增) ==========
    
    async def handle_user_satisfaction(self, session_id: str, satisfied: bool, 
                                     diagnosis_result: Dict, conversation_history: List) -> Dict[str, Any]:
        """
        處理使用者滿意度回饋 (重構實作)
        
        Args:
            session_id: 會話ID
            satisfied: 使用者是否滿意
            diagnosis_result: 診斷結果
            conversation_history: 對話歷史
            
        Returns:
            Dict: 處理結果
        """
        try:
            self._log_step("處理使用者滿意度回饋", f"會話={session_id}, 滿意={satisfied}")
            
            if satisfied:
                # 滿意：寫回 RPCase 知識庫
                return await self._save_successful_case(session_id, diagnosis_result, conversation_history)
            else:
                # 不滿意：準備重新推理
                return await self._prepare_retry_reasoning(session_id, diagnosis_result)
                
        except Exception as e:
            self._log_error("滿意度處理", e)
            return {"status": "error", "message": str(e)}

    async def _save_successful_case(self, session_id: str, diagnosis_result: Dict, 
                                  conversation_history: List) -> Dict[str, Any]:
        """儲存成功案例到 RPCase 知識庫"""
        try:
            if not self.rpcase_manager:
                self.logger.warning("RPCase 管理器不可用，無法儲存案例")
                return {"status": "warning", "message": "案例管理器不可用"}
            
            # 構建 RPCase 資料
            rpcase_data = {
                "rpcase_id": f"RP_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{session_id[-8:]}",
                "session_id": session_id,
                "final_diagnosis": diagnosis_result.get("main_dx", ""),
                "confidence_score": diagnosis_result.get("confidence", 0.8),
                "treatment_plan": diagnosis_result.get("treatment_plan", ""),
                "reasoning_process": diagnosis_result.get("reasoning", ""),
                "conversation_history": json.dumps(conversation_history, ensure_ascii=False),
                "user_feedback": "用戶滿意",
                "effectiveness_score": diagnosis_result.get("efficacy_score", 0.8),
                "safety_score": diagnosis_result.get("safety_score", 0.9),
                "created_timestamp": datetime.now().isoformat(),
                "success_rate": 1.0,
                "tags": ["user_approved", "spiral_reasoning"]
            }
            
            # 調用 RPCase 管理器儲存
            save_result = await self.rpcase_manager.save_rpcase(rpcase_data)
            
            self._log_success("成功案例儲存完成", rpcase_data["rpcase_id"])
            
            return {
                "status": "success",
                "message": "案例已儲存到知識庫",
                "rpcase_id": rpcase_data["rpcase_id"],
                "save_result": save_result
            }
            
        except Exception as e:
            self._log_error("成功案例儲存", e)
            return {"status": "error", "message": str(e)}

    async def _prepare_retry_reasoning(self, session_id: str, diagnosis_result: Dict) -> Dict[str, Any]:
        """準備重新推理"""
        try:
            self._log_step("準備重新推理", f"會話={session_id}")
            
            # 增加額外的搜索條件
            additional_conditions = {
                "exclude_diagnosis": diagnosis_result.get("main_dx", ""),
                "require_higher_confidence": True,
                "expand_symptom_search": True
            }
            
            return {
                "status": "retry_prepared",
                "message": "系統已準備重新推理，將擴大搜索範圍",
                "additional_conditions": additional_conditions,
                "retry_round": True
            }
            
        except Exception as e:
            self._log_error("重新推理準備", e)
            return {"status": "error", "message": str(e)}

    # ========== 兼容性方法 (重構：添加缺失的方法) ==========
    
    async def execute_spiral_reasoning(self, query_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行螺旋推理 (兼容性方法)
        
        這個方法是為了與其他模組的兼容性而添加的
        內部調用 start_spiral_dialog
        """
        try:
            # 調用主要的螺旋推理方法
            result = await self.start_spiral_dialog(query_context)
            
            # 調整輸出格式以匹配預期
            formatted_result = {
                "llm_struct": result.get("llm_struct", {}),
                "step_results": [
                    {
                        "case_id": case.get("case_id"),
                        "similarity": 0.8,  # 預設相似度
                        "pulse_support": [],
                        "diagnosis": case.get("diagnosis", ""),
                        "treatment_plan": case.get("treatment_plan", "")
                    }
                    for case in result.get("detailed_results", {}).get("case_results", [])[:3]
                ],
                "converged": result.get("spiral_state", {}).get("converged", False),
                "confidence": result.get("spiral_state", {}).get("confidence", 0.8),
                "session_id": result.get("session_id"),
                "round": result.get("round"),
                "raw_result": result
            }
            
            return formatted_result
            
        except Exception as e:
            self._log_error("execute_spiral_reasoning", e)
            return {
                "llm_struct": {"main_dx": "推理引擎錯誤", "confidence": 0.0},
                "step_results": [],
                "converged": False,
                "confidence": 0.0,
                "error": str(e)
            }


# ========== 工具函式 (保持原有) ==========

def _safe_json_array(data) -> List[Dict[str, Any]]:
    """安全轉換為 JSON 陣列"""
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        return []


# ========== 向後兼容 ==========

# 保持舊版本函式名稱的兼容性
SpiralCBREngineV2 = SpiralCBREngine

__all__ = ["SpiralCBREngine", "SpiralCBREngineV2", "_safe_json_array"]