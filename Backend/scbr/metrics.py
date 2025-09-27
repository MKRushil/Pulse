# scbr/metrics.py
from typing import Dict, List, Optional

def compute_metrics(scores: Dict[str, float], pulse_ids: Optional[List[str]] = None, diagnosis: Optional[str] = None) -> Dict[str, float]:
    """
    計算評估指標，包括 Case Matching Score (CMS) 和 Relative Confidence Index (RCI)。
    :param scores: 字典，鍵為案例ID，值為對應相似度分數（越高表示越相似）。
    :param pulse_ids: 可選，檢索到的相關脈象知識ID列表。
    :param diagnosis: 可選，最終給出的診斷結論。
    """
    metrics: Dict[str, float] = {}
    if not scores:
        metrics["cms"] = 0.0
        metrics["rci"] = 0.0
        return metrics

    # 1. CMS 計算：取最高的相似度分數作為CMS（或取平均亦可，此處取top1）
    top_scores = sorted(scores.values(), reverse=True)
    cms_value = top_scores[0]
    metrics["cms"] = float(cms_value)

    # 2. RCI 計算：
    # 方法A：候選差異（top1與top2差異比值）
    if len(top_scores) > 1:
        diff = top_scores[0] - top_scores[1]
        # 將差異規範到0~1之間（假設相似度本身0~1）
        rci_value = diff if diff >= 0 else 0.0
    else:
        # 若只有一個候選，則無差異，給一個固定高值表示明確
        rci_value = 1.0

    # 方法B：診斷與脈象一致性校正
    consistency_bonus = 0.0
    if diagnosis and pulse_ids:
        # 假設我們有脈象ID對應的模式，可從pulse_rules獲取其代表的證型
        from scbr import pulse_rules
        inferred_patterns = pulse_rules.infer_patterns_from_pulse(pulse_ids)
        # 簡化診斷和推斷模式為關鍵詞集來比對
        diag_keywords = set([diagnosis])  # 這裡可進一步拆分診斷詞彙
        pattern_keywords = set(inferred_patterns)
        # 若診斷包含任何脈象推斷出的模式關鍵詞，視為一致
        if diag_keywords & pattern_keywords:
            consistency_bonus = 0.3  # 給予一定加分
        else:
            consistency_bonus = -0.2  # 不一致扣分（最小降至0）
    # 將兩部分結合，確保在[0,1]範圍
    rci_value = max(0.0, min(1.0, rci_value + consistency_bonus))
    metrics["rci"] = float(rci_value)
    return metrics
