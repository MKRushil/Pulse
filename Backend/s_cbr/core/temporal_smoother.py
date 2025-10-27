# -*- coding: utf-8 -*-
"""
Backend/s_cbr/core/temporal_smoother.py
證型時間平滑器 - 防止證型跳變，提升診斷穩定性
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger("TemporalSmoother")

@dataclass
class SyndromeScore:
    """證型分數記錄"""
    syndrome: str
    score: float
    timestamp: str
    confidence: float

@dataclass
class TemporalConfig:
    """時間平滑配置"""
    # 平滑係數（當前輪權重）
    beta_current: float = 0.6
    beta_previous: float = 0.4
    
    # 穩定判定閾值
    stability_threshold: float = 0.1  # 分差 < 10% 視為穩定
    stability_window: int = 2  # 連續 2 輪穩定
    
    # 跳變檢測閾值
    jump_threshold: float = 0.25  # 分差 > 25% 視為跳變

class TemporalSmoother:
    """證型時間平滑器"""
    
    def __init__(self, config: TemporalConfig = None):
        self.config = config or TemporalConfig()
        self.history: Dict[str, List[SyndromeScore]] = {}  # session_id -> history
        logger.info("✅ 證型時間平滑器初始化")
        logger.info(f"   平滑係數: 當前={self.config.beta_current}, 歷史={self.config.beta_previous}")
    
    # ==================== 核心平滑算法 ====================
    def smooth_syndrome_scores(
        self,
        session_id: str,
        current_scores: Dict[str, float],
        round_num: int
    ) -> Dict[str, float]:
        """
        應用時間平滑到證型分數
        
        公式：Score_t = β_current * Score_t + β_previous * Score_{t-1}
        
        Args:
            session_id: 會話 ID
            current_scores: 當前輪證型分數 {syndrome: score}
            round_num: 當前輪次
            
        Returns:
            平滑後的證型分數
        """
        # 初始化會話歷史
        if session_id not in self.history:
            self.history[session_id] = []
        
        # 第 1 輪無歷史，直接返回
        if round_num == 1 or not self.history[session_id]:
            smoothed_scores = current_scores.copy()
            logger.info(f"🔄 第 {round_num} 輪（首輪）：無平滑，直接使用當前分數")
        else:
            # 獲取上一輪分數
            previous_round = self.history[session_id][-1]
            previous_scores = {
                record.syndrome: record.score 
                for record in previous_round
            }
            
            # 應用時間平滑
            smoothed_scores = {}
            
            for syndrome, current_score in current_scores.items():
                # 查找上一輪分數
                previous_score = previous_scores.get(syndrome, 0.0)
                
                # 平滑計算
                smoothed_score = (
                    self.config.beta_current * current_score +
                    self.config.beta_previous * previous_score
                )
                
                smoothed_scores[syndrome] = smoothed_score
                
                # 跳變檢測
                if previous_score > 0:
                    score_diff = abs(current_score - previous_score)
                    if score_diff > self.config.jump_threshold:
                        logger.warning(
                            f"⚠️  檢測到證型跳變: {syndrome} "
                            f"({previous_score:.2f} → {current_score:.2f}, Δ={score_diff:.2f})"
                        )
            
            # 對於只在歷史中出現的證型，也加入（衰減）
            for syndrome, prev_score in previous_scores.items():
                if syndrome not in smoothed_scores:
                    smoothed_scores[syndrome] = (
                        self.config.beta_previous * prev_score
                    )
            
            logger.info(f"🔄 第 {round_num} 輪時間平滑:")
            logger.info(f"   平滑證型數: {len(smoothed_scores)}")
            logger.info(f"   主證變化: {self._format_top_changes(previous_scores, current_scores, smoothed_scores)}")
        
        # 記錄到歷史
        current_round_records = [
            SyndromeScore(
                syndrome=syndrome,
                score=score,
                timestamp=datetime.now().isoformat(),
                confidence=current_scores.get(syndrome, 0.0)
            )
            for syndrome, score in smoothed_scores.items()
        ]
        
        if len(self.history[session_id]) >= round_num:
            self.history[session_id][-1] = current_round_records
        else:
            self.history[session_id].append(current_round_records)
        
        return smoothed_scores
    
    # ==================== 穩定性分析 ====================
    def check_stability(
        self,
        session_id: str,
        current_primary: str,
        current_score: float
    ) -> Tuple[bool, float]:
        """
        檢查證型穩定性
        
        Returns:
            (是否穩定, 穩定度分數 0-1)
        """
        if session_id not in self.history:
            return False, 0.0
        
        history = self.history[session_id]
        
        # 至少需要穩定窗口長度的歷史
        if len(history) < self.config.stability_window:
            return False, 0.0
        
        # 檢查最近 N 輪
        recent_rounds = history[-self.config.stability_window:]
        
        stable_count = 0
        max_diff = 0.0
        
        for round_records in recent_rounds:
            # 查找當前主證在歷史輪中的分數
            hist_score = 0.0
            for record in round_records:
                if record.syndrome == current_primary:
                    hist_score = record.score
                    break
            
            # 計算分差
            score_diff = abs(current_score - hist_score)
            max_diff = max(max_diff, score_diff)
            
            # 判斷穩定
            if score_diff <= self.config.stability_threshold:
                stable_count += 1
        
        # 計算穩定度
        stability_ratio = stable_count / len(recent_rounds)
        is_stable = stability_ratio >= 0.8  # 80% 以上輪次穩定
        
        stability_score = max(0.0, 1.0 - max_diff)
        
        if is_stable:
            logger.info(f"✅ 證型穩定: {current_primary} (穩定度={stability_score:.2f})")
        else:
            logger.info(f"⚠️  證型不穩定: {current_primary} (穩定度={stability_score:.2f})")
        
        return is_stable, stability_score
    
    # ==================== 趨勢分析 ====================
    def analyze_syndrome_trend(
        self,
        session_id: str,
        syndrome: str,
        window: int = 3
    ) -> Dict[str, any]:
        """
        分析證型分數趨勢
        
        Returns:
            {
                "trend": "rising" | "falling" | "stable",
                "rate": 變化率,
                "scores": [歷史分數列表]
            }
        """
        if session_id not in self.history:
            return {"trend": "unknown", "rate": 0.0, "scores": []}
        
        history = self.history[session_id]
        recent_rounds = history[-window:] if len(history) >= window else history
        
        # 提取分數序列
        scores = []
        for round_records in recent_rounds:
            for record in round_records:
                if record.syndrome == syndrome:
                    scores.append(record.score)
                    break
            else:
                scores.append(0.0)
        
        if len(scores) < 2:
            return {"trend": "unknown", "rate": 0.0, "scores": scores}
        
        # 計算趨勢
        first_score = scores[0]
        last_score = scores[-1]
        
        if first_score == 0:
            rate = 1.0 if last_score > 0 else 0.0
        else:
            rate = (last_score - first_score) / first_score
        
        # 判定趨勢
        if abs(rate) < 0.05:
            trend = "stable"
        elif rate > 0:
            trend = "rising"
        else:
            trend = "falling"
        
        return {
            "trend": trend,
            "rate": rate,
            "scores": scores,
            "direction": "↗" if trend == "rising" else ("↘" if trend == "falling" else "→")
        }
    
    # ==================== 輔助方法 ====================
    def _format_top_changes(
        self,
        prev: Dict[str, float],
        curr: Dict[str, float],
        smoothed: Dict[str, float],
        top_n: int = 3
    ) -> str:
        """格式化主要證型變化"""
        # 按平滑後分數排序
        sorted_syndromes = sorted(
            smoothed.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        changes = []
        for syndrome, smooth_score in sorted_syndromes:
            prev_score = prev.get(syndrome, 0.0)
            curr_score = curr.get(syndrome, 0.0)
            
            changes.append(
                f"{syndrome}({prev_score:.2f}→{curr_score:.2f}⇒{smooth_score:.2f})"
            )
        
        return ", ".join(changes)
    
    def get_syndrome_history(
        self,
        session_id: str,
        syndrome: str
    ) -> List[Dict]:
        """獲取特定證型的歷史記錄"""
        if session_id not in self.history:
            return []
        
        records = []
        for round_idx, round_records in enumerate(self.history[session_id], 1):
            for record in round_records:
                if record.syndrome == syndrome:
                    records.append({
                        "round": round_idx,
                        "score": record.score,
                        "timestamp": record.timestamp,
                        "confidence": record.confidence
                    })
                    break
        
        return records
    
    def clear_history(self, session_id: str):
        """清除會話歷史"""
        if session_id in self.history:
            del self.history[session_id]
            logger.info(f"🗑️  清除會話 {session_id} 的平滑歷史")