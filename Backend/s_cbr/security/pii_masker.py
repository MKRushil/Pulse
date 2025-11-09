# -*- coding: utf-8 -*-
"""
PII/PHI 脫敏器 (PII Masker)
職責：防止 LLM02 敏感資訊揭露

實施策略：
1. 自動識別 PII/PHI
2. 多層級脫敏處理
3. 保留診斷相關資訊
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
from ..utils.logger import get_logger

logger = get_logger("PIIMasker")


class PIIType(Enum):
    """PII 類型"""
    ID_CARD = "身份證號"
    PHONE = "電話號碼"
    EMAIL = "電子郵件"
    ADDRESS = "地址"
    NAME = "姓名"
    BIRTHDAY = "出生日期"
    MEDICAL_RECORD = "病歷號"


@dataclass
class PIIMatch:
    """PII 匹配結果"""
    type: PIIType
    original: str
    masked: str
    position: Tuple[int, int]


class PIIMasker:
    """
    PII/PHI 自動脫敏器
    
    符合 HIPAA 和個資法要求
    """
    
    def __init__(self):
        """初始化脫敏器"""
        # 定義脫敏模式
        self.pii_patterns = self._build_pii_patterns()
        
        # 統計
        self.masking_stats = {pii_type: 0 for pii_type in PIIType}
        
        logger.info("✅ PIIMasker 初始化完成")
    
    def mask(self, text: str, preserve_diagnosis_info: bool = True) -> Tuple[str, List[PIIMatch]]:
        """
        執行 PII 脫敏
        
        Args:
            text: 原始文本
            preserve_diagnosis_info: 是否保留診斷相關資訊
            
        Returns:
            (脫敏後文本, 匹配列表)
        """
        masked_text = text
        matches = []
        
        # 按順序處理每種 PII 類型
        for pii_type, pattern_info in self.pii_patterns.items():
            pattern = pattern_info["pattern"]
            mask_template = pattern_info["mask"]
            
            # 查找所有匹配
            for match in pattern.finditer(masked_text):
                original = match.group(0)
                
                # 生成脫敏後的文本
                if isinstance(mask_template, str):
                    masked_value = mask_template
                elif callable(mask_template):
                    masked_value = mask_template(original)
                else:
                    masked_value = "***已脫敏***"
                
                # 記錄匹配
                matches.append(PIIMatch(
                    type=pii_type,
                    original=original,
                    masked=masked_value,
                    position=(match.start(), match.end())
                ))
                
                # 替換
                masked_text = masked_text.replace(original, masked_value, 1)
                
                # 更新統計
                self.masking_stats[pii_type] += 1
        
        if matches:
            logger.info(f"🔒 脫敏 {len(matches)} 項 PII: {[m.type.value for m in matches]}")
        
        return masked_text, matches
    
    def _build_pii_patterns(self) -> Dict[PIIType, Dict]:
        """構建 PII 檢測模式"""
        return {
            # 台灣身份證號 (A123456789)
            PIIType.ID_CARD: {
                "pattern": re.compile(r'\b[A-Z]\d{9}\b'),
                "mask": "***身份證***",
                "description": "台灣身份證號碼"
            },
            
            # 電話號碼 (09123456 78 或 02-12345678)
            PIIType.PHONE: {
                "pattern": re.compile(r'\b(09\d{8}|\d{2,3}-\d{7,8}|\+886[-\s]?\d{1,3}[-\s]?\d{6,8})\b'),
                "mask": "***電話***",
                "description": "電話號碼"
            },
            
            # Email
            PIIType.EMAIL: {
                "pattern": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                "mask": "***信箱***",
                "description": "電子郵件地址"
            },
            
            # 地址（簡單模式）
            PIIType.ADDRESS: {
                "pattern": re.compile(r'地址[:：]\s*([\u4e00-\u9fa5\d]{5,50})'),
                "mask": lambda m: re.sub(r'(地址[:：]\s*).*', r'\1***地址***', m),
                "description": "地址"
            },
            
            # 姓名（保守模式，只匹配明確標註的）
            PIIType.NAME: {
                "pattern": re.compile(r'(姓名|名字)[:：]\s*([\u4e00-\u9fa5]{2,4})'),
                "mask": lambda m: re.sub(r'(姓名|名字[:：]\s*).*', r'\1***姓名***', m),
                "description": "姓名"
            },
            
            # 出生日期
            PIIType.BIRTHDAY: {
                "pattern": re.compile(
                    r'(出生日期?|生日)[:：]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?|'
                    r'\d{2,3}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)'
                ),
                "mask": lambda m: re.sub(
                    r'(出生日期?|生日[:：]\s*).*',
                    r'\1***出生日期***',
                    m
                ),
                "description": "出生日期"
            },
            
            # 病歷號
            PIIType.MEDICAL_RECORD: {
                "pattern": re.compile(r'(病歷號|就診號|掛號號碼?)[:：]\s*([A-Z0-9]{6,20})'),
                "mask": lambda m: re.sub(
                    r'(病歷號|就診號|掛號號碼?[:：]\s*).*',
                    r'\1***病歷號***',
                    m
                ),
                "description": "病歷號"
            }
        }
    
    def mask_with_partial_reveal(
        self,
        text: str,
        reveal_last_n: int = 2
    ) -> Tuple[str, List[PIIMatch]]:
        """
        部分脫敏（保留最後 N 位）
        
        Args:
            text: 原始文本
            reveal_last_n: 保留最後幾位
            
        Returns:
            (脫敏後文本, 匹配列表)
        """
        def partial_mask(value: str, keep_last: int = reveal_last_n) -> str:
            if len(value) <= keep_last:
                return "***"
            return "*" * (len(value) - keep_last) + value[-keep_last:]
        
        masked_text = text
        matches = []
        
        # 只對特定類型做部分脫敏
        partial_mask_types = [PIIType.PHONE, PIIType.ID_CARD, PIIType.MEDICAL_RECORD]
        
        for pii_type in partial_mask_types:
            if pii_type not in self.pii_patterns:
                continue
                
            pattern_info = self.pii_patterns[pii_type]
            pattern = pattern_info["pattern"]
            
            for match in pattern.finditer(masked_text):
                original = match.group(0)
                masked_value = partial_mask(original, reveal_last_n)
                
                matches.append(PIIMatch(
                    type=pii_type,
                    original=original,
                    masked=masked_value,
                    position=(match.start(), match.end())
                ))
                
                masked_text = masked_text.replace(original, masked_value, 1)
        
        return masked_text, matches
    
    def detect_only(self, text: str) -> List[PIIMatch]:
        """
        僅檢測 PII，不進行脫敏
        
        Args:
            text: 原始文本
            
        Returns:
            匹配列表
        """
        matches = []
        
        for pii_type, pattern_info in self.pii_patterns.items():
            pattern = pattern_info["pattern"]
            
            for match in pattern.finditer(text):
                matches.append(PIIMatch(
                    type=pii_type,
                    original=match.group(0),
                    masked="[未脫敏]",
                    position=(match.start(), match.end())
                ))
        
        return matches
    
    def get_stats(self) -> Dict:
        """獲取脫敏統計"""
        return {
            "total_masked": sum(self.masking_stats.values()),
            "by_type": {
                pii_type.value: count
                for pii_type, count in self.masking_stats.items()
                if count > 0
            }
        }
    
    def reset_stats(self):
        """重置統計"""
        self.masking_stats = {pii_type: 0 for pii_type in PIIType}


# ============================================
# 使用範例
# ============================================
if __name__ == "__main__":
    masker = PIIMasker()
    
    # 測試文本
    test_text = """
    姓名：王小明
    身份證：A123456789
    電話：0912345678
    Email：test@example.com
    地址：台北市信義區信義路五段7號
    
    主訴：我最近失眠，頭暈，心悸。
    """
    
    # 完全脫敏
    print("=== 完全脫敏 ===")
    masked, matches = masker.mask(test_text)
    print(masked)
    print(f"\n脫敏項目: {len(matches)}")
    for m in matches:
        print(f"  - {m.type.value}: {m.original} → {m.masked}")
    
    # 部分脫敏
    print("\n=== 部分脫敏 ===")
    partial_masked, partial_matches = masker.mask_with_partial_reveal(test_text, reveal_last_n=3)
    print(partial_masked)
    
    # 僅檢測
    print("\n=== 僅檢測 ===")
    detected = masker.detect_only(test_text)
    print(f"檢測到 {len(detected)} 項 PII:")
    for d in detected:
        print(f"  - {d.type.value}: {d.original}")
    
    # 統計
    print("\n=== 統計 ===")
    stats = masker.get_stats()
    print(f"總計脫敏: {stats['total_masked']} 項")
    print(f"分類統計: {stats['by_type']}")