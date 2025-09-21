"""
S-CBR 系統配置管理 v2.0

管理 S-CBR 螺旋推理系統的全局配置
支援會話配置與螺旋推理參數管理

版本：v2.0 - 螺旋互動版
更新：會話管理配置與螺旋推理優化
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
    vector_dimension: int = 128
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
    S-CBR 系統配置管理器 v2.0
    
    v2.0 特色：
    - 會話配置管理
    - 螺旋推理參數配置  
    - 智能體協調配置
    - 動態配置更新
    """
    
    def __init__(self, config_path: str = None):
        """初始化配置管理器"""
        self.logger = SpiralLogger.get_logger("SCBRConfig") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("SCBRConfig")
        self.version = "2.0"
        
        # 配置文件路徑
        self.config_path = config_path or self._get_default_config_path()
        
        # 初始化配置對象
        self.spiral_config = SpiralConfig()
        self.session_config = SessionConfig()
        self.agent_config = AgentConfig()
        self.database_config = DatabaseConfig()
        self.logging_config = LoggingConfig()
        
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
            'version': self.version
        }
    
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

# 便捷函數
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

# 向後兼容的類別名稱
SCBRConfigV2 = SCBRConfig

__all__ = [
    "SCBRConfig", "SCBRConfigV2", 
    "SpiralConfig", "SessionConfig", "AgentConfig", "DatabaseConfig", "LoggingConfig",
    "get_config", "reload_global_config",
    "get_spiral_config", "get_session_config", "get_agent_config", 
    "get_database_config", "get_logging_config"
]
