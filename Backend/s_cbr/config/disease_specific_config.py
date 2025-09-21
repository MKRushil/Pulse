"""
疾病特定參數配置 v2.0

為不同疾病或場景定義專用參數配置
支援個性化診療策略與精準推理

版本：v2.0 - 螺旋互動版
更新：疾病特定智能體參數與策略配置
"""

from typing import Dict, Any, List, Optional, Union
import json
import logging
from pathlib import Path
from datetime import datetime

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
    from ..config.scbr_config import SCBRConfig, get_config
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    SCBRConfig = None

class DiseaseSpecificConfig:
    """
    疾病特定配置管理器 v2.0
    
    v2.0 特色：
    - 疾病特定參數配置
    - 智能體策略自定義
    - 動態配置加載
    - 參數驗證與優化
    """
    
    def __init__(self, config_dir: str = "./configs/diseases"):
        """初始化疾病特定配置管理器 v2.0"""
        self.logger = SpiralLogger.get_logger("DiseaseConfig") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("DiseaseConfig")
        self.version = "2.0"
        
        # 配置目錄
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 已載入的配置
        self.disease_configs = {}
        
        # 預設配置模板
        self.default_templates = self._create_default_templates()
        
        # 載入所有疾病配置
        self._load_all_disease_configs()
        
        self.logger.info(f"疾病特定配置管理器 v{self.version} 初始化完成")
    
    def _create_default_templates(self) -> Dict[str, Dict[str, Any]]:
        """創建默認配置模板"""
        return {
            "hypertension": {
                "disease_info": {
                    "name": "高血壓",
                    "category": "心血管疾病",
                    "severity_levels": ["輕度", "中度", "重度"],
                    "common_symptoms": ["頭痛", "頭暈", "心悸", "耳鳴", "失眠"],
                    "key_indicators": ["血壓值", "脈壓差", "併發症"]
                },
                "diagnostic_agent": {
                    "confidence_threshold": 0.75,
                    "syndrome_weights": {
                        "pulse_contribution": 0.35,  # 脈診權重較高
                        "symptom_pattern": 0.30,
                        "constitution_type": 0.20,
                        "seasonal_factor": 0.10,
                        "age_gender_factor": 0.05
                    },
                    "key_syndromes": ["肝陽上亢", "陰虛陽亢", "痰濁中阻", "瘀血阻絡"],
                    "pulse_patterns": ["弦脈", "滑脈", "細數脈"],
                    "treatment_principles": ["平肝潛陽", "滋陰潛陽", "化痰降濁", "活血化瘀"]
                },
                "adaptation_agent": {
                    "adaptation_weights": {
                        "age_factor": 0.25,      # 年齡因素重要
                        "severity_factor": 0.20,
                        "complication_factor": 0.20,
                        "constitution_factor": 0.15,
                        "lifestyle_factor": 0.20
                    },
                    "age_adjustments": {
                        "young_adult": {"weight": 0.8, "focus": "生活方式"},
                        "middle_aged": {"weight": 1.0, "focus": "工作壓力"},
                        "elderly": {"weight": 1.2, "focus": "併發症防範"}
                    },
                    "severity_adjustments": {
                        "mild": {"medication_weight": 0.6, "lifestyle_weight": 1.4},
                        "moderate": {"medication_weight": 1.0, "lifestyle_weight": 1.0},
                        "severe": {"medication_weight": 1.4, "lifestyle_weight": 0.8}
                    }
                },
                "monitoring_agent": {
                    "safety_thresholds": {
                        "blood_pressure_high": 180,
                        "blood_pressure_low": 90,
                        "pulse_pressure_wide": 60,
                        "heart_rate_high": 100,
                        "heart_rate_low": 50
                    },
                    "risk_factors": {
                        "high_risk": ["腦出血史", "心肌梗死史", "腎功能異常"],
                        "medium_risk": ["糖尿病", "高脂血症", "肥胖"],
                        "monitoring_frequency": "weekly"
                    }
                },
                "spiral_config": {
                    "max_rounds": 4,
                    "convergence_threshold": 0.85,
                    "case_selection_strategy": "blood_pressure_focused",
                    "similarity_weights": {
                        "age_similarity": 0.20,
                        "bp_level_similarity": 0.30,
                        "symptom_similarity": 0.25,
                        "constitution_similarity": 0.15,
                        "complication_similarity": 0.10
                    }
                }
            },
            
            "insomnia": {
                "disease_info": {
                    "name": "失眠症",
                    "category": "神經精神疾病",
                    "severity_levels": ["輕度", "中度", "重度"],
                    "common_symptoms": ["入睡困難", "易醒", "早醒", "睡眠淺", "多夢"],
                    "key_indicators": ["睡眠質量", "睡眠時長", "日間功能"]
                },
                "diagnostic_agent": {
                    "confidence_threshold": 0.70,
                    "syndrome_weights": {
                        "pulse_contribution": 0.25,
                        "symptom_pattern": 0.40,  # 症狀模式權重較高
                        "constitution_type": 0.20,
                        "emotional_factor": 0.10,
                        "lifestyle_factor": 0.05
                    },
                    "key_syndromes": ["心神不寧", "肝鬱化火", "陰虛火旺", "心脾兩虛"],
                    "pulse_patterns": ["細數脈", "弦細脈", "虛脈"],
                    "treatment_principles": ["養心安神", "疏肝解鬱", "滋陰降火", "健脾養心"]
                },
                "adaptation_agent": {
                    "adaptation_weights": {
                        "sleep_pattern_factor": 0.30,
                        "stress_factor": 0.25,
                        "age_factor": 0.15,
                        "constitution_factor": 0.15,
                        "lifestyle_factor": 0.15
                    },
                    "sleep_pattern_adjustments": {
                        "difficulty_falling_asleep": {"anxiolytic_weight": 1.2},
                        "frequent_awakening": {"sedative_weight": 1.1},
                        "early_morning_awakening": {"depression_focus": 1.3}
                    }
                },
                "monitoring_agent": {
                    "safety_thresholds": {
                        "sleep_duration_min": 4,
                        "sleep_quality_min": 3,
                        "daytime_dysfunction_max": 7
                    },
                    "monitoring_parameters": ["睡眠日記", "主觀睡眠質量", "日間嗜睡程度"]
                },
                "spiral_config": {
                    "max_rounds": 5,
                    "convergence_threshold": 0.80,
                    "case_selection_strategy": "sleep_pattern_focused",
                    "similarity_weights": {
                        "sleep_pattern_similarity": 0.35,
                        "age_similarity": 0.15,
                        "stress_level_similarity": 0.20,
                        "constitution_similarity": 0.15,
                        "duration_similarity": 0.15
                    }
                }
            },
            
            "digestive_disorders": {
                "disease_info": {
                    "name": "消化系統疾病",
                    "category": "消化系統疾病",
                    "severity_levels": ["輕度", "中度", "重度"],
                    "common_symptoms": ["腹痛", "腹脹", "嘔吐", "腹瀉", "便秘", "食慾不振"],
                    "key_indicators": ["症狀部位", "疼痛性質", "排便情況"]
                },
                "diagnostic_agent": {
                    "confidence_threshold": 0.72,
                    "syndrome_weights": {
                        "pulse_contribution": 0.20,
                        "symptom_pattern": 0.35,
                        "tongue_pattern": 0.15,
                        "abdominal_examination": 0.20,
                        "constitution_type": 0.10
                    },
                    "key_syndromes": ["脾胃虛弱", "肝氣犯胃", "胃陰不足", "寒濕困脾"],
                    "pulse_patterns": ["緩脈", "弦脈", "細脈", "滑脈"],
                    "treatment_principles": ["健脾益氣", "疏肝和胃", "滋養胃陰", "溫中散寒"]
                },
                "adaptation_agent": {
                    "adaptation_weights": {
                        "dietary_factor": 0.30,
                        "stress_factor": 0.20,
                        "constitution_factor": 0.20,
                        "age_factor": 0.15,
                        "seasonal_factor": 0.15
                    },
                    "dietary_adjustments": {
                        "spleen_deficiency": {"warm_foods": 1.3, "cold_foods": 0.7},
                        "stomach_yin_deficiency": {"nourishing_foods": 1.2, "spicy_foods": 0.6}
                    }
                },
                "monitoring_agent": {
                    "safety_thresholds": {
                        "pain_severity_max": 8,
                        "vomiting_frequency_max": 5,
                        "weight_loss_max": 10  # 百分比
                    },
                    "red_flags": ["嚴重腹痛", "血便", "體重急劇下降", "持續嘔吐"]
                },
                "spiral_config": {
                    "max_rounds": 4,
                    "convergence_threshold": 0.82,
                    "case_selection_strategy": "symptom_location_focused",
                    "similarity_weights": {
                        "symptom_location_similarity": 0.30,
                        "pain_nature_similarity": 0.25,
                        "constitution_similarity": 0.20,
                        "age_similarity": 0.15,
                        "trigger_factor_similarity": 0.10
                    }
                }
            },
            
            "anxiety_depression": {
                "disease_info": {
                    "name": "焦慮抑鬱",
                    "category": "精神心理疾病",
                    "severity_levels": ["輕度", "中度", "重度"],
                    "common_symptoms": ["焦慮不安", "心情低落", "興趣喪失", "疲乏無力", "注意力不集中"],
                    "key_indicators": ["情緒狀態", "認知功能", "社會功能", "軀體症狀"]
                },
                "diagnostic_agent": {
                    "confidence_threshold": 0.73,
                    "syndrome_weights": {
                        "pulse_contribution": 0.25,
                        "emotional_symptoms": 0.35,
                        "physical_symptoms": 0.20,
                        "constitution_type": 0.15,
                        "trigger_factors": 0.05
                    },
                    "key_syndromes": ["肝氣鬱結", "心神不寧", "心脾兩虛", "腎陽虛衰"],
                    "pulse_patterns": ["弦脈", "細脈", "虛脈", "沉脈"],
                    "treatment_principles": ["疏肝解鬱", "養心安神", "健脾養心", "溫腎助陽"]
                },
                "adaptation_agent": {
                    "adaptation_weights": {
                        "psychological_factor": 0.35,
                        "stress_factor": 0.25,
                        "constitution_factor": 0.20,
                        "social_factor": 0.12,
                        "seasonal_factor": 0.08
                    },
                    "severity_adjustments": {
                        "mild": {"psychotherapy_weight": 1.3, "medication_weight": 0.8},
                        "moderate": {"psychotherapy_weight": 1.1, "medication_weight": 1.0},
                        "severe": {"psychotherapy_weight": 0.9, "medication_weight": 1.2}
                    }
                },
                "monitoring_agent": {
                    "safety_thresholds": {
                        "depression_score_max": 20,
                        "anxiety_score_max": 15,
                        "suicidal_ideation": 0
                    },
                    "risk_assessment": {
                        "suicide_risk_factors": ["既往自殺史", "嚴重抑鬱", "社會支持缺乏"],
                        "monitoring_frequency": "weekly"
                    }
                },
                "spiral_config": {
                    "max_rounds": 5,
                    "convergence_threshold": 0.78,
                    "case_selection_strategy": "emotional_pattern_focused",
                    "similarity_weights": {
                        "emotional_pattern_similarity": 0.35,
                        "trigger_factor_similarity": 0.20,
                        "severity_similarity": 0.20,
                        "age_similarity": 0.15,
                        "constitution_similarity": 0.10
                    }
                }
            },
            
            "chronic_fatigue": {
                "disease_info": {
                    "name": "慢性疲勞",
                    "category": "亞健康狀態",
                    "severity_levels": ["輕度", "中度", "重度"],
                    "common_symptoms": ["持續疲勞", "記憶力減退", "注意力不集中", "睡眠障礙", "肌肉關節痛"],
                    "key_indicators": ["疲勞程度", "持續時間", "功能影響", "伴隨症狀"]
                },
                "diagnostic_agent": {
                    "confidence_threshold": 0.68,
                    "syndrome_weights": {
                        "pulse_contribution": 0.20,
                        "fatigue_pattern": 0.30,
                        "constitutional_symptoms": 0.25,
                        "sleep_quality": 0.15,
                        "stress_factors": 0.10
                    },
                    "key_syndromes": ["氣虛", "血虛", "陰虛", "脾腎陽虛"],
                    "pulse_patterns": ["虛脈", "細脈", "緩脈", "沉脈"],
                    "treatment_principles": ["益氣養血", "滋陰補腎", "健脾溫陽", "調和陰陽"]
                },
                "adaptation_agent": {
                    "adaptation_weights": {
                        "fatigue_pattern_factor": 0.30,
                        "constitution_factor": 0.25,
                        "lifestyle_factor": 0.20,
                        "stress_factor": 0.15,
                        "age_factor": 0.10
                    },
                    "constitution_adjustments": {
                        "qi_deficiency": {"tonifying_weight": 1.3, "dispersing_weight": 0.7},
                        "yin_deficiency": {"nourishing_weight": 1.2, "warming_weight": 0.8}
                    }
                },
                "monitoring_agent": {
                    "safety_thresholds": {
                        "fatigue_severity_max": 8,
                        "functional_impairment_max": 7,
                        "sleep_quality_min": 3
                    },
                    "improvement_markers": ["活力恢復", "睡眠改善", "認知功能提升"]
                },
                "spiral_config": {
                    "max_rounds": 4,
                    "convergence_threshold": 0.75,
                    "case_selection_strategy": "constitution_focused",
                    "similarity_weights": {
                        "constitution_similarity": 0.30,
                        "fatigue_pattern_similarity": 0.25,
                        "age_similarity": 0.20,
                        "lifestyle_similarity": 0.15,
                        "duration_similarity": 0.10
                    }
                }
            }
        }
    
    def _load_all_disease_configs(self):
        """載入所有疾病配置"""
        try:
            # 從默認模板載入
            for disease_name, config in self.default_templates.items():
                self.disease_configs[disease_name] = config.copy()
            
            # 從文件載入自定義配置
            for config_file in self.config_dir.glob("*.json"):
                disease_name = config_file.stem
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        custom_config = json.load(f)
                    
                    # 合併配置
                    if disease_name in self.disease_configs:
                        self._merge_configs(self.disease_configs[disease_name], custom_config)
                    else:
                        self.disease_configs[disease_name] = custom_config
                        
                    self.logger.info(f"載入疾病配置: {disease_name}")
                    
                except Exception as e:
                    self.logger.error(f"載入配置文件失敗 {config_file}: {str(e)}")
            
            # 創建默認配置文件（如果不存在）
            self._create_default_config_files()
            
        except Exception as e:
            self.logger.error(f"載入疾病配置失敗: {str(e)}")
    
    def _create_default_config_files(self):
        """創建默認配置文件"""
        try:
            for disease_name, config in self.default_templates.items():
                config_file = self.config_dir / f"{disease_name}.json"
                
                if not config_file.exists():
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)
                    
                    self.logger.info(f"創建默認配置文件: {config_file}")
                    
        except Exception as e:
            self.logger.error(f"創建默認配置文件失敗: {str(e)}")
    
    def _merge_configs(self, base_config: Dict[str, Any], custom_config: Dict[str, Any]):
        """遞迴合併配置"""
        for key, value in custom_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                self._merge_configs(base_config[key], value)
            else:
                base_config[key] = value
    
    def get_disease_config(self, disease_name: str) -> Optional[Dict[str, Any]]:
        """
        獲取疾病配置
        
        Args:
            disease_name: 疾病名稱
            
        Returns:
            Optional[Dict[str, Any]]: 疾病配置，如果不存在則返回None
        """
        return self.disease_configs.get(disease_name)
    
    def get_agent_config(self, disease_name: str, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        獲取特定智能體的配置
        
        Args:
            disease_name: 疾病名稱
            agent_name: 智能體名稱 (diagnostic_agent, adaptation_agent, etc.)
            
        Returns:
            Optional[Dict[str, Any]]: 智能體配置
        """
        disease_config = self.get_disease_config(disease_name)
        if disease_config:
            return disease_config.get(agent_name)
        return None
    
    def get_spiral_config(self, disease_name: str) -> Optional[Dict[str, Any]]:
        """
        獲取螺旋推理配置
        
        Args:
            disease_name: 疾病名稱
            
        Returns:
            Optional[Dict[str, Any]]: 螺旋推理配置
        """
        disease_config = self.get_disease_config(disease_name)
        if disease_config:
            return disease_config.get("spiral_config")
        return None
    
    def list_available_diseases(self) -> List[str]:
        """
        列出可用的疾病配置
        
        Returns:
            List[str]: 疾病名稱列表
        """
        return list(self.disease_configs.keys())
    
    def save_disease_config(self, disease_name: str, config: Dict[str, Any]) -> bool:
        """
        保存疾病配置
        
        Args:
            disease_name: 疾病名稱
            config: 疾病配置
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 更新內存中的配置
            self.disease_configs[disease_name] = config
            
            # 保存到文件
            config_file = self.config_dir / f"{disease_name}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"保存疾病配置: {disease_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存疾病配置失敗 {disease_name}: {str(e)}")
            return False
    
    def validate_disease_config(self, disease_name: str) -> Dict[str, Any]:
        """
        驗證疾病配置
        
        Args:
            disease_name: 疾病名稱
            
        Returns:
            Dict[str, Any]: 驗證結果
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            config = self.get_disease_config(disease_name)
            if not config:
                result["valid"] = False
                result["errors"].append(f"疾病配置不存在: {disease_name}")
                return result
            
            # 檢查必需字段
            required_sections = ["disease_info", "diagnostic_agent", "spiral_config"]
            for section in required_sections:
                if section not in config:
                    result["errors"].append(f"缺少必需部分: {section}")
                    result["valid"] = False
            
            # 檢查診斷智能體配置
            if "diagnostic_agent" in config:
                diag_config = config["diagnostic_agent"]
                
                if "confidence_threshold" in diag_config:
                    threshold = diag_config["confidence_threshold"]
                    if not (0.0 <= threshold <= 1.0):
                        result["errors"].append("confidence_threshold 應在 0.0-1.0 範圍內")
                        result["valid"] = False
                
                if "syndrome_weights" in diag_config:
                    weights = diag_config["syndrome_weights"]
                    total_weight = sum(weights.values())
                    if abs(total_weight - 1.0) > 0.1:
                        result["warnings"].append(f"syndrome_weights 總和不等於1.0: {total_weight}")
            
            # 檢查螺旋配置
            if "spiral_config" in config:
                spiral_config = config["spiral_config"]
                
                if "max_rounds" in spiral_config:
                    max_rounds = spiral_config["max_rounds"]
                    if not (1 <= max_rounds <= 10):
                        result["errors"].append("max_rounds 應在 1-10 範圍內")
                        result["valid"] = False
                
                if "convergence_threshold" in spiral_config:
                    threshold = spiral_config["convergence_threshold"]
                    if not (0.0 <= threshold <= 1.0):
                        result["errors"].append("convergence_threshold 應在 0.0-1.0 範圍內")
                        result["valid"] = False
            
            return result
            
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"驗證過程發生錯誤: {str(e)}")
            return result
    
    def get_config_template(self, disease_category: str = "general") -> Dict[str, Any]:
        """
        獲取配置模板
        
        Args:
            disease_category: 疾病類別
            
        Returns:
            Dict[str, Any]: 配置模板
        """
        # 基礎模板
        template = {
            "disease_info": {
                "name": "",
                "category": disease_category,
                "severity_levels": ["輕度", "中度", "重度"],
                "common_symptoms": [],
                "key_indicators": []
            },
            "diagnostic_agent": {
                "confidence_threshold": 0.70,
                "syndrome_weights": {
                    "pulse_contribution": 0.25,
                    "symptom_pattern": 0.35,
                    "constitution_type": 0.20,
                    "seasonal_factor": 0.10,
                    "age_gender_factor": 0.10
                },
                "key_syndromes": [],
                "pulse_patterns": [],
                "treatment_principles": []
            },
            "adaptation_agent": {
                "adaptation_weights": {
                    "age_factor": 0.20,
                    "severity_factor": 0.20,
                    "constitution_factor": 0.20,
                    "lifestyle_factor": 0.20,
                    "seasonal_factor": 0.20
                }
            },
            "monitoring_agent": {
                "safety_thresholds": {},
                "monitoring_parameters": []
            },
            "spiral_config": {
                "max_rounds": 4,
                "convergence_threshold": 0.80,
                "case_selection_strategy": "symptom_focused",
                "similarity_weights": {
                    "symptom_similarity": 0.30,
                    "age_similarity": 0.20,
                    "constitution_similarity": 0.20,
                    "severity_similarity": 0.15,
                    "lifestyle_similarity": 0.15
                }
            }
        }
        
        return template
    
    def create_new_disease_config(self, disease_name: str, disease_category: str = "general") -> Dict[str, Any]:
        """
        創建新的疾病配置
        
        Args:
            disease_name: 疾病名稱
            disease_category: 疾病類別
            
        Returns:
            Dict[str, Any]: 新的疾病配置
        """
        try:
            template = self.get_config_template(disease_category)
            template["disease_info"]["name"] = disease_name
            template["disease_info"]["category"] = disease_category
            
            # 添加創建時間戳
            template["metadata"] = {
                "created_at": datetime.now().isoformat(),
                "version": self.version,
                "template_used": disease_category
            }
            
            # 保存配置
            self.save_disease_config(disease_name, template)
            
            return template
            
        except Exception as e:
            self.logger.error(f"創建疾病配置失敗 {disease_name}: {str(e)}")
            return {}
    
    def get_config_statistics(self) -> Dict[str, Any]:
        """
        獲取配置統計信息
        
        Returns:
            Dict[str, Any]: 統計信息
        """
        try:
            stats = {
                "total_diseases": len(self.disease_configs),
                "disease_categories": {},
                "agent_config_coverage": {
                    "diagnostic_agent": 0,
                    "adaptation_agent": 0,
                    "monitoring_agent": 0,
                    "feedback_agent": 0
                },
                "validation_status": {
                    "valid_configs": 0,
                    "configs_with_warnings": 0,
                    "invalid_configs": 0
                }
            }
            
            # 統計疾病類別
            for disease_name, config in self.disease_configs.items():
                category = config.get("disease_info", {}).get("category", "unknown")
                if category not in stats["disease_categories"]:
                    stats["disease_categories"][category] = 0
                stats["disease_categories"][category] += 1
                
                # 統計智能體配置覆蓋率
                for agent_name in stats["agent_config_coverage"]:
                    if agent_name in config:
                        stats["agent_config_coverage"][agent_name] += 1
                
                # 驗證狀態統計
                validation = self.validate_disease_config(disease_name)
                if validation["valid"]:
                    if validation["warnings"]:
                        stats["validation_status"]["configs_with_warnings"] += 1
                    else:
                        stats["validation_status"]["valid_configs"] += 1
                else:
                    stats["validation_status"]["invalid_configs"] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"獲取配置統計失敗: {str(e)}")
            return {"error": str(e)}

# 全域配置實例
_global_disease_config = None

def get_disease_config_manager(config_dir: str = "./configs/diseases") -> DiseaseSpecificConfig:
    """
    獲取全域疾病配置管理器實例
    
    Args:
        config_dir: 配置目錄
        
    Returns:
        DiseaseSpecificConfig: 配置管理器實例
    """
    global _global_disease_config
    
    if _global_disease_config is None:
        _global_disease_config = DiseaseSpecificConfig(config_dir)
    
    return _global_disease_config

def get_agent_config_for_disease(disease_name: str, agent_name: str) -> Optional[Dict[str, Any]]:
    """
    便捷函數：獲取疾病特定的智能體配置
    
    Args:
        disease_name: 疾病名稱
        agent_name: 智能體名稱
        
    Returns:
        Optional[Dict[str, Any]]: 智能體配置
    """
    manager = get_disease_config_manager()
    return manager.get_agent_config(disease_name, agent_name)

def get_spiral_config_for_disease(disease_name: str) -> Optional[Dict[str, Any]]:
    """
    便捷函數：獲取疾病特定的螺旋推理配置
    
    Args:
        disease_name: 疾病名稱
        
    Returns:
        Optional[Dict[str, Any]]: 螺旋推理配置
    """
    manager = get_disease_config_manager()
    return manager.get_spiral_config(disease_name)

# 向後兼容的類別名稱
DiseaseSpecificConfigV2 = DiseaseSpecificConfig

__all__ = [
    "DiseaseSpecificConfig", "DiseaseSpecificConfigV2",
    "get_disease_config_manager", "get_agent_config_for_disease", 
    "get_spiral_config_for_disease"
]