# -*- coding: utf-8 -*-
"""
螺旋推理收斂度計算模組
"""

import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..config import SCBRConfig
from ..utils.logger import get_logger

logger = get_logger("ConvergenceMetrics")

class ConvergenceMetrics:
    """收斂度計算器"""
    
    def __init__(self, config: SCBRConfig):
        self.config = config
        self.history: Dict[str, List[Dict[str, Any]]] = {}  # session_id -> history
        
        # 權重配置
        self.weights = {
            'case_stability': config.convergence.case_stability_weight,
            'score_improvement': config.convergence.score_improvement_weight,
            'semantic_consistency': config.convergence.semantic_consistency_weight,
            'evidence_coverage': config.convergence.evidence_coverage_weight
        }
        
        # TCM 關鍵症狀詞典
        self.tcm_symptoms = set(config.text_processor.tcm_keywords)
        
        logger.info("收斂度計算器初始化完成")
    
    def calculate_convergence(
        self,
        session_id: str,
        current_result: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        計算當前輪次的收斂度指標
        
        Returns:
            包含各項指標的字典：
            - case_stability: 案例穩定度 (0-1)
            - score_improvement: 分數提升率 (-1 to 1)
            - semantic_consistency: 語義一致性 (0-1)
            - evidence_coverage: 證據覆蓋度 (0-1)
            - overall_convergence: 綜合收斂度 (0-1)
        """
        # 初始化或獲取歷史記錄
        if session_id not in self.history:
            self.history[session_id] = []
        
        session_history = self.history[session_id]
        
        metrics = {
            'case_stability': 0.0,
            'score_improvement': 0.0,
            'semantic_consistency': 0.0,
            'evidence_coverage': 0.0,
            'overall_convergence': 0.0,
            'confidence': 0.0
        }
        
        # 獲取當前案例資訊
        current_case_id = None
        current_score = 0.0
        current_symptoms = set()
        
        if "primary" in current_result and current_result["primary"]:
            primary = current_result["primary"]
            current_case_id = primary.get("id")
            current_score = primary.get("_final", 0.0)
            current_symptoms = set(primary.get("_hits", []))
        
        # 計算各項指標
        if len(session_history) > 0:
            prev_result = session_history[-1]
            
            # 1. 案例穩定度
            metrics['case_stability'] = self._calculate_case_stability(
                session_history, current_case_id
            )
            
            # 2. 分數提升率
            metrics['score_improvement'] = self._calculate_score_improvement(
                prev_result, current_score
            )
            
            # 3. 語義一致性
            metrics['semantic_consistency'] = self._calculate_semantic_consistency(
                session_history, current_result
            )
            
            # 4. 證據覆蓋度
            metrics['evidence_coverage'] = self._calculate_evidence_coverage(
                session_history, current_symptoms
            )
        else:
            # 首輪初始化
            metrics['case_stability'] = 0.0
            metrics['score_improvement'] = 0.0
            metrics['semantic_consistency'] = 1.0
            metrics['evidence_coverage'] = len(current_symptoms & self.tcm_symptoms) / max(1, len(self.tcm_symptoms))
        
        # 計算綜合收斂度
        metrics['overall_convergence'] = self._calculate_overall_convergence(metrics)
        
        # 計算置信度
        metrics['confidence'] = self._calculate_confidence(metrics, len(session_history) + 1)
        
        # 記錄到歷史
        self.history[session_id].append({
            'timestamp': datetime.now().isoformat(),
            'case_id': current_case_id,
            'score': current_score,
            'symptoms': list(current_symptoms),
            'metrics': metrics.copy()
        })
        
        logger.info(f"📈 會話 {session_id} 收斂度: {metrics['overall_convergence']:.3f}")
        
        return metrics
    
    def _calculate_case_stability(
        self,
        history: List[Dict[str, Any]],
        current_case_id: str
    ) -> float:
        """計算案例穩定度"""
        if not current_case_id:
            return 0.0
        
        # 檢查最近N輪是否使用相同案例
        recent_window = min(3, len(history))
        if recent_window == 0:
            return 0.0
        
        same_case_count = sum(
            1 for h in history[-recent_window:]
            if h.get('case_id') == current_case_id
        )
        
        return same_case_count / recent_window
    
    def _calculate_score_improvement(
        self,
        prev_result: Dict[str, Any],
        current_score: float
    ) -> float:
        """計算分數提升率"""
        prev_score = prev_result.get('score', 0.0)
        
        if prev_score == 0:
            return current_score
        
        improvement = (current_score - prev_score) / max(0.01, prev_score)
        
        # 限制在 [-1, 1] 範圍
        return max(-1.0, min(1.0, improvement))
    
    def _calculate_semantic_consistency(
        self,
        history: List[Dict[str, Any]],
        current_result: Dict[str, Any]
    ) -> float:
        """計算語義一致性"""
        if len(history) == 0:
            return 1.0
        
        # 使用症狀重疊度作為語義一致性的代理指標
        current_symptoms = set()
        if "primary" in current_result and current_result["primary"]:
            current_symptoms = set(current_result["primary"].get("_hits", []))
        
        if not current_symptoms:
            return 0.5
        
        # 計算與歷史症狀的平均重疊度
        overlaps = []
        for h in history[-3:]:  # 只看最近3輪
            hist_symptoms = set(h.get('symptoms', []))
            if hist_symptoms:
                overlap = len(current_symptoms & hist_symptoms) / len(current_symptoms | hist_symptoms)
                overlaps.append(overlap)
        
        if overlaps:
            return sum(overlaps) / len(overlaps)
        
        return 0.5
    
    def _calculate_evidence_coverage(
        self,
        history: List[Dict[str, Any]],
        current_symptoms: set
    ) -> float:
        """計算證據覆蓋度"""
        # 收集所有歷史症狀
        all_symptoms = current_symptoms.copy()
        for h in history:
            all_symptoms.update(h.get('symptoms', []))
        
        # 計算TCM症狀覆蓋率
        covered = all_symptoms & self.tcm_symptoms
        
        if not self.tcm_symptoms:
            return 0.5
        
        return len(covered) / len(self.tcm_symptoms)
    
    def _calculate_overall_convergence(self, metrics: Dict[str, float]) -> float:
        """計算綜合收斂度"""
        weighted_sum = 0.0
        
        for key, weight in self.weights.items():
            value = metrics.get(key, 0.0)
            
            # 特殊處理分數提升率（可能為負）
            if key == 'score_improvement':
                value = (value + 1.0) / 2.0  # 轉換到 [0, 1]
            
            weighted_sum += value * weight
        
        return max(0.0, min(1.0, weighted_sum))
    
    def _calculate_confidence(self, metrics: Dict[str, float], round_num: int) -> float:
        """計算置信度"""
        # 基於收斂度和輪次計算置信度
        base_confidence = metrics['overall_convergence']
        
        # 輪次調整因子（越多輪次置信度越高，但有上限）
        round_factor = min(1.0, round_num / 5.0)
        
        # 穩定性加成
        stability_bonus = metrics['case_stability'] * 0.2
        
        confidence = base_confidence * 0.7 + round_factor * 0.2 + stability_bonus * 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def should_stop(
        self,
        metrics: Dict[str, float],
        round_num: int
    ) -> bool:
        """判斷是否應該停止螺旋推理"""
        # 未達最小輪次不停止
        if round_num < self.config.spiral.min_rounds:
            return False
        
        # 達到最大輪次強制停止
        if round_num >= self.config.spiral.max_rounds:
            logger.info(f"達到最大輪次 {self.config.spiral.max_rounds}，停止推理")
            return True
        
        # 收斂度達標
        if metrics['overall_convergence'] >= self.config.convergence.convergence_threshold:
            logger.info(f"收斂度達標 {metrics['overall_convergence']:.3f}，停止推理")
            return True
        
        # 案例穩定且分數不再提升
        if (metrics['case_stability'] >= 0.9 and 
            metrics['score_improvement'] <= 0.01):
            logger.info("案例穩定且分數不再提升，停止推理")
            return True
        
        return False
    
    def clear_history(self, session_id: str):
        """清除會話歷史"""
        if session_id in self.history:
            del self.history[session_id]
            logger.info(f"清除會話 {session_id} 的收斂歷史")
    
    def get_convergence_report(self, session_id: str) -> Dict[str, Any]:
        """生成收斂報告"""
        if session_id not in self.history:
            return {"error": "No history found"}
        
        history = self.history[session_id]
        
        if not history:
            return {"error": "Empty history"}
        
        # 提取所有收斂度值
        convergence_values = [h['metrics']['overall_convergence'] for h in history]
        
        # 計算統計資訊
        report = {
            'session_id': session_id,
            'total_rounds': len(history),
            'final_convergence': convergence_values[-1],
            'average_convergence': np.mean(convergence_values),
            'convergence_trend': convergence_values,
            'final_case_id': history[-1].get('case_id'),
            'final_score': history[-1].get('score'),
            'symptoms_collected': list(set(
                sym for h in history 
                for sym in h.get('symptoms', [])
            )),
            'improvement_rate': self._calculate_improvement_rate(convergence_values)
        }
        
        return report
    
    def _calculate_improvement_rate(self, values: List[float]) -> float:
        """計算改善率"""
        if len(values) < 2:
            return 0.0
        
        # 使用線性回歸計算趨勢
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        
        return float(coeffs[0])  # 斜率即為改善率