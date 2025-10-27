# -*- coding: utf-8 -*-
"""
TCM 知識庫加載器
"""

import yaml
from pathlib import Path
from typing import Dict, Any
from ..utils.logger import get_logger

logger = get_logger("KnowledgeLoader")

class TCMKnowledgeBase:
    """TCM 知識庫管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.knowledge_dir = Path(__file__).parent
        self.syndromes = {}
        self.constitutions = {}
        self.pathogenesis = {}
        self.treatment_principles = {}
        
        self._load_all_knowledge()
        self._initialized = True
    
    def _load_all_knowledge(self):
        """載入所有知識庫"""
        try:
            self.syndromes = self._load_yaml("syndromes.yaml")
            logger.info(f"✅ 載入證型規則: {len(self.syndromes['syndromes'])} 種")
            
            self.constitutions = self._load_yaml("constitutions.yaml")
            logger.info(f"✅ 載入體質分類: {len(self.constitutions['constitutions'])} 種")
            
            self.pathogenesis = self._load_yaml("pathogenesis.yaml")
            logger.info("✅ 載入病機模式庫")
            
            self.treatment_principles = self._load_yaml("treatment_principles.yaml")
            logger.info("✅ 載入治則治法庫")
            
        except Exception as e:
            logger.error(f"❌ 知識庫載入失敗: {e}")
            raise
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """載入 YAML 文件"""
        file_path = self.knowledge_dir / filename
        
        if not file_path.exists():
            logger.warning(f"⚠️  文件不存在: {file_path}")
            return {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return data or {}
    
    def get_syndrome(self, syndrome_name: str) -> Dict[str, Any]:
        """獲取證型資料"""
        return self.syndromes.get('syndromes', {}).get(syndrome_name, {})
    
    def get_constitution(self, constitution_name: str) -> Dict[str, Any]:
        """獲取體質資料"""
        return self.constitutions.get('constitutions', {}).get(constitution_name, {})
    
    def get_all_syndromes(self) -> Dict[str, Any]:
        """獲取所有證型"""
        return self.syndromes.get('syndromes', {})
    
    def get_all_constitutions(self) -> Dict[str, Any]:
        """獲取所有體質"""
        return self.constitutions.get('constitutions', {})
    
    def get_etiology_patterns(self) -> Dict[str, Any]:
        """獲取病因模式"""
        return self.pathogenesis.get('etiology', {})
    
    def get_location_patterns(self) -> Dict[str, Any]:
        """獲取病位模式"""
        return self.pathogenesis.get('location', {})
    
    def get_nature_patterns(self) -> Dict[str, Any]:
        """獲取病性模式"""
        return self.pathogenesis.get('nature', {})
    
    def get_treatment_principle(self, method: str) -> Dict[str, Any]:
        """獲取治法資料"""
        return self.treatment_principles.get('eight_methods', {}).get(method, {})

# 全局單例
knowledge_base = TCMKnowledgeBase()