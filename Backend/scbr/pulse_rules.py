# scbr/pulse_rules.py
from typing import List

# 定義脈象類型對應的模式關鍵詞
PULSE_PATTERN_MAP = {
    "無力": ["氣虛", "血虛"],   # 無力脈 -> 多為氣虛或血虛
    "有力": ["實證", "熱證"],   # 有力脈 -> 多為實證或熱証
    "遲":   ["寒證", "陽虛"],   # 遲脈 -> 偏寒、陽虛
    "數":   ["熱證", "陰虛"],   # 數脈 -> 偏熱、陰虛火旺
    "浮":   ["表證", "虛證"],   # 浮脈 -> 表證或虛陽
    "沉":   ["裡證", "氣滯"],   # 沉脈 -> 裡證或有氣滯/痰飲
    "軟":   ["虛證", "濕困"],   # 軟脈 -> 虛證或濕困脾胃
    # ... 其他脈象類型及其對應模式
}

def infer_patterns_from_pulse(pulse_ids: List[str]) -> List[str]:
    """
    根據脈象知識庫的ID列表，推斷可能的證型模式列表。
    這裡假設我們可從脈象知識的ID反查其脈象類型特徵，再映射到模式。
    """
    patterns = []
    # 模擬：假設脈象ID命名本身含義，如 "浮"、"遲" 等，或可查表獲得類型
    for pid in pulse_ids:
        for pulse_type, pat_list in PULSE_PATTERN_MAP.items():
            if pulse_type in pid:
                patterns.extend(pat_list)
    # 去重
    patterns = list(set(patterns))
    return patterns

def analyze_pulse_detail(pulse_data: dict) -> List[str]:
    """
    直接從原始脈診資料結構分析，提取脈象特徵並推斷模式。
    :param pulse_data: 例如病例中的 pulse 字段（含左右寸關尺的脈象信息）
    """
    inferred_patterns = []
    try:
        # 遍歷每個脈位，收集類型與附註
        for position, detail in pulse_data.items():
            types = detail.get("types", [])
            note = detail.get("note", "")
            # 匯總所有提及的脈象類型和附註
            for t in types:
                if t in PULSE_PATTERN_MAP:
                    inferred_patterns.extend(PULSE_PATTERN_MAP[t])
            if note and note in PULSE_PATTERN_MAP:
                inferred_patterns.extend(PULSE_PATTERN_MAP[note])
        inferred_patterns = list(set(inferred_patterns))
    except Exception:
        pass
    return inferred_patterns
