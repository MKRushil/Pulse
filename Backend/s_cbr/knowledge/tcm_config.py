# -*- coding: utf-8 -*-
"""
Backend/s_cbr/knowledge/tcm_config.py
TCM 知識配置管理器
"""

from pathlib import Path
from typing import Dict, List, Set
import logging

logger = logging.getLogger("s_cbr.knowledge.TCMConfig")

KNOWLEDGE_ROOT = Path(__file__).parent

class TCMConfig:
    """TCM 配置管理器"""
    
    def __init__(self):
        self._cache = {}
        self._load_all()
    
    def _load_all(self):
        """載入所有配置"""
        try:
            self._cache["stopwords"] = self._load_stopwords()
            self._cache["tcm_keywords"] = self._load_tcm_keywords()
            self._cache["syndrome_keywords"] = self._load_syndrome_keywords()
            self._cache["zangfu_keywords"] = self._load_zangfu_keywords()
            self._cache["symptom_categories"] = self._load_symptom_categories()
            self._cache["pulse_keywords"] = self._load_pulse_keywords()
            self._cache["tongue_keywords"] = self._load_tongue_keywords()
            
            logger.info("✅ TCM 配置載入成功")
        except Exception as e:
            logger.error(f"❌ TCM 配置載入失敗: {e}")
            import traceback
            traceback.print_exc()
    
    # ==================== 停用詞 ====================
    def _load_stopwords(self) -> Set[str]:
        """載入停用詞"""
        stopwords_file = KNOWLEDGE_ROOT / "stopwords.txt"
        
        if stopwords_file.exists():
            try:
                with open(stopwords_file, 'r', encoding='utf-8') as f:
                    words = set(
                        line.strip() 
                        for line in f 
                        if line.strip() and not line.startswith('#')
                    )
                logger.info(f"✅ 載入停用詞: {len(words)} 個")
                return words
            except Exception as e:
                logger.warning(f"⚠️  載入停用詞失敗: {e}，使用預設")
        
        # 預設停用詞
        return {
            "的", "了", "和", "與", "及", "呢", "啊", "嗎",
            "在", "是", "有", "也", "都", "就", "而", "會",
            "可以", "這個", "那個", "什麼", "怎麼", "為什麼"
        }
    
    # ==================== TCM 關鍵詞 ====================
    def _load_tcm_keywords(self) -> Set[str]:
        """載入 TCM 症狀關鍵詞"""
        keywords_file = KNOWLEDGE_ROOT / "tcm_keywords.txt"
        
        if keywords_file.exists():
            try:
                with open(keywords_file, 'r', encoding='utf-8') as f:
                    words = set(
                        line.strip() 
                        for line in f 
                        if line.strip() and not line.startswith('#')
                    )
                logger.info(f"✅ 載入 TCM 關鍵詞: {len(words)} 個")
                return words
            except Exception as e:
                logger.warning(f"⚠️  載入 TCM 關鍵詞失敗: {e}，使用預設")
        
        # 預設關鍵詞
        return {
            # 睡眠相關
            "失眠", "多夢", "易醒", "入睡困難", "睡眠淺",
            # 心神相關
            "心悸", "心煩", "心慌", "驚悸", "怔忡", "健忘", "煩躁",
            # 消化系統
            "食慾不振", "腹脹", "腹痛", "便秘", "腹瀉", "噁心", "嘔吐",
            # 呼吸系統
            "咳嗽", "喘", "氣短", "鼻塞", "流涕", "咽痛",
            # 疼痛症狀
            "頭痛", "頭暈", "胸悶", "胸痛", "脅痛", "腰痠", "腰痛",
            # 體感症狀
            "疲倦", "乏力", "盜汗", "自汗", "潮熱", "怕冷", "手足冰冷",
            "口乾", "口苦", "口臭", "耳鳴",
            # 情志症狀
            "抑鬱", "焦慮", "易怒", "善太息", "情緒低落"
        }
    
    # ==================== 證型關鍵詞 ====================
    def _load_syndrome_keywords(self) -> Dict[str, List[str]]:
        """
        載入證型關鍵詞
        支持兩種 YAML 格式：
        1. 複雜格式（來自 syndromes.yaml）
        2. 簡單格式（直接列表）
        """
        syndromes_file = KNOWLEDGE_ROOT / "syndromes.yaml"
        
        if syndromes_file.exists():
            try:
                import yaml
                with open(syndromes_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                syndrome_keywords = {}
                
                # 檢查是否有 'syndromes' 鍵
                if not data or 'syndromes' not in data:
                    logger.warning("⚠️  syndromes.yaml 格式錯誤，使用預設")
                    return self._get_default_syndrome_keywords()
                
                syndromes = data.get('syndromes', [])
                
                # 處理每個證型
                for item in syndromes:
                    # ✅ 檢查項目類型
                    if isinstance(item, str):
                        # 簡單格式：只有證型名稱
                        syndrome_keywords[item] = []
                        
                    elif isinstance(item, dict):
                        # 複雜格式：包含 name 和 symptoms
                        name = item.get('name')
                        if not name:
                            continue
                        
                        # 收集症狀關鍵詞
                        keywords = []
                        
                        # 從 symptoms 字段提取
                        symptoms = item.get('symptoms', {})
                        if isinstance(symptoms, dict):
                            keywords.extend(symptoms.get('primary', []))
                            keywords.extend(symptoms.get('secondary', []))
                        elif isinstance(symptoms, list):
                            keywords.extend(symptoms)
                        
                        syndrome_keywords[name] = keywords
                
                logger.info(f"✅ 載入證型關鍵詞: {len(syndrome_keywords)} 種")
                
                # 如果載入的證型為空或太少，合併預設值
                if len(syndrome_keywords) < 5:
                    logger.warning("⚠️  載入的證型數量過少，合併預設值")
                    default_syndromes = self._get_default_syndrome_keywords()
                    for name, symptoms in default_syndromes.items():
                        if name not in syndrome_keywords:
                            syndrome_keywords[name] = symptoms
                
                return syndrome_keywords
                
            except Exception as e:
                logger.error(f"❌ 從 YAML 載入證型失敗: {e}")
                import traceback
                traceback.print_exc()
                return self._get_default_syndrome_keywords()
        
        # 文件不存在，使用預設
        logger.info("ℹ️  syndromes.yaml 不存在，使用預設證型")
        return self._get_default_syndrome_keywords()
    
    def _get_default_syndrome_keywords(self) -> Dict[str, List[str]]:
        """獲取預設證型關鍵詞"""
        return {
            # 八綱辨證
            "表證": ["惡寒", "發熱", "頭痛", "身痛", "苔薄白", "脈浮"],
            "裡證": ["腹痛", "腹脹", "便秘", "腹瀉"],
            "寒證": ["怕冷", "手足冰冷", "喜溫", "苔白", "脈遲"],
            "熱證": ["發熱", "口乾", "喜冷", "苔黃", "脈數"],
            "虛證": ["乏力", "氣短", "自汗", "脈弱"],
            "實證": ["脹滿", "疼痛拒按", "便秘", "脈實"],
            
            # 氣血辨證
            "氣虛": ["乏力", "氣短", "自汗", "脈弱", "語聲低微"],
            "血虛": ["面色蒼白", "頭暈", "心悸", "失眠", "脈細"],
            "氣滯": ["脹痛", "走竄痛", "善太息", "脈弦"],
            "血瘀": ["刺痛", "固定痛", "面色晦暗", "舌紫暗"],
            
            # 陰陽辨證
            "陽虛": ["畏寒", "手足冰冷", "腰膝痠軟", "脈沉遲"],
            "陰虛": ["潮熱", "盜汗", "五心煩熱", "口乾", "脈細數"],
            
            # 臟腑辨證
            "心氣虛": ["心悸", "氣短", "乏力", "自汗"],
            "心血虛": ["心悸", "失眠", "多夢", "健忘", "面色蒼白"],
            "心陰虛": ["心煩", "失眠", "潮熱", "盜汗", "口乾"],
            "心陽虛": ["心悸", "胸悶", "畏寒", "手足冰冷"],
            
            "肝血虛": ["頭暈", "目乾澀", "肢麻", "月經量少"],
            "肝陰虛": ["頭暈", "目乾", "脅痛", "口乾"],
            "肝氣鬱結": ["脅痛", "脹痛", "善太息", "情志抑鬱"],
            "肝陽上亢": ["頭痛", "頭暈", "面紅", "易怒"],
            
            "脾氣虛": ["食慾不振", "腹脹", "便溏", "乏力"],
            "脾陽虛": ["腹痛", "腹瀉", "畏寒", "手足冰冷"],
            
            "肺氣虛": ["氣短", "咳嗽", "自汗", "易感冒"],
            "肺陰虛": ["乾咳", "口乾", "潮熱", "盜汗"],
            
            "腎陽虛": ["腰膝痠軟", "畏寒", "小便清長", "陽痿"],
            "腎陰虛": ["腰膝痠軟", "潮熱", "盜汗", "耳鳴", "遺精"],
            
            # 複合證型
            "心脾兩虛": ["心悸", "失眠", "多夢", "食慾不振", "面色蒼白", "乏力"],
            "肝鬱脾虛": ["脅痛", "脹痛", "食慾不振", "腹脹", "便溏"],
            "心腎不交": ["心煩", "失眠", "腰膝痠軟", "盜汗"],
            "肝腎陰虛": ["頭暈", "目乾", "腰膝痠軟", "潮熱", "盜汗"]
        }
    
    # ==================== 臟腑關鍵詞 ====================
    def _load_zangfu_keywords(self) -> Dict[str, List[str]]:
        """載入臟腑關鍵詞"""
        return {
            "心": ["心悸", "心煩", "失眠", "健忘", "胸悶", "心慌"],
            "肝": ["脅痛", "易怒", "頭暈", "目乾", "抑鬱", "善太息"],
            "脾": ["食慾不振", "腹脹", "便溏", "乏力", "四肢睏倦"],
            "肺": ["咳嗽", "氣短", "喘", "鼻塞", "自汗"],
            "腎": ["腰膝痠軟", "耳鳴", "遺精", "陽痿", "小便異常", "盜汗"]
        }
    
    # ==================== 症狀分類 ====================
    def _load_symptom_categories(self) -> Dict[str, List[str]]:
        """載入症狀分類"""
        return {
            "外感": ["惡寒", "發熱", "咳嗽", "鼻塞", "咽痛", "頭痛"],
            "脾胃": ["食慾不振", "腹脹", "腹痛", "便秘", "腹瀉", "噁心"],
            "心神": ["失眠", "多夢", "心悸", "健忘", "煩躁", "心煩"],
            "肝鬱": ["脅痛", "脹痛", "易怒", "抑鬱", "善太息"],
            "疼痛": ["頭痛", "胸痛", "腹痛", "脅痛", "腰痛", "關節痛"],
            "虛弱": ["乏力", "氣短", "自汗", "盜汗", "疲倦"]
        }
    
    # ==================== 脈象關鍵詞 ====================
    def _load_pulse_keywords(self) -> Dict[str, List[str]]:
        """載入脈象關鍵詞"""
        return {
            "浮脈": ["外感", "表證"],
            "沉脈": ["裡證", "陽虛"],
            "遲脈": ["寒證", "陽虛"],
            "數脈": ["熱證", "陰虛"],
            "虛脈": ["氣血虛", "正氣不足"],
            "實脈": ["實證", "邪氣盛"],
            "弦脈": ["肝鬱", "痰飲", "疼痛"],
            "滑脈": ["痰濕", "食積", "妊娠"],
            "細脈": ["血虛", "陰虛", "氣血兩虛"]
        }
    
    # ==================== 舌診關鍵詞 ====================
    def _load_tongue_keywords(self) -> Dict[str, List[str]]:
        """載入舌診關鍵詞"""
        return {
            # 舌質
            "淡紅舌": ["正常", "氣血調和"],
            "淡白舌": ["氣血虛", "陽虛"],
            "紅舌": ["熱證", "陰虛"],
            "絳舌": ["熱盛", "陰虛"],
            "紫舌": ["血瘀", "寒凝"],
            # 舌苔
            "薄白苔": ["正常", "表證"],
            "厚白苔": ["濕濁", "痰飲"],
            "黃苔": ["熱證", "裡熱"],
            "膩苔": ["痰濕", "食積"],
            "少苔": ["陰虛", "津液不足"],
            "無苔": ["陰虛", "胃陰虛"]
        }
    
    # ==================== 獲取方法 ====================
    def get(self, key: str, default=None):
        """獲取配置"""
        return self._cache.get(key, default)
    
    def get_stopwords(self) -> Set[str]:
        return self._cache.get("stopwords", set())
    
    def get_tcm_keywords(self) -> Set[str]:
        return self._cache.get("tcm_keywords", set())
    
    def get_syndrome_keywords(self) -> Dict[str, List[str]]:
        return self._cache.get("syndrome_keywords", {})
    
    def get_zangfu_keywords(self) -> Dict[str, List[str]]:
        return self._cache.get("zangfu_keywords", {})
    
    def get_symptom_categories(self) -> Dict[str, List[str]]:
        return self._cache.get("symptom_categories", {})
    
    def get_pulse_keywords(self) -> Dict[str, List[str]]:
        return self._cache.get("pulse_keywords", {})
    
    def get_tongue_keywords(self) -> Dict[str, List[str]]:
        return self._cache.get("tongue_keywords", {})

# ==================== 全局實例 ====================
_tcm_config = None

def get_tcm_config() -> TCMConfig:
    """獲取 TCM 配置單例"""
    global _tcm_config
    if _tcm_config is None:
        _tcm_config = TCMConfig()
    return _tcm_config

def reload_config():
    """重新載入配置"""
    global _tcm_config
    _tcm_config = None
    return get_tcm_config()