"""
S-CBR 配置管理模組 v1.0

v1.0 更新：
- 整合現有 Case 和 PulsePJ 知識庫欄位定義
- 繼承外部 config.py 配置
- 定義 S-CBR 特有參數

版本：v1.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# 動態添加外部配置路徑
SCBR_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SCBR_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import config
    CONFIG_LOADED = True
except ImportError as e:
    CONFIG_LOADED = False
    CONFIG_ERROR = str(e)

class SCBRConfig:
    """
    S-CBR 配置管理類 v1.0
    
    v1.0 特色：
    - 整合現有 Weaviate Case 和 PulsePJ 知識庫
    - 定義知識庫欄位映射
    - 提供統一配置接口
    """
    
    def __init__(self):
        """初始化配置管理器 v1.0"""
        if not CONFIG_LOADED:
            raise ImportError(f"無法載入外部 config.py: {CONFIG_ERROR}")
        
        self.version = "1.0"
        self._load_base_config()
        self._setup_scbr_config_v1()
        self._setup_knowledge_base_mapping_v1()
        self._validate_config()
    
    def _load_base_config(self):
        """載入外部 config.py 配置"""
        # LLM 配置繼承
        self.LLM_API_URL = getattr(config, 'LLM_API_URL', 'https://integrate.api.nvidia.com/v1')
        self.LLM_API_KEY = getattr(config, 'LLM_API_KEY', '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')
        self.LLM_MODEL_NAME = getattr(config, 'LLM_MODEL_NAME', 'meta/llama-3.3-70b-instruct')
        
        # Embedding 配置繼承
        self.EMBEDDING_API_KEY = getattr(config, 'EMBEDDING_API_KEY', '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')
        self.EMBEDDING_BASE_URL = getattr(config, 'EMBEDDING_BASE_URL', 'https://integrate.api.nvidia.com/v1')
        self.EMBEDDING_MODEL_NAME = getattr(config, 'EMBEDDING_MODEL_NAME', 'nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1')
        
        # Weaviate 配置繼承
        self.WV_HTTP_HOST = getattr(config, 'WV_HTTP_HOST', 'localhost')
        self.WV_HTTP_PORT = getattr(config, 'WV_HTTP_PORT', 8080)
        self.WV_HTTP_SECURE = getattr(config, 'WV_HTTP_SECURE', False)
        self.WV_API_KEY = getattr(config, 'WV_API_KEY', 'key-admin')
        self.WEAVIATE_URL = getattr(config, 'WEAVIATE_URL', 'http://localhost:8080')
    
    def _setup_scbr_config_v1(self):
        """設置 S-CBR v1.0 專有配置"""
        # 螺旋推理核心參數 v1.0
        self.SPIRAL_SETTINGS = {
            'max_spiral_iterations': 5,              
            'similarity_threshold': 0.75,           
            'feedback_score_threshold': 0.7,        
            'adaptation_confidence_threshold': 0.6, 
            'convergence_patience': 2,              
            'case_search_limit': 10,                # v1.0: Case 搜尋數量限制
            'pulse_search_limit': 5,                # v1.0: PulsePJ 搜尋數量限制
        }
        
        # v1.0 案例適配權重配置
        self.ADAPTATION_WEIGHTS = {
            'symptom_weight': 0.35,       # 症狀權重（降低以平衡脈診）
            'constitution_weight': 0.25,  # 體質權重  
            'history_weight': 0.20,       # 病史權重
            'pulse_weight': 0.15,         # v1.0 新增：脈診權重
            'environment_weight': 0.05    # 環境權重（降低）
        }
        
        # v1.0 Weaviate Schema 配置（現有 + S-CBR專用）
        self.EXISTING_CLASSES = {
            'case': 'Case',                    # 現有真實案例庫
            'pulse': 'PulsePJ',                # 現有脈診知識庫
        }
        
        self.SCBR_CLASSES = {
            'feedback_cases': 'SCBRFeedbackCases',     # S-CBR 反饋案例
            'spiral_sessions': 'SCBRSpiralSessions',   # S-CBR 會話記錄
            'adaptation_logs': 'SCBRAdaptationLogs',   # S-CBR 適配日誌
        }
        
        # v1.0 Agentive AI 配置
        self.AGENTIVE_CONFIG = {
            'diagnostic_agent': {
                'model': self.LLM_MODEL_NAME,
                'temperature': 0.7,
                'max_tokens': 1200,
                'system_prompt': "你是專業的中醫診斷智能體，擅長整合症狀和脈診資訊進行診斷分析。"
            },
            'adaptation_agent': {
                'model': self.LLM_MODEL_NAME,
                'temperature': 0.8,
                'max_tokens': 1500,
                'system_prompt': "你是專業的中醫處方適配智能體，擅長根據個體差異調整治療方案。"
            },
            'monitoring_agent': {
                'model': self.LLM_MODEL_NAME,
                'temperature': 0.6,
                'max_tokens': 1000,
                'system_prompt': "你是專業的中醫方案監控智能體，重視安全性和有效性評估。"
            },
            'feedback_agent': {
                'model': self.LLM_MODEL_NAME,
                'temperature': 0.7,
                'max_tokens': 1200,
                'system_prompt': "你是專業的中醫回饋分析智能體，擅長從用戶反饋中學習和改進。"
            }
        }
    
    def _setup_knowledge_base_mapping_v1(self):
        """v1.0 設置現有知識庫欄位映射"""
        
        # Case 知識庫欄位定義（基於您提供的結構）
        self.CASE_FIELDS = {
            'case_id': 'case_id',
            'timestamp': 'timestamp',
            'age': 'age',
            'gender': 'gender',
            'chief_complaint': 'chief_complaint',
            'present_illness': 'present_illness',
            'provisional_dx': 'provisional_dx',
            'pulse_text': 'pulse_text',
            'inspection_tags': 'inspection_tags',
            'inquiry_tags': 'inquiry_tags', 
            'pulse_tags': 'pulse_tags',
            'summary_text': 'summary_text',
            'summary': 'summary',
            'diagnosis_main': 'diagnosis_main',
            'diagnosis_sub': 'diagnosis_sub',
            'llm_struct': 'llm_struct'
        }
        
        # PulsePJ 知識庫欄位定義（基於您提供的結構）
        self.PULSE_FIELDS = {
            'name': 'name',                    # 脈象名稱
            'description': 'description',      # 脈象描述
            'main_disease': 'main_disease',    # 主要疾病
            'symptoms': 'symptoms',            # 相關症狀
            'category': 'category',            # 脈診分類
            'knowledge_chain': 'knowledge_chain' # 知識鏈
        }
        
        # v1.0 查詢策略配置
        self.QUERY_STRATEGIES = {
            'case_search': {
                'primary_fields': ['chief_complaint', 'summary_text', 'diagnosis_main'],
                'secondary_fields': ['present_illness', 'symptoms', 'provisional_dx'],
                'weight_distribution': {
                    'chief_complaint': 0.4,
                    'summary_text': 0.3, 
                    'diagnosis_main': 0.2,
                    'present_illness': 0.1
                }
            },
            'pulse_search': {
                'primary_fields': ['name', 'description', 'main_disease'],
                'secondary_fields': ['symptoms', 'category'],
                'weight_distribution': {
                    'name': 0.3,
                    'description': 0.3,
                    'main_disease': 0.2,
                    'symptoms': 0.2
                }
            }
        }
    
    def _validate_config(self):
        """驗證 v1.0 配置完整性"""
        # API 金鑰檢查
        required_keys = ['LLM_API_KEY', 'EMBEDDING_API_KEY', 'WV_API_KEY']
        for key in required_keys:
            if not getattr(self, key):
                raise ValueError(f"{key} 未設置")
        
        # v1.0 參數範圍檢查
        if self.SPIRAL_SETTINGS['max_spiral_iterations'] < 1:
            raise ValueError("max_spiral_iterations 必須大於 0")
        
        # v1.0 權重總和檢查
        total_weight = sum(self.ADAPTATION_WEIGHTS.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"適配權重總和應為 1.0，當前為 {total_weight}")
    
    # v1.0 配置獲取方法
    def get_case_search_config(self) -> Dict[str, Any]:
        """獲取 Case 搜尋配置"""
        return {
            'class_name': self.EXISTING_CLASSES['case'],
            'fields': list(self.CASE_FIELDS.values()),
            'strategy': self.QUERY_STRATEGIES['case_search'],
            'limit': self.SPIRAL_SETTINGS['case_search_limit']
        }
    
    def get_pulse_search_config(self) -> Dict[str, Any]:
        """獲取 PulsePJ 搜尋配置"""
        return {
            'class_name': self.EXISTING_CLASSES['pulse'],
            'fields': list(self.PULSE_FIELDS.values()),
            'strategy': self.QUERY_STRATEGIES['pulse_search'], 
            'limit': self.SPIRAL_SETTINGS['pulse_search_limit']
        }
    
    @classmethod
    def get_weaviate_config(cls) -> Dict[str, Any]:
        """獲取 Weaviate 連接配置"""
        instance = cls()
        return {
            'url': instance.WEAVIATE_URL,
            'auth_api_key': instance.WV_API_KEY,
            'additional_headers': {
                'X-OpenAI-Api-Key': instance.EMBEDDING_API_KEY
            }
        }
    
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """獲取智能體配置 v1.0 - 修復缺失方法"""
        valid_agents = ['diagnostic_agent', 'adaptation_agent', 'monitoring_agent', 'feedback_agent']
        
        if agent_name not in valid_agents:
            raise ValueError(f"無效的智能體名稱: {agent_name}. 有效選項: {valid_agents}")
        
        agent_config = self.AGENTIVE_CONFIG.get(agent_name)
        
        if not agent_config:
            # 預設配置備用
            return {
                'model': self.LLM_MODEL_NAME,
                'temperature': 0.7,
                'max_tokens': 1200,
                'system_prompt': f"你是專業的中醫{agent_name.replace('_agent', '')}智能體。"
            }
        
        return agent_config.copy()  # 返回副本，避免意外修改
    
    def get_llm_config(self) -> Dict[str, Any]:
        """獲取通用 LLM 配置 v1.0"""
        return {
            'model': self.LLM_MODEL_NAME,
            'temperature': 0.7,  
            'max_tokens': 2000,
            'api_url': self.LLM_API_URL,
            'api_key': self.LLM_API_KEY
        }
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """獲取嵌入模型配置 v1.0"""
        return {
            'model': self.EMBEDDING_MODEL_NAME,
            'api_key': self.EMBEDDING_API_KEY,
            'base_url': self.EMBEDDING_BASE_URL,
            'max_length': 512
        }
    
    def get_spiral_config(self) -> Dict[str, Any]:
        """獲取螺旋推理配置 v1.0"""
        return self.SPIRAL_SETTINGS.copy()
    
    def get_adaptation_weights(self) -> Dict[str, float]:
        """獲取適配權重配置 v1.0"""
        return self.ADAPTATION_WEIGHTS.copy()
    
    def get_knowledge_base_config(self, kb_type: str) -> Dict[str, Any]:
        """獲取知識庫配置 v1.0"""
        if kb_type == 'case':
            return self.get_case_search_config()
        elif kb_type == 'pulse':
            return self.get_pulse_search_config()
        else:
            raise ValueError(f"無效的知識庫類型: {kb_type}. 有效選項: ['case', 'pulse']")
    
    def get_all_config_summary(self) -> Dict[str, Any]:
        """獲取配置摘要 v1.0 - 用於調試"""
        return {
            'version': self.version,
            'loaded_from_external_config': CONFIG_LOADED,
            'available_classes': {**self.EXISTING_CLASSES, **self.SCBR_CLASSES},
            'spiral_settings': self.SPIRAL_SETTINGS,
            'adaptation_weights': self.ADAPTATION_WEIGHTS,
            'agentive_agents': list(self.AGENTIVE_CONFIG.keys()),
            'knowledge_bases': list(self.EXISTING_CLASSES.keys())
        }
