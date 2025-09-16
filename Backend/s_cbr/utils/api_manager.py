"""
S-CBR API 管理器 v1.1 - 單例模式修復版

完整功能：
- 單例模式防止重複初始化
- 智能速率限制管理 (25 RPM 保守設定)
- 優雅降級策略
- 完整錯誤處理
- 混合向量搜尋支持

版本：v1.1-Singleton
"""

import asyncio
import logging
import time
import random
import threading
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
import hashlib
import math
from collections import deque
from enum import Enum

try:
    from openai import AsyncOpenAI
    import weaviate
    from weaviate.auth import AuthApiKey
    import httpx
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    IMPORT_ERROR = str(e)

from s_cbr.config.scbr_config import SCBRConfig

class RequestPriority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SCBRAPIManager:
    """S-CBR API 管理器 v1.1 - 單例模式"""
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        """🔥 關鍵修復：實現單例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SCBRAPIManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化 API 管理器 - 只執行一次"""
        
        # 🔥 關鍵修復：防止重複初始化
        if self._initialized:
            if hasattr(self, 'logger'):
                self.logger.debug(f"♻️  API 管理器已存在，複用實例 (ID: {id(self)})")
            return
        
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError(f"缺少必要依賴: {IMPORT_ERROR}")
        
        # 🔥 關鍵修復：使用修復後的日誌器
        from s_cbr.utils.spiral_logger import SpiralLogger
        self.logger = SpiralLogger.get_logger("api_manager")
        
        self.config = SCBRConfig()
        self.version = "1.1-singleton"
        self.instance_id = id(self)
        
        self.logger.info(f"🚀 創建新的 API 管理器實例 (ID: {self.instance_id})")
        
        # 初始化所有管理器組件
        self._init_rate_limiter()
        self._init_batch_processor()
        self._init_priority_manager()
        self._init_retry_config()
        self._init_degradation_manager()
        self._init_health_monitor()
        self._init_statistics()
        
        # 初始化客戶端
        self._initialize_clients()
        
        # 啟動後台服務
        self._background_tasks = []
        self._start_background_services()
        
        # 🔥 關鍵修復：設置初始化標記
        SCBRAPIManager._initialized = True
        
        self.logger.info(f"✅ API 管理器單例初始化完成 (ID: {self.instance_id})")
    
    def _init_rate_limiter(self):
        """初始化速率限制器"""
        self.rate_limiter = {
            'requests_per_minute': 25,      # 進一步保守設定
            'request_timestamps': deque(),
            'min_interval': 3.0,            # 增加到3秒間隔
            'last_request_time': 0,
            'burst_allowance': 2,           # 減少突發允許
            'current_burst': 0,
            'daily_quota': 800,             # 減少每日配額
            'daily_used': 0,
            'quota_reset_time': 0
        }
    
    def _init_batch_processor(self):
        """初始化批量處理器"""
        self.batch_processor = {
            'pending_tasks': [],
            'batch_size': 2,                # 減少批量大小
            'batch_timeout': 10,            # 增加超時
            'last_batch_time': 0,
            'batch_stats': {
                'total_batches': 0,
                'total_tasks_processed': 0,
                'api_calls_saved': 0
            }
        }
    
    def _init_priority_manager(self):
        """初始化優先級管理器"""
        self.priority_manager = {
            'queues': {
                RequestPriority.HIGH: deque(),
                RequestPriority.MEDIUM: deque(),
                RequestPriority.LOW: deque()
            },
            'processing': False,
            'processor_lock': asyncio.Lock(),
            'stats': {
                'high_processed': 0,
                'medium_processed': 0,
                'low_processed': 0
            }
        }
    
    def _init_retry_config(self):
        """初始化重試配置"""
        self.retry_config = {
            'max_retries': 4,               # 減少重試次數
            'base_delay': 5,               # 增加基礎延遲
            'max_delay': 120,              # 增加最大延遲
            'exponential_base': 2.0,
            'jitter': True,
            'jitter_range': 0.3
        }
    
    def _init_degradation_manager(self):
        """初始化降級管理器"""
        self.degradation_manager = {
            'fallback_enabled': True,
            'quality_levels': ['full', 'optimized', 'basic', 'minimal'],
            'current_level': 'full',
            'performance_metrics': {
                'success_rate': 1.0,
                'avg_response_time': 0.0,
                'error_count': 0,
                'last_success_time': time.time()
            }
        }
    
    def _init_health_monitor(self):
        """初始化健康監控"""
        self.health_monitor = {
            'last_health_check': 0,
            'health_check_interval': 600,  # 增加到10分鐘
            'api_health_status': 'unknown',
            'consecutive_failures': 0,
            'service_alerts': []
        }
    
    def _init_statistics(self):
        """初始化統計系統"""
        self.statistics = {
            'session_start_time': time.time(),
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_wait_time': 0.0,
            'api_quota_efficiency': 0.0,
            'feature_usage': {
                'batch_processing': 0,
                'priority_scheduling': 0,
                'fallback_responses': 0,
                'rate_limit_waits': 0
            }
        }
    
    def _initialize_clients(self):
        """初始化所有 API 客戶端 - 單例版本"""
        try:
            # 檢查是否已經初始化過客戶端
            if hasattr(self, 'llm_client') and self.llm_client is not None:
                self.logger.info(f"♻️  API 客戶端已存在，跳過重複初始化 (ID: {self.instance_id})")
                return
            
            self.logger.info(f"🔧 初始化 API 客戶端 (ID: {self.instance_id})")
            
            # 使用修復後的 HTTP 傳輸層
            transport = httpx.AsyncHTTPTransport(retries=1)
            
            timeout_config = httpx.Timeout(
                connect=45.0,
                read=180.0,
                write=45.0,
                pool=240.0
            )
            
            connection_limits = httpx.Limits(
                max_keepalive_connections=5,   # 減少連接數
                max_connections=10,
                keepalive_expiry=600
            )
            
            # 創建 HTTP 客戶端
            self.http_client = httpx.AsyncClient(
                transport=transport,
                timeout=timeout_config,
                limits=connection_limits,
                headers={
                    'User-Agent': f'S-CBR-API-Manager-Singleton/{self.version}',
                    'Accept': 'application/json'
                }
            )
            
            # 初始化 LLM 客戶端
            self.llm_client = AsyncOpenAI(
                api_key=self.config.LLM_API_KEY,
                base_url=self.config.LLM_API_URL,
                http_client=self.http_client,
                max_retries=0  # 我們有自己的重試邏輯
            )
            self.llm_model_name = self.config.LLM_MODEL_NAME
            
            # 初始化 Embedding 客戶端
            self.embedding_client = AsyncOpenAI(
                api_key=self.config.EMBEDDING_API_KEY,
                base_url=self.config.EMBEDDING_BASE_URL,
                http_client=self.http_client,
                max_retries=0
            )
            self.embedding_model_name = self.config.EMBEDDING_MODEL_NAME
            
            # 初始化 Weaviate 客戶端
            auth_config = AuthApiKey(api_key=self.config.WV_API_KEY)
            self.weaviate_client = weaviate.Client(
                url=self.config.WEAVIATE_URL,
                auth_client_secret=auth_config
            )
            
            self.logger.info(f"✅ API 客戶端初始化完成 (單例模式 - ID: {self.instance_id})")
            
        except Exception as e:
            self.logger.error(f"❌ API 客戶端初始化失敗: {str(e)}")
            raise
    
    # ==================== 速率限制管理 ====================
    
    async def _wait_for_rate_limit(self):
        """智能速率限制等待"""
        current_time = time.time()
        
        # 每日配額重置檢查
        if current_time - self.rate_limiter['quota_reset_time'] > 86400:
            self.rate_limiter['daily_used'] = 0
            self.rate_limiter['quota_reset_time'] = current_time
            self.logger.info("🔄 每日API配額已重置")
        
        # 檢查每日配額
        if self.rate_limiter['daily_used'] >= self.rate_limiter['daily_quota']:
            self.logger.error("🚫 每日API配額已用盡，啟用降級模式")
            return
        
        # 清理過期的請求記錄
        cutoff_time = current_time - 60
        while (self.rate_limiter['request_timestamps'] and 
               self.rate_limiter['request_timestamps'][0] <= cutoff_time):
            self.rate_limiter['request_timestamps'].popleft()
        
        # 突發限制檢查
        if self.rate_limiter['current_burst'] >= self.rate_limiter['burst_allowance']:
            burst_cooldown = 10
            self.logger.warning(f"⚡ 突發限制觸發，冷卻 {burst_cooldown} 秒")
            await asyncio.sleep(burst_cooldown)
            self.rate_limiter['current_burst'] = 0
            self.statistics['feature_usage']['rate_limit_waits'] += 1
        
        # 每分鐘限制檢查
        recent_requests = len(self.rate_limiter['request_timestamps'])
        if recent_requests >= self.rate_limiter['requests_per_minute']:
            oldest_request = self.rate_limiter['request_timestamps'][0]
            wait_time = 62 - (current_time - oldest_request)
            
            if wait_time > 0:
                self.logger.warning(f"⏳ 每分鐘限制：等待 {wait_time:.1f} 秒 ({recent_requests}/{self.rate_limiter['requests_per_minute']})")
                self.statistics['total_wait_time'] += wait_time
                await asyncio.sleep(wait_time)
                current_time = time.time()
        
        # 最小間隔檢查
        time_since_last = current_time - self.rate_limiter['last_request_time']
        if time_since_last < self.rate_limiter['min_interval']:
            wait_time = self.rate_limiter['min_interval'] - time_since_last
            self.logger.debug(f"⏱️  間隔控制：等待 {wait_time:.1f} 秒")
            await asyncio.sleep(wait_time)
            current_time = time.time()
        
        # 記錄請求
        self.rate_limiter['request_timestamps'].append(current_time)
        self.rate_limiter['last_request_time'] = current_time
        self.rate_limiter['current_burst'] += 1
        self.rate_limiter['daily_used'] += 1
    
    # ==================== 核心 API 方法 ====================
    
    async def generate_llm_response(self, prompt: str, agent_config: Dict[str, Any] = None) -> str:
        """生成 LLM 回應 - 單例版本"""
        return await self._execute_llm_request_with_retry(prompt, agent_config)
    
    async def generate_high_priority_response(self, prompt: str, agent_config: Dict[str, Any] = None) -> str:
        """生成高優先級 LLM 回應"""
        return await self._execute_llm_request_with_retry(prompt, agent_config)
    
    async def _execute_llm_request_with_retry(self, prompt: str, agent_config: Dict[str, Any] = None) -> str:
        """執行 LLM 請求 - 帶重試機制"""
        
        for attempt in range(self.retry_config['max_retries']):
            try:
                # 速率限制檢查
                await self._wait_for_rate_limit()
                
                config = agent_config or self.config.get_llm_config()
                
                self.logger.info(f"🚀 執行LLM請求 (嘗試 {attempt + 1}/{self.retry_config['max_retries']}) - ID: {self.instance_id}")
                
                start_time = time.time()
                
                response = await asyncio.wait_for(
                    self.llm_client.chat.completions.create(
                        model=config.get('model', self.llm_model_name),
                        messages=[
                            {"role": "system", "content": config.get('system_prompt', "你是專業的中醫AI助理。")},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=config.get('temperature', 0.7),
                        max_tokens=config.get('max_tokens', 2000)
                    ),
                    timeout=180  # 3分鐘超時
                )
                
                response_time = time.time() - start_time
                
                # 更新統計
                self.statistics['total_requests'] += 1
                self.statistics['successful_requests'] += 1
                
                self.logger.info(f"✅ LLM請求成功 (耗時: {response_time:.2f}s) - ID: {self.instance_id}")
                
                return response.choices[0].message.content
                
            except Exception as e:
                error_str = str(e).lower()
                
                self.statistics['total_requests'] += 1
                self.statistics['failed_requests'] += 1
                
                if attempt == self.retry_config['max_retries'] - 1:
                    self.logger.error(f"❌ LLM請求最終失敗: {str(e)}")
                    self.statistics['feature_usage']['fallback_responses'] += 1
                    return self._generate_fallback_response(prompt, f"API調用失敗: {str(e)[:100]}")
                
                # 計算重試延遲
                delay = self._calculate_retry_delay(attempt)
                
                self.logger.warning(f"⚠️ LLM請求失敗 (嘗試 {attempt + 1}): {str(e)[:100]}")
                self.logger.info(f"⏳ {delay:.1f}秒後重試...")
                
                await asyncio.sleep(delay)
        
        return self._generate_fallback_response(prompt, "重試機制異常")
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """計算重試延遲"""
        base_delay = self.retry_config['base_delay']
        exponential_delay = base_delay * (self.retry_config['exponential_base'] ** attempt)
        delay = min(exponential_delay, self.retry_config['max_delay'])
        
        if self.retry_config['jitter']:
            jitter = random.uniform(-self.retry_config['jitter_range'], self.retry_config['jitter_range']) * delay
            delay = max(2.0, delay + jitter)
        
        return delay
    
    # ==================== 向量搜尋方法 ====================
    
    def _deterministic_vector(self, seed: str, dim: int = 384) -> List[float]:
        """生成確定性向量"""
        out: List[float] = []
        i = 0
        while len(out) < dim:
            h = hashlib.sha256(f"{seed}:{i}".encode("utf-8")).digest()
            for j in range(0, len(h), 4):
                chunk = h[j:j+4]
                if len(chunk) < 4:
                    break
                n = int.from_bytes(chunk, byteorder="big", signed=False)
                out.append((n % 2000000) / 1000000.0 - 1.0)
                if len(out) >= dim:
                    break
            i += 1
        return out

    def _generate_case_compatible_embedding(self, text: str, input_type: str = "passage") -> List[float]:
        """生成與Case上傳時相容的384維向量"""
        seed = f"{input_type}|{text}"
        return self._deterministic_vector(seed, dim=384)

    async def search_cases(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜尋Case知識庫"""
        try:
            query_vector = self._generate_case_compatible_embedding(query, "passage")
            self.logger.info(f"🔍 Case搜尋，向量維度：{len(query_vector)} - ID: {self.instance_id}")
            
            result = self.weaviate_client.query.get(
                "Case",
                ["case_id", "chief_complaint", "summary_text", "diagnosis_main", 
                 "age", "gender", "pulse_text", "present_illness", "provisional_dx"]
            ).with_near_vector({
                "vector": query_vector
            }).with_limit(limit).with_additional(['certainty']).do()
            
            cases = []
            if result.get("data", {}).get("Get", {}).get("Case"):
                for item in result["data"]["Get"]["Case"]:
                    case_data = {
                        'case_id': item.get('case_id', ''),
                        'chief_complaint': item.get('chief_complaint', ''),
                        'summary_text': item.get('summary_text', ''),
                        'diagnosis_main': item.get('diagnosis_main', ''),
                        'age': item.get('age', ''),
                        'gender': item.get('gender', ''),
                        'pulse_text': item.get('pulse_text', ''),
                        'present_illness': item.get('present_illness', ''),
                        'provisional_dx': item.get('provisional_dx', ''),
                        'similarity': item.get('_additional', {}).get('certainty', 0.0)
                    }
                    cases.append(case_data)
            
            self.logger.info(f"✅ Case搜尋完成，找到 {len(cases)} 個相關案例")
            return cases
            
        except Exception as e:
            self.logger.error(f"Case搜尋失敗: {str(e)}")
            return []

    async def get_embeddings_v1(self, text: str, input_type: str = "query") -> List[float]:
        """獲取文本嵌入向量"""
        try:
            if not text or not text.strip():
                return self._get_default_embedding()
            
            text = text[:8192] if len(text) > 8192 else text
            
            response = await self.embedding_client.embeddings.create(
                input=[text],
                model=self.embedding_model_name,
                encoding_format="float",
                extra_body={
                    "modality": ["text"],
                    "input_type": input_type,
                    "truncate": "NONE"
                }
            )
            
            embedding = response.data[0].embedding
            self.logger.debug(f"✅ 獲取 {input_type} embedding成功，維度：{len(embedding)}")
            return embedding
            
        except Exception as e:
            self.logger.error(f"Embedding調用失敗: {str(e)}")
            return self._generate_text_based_embedding(text)

    async def search_pulse_knowledge(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜尋PulsePJ知識庫"""
        try:
            query_vector = await self.get_embeddings_v1(query, input_type="query")
            
            result = self.weaviate_client.query.get(
                "PulsePJ",
                ["name", "description", "main_disease", "symptoms", "category"]
            ).with_near_vector({
                "vector": query_vector
            }).with_limit(limit).with_additional(['certainty']).do()
            
            pulse_knowledge = []
            if result.get("data", {}).get("Get", {}).get("PulsePJ"):
                for item in result["data"]["Get"]["PulsePJ"]:
                    pulse_data = {
                        'name': item.get('name', ''),
                        'description': item.get('description', ''),
                        'main_disease': item.get('main_disease', ''),
                        'symptoms': item.get('symptoms', ''),
                        'category': item.get('category', ''),
                        'similarity': item.get('_additional', {}).get('certainty', 0.0)
                    }
                    pulse_knowledge.append(pulse_data)
            
            self.logger.info(f"PulsePJ搜尋完成，找到 {len(pulse_knowledge)} 個相關脈診知識")
            return pulse_knowledge
            
        except Exception as e:
            self.logger.error(f"PulsePJ搜尋失敗: {str(e)}")
            return []

    async def comprehensive_search(self, query: str, search_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """綜合搜尋"""
        try:
            search_options = search_options or {}
            case_limit = search_options.get('case_limit', 10)
            pulse_limit = search_options.get('pulse_limit', 5)
            
            case_results, pulse_results = await asyncio.gather(
                self.search_cases(query, case_limit),
                self.search_pulse_knowledge(query, pulse_limit)
            )
            
            all_similarities = []
            if case_results:
                all_similarities.extend([c.get('similarity', 0) for c in case_results])
            if pulse_results:
                all_similarities.extend([p.get('similarity', 0) for p in pulse_results])
            
            overall_similarity = max(all_similarities) if all_similarities else 0.0
            
            return {
                'cases': case_results,
                'pulse_knowledge': pulse_results,
                'total_cases_found': len(case_results),
                'total_pulse_found': len(pulse_results),
                'best_case': case_results[0] if case_results else None,
                'best_pulse': pulse_results[0] if pulse_results else None,
                'overall_similarity': overall_similarity,
                'search_success': True,
                'api_manager_id': self.instance_id,
                'query': query,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"綜合搜尋失敗: {str(e)}")
            return {
                'cases': [], 'pulse_knowledge': [], 'total_cases_found': 0,
                'total_pulse_found': 0, 'best_case': None, 'best_pulse': None,
                'overall_similarity': 0.0, 'search_success': False,
                'error': str(e), 'query': query, 'timestamp': datetime.now().isoformat()
            }

    # ==================== 後台服務 ====================
    
    def _start_background_services(self):
        """啟動後台服務 - 防止重複啟動"""
        
        # 🔥 關鍵修復：檢查是否已啟動後台服務
        if hasattr(self, '_services_started') and self._services_started:
            self.logger.info(f"♻️  後台服務已啟動，跳過重複啟動 (ID: {self.instance_id})")
            return
        
        # 啟動後台服務（頻率調整）
        self._background_tasks.append(
            asyncio.create_task(self._statistics_reporter())
        )
        
        self._services_started = True
        self.logger.info(f"🔄 後台服務已啟動 (單例模式 - ID: {self.instance_id})")
    
    async def _statistics_reporter(self):
        """統計報告服務 - 降低頻率"""
        while True:
            try:
                await asyncio.sleep(300)  # 改為5分鐘報告一次
                await self._generate_statistics_report()
            except Exception as e:
                self.logger.error(f"統計報告服務異常: {str(e)}")
                await asyncio.sleep(600)
    
    async def _generate_statistics_report(self):
        """生成統計報告"""
        uptime = time.time() - self.statistics['session_start_time']
        
        total_requests = self.statistics['total_requests']
        success_rate = (
            (self.statistics['successful_requests'] / total_requests * 100) 
            if total_requests > 0 else 100
        )
        
        self.logger.info("📊 === S-CBR API 管理器統計報告 (單例模式) ===")
        self.logger.info(f"🆔 實例ID: {self.instance_id}")
        self.logger.info(f"⏱️  運行時間: {uptime/3600:.1f}小時")
        self.logger.info(f"📈 請求統計: 總計{total_requests}, 成功率{success_rate:.1f}%")
        self.logger.info(f"🎯 每日配額: {self.rate_limiter['daily_used']}/{self.rate_limiter['daily_quota']}")
    
    # ==================== 工具方法 ====================
    
    def _generate_fallback_response(self, prompt: str, reason: str = "API調用失敗") -> str:
        """智能備用回應生成"""
        keywords = prompt.lower()
        
        if any(word in keywords for word in ['失眠', '睡眠', '多夢', '入睡困難', '頭痛']):
            return f"""🔄 **S-CBR v1.1 單例模式分析** (ID: {self.instance_id})

🎯 **基於症狀的中醫分析**：

**失眠頭痛綜合分析**：
- 常見證型：肝陽上亢、心腎不交、氣血不足
- 病機特點：情志不遂、勞累過度、思慮過多
- 發病規律：多與工作壓力、生活節奏相關

**治療建議**：
- 治法：平肝潛陽，養心安神
- 方藥：天麻鉤藤飲、甘麥大棗湯加減
- 針灸：百會、四神聰、神門、太衝等穴

**生活調理**：
- 作息規律，避免熬夜
- 適度運動，如散步、太極
- 情緒管理，學會放鬆

⚠️ **重要提醒**：請諮詢專業中醫師進行詳細診斷

🔄 **系統狀態**：{reason} | 單例ID：{self.instance_id} | 建議稍後重試獲得完整分析"""
        
        return f"""🔄 **S-CBR v1.1 單例模式** (ID: {self.instance_id})

🎯 **中醫辨證要點**：
1. 詳細記錄症狀的時間、程度、誘因
2. 注意觀察舌象、脈象變化
3. 結合既往病史和用藥情況
4. 考慮情緒、飲食、作息等因素

💡 **系統優勢**：
- 單例模式確保資源統一管理
- 智能速率限制保證服務穩定
- 25 RPM保守配額設計
- 優雅降級策略保證服務連續性

🔄 **系統狀態**：{reason}
🆔 **實例ID**：{self.instance_id}
⏱️  **建議操作**：稍後重試獲得完整螺旋推理分析

⚠️ **重要**：請諮詢專業中醫師進行準確診斷

*S-CBR v1.1 單例優化版 - 穩定高效的智能服務*"""
    
    def _get_default_embedding(self) -> List[float]:
        return [0.01] * 1024
    
    def _generate_text_based_embedding(self, text: str) -> List[float]:
        hash_obj = hashlib.md5(text.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        embedding = []
        for i in range(1024):
            hash_val = int(hash_hex[i % len(hash_hex)], 16) / 15.0 - 0.5
            embedding.append(hash_val)
        return embedding
    
    # ==================== 單例管理方法 ====================
    
    @classmethod
    def get_instance(cls):
        """獲取單例實例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置單例實例 (僅用於測試)"""
        with cls._lock:
            if cls._instance is not None:
                # 清理資源
                if hasattr(cls._instance, 'http_client'):
                    try:
                        asyncio.create_task(cls._instance.http_client.aclose())
                    except:
                        pass
            cls._instance = None
            cls._initialized = False
    
    def get_client_info(self) -> Dict[str, Any]:
        """獲取客戶端資訊"""
        return {
            "version": self.version,
            "instance_id": self.instance_id,
            "optimization_level": "singleton_mode",
            "rate_limit": f"{self.rate_limiter['requests_per_minute']} RPM",
            "daily_quota": f"{self.rate_limiter['daily_used']}/{self.rate_limiter['daily_quota']}",
            "initialized_at": datetime.now().isoformat()
        }

# ==================== 便捷函數 ====================

def get_api_manager():
    """獲取 API 管理器單例實例"""
    return SCBRAPIManager.get_instance()

# 匯出
__all__ = ["SCBRAPIManager", "get_api_manager"]
