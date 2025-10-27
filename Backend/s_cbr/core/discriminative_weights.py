# -*- coding: utf-8 -*-
"""
Backend/s_cbr/core/discriminative_weights.py
高鑑別權重系統 - 實現症狀權重動態化、舌脈決策閘
"""

from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from ..utils.logger import get_logger
from ..config import SCBRConfig

logger = get_logger("DiscriminativeWeights")

@dataclass
class DiscriminativeConfig:
    """鑑別權重配置"""
    # 高鑑別症狀加權值
    high_discriminative_bonus: float = 0.20
    medium_discriminative_bonus: float = 0.15
    low_discriminative_bonus: float = 0.10
    
    # 舌脈 prior 加權
    tongue_pulse_prior: float = 0.15
    
    # 互斥對抑制值
    mutual_exclusion_penalty: float = -0.25

class DiscriminativeWeightSystem:
    """高鑑別權重系統"""
    
    def __init__(self, config: DiscriminativeConfig):
        self.config = config
        
        # ✅ 擴充舌脈關鍵詞（最全版本）
        self.tongue_pulse_keywords = {
            # === 舌質 ===
            "舌紅", "舌淡", "舌暗", "舌紫", "舌絳",
            "舌質紅", "舌質淡", "舌質暗", "舌質紫",
            "舌尖紅", "舌邊紅", "舌根紅",
            "舌胖", "舌瘦", "舌嫩", "舌老",
            "舌胖大", "舌有齒痕",
            
            # === 舌苔 ===
            "苔白", "苔黃", "苔灰", "苔黑",
            "苔膩", "苔厚", "苔薄", "苔剝",
            "苔薄白", "苔厚膩", "苔黃膩", "苔白膩",
            "無苔", "少苔", "苔脫",
            
            # === 脈象（28脈） ===
            # 浮沉類
            "脈浮", "脈沉", "脈伏", "浮脈", "沉脈",
            # 遲數類
            "脈遲", "脈數", "脈疾", "遲脈", "數脈",
            # 虛實類
            "脈虛", "脈實", "虛脈", "實脈",
            # 滑澀類
            "脈滑", "脈澀", "滑脈", "澀脈",
            # 其他常見脈
            "脈細", "脈弦", "脈緊", "脈洪", "脈微",
            "脈弱", "脈濡", "脈革", "脈牢", "脈促",
            "脈結", "脈代", "脈散", "脈芤", "脈動",
            "細脈", "弦脈", "緊脈", "洪脈", "微脈",
            
            # === 脈位 ===
            "左寸", "左關", "左尺",
            "右寸", "右關", "右尺",
            "寸脈", "關脈", "尺脈",
            "寸口", "脈口",
            
            # === 組合描述 ===
            "脈搏", "脈象", "舌象", "舌苔",
            "脈搏有點", "脈搏微", "舌頭",
            "舌質淡紅", "舌淡紅", "舌紅少苔"
        }
        
        # ✅ 症狀互斥對（擴充版）
        self.mutually_exclusive_pairs = [
            # 寒熱互斥
            ("怕冷", "怕熱"),
            ("惡寒", "發熱"),
            ("手足冰冷", "五心煩熱"),
            ("喜溫飲", "喜冷飲"),
            
            # 虛實互斥
            ("氣虛", "氣實"),
            ("脈弱", "脈洪"),
            ("聲音低微", "聲音洪亮"),
            
            # 便秘腹瀉互斥
            ("便秘", "腹瀉"),
            ("大便乾", "大便溏"),
            
            # 多尿少尿互斥
            ("小便頻數", "小便不利"),
            ("尿多", "尿少"),
            
            # 食慾互斥
            ("食慾不振", "食慾亢進"),
            ("納差", "多食易飢"),
            
            # 汗證互斥
            ("無汗", "多汗"),
            ("盜汗", "自汗")  # 部分互斥
        ]
        
        # ✅ 高鑑別症狀（權重 2.0）
        self.high_discriminative_symptoms = {
            # 舌脈（權重最高）
            **{k: 2.5 for k in self.tongue_pulse_keywords},
            
            # 特殊症狀（權重 2.0）
            "盜汗": 2.0,
            "自汗": 2.0,
            "五心煩熱": 2.0,
            "手足冰冷": 2.0,
            "潮熱": 2.0,
            "惡寒": 2.0,
            "惡風": 2.0,
            "喜溫飲": 1.8,
            "喜冷飲": 1.8,
            "腰膝酸軟": 1.8,
            "耳鳴": 1.8,
            "健忘": 1.8
        }
        
        # ✅ 為 calculate_symptom_weights 方法準備的集合屬性
        # 高鑑別症狀集合
        self.high_discriminative = set(self.high_discriminative_symptoms.keys())
        
        # 中等鑑別症狀
        self.medium_discriminative = {
            "頭暈", "乏力", "納差", "便溏", "腹脹",
            "胸悶", "氣短", "咳嗽", "咽乾", "口苦",
            "脅痛", "腰痛", "肢體困重", "身熱",
            "煩躁", "易怒", "抑鬱", "焦慮",
            "月經不調", "痛經", "白帶", "遺精", "陽痿",
            "目眩", "耳聾", "牙痛", "咽痛", "鼻塞"
        }
        
        # 低鑑別症狀（一般症狀）
        self.low_discriminative = {
            "疲倦", "食慾不振", "睡眠不佳", "精神不振",
            "頭痛", "腹痛", "不適", "疼痛", "酸痛",
            "乏力", "倦怠", "困倦"
        }
        
        logger.info("✅ 高鑑別權重系統初始化")
        logger.info(f"   舌脈關鍵詞: {len(self.tongue_pulse_keywords)} 個")
        logger.info(f"   互斥對: {len(self.mutually_exclusive_pairs)} 對")
        logger.info(f"   高鑑別症狀: {len(self.high_discriminative_symptoms)} 個")
        logger.info(f"   中等鑑別症狀: {len(self.medium_discriminative)} 個")
        logger.info(f"   低鑑別症狀: {len(self.low_discriminative)} 個")
    
    # ==================== B1: 計算症狀權重 ====================
    def calculate_symptom_weights(
        self,
        symptoms: List[str]
    ) -> Dict[str, float]:
        """
        計算症狀的鑑別權重
        
        Returns:
            {symptom: weight_bonus}
        """
        weights = {}
        
        for symptom in symptoms:
            bonus = 0.0
            
            # 高鑑別度
            if symptom in self.high_discriminative:
                bonus = self.config.high_discriminative_bonus
                
            # 中等鑑別度
            elif symptom in self.medium_discriminative:
                bonus = self.config.medium_discriminative_bonus
                
            # 低鑑別度
            elif symptom in self.low_discriminative:
                bonus = self.config.low_discriminative_bonus
            
            # 模糊匹配（包含關鍵詞）
            else:
                for high_disc in self.high_discriminative:
                    if high_disc in symptom or symptom in high_disc:
                        bonus = self.config.high_discriminative_bonus * 0.8
                        break
            
            if bonus > 0:
                weights[symptom] = bonus
        
        logger.info(f"🎯 症狀鑑別權重: {len(weights)} 個症狀獲得加權")
        return weights
    
    # ==================== B1: 檢查互斥對 ====================
    def check_mutual_exclusions(
        self,
        symptoms: List[str]
    ) -> Dict[str, float]:
        """
        檢查互斥症狀對，返回抑制權重
        
        Returns:
            {symptom: penalty}
        """
        penalties = {}
        symptom_set = set(symptoms)
        
        for pair in self.mutually_exclusive_pairs:
            # 如果互斥對同時出現
            if pair[0] in symptom_set and pair[1] in symptom_set:
                # 兩者都施加懲罰（避免同時高分）
                penalties[pair[0]] = self.config.mutual_exclusion_penalty
                penalties[pair[1]] = self.config.mutual_exclusion_penalty
                
                logger.warning(f"⚠️  檢測到互斥對: {pair[0]} ↔ {pair[1]}")
        
        return penalties
    
    # ==================== 綜合應用 ====================
    def apply_discriminative_weights(
        self,
        symptoms: List[str],
        base_scores: Dict[str, float],
        candidate_syndromes: Dict[str, float] = None
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        綜合應用所有鑑別權重機制
        
        Args:
            symptoms: 症狀列表
            base_scores: 症狀基礎分數 {symptom: score}
            candidate_syndromes: 候選證型分數 {syndrome: score}
            
        Returns:
            (症狀調整分數, 證型調整分數)
        """
        # 1. 計算症狀權重
        symptom_weights = self.calculate_symptom_weights(symptoms)
        
        # 2. 檢查互斥對
        mutual_penalties = self.check_mutual_exclusions(symptoms)
        
        # 3. 綜合調整症狀分數
        adjusted_symptom_scores = base_scores.copy()
        for symptom, score in adjusted_symptom_scores.items():
            # 加權
            if symptom in symptom_weights:
                adjusted_symptom_scores[symptom] += symptom_weights[symptom]
            
            # 互斥懲罰
            if symptom in mutual_penalties:
                adjusted_symptom_scores[symptom] += mutual_penalties[symptom]
        
        # 4. 證型調整分數（目前為空字典）
        adjusted_syndrome_scores = candidate_syndromes.copy() if candidate_syndromes else {}
        
        logger.info(f"✅ 鑑別權重應用完成:")
        logger.info(f"   症狀加權: {len(symptom_weights)} 個")
        logger.info(f"   互斥懲罰: {len(mutual_penalties)} 對")
        
        return adjusted_symptom_scores, adjusted_syndrome_scores