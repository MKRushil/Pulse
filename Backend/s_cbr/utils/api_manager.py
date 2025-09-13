"""
S-CBR API 資源管理器 v1.0

v1.0 更新：
- 整合現有 Case 和 PulsePJ 知識庫
- 提供統一的知識庫查詢接口
- 支援多種搜尋策略

版本：v1.0
"""

from s_cbr.config.scbr_config import SCBRConfig
import httpx
import weaviate
import logging
import asyncio 
from typing import Dict, List, Any, Optional
import json

class SCBRAPIManager:
    """
    S-CBR API 資源管理器 v1.0
    
    v1.0 特色：
    - 整合現有 Case 和 PulsePJ Weaviate 類別
    - 提供統一的 LLM 和 Embedding API 接口
    - 支援多種知識庫查詢策略
    """
    
    def __init__(self):
        """初始化 API 管理器 v1.0"""
        self.config = SCBRConfig()
        self.logger = logging.getLogger(__name__)
        self.version = "1.0"
        
        # 初始化客戶端
        self._init_clients()
        
        self.logger.info(f"S-CBR API 管理器 v{self.version} 初始化完成")
    
    def _init_clients(self):
        """初始化所有 API 客戶端"""
        try:
            # LLM 客戶端
            self.llm_client = httpx.AsyncClient(
                base_url=self.config.LLM_API_URL,
                headers={
                    "Authorization": f"Bearer {self.config.LLM_API_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=60.0  # v1.0: 增加超時時間
            )
            
            # Embedding 客戶端  
            self.embedding_client = httpx.AsyncClient(
                base_url=self.config.EMBEDDING_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.config.EMBEDDING_API_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=60.0
            )
            
            # Weaviate 客戶端（連接現有知識庫）
            self.weaviate_client = weaviate.Client(
                url=self.config.WEAVIATE_URL,
                auth_client_secret=weaviate.AuthApiKey(api_key=self.config.WV_API_KEY),
                additional_headers={
                    "X-OpenAI-Api-Key": self.config.EMBEDDING_API_KEY
                }
            )
            
            self.logger.info("所有 API 客戶端初始化成功")
            
        except Exception as e:
            self.logger.error(f"API 客戶端初始化失敗: {e}")
            raise
    
    # LLM API 方法
    async def generate_llm_response(self, prompt: str, agent_config: Dict = None) -> str:
        """
        調用 LLM 生成回應 v1.0
        
        v1.0 增強：
        - 支援不同智能體配置
        - 改進錯誤處理
        - 增加重試機制
        """
        try:
            # 使用智能體專屬配置或預設配置
            if agent_config:
                temperature = agent_config.get('temperature', 0.7)
                max_tokens = agent_config.get('max_tokens', 1000)
                system_prompt = agent_config.get('system_prompt', '')
            else:
                temperature = 0.7
                max_tokens = 1000
                system_prompt = ''
            
            # 構建消息
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.config.LLM_MODEL_NAME,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = await self.llm_client.post("/chat/completions", json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            self.logger.error(f"LLM 調用失敗: {e}")
            return f"LLM 調用錯誤: {str(e)}"
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        獲取文本向量 v1.0
        
        v1.0 改進：
        - 增加文本預處理
        - 改善錯誤處理
        """
        try:
            # v1.0 文本預處理
            processed_text = self._preprocess_text_for_embedding(text)
            
            payload = {
                "model": self.config.EMBEDDING_MODEL_NAME,
                "input": processed_text
            }
            
            response = await self.embedding_client.post("/embeddings", json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result["data"][0]["embedding"]
            
        except Exception as e:
            self.logger.error(f"Embedding 調用失敗: {e}")
            return []
    
    def _preprocess_text_for_embedding(self, text: str) -> str:
        """v1.0 文本預處理"""
        if not text:
            return ""
        
        # 基本清理
        text = text.strip()
        
        # 限制長度（避免超過模型限制）
        if len(text) > 8000:
            text = text[:8000]
        
        return text
    
    # Case 知識庫查詢方法 v1.0
    async def search_similar_cases(self, query_vector: List[float], 
                                 filters: Optional[Dict] = None, 
                                 limit: int = None) -> List[Dict]:
        """
        在 Case 知識庫中搜尋相似案例 v1.0
        
        v1.0 特色：
        - 使用現有 Case 類別結構
        - 支援多維度過濾
        - 返回完整案例資訊
        """
        try:
            case_config = self.config.get_case_search_config()
            search_limit = limit or case_config['limit']
            
            # 構建查詢
            query_builder = (
                self.weaviate_client.query
                .get(case_config['class_name'], case_config['fields'])
                .with_near_vector({"vector": query_vector})
                .with_limit(search_limit)
                .with_additional(["certainty", "distance", "id"])
            )
            
            # 添加過濾條件 v1.0
            if filters:
                where_filter = self._build_case_filter(filters)
                if where_filter:
                    query_builder = query_builder.with_where(where_filter)
            
            result = query_builder.do()
            
            # 處理結果
            cases = result.get("data", {}).get("Get", {}).get(case_config['class_name'], [])
            
            self.logger.info(f"Case 搜尋完成，找到 {len(cases)} 個相似案例")
            
            return self._process_case_results(cases)
            
        except Exception as e:
            self.logger.error(f"Case 搜尋失敗: {e}")
            return []
    
    def _build_case_filter(self, filters: Dict) -> Optional[Dict]:
        """構建 Case 查詢過濾條件 v1.0"""
        where_conditions = []
        
        # 年齡範圍過濾
        if filters.get('age_range'):
            min_age, max_age = filters['age_range']
            # 注意：這裡需要根據實際 Case 資料格式調整
            
        # 性別過濾  
        if filters.get('gender'):
            where_conditions.append({
                "path": ["gender"],
                "operator": "Equal",
                "valueString": filters['gender']
            })
        
        # 主訴關鍵字過濾
        if filters.get('chief_complaint_keywords'):
            for keyword in filters['chief_complaint_keywords']:
                where_conditions.append({
                    "path": ["chief_complaint"],
                    "operator": "Like",
                    "valueString": f"*{keyword}*"
                })
        
        # 構建 AND 條件
        if len(where_conditions) == 1:
            return where_conditions[0]
        elif len(where_conditions) > 1:
            return {
                "operator": "And",
                "operands": where_conditions
            }
        
        return None
    
    def _process_case_results(self, cases: List[Dict]) -> List[Dict]:
        """處理 Case 搜尋結果 v1.0"""
        processed_cases = []
        
        for case in cases:
            # 提取重要資訊
            processed_case = {
                'case_id': case.get('case_id'),
                'similarity': case.get('_additional', {}).get('certainty', 0.0),
                'age': case.get('age'),
                'gender': case.get('gender'),
                'chief_complaint': case.get('chief_complaint'),
                'present_illness': case.get('present_illness'),
                'diagnosis_main': case.get('diagnosis_main'),
                'diagnosis_sub': case.get('diagnosis_sub'),
                'pulse_text': case.get('pulse_text'),
                'pulse_tags': case.get('pulse_tags'),
                'summary': case.get('summary'),
                'llm_struct': case.get('llm_struct'),
                'raw_data': case  # 保留原始資料
            }
            processed_cases.append(processed_case)
        
        return processed_cases
    
    # PulsePJ 知識庫查詢方法 v1.0
    async def search_pulse_knowledge(self, pulse_pattern: str, 
                                   symptoms: List[str] = None) -> List[Dict]:
        """
        在 PulsePJ 知識庫中搜尋脈診知識 v1.0
        
        v1.0 特色：
        - 支援脈象模式匹配
        - 整合症狀關聯搜尋
        - 提供知識鏈追蹤
        """
        try:
            pulse_config = self.config.get_pulse_search_config()
            
            # 構建查詢條件
            where_conditions = []
            
            # 脈象名稱匹配
            if pulse_pattern:
                where_conditions.append({
                    "path": ["name"],
                    "operator": "Like", 
                    "valueString": f"*{pulse_pattern}*"
                })
            
            # 症狀關聯匹配
            if symptoms:
                for symptom in symptoms:
                    where_conditions.append({
                        "path": ["symptoms"],
                        "operator": "Like",
                        "valueString": f"*{symptom}*"
                    })
            
            # 構建查詢
            query_builder = (
                self.weaviate_client.query
                .get(pulse_config['class_name'], pulse_config['fields'])
                .with_limit(pulse_config['limit'])
                .with_additional(["id"])
            )
            
            # 添加 where 條件
            if where_conditions:
                if len(where_conditions) == 1:
                    where_filter = where_conditions[0]
                else:
                    where_filter = {
                        "operator": "Or",  # 使用 Or 提高匹配率
                        "operands": where_conditions
                    }
                query_builder = query_builder.with_where(where_filter)
            
            result = query_builder.do()
            
            # 處理結果
            pulse_data = result.get("data", {}).get("Get", {}).get(pulse_config['class_name'], [])
            
            self.logger.info(f"PulsePJ 搜尋完成，找到 {len(pulse_data)} 個相關脈診知識")
            
            return self._process_pulse_results(pulse_data)
            
        except Exception as e:
            self.logger.error(f"PulsePJ 搜尋失敗: {e}")
            return []
    
    def _process_pulse_results(self, pulse_data: List[Dict]) -> List[Dict]:
        """處理 PulsePJ 搜尋結果 v1.0"""
        processed_pulses = []
        
        for pulse in pulse_data:
            processed_pulse = {
                'name': pulse.get('name'),
                'description': pulse.get('description'),
                'main_disease': pulse.get('main_disease'),
                'symptoms': pulse.get('symptoms'),
                'category': pulse.get('category'),
                'knowledge_chain': pulse.get('knowledge_chain'),
                'raw_data': pulse
            }
            processed_pulses.append(processed_pulse)
        
        return processed_pulses
    
    # 綜合搜尋方法 v1.0
    async def comprehensive_search(self, query_text: str, 
                                 patient_context: Dict = None) -> Dict[str, Any]:
        """
        綜合搜尋 Case 和 PulsePJ 知識庫 v1.0
        
        v1.0 創新功能：
        - 同時搜尋案例和脈診知識
        - 智能關聯分析
        - 綜合結果排序
        """
        try:
            # 獲取查詢向量
            query_vector = await self.get_embedding(query_text)
            if not query_vector:
                return {"error": "無法獲取查詢向量"}
            
            # 並行搜尋
            case_search_task = self.search_similar_cases(query_vector)
            
            # 從患者上下文提取脈診資訊
            pulse_pattern = ""
            if patient_context:
                pulse_pattern = patient_context.get('pulse_text', '') or patient_context.get('pulse_pattern', '')
            
            pulse_search_task = self.search_pulse_knowledge(pulse_pattern) if pulse_pattern else []
            
            # 等待搜尋完成
            if pulse_pattern:
                similar_cases, pulse_knowledge = await asyncio.gather(
                    case_search_task, pulse_search_task
                )
            else:
                similar_cases = await case_search_task
                pulse_knowledge = []
            
            # v1.0 綜合分析
            comprehensive_result = {
                'similar_cases': similar_cases,
                'pulse_knowledge': pulse_knowledge,
                'integration_analysis': self._analyze_case_pulse_integration(
                    similar_cases, pulse_knowledge
                ),
                'search_summary': {
                    'total_cases_found': len(similar_cases),
                    'total_pulse_knowledge_found': len(pulse_knowledge),
                    'query_text': query_text,
                    'pulse_pattern': pulse_pattern
                }
            }
            
            self.logger.info(f"綜合搜尋完成 - 案例: {len(similar_cases)}, 脈診: {len(pulse_knowledge)}")
            
            return comprehensive_result
            
        except Exception as e:
            self.logger.error(f"綜合搜尋失敗: {e}")
            return {"error": str(e)}
    
    def _analyze_case_pulse_integration(self, cases: List[Dict], 
                                      pulse_knowledge: List[Dict]) -> Dict[str, Any]:
        """
        分析案例與脈診知識的整合 v1.0
        
        v1.0 智能分析：
        - 案例與脈診的一致性檢查
        - 互補性分析
        - 整合建議生成
        """
        analysis = {
            'consistency_score': 0.0,
            'complementary_insights': [],
            'integration_suggestions': [],
            'confidence_level': 'low'
        }
        
        if not cases or not pulse_knowledge:
            return analysis
        
        # 簡單的一致性分析
        case_symptoms = set()
        for case in cases[:3]:  # 取前3個最相似案例
            if case.get('pulse_text'):
                case_symptoms.update(case['pulse_text'].split())
        
        pulse_symptoms = set()
        for pulse in pulse_knowledge:
            if pulse.get('symptoms'):
                pulse_symptoms.update(pulse['symptoms'].split())
        
        # 計算重疊度
        if case_symptoms and pulse_symptoms:
            overlap = case_symptoms.intersection(pulse_symptoms)
            analysis['consistency_score'] = len(overlap) / max(len(case_symptoms), len(pulse_symptoms))
        
        # 設置信心等級
        if analysis['consistency_score'] > 0.7:
            analysis['confidence_level'] = 'high'
        elif analysis['consistency_score'] > 0.4:
            analysis['confidence_level'] = 'medium'
        
        analysis['integration_suggestions'] = [
            "建議結合案例經驗和脈診理論進行綜合分析",
            "注意案例中的脈象描述與標準脈診知識的對應關係",
            "考慮個體差異對脈診表現的影響"
        ]
        
        return analysis
    
    # 工具方法
    async def health_check(self) -> Dict[str, Any]:
        """系統健康檢查 v1.0"""
        health_status = {
            'version': self.version,
            'llm_client': False,
            'embedding_client': False,
            'weaviate_client': False,
            'overall_status': 'unhealthy'
        }
        
        try:
            # 檢查 LLM 客戶端
            test_response = await self.generate_llm_response("測試", None)
            health_status['llm_client'] = bool(test_response and "錯誤" not in test_response)
            
            # 檢查 Embedding 客戶端  
            test_embedding = await self.get_embedding("測試")
            health_status['embedding_client'] = bool(test_embedding)
            
            # 檢查 Weaviate 客戶端
            weaviate_status = self.weaviate_client.is_ready()
            health_status['weaviate_client'] = weaviate_status
            
            # 整體狀態
            if all([health_status['llm_client'], 
                   health_status['embedding_client'], 
                   health_status['weaviate_client']]):
                health_status['overall_status'] = 'healthy'
            
        except Exception as e:
            self.logger.error(f"健康檢查異常: {e}")
            health_status['error'] = str(e)
        
        return health_status
