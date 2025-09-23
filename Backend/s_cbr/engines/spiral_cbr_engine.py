"""
S-CBR 螺旋推理引擎 v2.1 - Backend 配置整合版

整合真實 LLM 調用邏輯、Step1-4 實際實現、三個向量庫檢索和螺旋推理多輪對話邏輯
使用 SCBRConfig v2.1 統一配置管理

核心功能：
1. 真實 LLM 調用邏輯 (通過 SCBRConfig)
2. Step1-4 的實際實現
3. 三個向量庫（Case、PulsePJ、RPCase）的整合檢索
4. 螺旋推理的多輪對話邏輯
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

try:
    from ..utils.spiral_logger import SpiralLogger
    logger = SpiralLogger.get_logger("SpiralCBREngine")
except ImportError:
    logger = logging.getLogger("SpiralCBREngine")

try:
    from ..config.scbr_config import SCBRConfig
except ImportError:
    logger.warning("無法載入 SCBRConfig")
    SCBRConfig = None

try:
    from ..knowledge.rpcase_manager import RPCaseManager
except ImportError:
    logger.warning("無法載入 RPCaseManager")
    RPCaseManager = None

class SpiralCBREngine:
    """
    S-CBR 螺旋推理引擎 v2.1 - Backend 配置整合版
    
    整合三個向量知識庫：
    - Case: 傳統中醫病例知識庫
    - PulsePJ: 中醫脈象診斷知識庫  
    - RPCase: 螺旋推理回饋案例知識庫
    
    支援完整的螺旋推理流程：
    Step 1: 案例檢索 (Case Retrieval)
    Step 2: 案例適配 (Case Adaptation) 
    Step 3: 方案監控 (Solution Monitoring)
    Step 4: 反饋學習 (Feedback Learning)
    """
    
    def __init__(self):
        """初始化螺旋 CBR 引擎 v2.1"""
        self.logger = logger
        self.config = SCBRConfig() if SCBRConfig else None
        
        # 初始化組件
        self._init_llm_client()
        self._init_weaviate_client()
        self._init_rpcase_manager()
        
        # 推理狀態
        self.conversation_history = []
        self.current_session_id = None
        self.used_cases = []
        
        self.version = "2.1"
        self.logger.info(f"S-CBR 螺旋推理引擎 v{self.version} 初始化完成")
    
    def _init_llm_client(self):
        """初始化 LLM 客戶端 - v2.1 使用 SCBRConfig"""
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
        """初始化 Weaviate 向量資料庫客戶端 - v2.1 使用 SCBRConfig"""
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
            if RPCaseManager and self.weaviate_client:
                self.rpcase_manager = RPCaseManager(self.weaviate_client)
                self.logger.info("✅ RPCase 管理器初始化成功")
            else:
                self.rpcase_manager = None
                self.logger.warning("RPCase 管理器不可用")
        except Exception as e:
            self.logger.error(f"RPCase 管理器初始化失敗: {e}")
            self.rpcase_manager = None

    async def start_spiral_dialog(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        啟動螺旋推理對話 v2.1
        
        Args:
            query: 查詢參數
                - question: 患者問題描述
                - session_id: 會話ID  
                - round: 當前輪次
                - used_cases: 已使用案例列表
                - continue_spiral: 是否繼續螺旋推理
                
        Returns:
            Dict: 螺旋推理結果
        """
        try:
            # 提取查詢參數
            question = query.get("question", "")
            session_id = query.get("session_id", "")
            current_round = query.get("round", 1)
            used_cases = query.get("used_cases", [])
            patient_ctx = query.get("patient_ctx", {})
            trace_id = query.get("trace_id", "")
            
            self.current_session_id = session_id
            self.used_cases = used_cases
            
            self.logger.info(f"開始螺旋推理 v2.1 - Session: {session_id}, Round: {current_round}")
            self.logger.info(f"已使用案例數: {len(used_cases)}")
            
            # Step 1: 案例檢索 (Case Retrieval)
            self.logger.info(f"Step 1 - 案例檢索 v2.1 (Round {current_round})")
            retrieved_cases = await self._step1_case_retrieval(question, patient_ctx, used_cases)
            
            # Step 2: 案例適配 (Case Adaptation)
            self.logger.info(f"Step 2 - 案例適配 v2.1 (Round {current_round})")
            adapted_solution = await self._step2_case_adaptation(question, patient_ctx, retrieved_cases)
            
            # Step 3: 方案監控 (Solution Monitoring)
            self.logger.info(f"Step 3 - 方案監控 v2.1 (Round {current_round})")
            monitoring_result = await self._step3_solution_monitoring(question, adapted_solution, retrieved_cases)
            
            # Step 4: 反饋學習 (Feedback Learning)
            self.logger.info(f"Step 4 - 反饋學習 v2.1 (Round {current_round})")
            final_result = await self._step4_feedback_learning(question, monitoring_result, retrieved_cases)
            
            self.logger.info(f"螺旋推理 v2.1 完成 - Session: {session_id}, Round: {current_round}")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"螺旋推理失敗: {str(e)}")
            return {
                "error": True,
                "error_message": str(e),
                "diagnosis": "推理過程發生錯誤",
                "treatment_plan": "請重新嘗試或尋求專業醫師協助",
                "confidence": 0.0,
                "safety_score": 0.0,
                "efficacy_score": 0.0,
                "case_used": "",
                "llm_struct": {"error": str(e)}
            }

    async def _step1_case_retrieval(self, question: str, patient_ctx: Dict[str, Any], used_cases: List[str]) -> Dict[str, Any]:
        """
        Step 1: 案例檢索 - 從三個向量庫檢索相關案例 v2.1
        
        整合檢索策略：
        1. Case 知識庫 - 傳統中醫病例
        2. PulsePJ 知識庫 - 脈象診斷知識  
        3. RPCase 知識庫 - 螺旋推理回饋案例
        """
        try:
            retrieved_cases = {
                "Case": [],
                "pulse_knowledge": [],
                "feedback_cases": [],
                "total_retrieved": 0
            }
            
            if not self.weaviate_client:
                self.logger.warning("Weaviate 客戶端不可用，嘗試其他檢索方式")
                
                # 嘗試使用現有的檢索系統
                try:
                    # 導入現有的案例檢索器
                    from ..steps.step1_case_finder import Step1CaseFinder
                    case_finder = Step1CaseFinder()
                    existing_cases = await case_finder.find_similar_cases(question, limit=3)
                    
                    if existing_cases:
                        retrieved_cases["cases"] = existing_cases
                        retrieved_cases["total_retrieved"] = len(existing_cases)
                        self.logger.info(f"使用現有檢索系統找到 {len(existing_cases)} 個案例")
                        return retrieved_cases
                except Exception as e:
                    self.logger.error(f"現有檢索系統失敗: {e}")
                
                # 最後降級到模擬案例
                return self._get_mock_cases(question)
            
            # 使用 Weaviate 檢索
            query_vector = await self._generate_query_vector(question)
            
            # 1. 檢索 Case 知識庫
            try:
                case_results = await self._retrieve_from_case_kb(query_vector, used_cases, limit=3)
                retrieved_cases["cases"] = case_results
                self.logger.info(f"Case 知識庫檢索: {len(case_results)} 個案例")
            except Exception as e:
                self.logger.error(f"Case 知識庫檢索失敗: {e}")
            
            # 2. 檢索 PulsePJ 知識庫  
            try:
                pulse_results = await self._retrieve_from_pulse_kb(query_vector, limit=2)
                retrieved_cases["pulse_knowledge"] = pulse_results
                self.logger.info(f"PulsePJ 知識庫檢索: {len(pulse_results)} 個脈象知識")
            except Exception as e:
                self.logger.error(f"PulsePJ 知識庫檢索失敗: {e}")
            
            # 3. 檢索 RPCase 知識庫
            if self.rpcase_manager:
                try:
                    rpcase_results = await self.rpcase_manager.search_similar_rpcases(question, limit=2)
                    retrieved_cases["feedback_cases"] = rpcase_results
                    self.logger.info(f"RPCase 知識庫檢索: {len(rpcase_results)} 個回饋案例")
                except Exception as e:
                    self.logger.error(f"RPCase 知識庫檢索失敗: {e}")
            
            retrieved_cases["total_retrieved"] = (
                len(retrieved_cases["cases"]) + 
                len(retrieved_cases["pulse_knowledge"]) + 
                len(retrieved_cases["feedback_cases"])
            )
            
            self.logger.info(f"Step 1 完成 - 總檢索案例數: {retrieved_cases['total_retrieved']}")
            
            # 如果沒有檢索到任何案例，使用模擬案例
            if retrieved_cases["total_retrieved"] == 0:
                self.logger.warning("未檢索到任何案例，使用模擬案例")
                return self._get_mock_cases(question)
            
            return retrieved_cases
            
        except Exception as e:
            self.logger.error(f"Step 1 案例檢索失敗: {e}")
            return self._get_mock_cases(question)

    async def _retrieve_from_case_kb(self, query_vector: List[float], used_cases: List[str], limit: int = 3) -> List[Dict[str, Any]]:
        """從 Case 知識庫檢索案例"""
        try:
            # 檢查 Case class 是否存在
            schema = self.weaviate_client.schema.get()
            available_classes = [cls['class'] for cls in schema.get('classes', [])]
            
            if 'Case' not in available_classes:
                self.logger.warning(f"Case 類別不存在於 Weaviate Schema 中。可用類別: {available_classes}")
                return []
            
            query_builder = (
                self.weaviate_client.query
                .get("Case", [
                    "case_id", "age", "gender", "chief_complaint", 
                    "present_illness", "diagnosis_main", "treatment_plan", "summary"
                ])
                .with_near_vector({
                    "vector": query_vector,
                    "certainty": 0.7  # 降低相似度門檻
                })
                .with_limit(limit)
            )
            
            # 如果有已使用案例，添加過濾條件
            if used_cases:
                where_filter = {
                    "path": ["case_id"],
                    "operator": "NotEqual",
                    "valueString": used_cases[0] if len(used_cases) == 1 else used_cases
                }
                query_builder = query_builder.with_where(where_filter)
            
            result = query_builder.do()
            cases = result.get("data", {}).get("Get", {}).get("Case", [])
            
            self.logger.info(f"從 Case 知識庫檢索到 {len(cases)} 個案例")
            return cases
            
        except Exception as e:
            self.logger.error(f"Case 知識庫檢索失敗: {e}")
            return []

    async def _retrieve_from_pulse_kb(self, query_vector: List[float], limit: int = 2) -> List[Dict[str, Any]]:
        """從 PulsePJ 脈象知識庫檢索"""
        try:
            # 檢查 PulsePJ class 是否存在
            schema = self.weaviate_client.schema.get()
            available_classes = [cls['class'] for cls in schema.get('classes', [])]
            
            if 'PulsePJ' not in available_classes:
                self.logger.warning(f"PulsePJ 類別不存在於 Weaviate Schema 中。可用類別: {available_classes}")
                return []
            
            result = (
                self.weaviate_client.query
                .get("PulsePJ", [
                    "pulse_id", "pulse_name", "pulse_description",
                    "associated_conditions", "diagnostic_significance", "treatment_approach"
                ])
                .with_near_vector({
                    "vector": query_vector,
                    "certainty": 0.6  # 降低相似度門檻
                })
                .with_limit(limit)
                .do()
            )
            
            pulses = result.get("data", {}).get("Get", {}).get("PulsePJ", [])
            self.logger.info(f"從 PulsePJ 知識庫檢索到 {len(pulses)} 個脈象知識")
            return pulses
            
        except Exception as e:
            self.logger.error(f"PulsePJ 知識庫檢索失敗: {e}")
            return []

    async def _generate_query_vector(self, text: str) -> List[float]:
        """生成查詢文本的向量表示 - v2.1 使用 SCBRConfig"""
        try:
            if not self.config:
                self.logger.error("SCBRConfig 不可用，無法生成向量")
                return [0.0] * 384
            
            # 通過 SCBRConfig 獲取 Embedding 配置
            embedding_config = self.config.get_embedding_config()
            
            embedding_api_key = embedding_config.get("api_key", "")
            embedding_base_url = embedding_config.get("base_url", "https://integrate.api.nvidia.com/v1")
            embedding_model = embedding_config.get("model", "nvidia/nv-embedqa-e5-v5")
            
            self.logger.info(f"Embedding 配置載入: URL={embedding_base_url}, Model={embedding_model}, Key={'有' if embedding_api_key else '無'}")
            
            # 方案 1: 使用 NVIDIA Embeddings API
            if embedding_api_key and embedding_api_key != "" and embedding_api_key != "None":
                import httpx
                async with httpx.AsyncClient() as client:
                    # 修正 API 調用格式
                    payload = {
                        "input": [text],  # 確保是陣列格式
                        "model": embedding_model,
                        "input_type": "query",
                        "encoding_format": "float"
                    }
                    
                    headers = {
                        "Authorization": f"Bearer {embedding_api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    
                    self.logger.debug(f"調用 Embedding API: {embedding_base_url}/embeddings")
                    self.logger.debug(f"Payload: {payload}")
                    
                    response = await client.post(
                        f"{embedding_base_url}/embeddings",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        vector = result["data"][0]["embedding"]
                        self.logger.info(f"✅ 生成 {len(vector)} 維向量 (NVIDIA Embedding)")
                        return vector
                    else:
                        error_detail = response.text
                        self.logger.error(f"❌ NVIDIA Embedding API 錯誤: {response.status_code} - {error_detail}")
                        # 不要拋出異常，繼續到下一個方案
            else:
                self.logger.warning("Embedding API Key 未設置，跳過 NVIDIA Embedding")
            
            # 方案 2: 降級到 OpenAI Embeddings (如果有 OpenAI 客戶端)
            if hasattr(self, 'llm_client') and self.llm_client:
                try:
                    # 嘗試使用 LLM 客戶端的 embeddings
                    self.logger.info("嘗試使用 LLM 客戶端生成向量")
                    response = await self.llm_client.embeddings.create(
                        input=text,
                        model="text-embedding-ada-002"
                    )
                    vector = response.data[0].embedding
                    self.logger.info(f"✅ 生成 {len(vector)} 維向量 (通過 LLM 客戶端)")
                    return vector
                except Exception as e:
                    self.logger.warning(f"通過 LLM 客戶端生成向量失敗: {e}")
            
            # 方案 3: 使用本地 Sentence Transformers (如果可用)
            try:
                from sentence_transformers import SentenceTransformer
                
                # 使用中文友好的模型
                model = SentenceTransformer('all-MiniLM-L6-v2')
                vector = model.encode(text).tolist()
                self.logger.info(f"✅ 生成 {len(vector)} 維向量 (SentenceTransformers)")
                return vector
                
            except ImportError:
                self.logger.warning("SentenceTransformers 不可用")
            except Exception as e:
                self.logger.warning(f"SentenceTransformers 失敗: {e}")
            
            # 方案 4: 使用簡單的文本特徵向量化
            try:
                import hashlib
                
                # 基於文本內容生成一致的特徵向量
                words = text.split()
                vector = []
                
                # 生成基於詞彙的特徵
                for i in range(1536):
                    if i < len(words):
                        word_hash = hashlib.md5(words[i].encode('utf-8')).hexdigest()
                        feature = int(word_hash[:8], 16) / (16**8)  # 標準化到 0-1
                    else:
                        # 使用文本全體hash生成補充特徵
                        text_hash = hashlib.md5((text + str(i)).encode('utf-8')).hexdigest()
                        feature = int(text_hash[:8], 16) / (16**8)
                    
                    vector.append(feature)
                
                self.logger.info(f"✅ 生成 {len(vector)} 維特徵向量 (基於文本特徵)")
                return vector
                
            except Exception as e:
                self.logger.warning(f"文本特徵向量化失敗: {e}")
            
            # 最後降級：改進的隨機向量（基於文本內容）
            import hashlib
            
            # 基於文本內容生成一致的「隨機」向量
            text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
            import random
            random.seed(int(text_hash[:8], 16))  # 使用文本hash作為種子
            
            vector = [random.random() for _ in range(1536)]
            self.logger.warning(f"⚠️ 使用基於內容的模擬向量 (seed: {text_hash[:8]})")
            return vector
                
        except Exception as e:
            self.logger.error(f"向量生成失敗: {e}")
            # 最終降級：零向量
            return [0.0] * 1536

    def _get_mock_cases(self, question: str) -> Dict[str, Any]:
        """獲取模擬案例數據（當向量庫不可用時）"""
        return {
            "cases": [
                {
                    "case_id": "MOCK_CASE_001",
                    "age": 35,
                    "gender": "女",
                    "chief_complaint": "壓力大，失眠多夢，情緒不穩",
                    "diagnosis_main": "心腎不交，肝氣鬱結",
                    "summary": "模擬案例：壓力性失眠合併情緒不穩的中醫治療"
                }
            ],
            "pulse_knowledge": [
                {
                    "pulse_name": "弦脈", 
                    "pulse_description": "脈象如琴弦，端直而長，主肝膽病",
                    "associated_conditions": "肝氣鬱結，情志不暢，壓力過大"
                }
            ],
            "feedback_cases": [],
            "total_retrieved": 2
        }

    async def _step2_case_adaptation(self, question: str, patient_ctx: Dict[str, Any], retrieved_cases: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: 案例適配 - 使用 LLM 分析檢索案例並適配當前患者
        """
        try:
            if not self.llm_client:
                return self._get_mock_adaptation(retrieved_cases)
            
            # 構建案例適配的 LLM Prompt
            adaptation_prompt = self._build_adaptation_prompt(question, patient_ctx, retrieved_cases)
            
            # 調用 LLM 進行案例適配
            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_tcm_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": adaptation_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            llm_response = response.choices[0].message.content
            self.logger.debug(f"LLM 案例適配回應: {llm_response[:200]}...")
            
            # 解析 LLM 回應
            adapted_result = await self._parse_adaptation_response(llm_response, retrieved_cases)
            
            self.logger.info("Step 2 案例適配完成")
            return adapted_result
            
        except Exception as e:
            self.logger.error(f"Step 2 案例適配失敗: {e}")
            return self._get_mock_adaptation(retrieved_cases)

    def _build_adaptation_prompt(self, question: str, patient_ctx: Dict[str, Any], cases: Dict[str, Any]) -> str:
        """構建案例適配的 LLM Prompt"""
        
        # 格式化檢索到的案例
        cases_text = ""
        
        # 1. 傳統案例
        for i, case in enumerate(cases.get("cases", []), 1):
            cases_text += f"\n【病例 {i}】\n"
            cases_text += f"- 年齡性別: {case.get('age', '未知')}歲，{case.get('gender', '未知')}\n"
            cases_text += f"- 主訴: {case.get('chief_complaint', '')}\n"
            cases_text += f"- 診斷: {case.get('diagnosis_main', '')}\n"
            cases_text += f"- 治療方案: {case.get('treatment_plan', '')}\n"
        
        # 2. 脈象知識
        for i, pulse in enumerate(cases.get("pulse_knowledge", []), 1):
            cases_text += f"\n【脈象知識 {i}】\n"
            cases_text += f"- 脈象: {pulse.get('pulse_name', '')}\n"
            cases_text += f"- 描述: {pulse.get('pulse_description', '')}\n"
            cases_text += f"- 相關病症: {pulse.get('associated_conditions', '')}\n"
        
        # 3. 回饋案例
        for i, rpcase in enumerate(cases.get("feedback_cases", []), 1):
            cases_text += f"\n【回饋案例 {i}】\n"
            cases_text += f"- 原始問題: {rpcase.get('original_question', '')}\n"
            cases_text += f"- 診斷結果: {rpcase.get('final_diagnosis', '')}\n"
            cases_text += f"- 治療方案: {rpcase.get('treatment_plan', '')}\n"
            cases_text += f"- 信心度: {rpcase.get('confidence_score', 0.0):.2f}\n"

        prompt = f"""
作為專業中醫師，請基於檢索到的相關案例，為當前患者提供適配的診斷和治療建議。

【當前患者】
問題描述: {question}
患者背景: {json.dumps(patient_ctx, ensure_ascii=False)}

【相關案例參考】
{cases_text}

【任務要求】
1. 綜合分析當前患者症狀與相關案例的相似性和差異性
2. 基於中醫理論，適配現有案例形成針對性的診斷
3. 提出個性化的治療方案，考慮患者特殊情況
4. 評估診斷信心度、治療安全性和預期療效

【回應格式】
請嚴格按照以下JSON格式回應：
{{
    "analysis": "案例分析過程",
    "primary_diagnosis": "主要診斷",
    "secondary_diagnosis": "次要診斷（如有）",
    "treatment_principle": "治療原則",
    "herbal_formula": "推薦方劑",
    "modifications": "加減用藥",
    "lifestyle_advice": "生活建議",
    "confidence_score": 0.85,
    "safety_score": 0.90,
    "efficacy_score": 0.80,
    "case_similarity": "與參考案例的相似度分析",
    "adaptation_notes": "適配說明"
}}
"""
        return prompt

    async def _parse_adaptation_response(self, llm_response: str, cases: Dict[str, Any]) -> Dict[str, Any]:
        """解析 LLM 案例適配回應"""
        try:
            # 嘗試解析 JSON 回應
            if "{" in llm_response and "}" in llm_response:
                json_start = llm_response.find("{")
                json_end = llm_response.rfind("}") + 1
                json_str = llm_response[json_start:json_end]
                
                parsed = json.loads(json_str)
                
                # 標記使用的案例
                used_case_id = None
                if cases.get("cases"):
                    used_case_id = cases["cases"][0].get("case_id", "")
                
                return {
                    "adapted_diagnosis": parsed.get("primary_diagnosis", ""),
                    "treatment_plan": f"{parsed.get('herbal_formula', '')} {parsed.get('modifications', '')}".strip(),
                    "analysis": parsed.get("analysis", ""),
                    "confidence": float(parsed.get("confidence_score", 0.8)),
                    "safety_score": float(parsed.get("safety_score", 0.9)),
                    "efficacy_score": float(parsed.get("efficacy_score", 0.8)),
                    "case_used_id": used_case_id,
                    "case_similarity": parsed.get("case_similarity", ""),
                    "lifestyle_advice": parsed.get("lifestyle_advice", ""),
                    "raw_llm_response": llm_response,
                    "adaptation_success": True
                }
            else:
                # 非 JSON 格式，嘗試文本解析
                return self._parse_text_adaptation(llm_response, cases)
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"LLM JSON 解析失敗: {e}")
            return self._parse_text_adaptation(llm_response, cases)
        except Exception as e:
            self.logger.error(f"適配回應解析失敗: {e}")
            return self._get_mock_adaptation(cases)

    def _parse_text_adaptation(self, text: str, cases: Dict[str, Any]) -> Dict[str, Any]:
        """解析文本格式的 LLM 回應"""
        try:
            lines = text.split('\n')
            diagnosis = ""
            treatment = ""
            
            for line in lines:
                line = line.strip()
                if any(keyword in line for keyword in ["診斷", "病名", "證型"]):
                    diagnosis = line.split(":")[-1].strip() if ":" in line else line
                elif any(keyword in line for keyword in ["治療", "方劑", "用藥"]):
                    treatment = line.split(":")[-1].strip() if ":" in line else line
            
            used_case_id = cases.get("cases", [{}])[0].get("case_id", "") if cases.get("cases") else ""
            
            return {
                "adapted_diagnosis": diagnosis or "需進一步辨證論治",
                "treatment_plan": treatment or "請諮詢專業中醫師",
                "confidence": 0.7,
                "safety_score": 0.8,
                "efficacy_score": 0.7,
                "case_used_id": used_case_id,
                "adaptation_success": True,
                "raw_llm_response": text
            }
            
        except Exception as e:
            self.logger.error(f"文本適配解析失敗: {e}")
            return self._get_mock_adaptation(cases)

    def _get_mock_adaptation(self, cases: Dict[str, Any]) -> Dict[str, Any]:
        """獲取模擬適配結果"""
        used_case_id = cases.get("cases", [{}])[0].get("case_id", "MOCK_CASE") if cases.get("cases") else "MOCK_CASE"
        
        return {
            "adapted_diagnosis": "肝鬱脾虛證",
            "treatment_plan": "逍遙散加減：柴胡10g, 當歸15g, 白芍15g, 白術12g, 茯苓15g, 甘草6g, 生薑3片, 薄荷6g",
            "confidence": 0.75,
            "safety_score": 0.85,
            "efficacy_score": 0.80,
            "case_used_id": used_case_id,
            "adaptation_success": False,
            "mock_reason": "LLM 客戶端不可用"
        }

    async def _step3_solution_monitoring(self, question: str, adapted_solution: Dict[str, Any], cases: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: 方案監控 - 評估適配方案的安全性、有效性和合理性
        """
        try:
            if not self.llm_client:
                return self._get_mock_monitoring(adapted_solution)
            
            # 構建監控評估的 Prompt
            monitoring_prompt = self._build_monitoring_prompt(question, adapted_solution, cases)
            
            # 調用 LLM 進行方案監控
            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_monitoring_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": monitoring_prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            monitoring_response = response.choices[0].message.content
            self.logger.debug(f"LLM 方案監控回應: {monitoring_response[:200]}...")
            
            # 解析監控結果
            monitoring_result = await self._parse_monitoring_response(monitoring_response, adapted_solution)
            
            self.logger.info("Step 3 方案監控完成")
            return monitoring_result
            
        except Exception as e:
            self.logger.error(f"Step 3 方案監控失敗: {e}")
            return self._get_mock_monitoring(adapted_solution)

    def _build_monitoring_prompt(self, question: str, solution: Dict[str, Any], cases: Dict[str, Any]) -> str:
        """構建方案監控的 Prompt"""
        
        prompt = f"""
作為中醫臨床專家和安全評估師，請對以下診療方案進行全面的安全性、有效性和合理性評估。

【患者情況】
患者問題: {question}

【當前診療方案】
診斷: {solution.get('adapted_diagnosis', '')}
治療方案: {solution.get('treatment_plan', '')}
初始信心度: {solution.get('confidence', 0.0)}

【評估要求】
1. 安全性評估：檢查是否有配伍禁忌、毒副作用、劑量安全性等
2. 有效性評估：基於中醫理論分析方案的治療針對性和預期效果
3. 合理性評估：評估診斷與治療的邏輯一致性，是否符合中醫辨證論治原則
4. 風險識別：識別潛在的治療風險和注意事項
5. 改進建議：提出優化建議

【回應格式】
請嚴格按照以下JSON格式回應：
{{
    "safety_assessment": {{
        "safety_score": 0.90,
        "safety_issues": ["issue1", "issue2"],
        "contraindications": "禁忌事項",
        "side_effects": "可能副作用"
    }},
    "efficacy_assessment": {{
        "efficacy_score": 0.85,
        "treatment_rationale": "治療理論依據",
        "expected_outcomes": "預期療效",
        "treatment_duration": "預估療程"
    }},
    "rationality_assessment": {{
        "logic_score": 0.88,
        "diagnosis_accuracy": "診斷準確性評估",
        "treatment_consistency": "治療一致性評估"
    }},
    "risk_factors": ["risk1", "risk2"],
    "improvement_suggestions": "改進建議",
    "overall_confidence": 0.85,
    "monitoring_notes": "監控要點"
}}
"""
        return prompt

    async def _parse_monitoring_response(self, response: str, solution: Dict[str, Any]) -> Dict[str, Any]:
        """解析監控評估回應"""
        try:
            # 解析 JSON 回應
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                
                parsed = json.loads(json_str)
                
                # 提取評估結果
                safety_score = parsed.get("safety_assessment", {}).get("safety_score", 0.85)
                efficacy_score = parsed.get("efficacy_assessment", {}).get("efficacy_score", 0.80)
                overall_confidence = parsed.get("overall_confidence", 0.82)
                
                return {
                    "monitored_diagnosis": solution.get("adapted_diagnosis", ""),
                    "monitored_treatment": solution.get("treatment_plan", ""),
                    "safety_score": float(safety_score),
                    "efficacy_score": float(efficacy_score),
                    "confidence": float(overall_confidence),
                    "safety_issues": parsed.get("safety_assessment", {}).get("safety_issues", []),
                    "risk_factors": parsed.get("risk_factors", []),
                    "improvement_suggestions": parsed.get("improvement_suggestions", ""),
                    "monitoring_success": True,
                    "raw_monitoring_response": response
                }
            else:
                return self._parse_text_monitoring(response, solution)
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"監控 JSON 解析失敗: {e}")
            return self._parse_text_monitoring(response, solution)
        except Exception as e:
            self.logger.error(f"監控回應解析失敗: {e}")
            return self._get_mock_monitoring(solution)

    def _parse_text_monitoring(self, text: str, solution: Dict[str, Any]) -> Dict[str, Any]:
        """解析文本格式的監控回應"""
        # 簡單的文本解析邏輯
        safety_score = 0.85
        efficacy_score = 0.80
        confidence = 0.82
        
        # 尋找評分相關文本
        if "安全" in text:
            if "高" in text or "良好" in text:
                safety_score = 0.90
            elif "低" in text or "風險" in text:
                safety_score = 0.70
        
        return {
            "monitored_diagnosis": solution.get("adapted_diagnosis", ""),
            "monitored_treatment": solution.get("treatment_plan", ""),
            "safety_score": safety_score,
            "efficacy_score": efficacy_score,
            "confidence": confidence,
            "monitoring_success": True,
            "raw_monitoring_response": text
        }

    def _get_mock_monitoring(self, solution: Dict[str, Any]) -> Dict[str, Any]:
        """獲取模擬監控結果"""
        return {
            "monitored_diagnosis": solution.get("adapted_diagnosis", "肝鬱脾虛證"),
            "monitored_treatment": solution.get("treatment_plan", "逍遙散加減"),
            "safety_score": 0.85,
            "efficacy_score": 0.80,
            "confidence": 0.82,
            "monitoring_success": False,
            "mock_reason": "LLM 客戶端不可用"
        }

    async def _step4_feedback_learning(self, question: str, monitoring_result: Dict[str, Any], cases: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: 反饋學習 - 整合前三步結果，產生最終診斷和治療建議
        """
        try:
            if not self.llm_client:
                return self._get_mock_final_result(monitoring_result)
            
            # 構建最終整合的 Prompt
            learning_prompt = self._build_learning_prompt(question, monitoring_result, cases)
            
            # 調用 LLM 進行最終整合
            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_learning_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": learning_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            learning_response = response.choices[0].message.content
            self.logger.debug(f"LLM 反饋學習回應: {learning_response[:200]}...")
            
            # 解析最終結果
            final_result = await self._parse_learning_response(learning_response, monitoring_result)
            
            self.logger.info("Step 4 反饋學習完成")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Step 4 反饋學習失敗: {e}")
            return self._get_mock_final_result(monitoring_result)

    def _build_learning_prompt(self, question: str, monitoring: Dict[str, Any], cases: Dict[str, Any]) -> str:
        """構建反饋學習的 Prompt"""
        
        prompt = f"""
作為資深中醫專家，請基於完整的螺旋推理過程，為患者提供最終的診療建議和學習反饋。

【患者問題】
{question}

【螺旋推理結果】
診斷: {monitoring.get('monitored_diagnosis', '')}
治療方案: {monitoring.get('monitored_treatment', '')}
安全評分: {monitoring.get('safety_score', 0.85)}
有效評分: {monitoring.get('efficacy_score', 0.80)}
信心度: {monitoring.get('confidence', 0.82)}

【已檢索案例數】
總案例數: {cases.get('total_retrieved', 0)}

【任務要求】
1. 綜合螺旋推理過程，提供最終的診斷結論
2. 完善治療方案，包括具體用藥指導
3. 提供詳細的患者建議和注意事項
4. 評估本次推理的學習價值和可改進點
5. 生成用於螺旋對話的友好回覆

【回應格式】
請嚴格按照以下JSON格式回應：
{{
    "final_diagnosis": "最終診斷",
    "treatment_plan": "完整治療方案",
    "medication_details": "用藥詳情和注意事項",
    "lifestyle_recommendations": "生活方式建議",
    "follow_up_advice": "隨訪建議",
    "safety_score": 0.88,
    "efficacy_score": 0.85,
    "confidence": 0.86,
    "learning_insights": "本次推理的學習洞察",
    "case_used_summary": "使用案例總結",
    "recommendations": "給患者的綜合建議",
    "spiral_dialog": "對話式回覆內容"
}}
"""
        return prompt

    async def _parse_learning_response(self, response: str, monitoring: Dict[str, Any]) -> Dict[str, Any]:
        """解析反饋學習回應"""
        try:
            # 解析 JSON 回應
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                
                parsed = json.loads(json_str)
                
                return {
                    "diagnosis": parsed.get("final_diagnosis", monitoring.get("monitored_diagnosis", "")),
                    "treatment_plan": parsed.get("treatment_plan", monitoring.get("monitored_treatment", "")),
                    "recommendations": parsed.get("recommendations", ""),
                    "safety_score": float(parsed.get("safety_score", monitoring.get("safety_score", 0.85))),
                    "efficacy_score": float(parsed.get("efficacy_score", monitoring.get("efficacy_score", 0.80))),
                    "confidence": float(parsed.get("confidence", monitoring.get("confidence", 0.82))),
                    "case_used": parsed.get("case_used_summary", ""),
                    "case_used_id": monitoring.get("case_used_id", ""),
                    "spiral_dialog": parsed.get("spiral_dialog", ""),
                    "llm_struct": {
                        "main_dx": parsed.get("final_diagnosis", ""),
                        "treatment": parsed.get("treatment_plan", ""),
                        "medication_details": parsed.get("medication_details", ""),
                        "lifestyle": parsed.get("lifestyle_recommendations", ""),
                        "follow_up": parsed.get("follow_up_advice", ""),
                        "learning_insights": parsed.get("learning_insights", ""),
                        "confidence": float(parsed.get("confidence", 0.82))
                    },
                    "learning_success": True,
                    "raw_learning_response": response
                }
            else:
                return self._parse_text_learning(response, monitoring)
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"學習 JSON 解析失敗: {e}")
            return self._parse_text_learning(response, monitoring)
        except Exception as e:
            self.logger.error(f"學習回應解析失敗: {e}")
            return self._get_mock_final_result(monitoring)

    def _parse_text_learning(self, text: str, monitoring: Dict[str, Any]) -> Dict[str, Any]:
        """解析文本格式的學習回應"""
        lines = text.split('\n')
        diagnosis = monitoring.get("monitored_diagnosis", "")
        treatment = monitoring.get("monitored_treatment", "")
        
        for line in lines:
            line = line.strip()
            if "診斷" in line and ":" in line:
                diagnosis = line.split(":")[-1].strip()
            elif "治療" in line and ":" in line:
                treatment = line.split(":")[-1].strip()
        
        return {
            "diagnosis": diagnosis,
            "treatment_plan": treatment,
            "recommendations": "請按時服藥，注意飲食調理",
            "safety_score": monitoring.get("safety_score", 0.85),
            "efficacy_score": monitoring.get("efficacy_score", 0.80),
            "confidence": monitoring.get("confidence", 0.82),
            "case_used": "基於相似案例適配",
            "llm_struct": {
                "main_dx": diagnosis,
                "treatment": treatment,
                "confidence": monitoring.get("confidence", 0.82)
            },
            "learning_success": True,
            "raw_learning_response": text
        }

    def _get_mock_final_result(self, monitoring: Dict[str, Any]) -> Dict[str, Any]:
        """獲取模擬最終結果"""
        return {
            "diagnosis": monitoring.get("monitored_diagnosis", "肝鬱脾虛證"),
            "treatment_plan": monitoring.get("monitored_treatment", "逍遙散加減調治"),
            "recommendations": "建議：保持心情舒暢，規律作息，按時服藥。如症狀持續請及時就醫。",
            "safety_score": monitoring.get("safety_score", 0.85),
            "efficacy_score": monitoring.get("efficacy_score", 0.80),
            "confidence": monitoring.get("confidence", 0.82),
            "case_used": "參考傳統中醫經典案例",
            "llm_struct": {
                "main_dx": monitoring.get("monitored_diagnosis", "肝鬱脾虛證"),
                "treatment": monitoring.get("monitored_treatment", "逍遙散加減"),
                "confidence": monitoring.get("confidence", 0.82),
                "mock_mode": True
            },
            "learning_success": False,
            "mock_reason": "LLM 客戶端不可用，使用預設診療建議"
        }

    def _get_tcm_system_prompt(self) -> str:
        """獲取中醫系統 Prompt"""
        return """
你是一位經驗豐富的中醫師，擅長中醫辨證論治。請基於以下原則進行診療：

1. 中醫基礎理論：陰陽學說、五行學說、藏象學說、經絡學說
2. 診斷方法：望、聞、問、切四診合參
3. 辨證論治：根據證候特點確定治法方藥
4. 整體觀念：將人體看作有機整體，注重內外環境協調
5. 預防思想：治未病，重視養生保健

診療時應：
- 詳細分析患者症狀，準確辨證
- 選方用藥要有理論依據
- 考慮個體差異，個性化治療
- 注重安全性，避免毒副作用
- 給出明確的用法用量和注意事項
"""

    def _get_monitoring_system_prompt(self) -> str:
        """獲取監控評估系統 Prompt"""
        return """
你是中醫臨床安全評估專家，負責評估診療方案的安全性、有效性和合理性。

評估標準：
1. 安全性：配伍禁忌、毒副作用、劑量安全、特殊人群禁忌
2. 有效性：理法方藥一致性、治療針對性、預期療效
3. 合理性：辨證準確性、用藥邏輯、劑量合理性
4. 風險管理：潛在風險識別、預防措施、監測要點

請客觀、專業地評估，提出具體的改進建議。
"""

    def _get_learning_system_prompt(self) -> str:
        """獲取學習整合系統 Prompt"""
        return """
你是中醫臨床決策專家，負責整合螺旋推理過程，提供最終診療建議。

整合要求：
1. 綜合分析前期推理結果，形成最終診斷
2. 完善治療方案，提供具體指導
3. 給出患者友好的建議和注意事項
4. 評估推理過程的學習價值
5. 生成適合患者理解的對話式回覆

回覆應該：專業而易懂、溫暖而負責、具體而實用。
"""

# 導出
__all__ = ["SpiralCBREngine"]
