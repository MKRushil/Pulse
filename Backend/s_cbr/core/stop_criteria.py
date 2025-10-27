# -*- coding: utf-8 -*-
"""
終止條件管理器 - 硬條件 + 軟條件雙層判斷
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import yaml
from pathlib import Path
from ..utils.logger import get_logger

logger = get_logger("StopCriteria")

@dataclass
class StopDecision:
    """終止決策"""
    should_stop: bool
    stop_reason: str
    hard_rule_triggered: str  # 觸發的硬規則名稱
    soft_score: float         # 軟條件加權分數
    can_save: bool
    treatment_effective: bool
    recommendations: List[str]  # 給使用者的建議

class StopCriteriaManager:
    """終止條件管理器"""
    
    def __init__(self, config_path: Path = None):
        """載入終止規則配置"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "knowledge" / "stop_rules.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.rules = yaml.safe_load(f)
        
        self.hard_rules = self.rules['hard_rules']
        self.soft_rules = self.rules['soft_rules']
        self.strategy = self.rules['stop_strategy']
        self.feedback_criteria = self.rules['feedback_criteria']
        
        logger.info("✅ 終止條件管理器初始化")
        logger.info(f"   硬規則: {len(self.hard_rules)} 條")
        logger.info(f"   軟規則: {len(self.soft_rules)} 條")
    
    def evaluate(
        self,
        session_id: str,
        round_num: int,
        metrics: Dict[str, float],
        history: List[Dict[str, Any]],
        user_satisfied: bool = False
    ) -> StopDecision:
        """
        評估是否應該終止
        
        Args:
            session_id: 會話ID
            round_num: 當前輪次
            metrics: 收斂指標 {CI, SC, RCI, CMS, CSC, CAS, ...}
            history: 歷史記錄
            user_satisfied: 使用者是否標記滿意
        
        Returns:
            StopDecision
        """
        
        # ==================== 1. 最小輪次保護 ====================
        if round_num < self.strategy['min_rounds']:
            return StopDecision(
                should_stop=False,
                stop_reason=f"未達最小輪次 {self.strategy['min_rounds']}",
                hard_rule_triggered="",
                soft_score=0.0,
                can_save=False,
                treatment_effective=False,
                recommendations=["繼續補充症狀資訊"]
            )
        
        # ==================== 2. 硬條件檢查 ====================
        hard_triggered, hard_reason = self._check_hard_rules(
            round_num, metrics, history, user_satisfied
        )
        
        if hard_triggered:
            logger.info(f"🛑 硬條件觸發: {hard_reason}")
            
            # 判斷是否可儲存
            can_save, treatment_effective = self._evaluate_feedback_criteria(metrics, round_num)
            
            return StopDecision(
                should_stop=True,
                stop_reason=hard_reason,
                hard_rule_triggered=hard_triggered,
                soft_score=0.0,  # 硬條件觸發時軟分數不重要
                can_save=can_save,
                treatment_effective=treatment_effective,
                recommendations=self._generate_recommendations(metrics, can_save)
            )
        
        # ==================== 3. 軟條件檢查 ====================
        if round_num >= self.strategy['soft_start_round']:
            soft_score = self._calculate_soft_score(metrics, history)
            
            logger.info(f"📊 軟條件分數: {soft_score:.2f}")
            
            if soft_score >= self.strategy['soft_threshold']:
                logger.info(f"⚠️  軟條件建議終止 (分數 {soft_score:.2f} ≥ {self.strategy['soft_threshold']})")
                
                can_save, treatment_effective = self._evaluate_feedback_criteria(metrics, round_num)
                
                return StopDecision(
                    should_stop=True,
                    stop_reason=f"軟條件建議終止 (分數={soft_score:.2f})",
                    hard_rule_triggered="",
                    soft_score=soft_score,
                    can_save=can_save,
                    treatment_effective=treatment_effective,
                    recommendations=self._generate_recommendations(metrics, can_save)
                )
        
        # ==================== 4. 繼續推理 ====================
        return StopDecision(
            should_stop=False,
            stop_reason="",
            hard_rule_triggered="",
            soft_score=self._calculate_soft_score(metrics, history) if round_num >= self.strategy['soft_start_round'] else 0.0,
            can_save=False,
            treatment_effective=False,
            recommendations=self._generate_continue_recommendations(metrics, history)
        )
    
    def _check_hard_rules(
        self,
        round_num: int,
        metrics: Dict[str, float],
        history: List[Dict[str, Any]],
        user_satisfied: bool
    ) -> Tuple[str, str]:
        """
        檢查硬條件
        
        Returns:
            (觸發的規則名稱, 原因描述)
        """
        # 按優先級排序
        sorted_rules = sorted(self.hard_rules, key=lambda r: r.get('priority', 999))
        
        for rule in sorted_rules:
            name = rule['name']
            conditions = rule['conditions']
            
            # 規則 1: convergence_coverage
            if name == "convergence_coverage":
                ci = metrics.get('Final', metrics.get('overall_convergence', 0))
                sc = metrics.get('evidence_coverage', 0)
                
                if ci >= conditions['ci_min'] and sc >= conditions['sc_min']:
                    return name, f"CI={ci:.2f} ≥ {conditions['ci_min']}, SC={sc:.2f} ≥ {conditions['sc_min']}"
            
            # 規則 2: retrieval_stability
            elif name == "retrieval_stability":
                rci = metrics.get('RCI', 0)
                same_rounds = conditions['same_diagnosis_rounds']
                
                if rci >= conditions['rci_min']:
                    # 檢查最近 N 輪診斷是否相同
                    if self._check_diagnosis_consistency(history, same_rounds):
                        return name, f"RCI={rci:.2f} ≥ {conditions['rci_min']}, 連續{same_rounds}輪診斷一致"
            
            # 規則 3: user_satisfied
            elif name == "user_satisfied":
                if user_satisfied:
                    return name, "使用者標記滿意"
            
            # 規則 4: max_rounds_reached
            elif name == "max_rounds_reached":
                if round_num >= conditions['max_rounds']:
                    return name, f"達到最大輪次 {conditions['max_rounds']}"
        
        return "", ""
    
    def _calculate_soft_score(
        self,
        metrics: Dict[str, float],
        history: List[Dict[str, Any]]
    ) -> float:
        """計算軟條件加權分數"""
        total_score = 0.0
        
        for rule in self.soft_rules:
            name = rule['name']
            conditions = rule['conditions']
            weight = rule['weight']
            satisfied = False
            
            # 軟規則 1: convergence_plateau
            if name == "convergence_plateau":
                satisfied = self._check_convergence_plateau(
                    history,
                    conditions['delta_ci_max'],
                    conditions['plateau_rounds']
                )
            
            # 軟規則 2: low_new_symptoms
            elif name == "low_new_symptoms":
                new_rate = metrics.get('new_symptom_rate', 1.0)
                satisfied = new_rate <= conditions['new_symptom_rate_max']
            
            # 軟規則 3: high_case_stability
            elif name == "high_case_stability":
                stability = metrics.get('case_stability', 0)
                satisfied = stability >= conditions['case_stability_min']
            
            # 軟規則 4: high_semantic_consistency
            elif name == "high_semantic_consistency":
                consistency = metrics.get('semantic_consistency', 0)
                satisfied = consistency >= conditions['semantic_consistency_min']
            
            if satisfied:
                total_score += weight
                logger.debug(f"  ✓ {name} 滿足 (+{weight})")
        
        return total_score
    
    def _check_diagnosis_consistency(
        self,
        history: List[Dict[str, Any]],
        required_rounds: int
    ) -> bool:
        """檢查最近 N 輪診斷是否一致"""
        if len(history) < required_rounds:
            return False
        
        recent = history[-required_rounds:]
        diagnoses = [h.get('primary', {}).get('diagnosis', '') for h in recent]
        
        return len(set(diagnoses)) == 1 and diagnoses[0] != ''
    
    def _check_convergence_plateau(
        self,
        history: List[Dict[str, Any]],
        max_delta: float,
        required_rounds: int
    ) -> bool:
        """檢查收斂是否趨緩"""
        if len(history) < required_rounds + 1:
            return False
        
        recent = history[-(required_rounds + 1):]
        cis = [h.get('convergence', {}).get('overall_convergence', 0) for h in recent]
        
        # 計算相鄰輪次的變化量
        deltas = [abs(cis[i+1] - cis[i]) for i in range(len(cis) - 1)]
        
        return all(d <= max_delta for d in deltas)
    
    def _evaluate_feedback_criteria(
        self,
        metrics: Dict[str, float],
        round_num: int
    ) -> Tuple[bool, bool]:
        """
        評估回饋判定
        
        Returns:
            (can_save, treatment_effective)
        """
        save_crit = self.feedback_criteria['can_save']
        treat_crit = self.feedback_criteria['treatment_effective']
        
        ci = metrics.get('Final', metrics.get('overall_convergence', 0))
        coverage = metrics.get('evidence_coverage', 0)
        stability = metrics.get('case_stability', 0)
        semantic = metrics.get('semantic_consistency', 0)
        
        # 可儲存判定
        can_save = (
            ci >= save_crit['ci_min'] and
            coverage >= save_crit['coverage_min'] and
            stability >= save_crit['stability_min'] and
            round_num >= save_crit['min_rounds']
        )
        
        # 治療有效判定（更嚴格）
        treatment_effective = (
            ci >= treat_crit['ci_min'] and
            coverage >= treat_crit['coverage_min'] and
            stability >= treat_crit['stability_min'] and
            semantic >= treat_crit['semantic_min']
        )
        
        return can_save, treatment_effective
    
    def _generate_recommendations(
        self,
        metrics: Dict[str, float],
        can_save: bool
    ) -> List[str]:
        """生成終止後的建議"""
        recs = []
        
        if can_save:
            recs.append("✅ 診斷已收斂，可儲存為回饋案例")
        
        ci = metrics.get('Final', 0)
        if ci >= 0.90:
            recs.append("🎯 診斷置信度極高，建議依此制定治療方案")
        elif ci >= 0.85:
            recs.append("📋 診斷基本確定，可作為臨床參考")
        else:
            recs.append("⚠️  診斷尚可，建議結合臨床複診")
        
        return recs
    
    def _generate_continue_recommendations(
        self,
        metrics: Dict[str, float],
        history: List[Dict[str, Any]]
    ) -> List[str]:
        """生成繼續推理的建議"""
        recs = []
        
        # 檢查缺口
        coverage = metrics.get('evidence_coverage', 0)
        if coverage < 0.6:
            recs.append("請補充更多症狀描述")
        
        # 檢查舌脈
        has_tongue = any('舌' in str(h) for h in history)
        has_pulse = any('脈' in str(h) for h in history)
        
        if not has_tongue:
            recs.append("建議補充舌象資訊（舌質、舌苔）")
        if not has_pulse:
            recs.append("建議補充脈象資訊")
        
        if not recs:
            recs.append("繼續補充細節以提高診斷準確性")
        
        return recs