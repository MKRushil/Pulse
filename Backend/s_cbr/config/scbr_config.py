"""
S-CBR 系統配置管理 v2.1 - Backend 整合版

管理 S-CBR 螺旋推理系統的全局配置
支援會話配置與螺旋推理參數管理
整合 Backend/config.py 的 LLM、Embedding、Weaviate 配置

版本：v2.1 - Backend 整合版  
更新：整合 Backend/config.py，支援統一配置管理
"""

from typing import Dict, Any, List, Optional, Union
import os
import yaml
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
except ImportError:
    import logging as SpiralLogger

@dataclass
class SpiralConfig:
    """螺旋推理配置"""
    max_rounds: int = 10
    min_rounds: int = 1
    effectiveness_threshold: float = 0.8
    similarity_threshold: float = 0.7
    case_diversity_weight: float = 0.3
    session_timeout: int = 3600  # 秒

@dataclass
class SessionConfig:
    """會話管理配置"""
    max_concurrent_sessions: int = 100
    session_cleanup_interval: int = 300  # 秒
    session_memory_limit: int = 1000
    enable_session_persistence: bool = True
    session_storage_path: str = "data/sessions"

@dataclass 
class AgentConfig:
    """智能體配置"""
    diagnostic_weight: float = 0.4
    adaptation_weight: float = 0.3
    monitoring_weight: float = 0.2
    feedback_weight: float = 0.1
    enable_parallel_processing: bool = True
    agent_timeout: int = 30  # 秒

@dataclass
class DatabaseConfig:
    """數據庫配置"""
    weaviate_url: str = "http://localhost:8080"
    weaviate_timeout: int = 30
    vector_dimension: int = 1536
    enable_vector_cache: bool = True
    cache_size: int = 1000

@dataclass
class LoggingConfig:
    """日誌配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/scbr.log"
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5

class SCBRConfig:
    """
    S-CBR 系統配置管理器 v2.1 - Backend 整合版
    
    v2.1 特色：
    - 整合 Backend/config.py 配置
    - 統一的配置管理介面
    - 會話配置管理
    - 螺旋推理參數配置 
    - 智能體協調配置
    - 動態配置更新
    """
    
    def __init__(self, config_path: str = None):
        """初始化配置管理器"""
        self.logger = SpiralLogger.get_logger("SCBRConfig") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("SCBRConfig")
        self.version = "2.1"
        
        # 配置文件路徑
        self.config_path = config_path or self._get_default_config_path()
        
        # 初始化配置對象
        self.spiral_config = SpiralConfig()
        self.session_config = SessionConfig()
        self.agent_config = AgentConfig()
        self.database_config = DatabaseConfig()
        self.logging_config = LoggingConfig()
        
        # Backend 配置緩存
        self._backend_config_cache = None
        
        # 載入配置
        self._load_config()
        
        self.logger.info(f"S-CBR 配置管理器 v{self.version} 初始化完成")
    
    def _get_default_config_path(self) -> str:
        """獲取默認配置文件路徑"""
        return os.path.join(os.path.dirname(__file__), "..", "..", "configs", "scbr_config.yaml")
    
    def _load_config(self):
        """載入配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                        config_data = yaml.safe_load(f)
                    else:
                        config_data = json.load(f)
                
                self._update_config_from_dict(config_data)
                self.logger.info(f"從文件載入配置: {self.config_path}")
            else:
                self.logger.info("使用默認配置")
                self._create_default_config_file()
        
        except Exception as e:
            self.logger.warning(f"載入配置失敗，使用默認配置: {str(e)}")
    
    def _update_config_from_dict(self, config_data: Dict[str, Any]):
        """從字典更新配置"""
        try:
            # 更新螺旋配置
            if 'spiral' in config_data:
                spiral_data = config_data['spiral']
                for key, value in spiral_data.items():
                    if hasattr(self.spiral_config, key):
                        setattr(self.spiral_config, key, value)
            
            # 更新會話配置
            if 'session' in config_data:
                session_data = config_data['session']
                for key, value in session_data.items():
                    if hasattr(self.session_config, key):
                        setattr(self.session_config, key, value)
            
            # 更新智能體配置
            if 'agent' in config_data:
                agent_data = config_data['agent']
                for key, value in agent_data.items():
                    if hasattr(self.agent_config, key):
                        setattr(self.agent_config, key, value)
            
            # 更新數據庫配置
            if 'database' in config_data:
                db_data = config_data['database']
                for key, value in db_data.items():
                    if hasattr(self.database_config, key):
                        setattr(self.database_config, key, value)
            
            # 更新日誌配置
            if 'logging' in config_data:
                log_data = config_data['logging']
                for key, value in log_data.items():
                    if hasattr(self.logging_config, key):
                        setattr(self.logging_config, key, value)
        
        except Exception as e:
            self.logger.error(f"更新配置失敗: {str(e)}")
    
    def _create_default_config_file(self):
        """創建默認配置文件"""
        try:
            config_dir = os.path.dirname(self.config_path)
            os.makedirs(config_dir, exist_ok=True)
            
            default_config = {
                'spiral': asdict(self.spiral_config),
                'session': asdict(self.session_config),
                'agent': asdict(self.agent_config),
                'database': asdict(self.database_config),
                'logging': asdict(self.logging_config)
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"創建默認配置文件: {self.config_path}")
        
        except Exception as e:
            self.logger.error(f"創建默認配置文件失敗: {str(e)}")
    
    def get_spiral_config(self) -> SpiralConfig:
        """獲取螺旋推理配置"""
        return self.spiral_config
    
    def get_session_config(self) -> SessionConfig:
        """獲取會話管理配置"""
        return self.session_config
    
    def get_agent_config(self) -> AgentConfig:
        """獲取智能體配置"""
        return self.agent_config
    
    def get_database_config(self) -> DatabaseConfig:
        """獲取數據庫配置"""
        return self.database_config
    
    def get_logging_config(self) -> LoggingConfig:
        """獲取日誌配置"""
        return self.logging_config
    
    def get_backend_config(self) -> Dict[str, Any]:
        """
        獲取 Backend/config.py 的配置 v2.1
        
        提供與 Backend/config.py 的整合，優先使用主配置檔案的設定
        支援配置緩存以提升性能
        """
        # 如果已有緩存且未過期，直接返回
        if self._backend_config_cache is not None:
            return self._backend_config_cache
        
        backend_config = {}
        
        try:
            import sys
            import os
            
            # 添加 Backend 路徑
            backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
            if backend_path not in sys.path:
                sys.path.append(backend_path)
            
            # 導入 Backend 配置
            from Backend.config import (
                LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME,
                EMBEDDING_API_KEY, EMBEDDING_BASE_URL, EMBEDDING_MODEL_NAME, NVIDIA_API_KEY, EMBEDDING_NV_MODEL_NAME,
                WV_API_KEY, WEAVIATE_URL, WV_HTTP_SECURE, WV_HTTP_HOST, WV_HTTP_PORT
            )
            
            backend_config = {
                "llm": {
                    "api_url": LLM_API_URL,
                    "api_key": LLM_API_KEY,
                    "model": LLM_MODEL_NAME,
                    "timeout": 60
                },
                "embedding": {
                    "api_key": NVIDIA_API_KEY,
                    "base_url": EMBEDDING_BASE_URL,
                    "model": EMBEDDING_NV_MODEL_NAME,
                    "timeout": 30
                },
                "weaviate": {
                    "url": WEAVIATE_URL,
                    "api_key": WV_API_KEY,
                    "secure": WV_HTTP_SECURE,
                    "host": WV_HTTP_HOST,
                    "port": WV_HTTP_PORT,
                    "timeout": 30
                }
            }
            
            # 緩存配置
            self._backend_config_cache = backend_config
            self.logger.info("✅ 成功載入 Backend 配置")
            
        except ImportError as e:
            self.logger.warning(f"無法載入 Backend 配置: {e}")
            # 使用預設值
            backend_config = {
                "llm": {
                    "api_url": "https://integrate.api.nvidia.com/v1",
                    "api_key": "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",
                    "model": "meta/llama-3.3-70b-instruct",
                    "timeout": 60
                },
                "embedding": {
                    "api_key": "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",
                    "base_url": "https://integrate.api.nvidia.com/v1",
                    "model": "nvidia/nv-embedqa-e5-v5",
                    "timeout": 30
                },
                "weaviate": {
                    "url": "http://localhost:8080",
                    "api_key": "key-admin",
                    "secure": False,
                    "host": "localhost",
                    "port": 8080,
                    "timeout": 30
                }
            }
            # 緩存預設配置
            self._backend_config_cache = backend_config
        except Exception as e:
            self.logger.error(f"Backend 配置載入異常: {e}")
            # 返回空配置避免程序崩潰
            backend_config = {
                "llm": {},
                "embedding": {},
                "weaviate": {}
            }
        
        return backend_config

    def get_llm_config(self) -> Dict[str, Any]:
        """獲取 LLM 配置"""
        backend_config = self.get_backend_config()
        return backend_config.get("llm", {})

    def get_embedding_config(self) -> Dict[str, Any]:
        """獲取 Embedding 配置"""
        backend_config = self.get_backend_config()
        return backend_config.get("embedding", {})

    def get_weaviate_config(self) -> Dict[str, Any]:
        """獲取 Weaviate 配置"""
        backend_config = self.get_backend_config()
        return backend_config.get("weaviate", {})

    def clear_backend_cache(self):
        """清除 Backend 配置緩存"""
        self._backend_config_cache = None
        self.logger.debug("Backend 配置緩存已清除")

    def reload_backend_config(self):
        """重新載入 Backend 配置"""
        self.clear_backend_cache()
        return self.get_backend_config()
    
    def update_spiral_config(self, **kwargs):
        """更新螺旋推理配置"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.spiral_config, key):
                    setattr(self.spiral_config, key, value)
                    self.logger.info(f"更新螺旋配置 {key}: {value}")
                else:
                    self.logger.warning(f"未知的螺旋配置項: {key}")
        except Exception as e:
            self.logger.error(f"更新螺旋配置失敗: {str(e)}")
    
    def update_session_config(self, **kwargs):
        """更新會話配置"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.session_config, key):
                    setattr(self.session_config, key, value)
                    self.logger.info(f"更新會話配置 {key}: {value}")
                else:
                    self.logger.warning(f"未知的會話配置項: {key}")
        except Exception as e:
            self.logger.error(f"更新會話配置失敗: {str(e)}")
    
    def save_config(self):
        """保存配置到文件"""
        try:
            config_data = {
                'spiral': asdict(self.spiral_config),
                'session': asdict(self.session_config),
                'agent': asdict(self.agent_config),
                'database': asdict(self.database_config),
                'logging': asdict(self.logging_config)
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"配置已保存到: {self.config_path}")
        
        except Exception as e:
            self.logger.error(f"保存配置失敗: {str(e)}")
    
    def reload_config(self):
        """重新載入配置"""
        try:
            self.clear_backend_cache()  # 清除 Backend 緩存
            self._load_config()
            self.logger.info("配置已重新載入")
        except Exception as e:
            self.logger.error(f"重新載入配置失敗: {str(e)}")
    
    def get_config_dict(self) -> Dict[str, Any]:
        """獲取完整配置字典"""
        return {
            'spiral': asdict(self.spiral_config),
            'session': asdict(self.session_config),
            'agent': asdict(self.agent_config),
            'database': asdict(self.database_config),
            'logging': asdict(self.logging_config),
            'backend': self.get_backend_config(),
            'version': self.version
        }
    
    def get_config(self, key_path: str, default=None):
        """
        通用配置獲取方法 v2.1 - 支援 Backend 配置
        
        支援點分路徑訪問配置，包括 Backend/config.py 的配置
        
        Args:
            key_path (str): 配置鍵路徑，支援點分層級
            例如: 'llm.api_key'  # 從 Backend/config.py
                  'backend.llm.model'  # 從 Backend/config.py
                  'session.max_concurrent_sessions'  # 從 scbr_config.yaml
            default: 默認值，當配置項不存在時返回
        
        Returns:
            配置值或默認值
        
        Examples:
            >>> config.get_config('llm.api_key')
            'nvapi-xxxxx'
            >>> config.get_config('session.max_concurrent_sessions')
            100
            >>> config.get_config('weaviate.url')
            'http://localhost:8080'
        """
        try:
            keys = key_path.split('.')
            
            # 第一級：配置對象映射（包含 Backend 配置）
            config_mapping = {
                # S-CBR 配置
                'spiral': self.spiral_config,
                'session': self.session_config,
                'agent': self.agent_config,
                'database': self.database_config,
                'logging': self.logging_config,
                # 向後兼容的映射
                'spiral_config': self.spiral_config,
                'session_config': self.session_config,
                'agent_config': self.agent_config,
                'database_config': self.database_config,
                'logging_config': self.logging_config,
                # Backend 配置映射
                'backend': self.get_backend_config(),
                'llm': self.get_llm_config(),
                'embedding': self.get_embedding_config(),
                'weaviate': self.get_weaviate_config()
            }
            
            # 處理第一級配置對象
            if len(keys) >= 1 and keys[0] in config_mapping:
                current_obj = config_mapping[keys[0]]
                
                # 如果只有一級路徑，返回整個配置對象
                if len(keys) == 1:
                    if hasattr(current_obj, '__dict__'):
                        return current_obj.__dict__
                    return current_obj if isinstance(current_obj, dict) else asdict(current_obj) if hasattr(current_obj, '__dataclass_fields__') else current_obj
                
                # 處理多級路徑
                for key in keys[1:]:
                    if hasattr(current_obj, key):
                        current_obj = getattr(current_obj, key)
                    elif isinstance(current_obj, dict) and key in current_obj:
                        current_obj = current_obj[key]
                    else:
                        self.logger.debug(f"配置路徑 '{key_path}' 中的 '{key}' 不存在，返回默認值: {default}")
                        return default
                
                return current_obj
            
            # 嘗試直接在當前配置實例中查找（向後兼容）
            current_obj = self
            for key in keys:
                if hasattr(current_obj, key):
                    current_obj = getattr(current_obj, key)
                elif isinstance(current_obj, dict) and key in current_obj:
                    current_obj = current_obj[key]
                else:
                    self.logger.debug(f"配置路徑 '{key_path}' 中的 '{key}' 不存在，返回默認值: {default}")
                    return default
            
            return current_obj
            
        except Exception as e:
            self.logger.warning(f"獲取配置 '{key_path}' 時發生錯誤: {str(e)}，返回默認值: {default}")
            return default
    
    def validate_config(self) -> Dict[str, Any]:
        """驗證配置有效性"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 驗證螺旋配置
            if self.spiral_config.max_rounds < self.spiral_config.min_rounds:
                validation_result['errors'].append("螺旋推理最大輪次不能小於最小輪次")
                validation_result['valid'] = False
            
            if not (0.0 <= self.spiral_config.effectiveness_threshold <= 1.0):
                validation_result['errors'].append("有效性閾值必須在0.0-1.0之間")
                validation_result['valid'] = False
            
            if not (0.0 <= self.spiral_config.similarity_threshold <= 1.0):
                validation_result['errors'].append("相似度閾值必須在0.0-1.0之間")
                validation_result['valid'] = False
            
            # 驗證會話配置
            if self.session_config.max_concurrent_sessions <= 0:
                validation_result['errors'].append("最大並發會話數必須大於0")
                validation_result['valid'] = False
            
            # 驗證智能體配置
            total_weight = (self.agent_config.diagnostic_weight + 
                          self.agent_config.adaptation_weight + 
                          self.agent_config.monitoring_weight + 
                          self.agent_config.feedback_weight)
            
            if abs(total_weight - 1.0) > 0.01:
                validation_result['warnings'].append(f"智能體權重總和為{total_weight:.2f}，建議調整為1.0")
            
            # 驗證數據庫配置
            if self.database_config.vector_dimension <= 0:
                validation_result['errors'].append("向量維度必須大於0")
                validation_result['valid'] = False
            
            self.logger.info(f"配置驗證完成: {'有效' if validation_result['valid'] else '無效'}")
        
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"配置驗證過程出錯: {str(e)}")
            self.logger.error(f"配置驗證失敗: {str(e)}")
        
        return validation_result

    def validate_backend_config(self) -> Dict[str, Any]:
        """驗證 Backend 配置的完整性 v2.1"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            backend_config = self.get_backend_config()
            
            # 驗證 LLM 配置
            llm_config = backend_config.get("llm", {})
            if not llm_config.get("api_key"):
                validation_result['warnings'].append("LLM API Key 未設置，將無法使用真實 LLM 服務")
            
            if not llm_config.get("api_url"):
                validation_result['errors'].append("LLM API URL 未設置")
                validation_result['valid'] = False
            
            if not llm_config.get("model"):
                validation_result['warnings'].append("LLM 模型未指定")
            
            # 驗證 Embedding 配置
            embedding_config = backend_config.get("embedding", {})
            if not embedding_config.get("api_key"):
                validation_result['warnings'].append("Embedding API Key 未設置，將使用降級向量化方法")
            
            if not embedding_config.get("base_url"):
                validation_result['warnings'].append("Embedding API URL 未設置")
            
            # 驗證 Weaviate 配置
            weaviate_config = backend_config.get("weaviate", {})
            if not weaviate_config.get("url"):
                validation_result['errors'].append("Weaviate URL 未設置")
                validation_result['valid'] = False
            
            # 檢查 Weaviate 連接性（可選）
            try:
                import weaviate
                url = weaviate_config.get("url", "http://localhost:8080")
                api_key = weaviate_config.get("api_key")
                
                if api_key:
                    client = weaviate.Client(
                        url=url,
                        auth_client_secret=weaviate.AuthApiKey(api_key=api_key),
                        timeout_config=(5, 5)
                    )
                else:
                    client = weaviate.Client(
                        url=url,
                        timeout_config=(5, 5)
                    )
                
                # 測試連接
                client.is_ready()
                validation_result['warnings'].append(f"Weaviate 連接測試成功: {url}")
                
            except Exception as e:
                validation_result['warnings'].append(f"Weaviate 連接測試失敗: {str(e)}")
            
            self.logger.info(f"Backend 配置驗證完成: {'有效' if validation_result['valid'] else '無效'}")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Backend 配置驗證過程出錯: {str(e)}")
            self.logger.error(f"Backend 配置驗證失敗: {str(e)}")
        
        return validation_result

    def get_full_validation(self) -> Dict[str, Any]:
        """獲取完整的配置驗證報告"""
        scbr_validation = self.validate_config()
        backend_validation = self.validate_backend_config()
        
        return {
            "scbr_config": scbr_validation,
            "backend_config": backend_validation,
            "overall_valid": scbr_validation['valid'] and backend_validation['valid'],
            "total_errors": len(scbr_validation['errors']) + len(backend_validation['errors']),
            "total_warnings": len(scbr_validation['warnings']) + len(backend_validation['warnings'])
        }

# 全局配置實例
_global_config = None

def get_config(config_path: str = None) -> SCBRConfig:
    """獲取全局配置實例"""
    global _global_config
    if _global_config is None:
        _global_config = SCBRConfig(config_path)
    return _global_config

def reload_global_config():
    """重新載入全局配置"""
    global _global_config
    if _global_config is not None:
        _global_config.reload_config()

# 便捷函數 - S-CBR 配置
def get_spiral_config() -> SpiralConfig:
    """獲取螺旋推理配置"""
    return get_config().get_spiral_config()

def get_session_config() -> SessionConfig:
    """獲取會話配置"""
    return get_config().get_session_config()

def get_agent_config() -> AgentConfig:
    """獲取智能體配置"""
    return get_config().get_agent_config()

def get_database_config() -> DatabaseConfig:
    """獲取數據庫配置"""
    return get_config().get_database_config()

def get_logging_config() -> LoggingConfig:
    """獲取日誌配置"""
    return get_config().get_logging_config()

# 便捷函數 - Backend 配置 (v2.1 新增)
def get_llm_config() -> Dict[str, Any]:
    """獲取 LLM 配置"""
    return get_config().get_llm_config()

def get_embedding_config() -> Dict[str, Any]:
    """獲取 Embedding 配置"""
    return get_config().get_embedding_config()

def get_weaviate_config() -> Dict[str, Any]:
    """獲取 Weaviate 配置"""
    return get_config().get_weaviate_config()

def get_backend_config() -> Dict[str, Any]:
    """獲取完整的 Backend 配置"""
    return get_config().get_backend_config()

# 便捷函數 - 配置驗證 (v2.1 新增)
def validate_all_configs() -> Dict[str, Any]:
    """驗證所有配置"""
    return get_config().get_full_validation()

def clear_config_cache():
    """清除配置緩存"""
    get_config().clear_backend_cache()

# 向後兼容的類別名稱
SCBRConfigV2 = SCBRConfig
SCBRConfigV21 = SCBRConfig

__all__ = [
    "SCBRConfig", "SCBRConfigV2", "SCBRConfigV21",
    "SpiralConfig", "SessionConfig", "AgentConfig", "DatabaseConfig", "LoggingConfig",
    "get_config", "reload_global_config",
    "get_spiral_config", "get_session_config", "get_agent_config", 
    "get_database_config", "get_logging_config",
    # v2.1 新增的 Backend 配置函數
    "get_llm_config", "get_embedding_config", "get_weaviate_config", "get_backend_config",
    # v2.1 新增的驗證和工具函數
    "validate_all_configs", "clear_config_cache"
]
