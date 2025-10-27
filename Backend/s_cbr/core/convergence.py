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
    

    def calculate_evaluation_metrics(
        self,
        session_id: str,
        current_result: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        計算統一的四項評估指標
        
        Returns:
            RCI: Retrieval Case Index (案例檢索相似度)
            CMS: Convergence Measure Score (收斂度)
            CSC: Consistency Score (辨證與診斷一致性)
            CAS: Case Agreement Score (案例內容一致度)
            Final: 最終置信度
        """
        # 先計算原有指標
        raw_metrics = self.calculate_convergence(session_id, current_result)
        
        # 提取必要資訊
        round_num = len(self.history.get(session_id, [])) + 1
        
        # 計算統一指標
        rci = self._calculate_rci(current_result)
        cms = raw_metrics.get("overall_convergence", 0.0)
        csc = self._calculate_csc(current_result, session_id)
        cas = self._calculate_cas(current_result)
        
        # 計算最終置信度（動態權重）
        weights = self._get_dynamic_weights(round_num)
        final = (
            weights["RCI"] * rci +
            weights["CMS"] * cms +
            weights["CSC"] * csc +
            weights["CAS"] * cas
        )
        
        metrics = {
            "RCI": round(rci, 3),
            "CMS": round(cms, 3),
            "CSC": round(csc, 3),
            "CAS": round(cas, 3),
            "Final": round(final, 3),
            # 保留原有指標用於內部邏輯
            "_raw": raw_metrics
        }
        
        logger.info(f"📊 評估指標 [Round {round_num}]:")
        logger.info(f"   RCI={metrics['RCI']:.3f}, CMS={metrics['CMS']:.3f}")
        logger.info(f"   CSC={metrics['CSC']:.3f}, CAS={metrics['CAS']:.3f}")
        logger.info(f"   Final={metrics['Final']:.3f}")
        
        return metrics

    def _calculate_rci(self, current_result: Dict) -> float:
        """
        計算 RCI (Retrieval Case Index)
        案例檢索相似度：Top-k 案例平均相似度加權
        """
        if "primary" not in current_result or not current_result["primary"]:
            return 0.0
        
        primary = current_result["primary"]
        primary_score = primary.get("_final", 0.0)
        
        # 如果有補充案例
        supplement_score = 0.0
        if "supplement" in current_result and current_result["supplement"]:
            supplement_score = current_result["supplement"].get("_final", 0.0)
        
        # 加權平均（主案例權重0.7，補充案例0.3）
        rci = primary_score * 0.7
        if supplement_score > 0:
            rci += supplement_score * 0.3
        else:
            rci = primary_score
        
        return min(rci, 1.0)

    def _calculate_csc(self, current_result: Dict, session_id: str = None) -> float:
        """
        計算 CSC (Consistency Score)
        辨證與診斷一致性：八綱屬性 + 臟腑歸屬一致率
        
        Args:
            current_result: 當前推理結果
            session_id: 會話ID（用於獲取歷史）
        
        Returns:
            一致性分數 (0-1)
        """
        if "pattern_diagnosis" not in current_result:
            # Fallback：使用原有的語義一致性
            if session_id and session_id in self.history:
                return self._calculate_semantic_consistency(
                    self.history.get(session_id, []),
                    current_result
                )
            else:
                # 如果沒有 session_id 或歷史，返回默認值
                return 0.5
        
        pd = current_result["pattern_diagnosis"]
        pattern_reasoning = pd.get("pattern_reasoning", {})
        diagnosis_reasoning = pd.get("diagnosis_reasoning", {})
        
        # 檢查八綱與病機的一致性
        eight_principles = set(pattern_reasoning.get("eight_principles", []))
        pathomechanism = diagnosis_reasoning.get("pathomechanism", "")
        
        consistency_score = 0.0
        
        # 規則檢查
        if "陰虛" in eight_principles and "陰虛" in pathomechanism:
            consistency_score += 0.3
        if "陽虛" in eight_principles and "陽虛" in pathomechanism:
            consistency_score += 0.3
        if "氣滯" in eight_principles and "氣滯" in pathomechanism:
            consistency_score += 0.2
        
        # 臟腑一致性
        zangfu = set(pattern_reasoning.get("zangfu", []))
        if zangfu:
            for organ in zangfu:
                if organ in pathomechanism:
                    consistency_score += 0.2
        
        return min(consistency_score, 1.0)

    def _calculate_cas(self, current_result: Dict) -> float:
        """
        計算 CAS (Case Agreement Score)
        案例內容一致度
        公式：CAS = 0.5*pattern_match + 0.3*pathomechanism + 0.2*snippet
        """
        pattern_match = self._calc_pattern_tag_match(current_result)
        pathomechanism_overlap = self._calc_pathomechanism_overlap(current_result)
        snippet_alignment = self._calc_snippet_alignment(current_result)
        
        cas = (
            0.5 * pattern_match +
            0.3 * pathomechanism_overlap +
            0.2 * snippet_alignment
        )
        
        return min(cas, 1.0)

    def _calc_pattern_tag_match(self, result: Dict) -> float:
        """計算證型標籤匹配度（Jaccard相似度）"""
        if "pattern_diagnosis" not in result or "primary" not in result:
            return 0.5
        
        # 從雙層推理結果提取證型
        pd_patterns = set()
        if "pattern_diagnosis" in result:
            pr = result["pattern_diagnosis"].get("pattern_reasoning", {})
            primary = pr.get("primary_pattern", {})
            if primary.get("label"):
                pd_patterns.add(primary["label"])
        
        # 從案例提取證型
        case_patterns = set()
        if "primary" in result and result["primary"]:
            syndrome_terms = result["primary"].get("syndrome_terms", [])
            if syndrome_terms:
                case_patterns.update(syndrome_terms[:3])
        
        # Jaccard 相似度
        if not pd_patterns and not case_patterns:
            return 0.0
        
        intersection = pd_patterns & case_patterns
        union = pd_patterns | case_patterns
        
        return len(intersection) / len(union) if union else 0.0

    def _calc_pathomechanism_overlap(self, result: Dict) -> float:
        """計算病機重疊度"""
        if "pattern_diagnosis" not in result:
            return 0.5
        
        pd = result["pattern_diagnosis"]
        diagnosis_reasoning = pd.get("diagnosis_reasoning", {})
        pathomechanism = diagnosis_reasoning.get("pathomechanism", "")
        
        if not pathomechanism:
            return 0.0
        
        # 簡單的關鍵詞匹配評分
        score = 0.0
        keywords = ["陰虛", "陽虛", "氣滯", "血瘀", "痰濕", "火旺"]
        
        for kw in keywords:
            if kw in pathomechanism:
                score += 0.2
        
        return min(score, 1.0)

    def _calc_snippet_alignment(self, result: Dict) -> float:
        """計算片段對齊度"""
        if "primary" not in result or not result["primary"]:
            return 0.0
        
        primary = result["primary"]
        
        # 提取關鍵症狀
        hits = primary.get("_hits", [])
        if not hits:
            return 0.0
        
        # 簡單評分：命中症狀數量
        score = min(len(hits) / 5.0, 1.0)  # 假設5個症狀為完整
        
        return score

    def _get_dynamic_weights(self, round_num: int) -> Dict[str, float]:
            """
            根據輪次動態調整權重
            
            策略:
            - R1: 探索期（RCI 主導）- 允許檢索探索
            - R2-R3: 平衡期 - 症狀覆蓋與檢索並重
            - R4+: 收斂期（CMS、CSC 主導）- 強調收斂與一致性
            
            Returns:
                權重字典 {指標名: 權重值}
            """
            if round_num == 1:
                # 第1輪：探索期（RCI 主導）
                return {
                    "RCI": 0.50,  # 檢索相關性最重要
                    "CMS": 0.20,  # 案例匹配
                    "CSC": 0.20,  # 一致性
                    "CAS": 0.10   # 案例符合
                }
            elif round_num <= 3:
                # 第2-3輪：平衡期
                return {
                    "RCI": 0.30,  # 降低探索權重
                    "CMS": 0.30,  # 提高收斂權重
                    "CSC": 0.25,  # 一致性
                    "CAS": 0.15   # 案例符合
                }
            else:
                # 第4輪+：收斂期
                return {
                    "RCI": 0.15,  # 最小探索
                    "CMS": 0.35,  # 最大收斂
                    "CSC": 0.30,  # 強調一致性
                    "CAS": 0.20   # 強調案例符合
                }
        
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
    ) -> Dict[str, Any]:  # ✅ 改為返回字典
        """
        判斷是否應該停止螺旋推理
        
        Returns:
            {
                "should_stop": bool,  # 是否停止
                "can_save": bool,  # 是否可儲存
                "treatment_effective": bool,  # 治療是否有效
                "stop_reason": str,  # 停止原因
                "continue_reason": str  # 繼續原因
            }
        """
        
        # 未達最小輪次不停止
        if round_num < self.config.spiral.min_rounds:
            logger.info(f"未達最小輪次 {self.config.spiral.min_rounds}")
            return {
                "should_stop": False,
                "can_save": False,
                "treatment_effective": False,
                "stop_reason": "",
                "continue_reason": f"未達最小輪次 {self.config.spiral.min_rounds}"
            }
        
        # 達到最大輪次強制停止
        if round_num >= self.config.spiral.max_rounds:
            logger.info(f"✋ 達到最大輪次 {self.config.spiral.max_rounds}，停止推理")
            return {
                "should_stop": True,
                "can_save": False,
                "treatment_effective": False,
                "stop_reason": f"達到最大輪次 {self.config.spiral.max_rounds}",
                "continue_reason": ""
            }
        
        # ✅ 收斂度達標（使用配置的閾值）
        threshold = self.config.convergence.convergence_threshold
        overall_conv = metrics['overall_convergence']
        
        if overall_conv >= threshold:
            logger.info(f"✅ 收斂度達標 {overall_conv:.3f} ≥ {threshold}，停止推理")
            
            # 判斷是否有效治療（可儲存）
            is_stable = metrics['case_stability'] >= 0.8
            is_covered = metrics['evidence_coverage'] >= 0.6
            treatment_effective = is_stable and is_covered
            
            return {
                "should_stop": True,
                "can_save": treatment_effective,
                "treatment_effective": treatment_effective,
                "stop_reason": f"收斂度達標 {overall_conv:.3f}",
                "continue_reason": ""
            }
        
        # 案例穩定且分數不再提升
        if (metrics['case_stability'] >= 0.9 and 
            metrics['score_improvement'] <= 0.01):
            logger.info("✅ 案例穩定且分數不再提升，停止推理")
            return {
                "should_stop": True,
                "can_save": True,
                "treatment_effective": True,
                "stop_reason": "案例穩定且分數不再提升",
                "continue_reason": ""
            }
        
        logger.info(f"⏳ 繼續推理（收斂度 {overall_conv:.3f} < {threshold}）")
        return {
            "should_stop": False,
            "can_save": False,
            "treatment_effective": False,
            "stop_reason": "",
            "continue_reason": f"收斂度 {overall_conv:.3f} < {threshold}"
        }

    def _evaluate_treatment_effectiveness(
        self,
        metrics: Dict[str, float],
        primary_case: Optional[Dict[str, Any]],
        round_num: int
    ) -> bool:
        """
        評估治療是否有效
        
        判斷標準：
        1. 收斂度 >= 0.8
        2. 案例穩定度 >= 0.7
        3. 症狀覆蓋率 >= 0.6（如果有調整後案例）
        4. 至少進行過 2 輪推理
        """
        
        # 基礎條件
        if round_num < 2:
            return False
        
        overall = metrics.get('overall_convergence', 0)
        stability = metrics.get('case_stability', 0)
        
        # 核心判斷
        is_converged = overall >= 0.8
        is_stable = stability >= 0.7
        
        # 如果有調整後案例，檢查症狀覆蓋率
        has_good_coverage = True
        if primary_case and primary_case.get("adjusted"):
            coverage = primary_case.get("match_stats", {}).get("coverage", 0)
            has_good_coverage = coverage >= 0.6
        
        is_effective = is_converged and is_stable and has_good_coverage
        
        logger.info(f"📊 治療有效性評估:")
        logger.info(f"   收斂: {overall:.1%} {'✓' if is_converged else '✗'}")
        logger.info(f"   穩定: {stability:.1%} {'✓' if is_stable else '✗'}")
        if primary_case and primary_case.get("adjusted"):
            logger.info(f"   覆蓋: {primary_case.get('match_stats', {}).get('coverage', 0):.1%} {'✓' if has_good_coverage else '✗'}")
        logger.info(f"   結論: {'有效 ✅' if is_effective else '無效 ❌'}")
        
        return is_effective
    
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
    
    # 在 ConvergenceMetrics 類中添加

    def calculate_enhanced_convergence(
        self,
        session_id: str,
        current_result: Dict[str, Any],
        tongue_pulse_hits: int = 0  # 新增：舌脈命中數
    ) -> Dict[str, float]:
        """
        增強版收斂度計算
        
        公式：
        - Coverage: 加權命中比例（舌/脈 ×1.3）
        - Stability: 主證連續一致 + 關鍵依據 IoU
        - Confidence: 主證與次證分差的 sigmoid
        - Convergence = 0.4*Stability + 0.35*Coverage + 0.25*Confidence
        """
        if session_id not in self.history:
            self.history[session_id] = []
        
        session_history = self.history[session_id]
        
        metrics = {
            'case_stability': 0.0,
            'score_improvement': 0.0,
            'semantic_consistency': 0.0,
            'evidence_coverage': 0.0,
            'overall_convergence': 0.0,
            'confidence': 0.0,
            'syndrome_confidence': 0.0  # 新增
        }
        
        # 獲取當前資訊
        current_case_id = None
        current_score = 0.0
        current_symptoms = set()
        primary_syndrome = None
        secondary_syndromes = []
        
        if "primary" in current_result and current_result["primary"]:
            primary = current_result["primary"]
            current_case_id = primary.get("id")
            current_score = primary.get("_final", 0.0)
            current_symptoms = set(primary.get("_hits", []))
            
            # 提取證型信息（如果有辨證結果）
            if "syndrome_result" in current_result:
                syndrome_result = current_result["syndrome_result"]
                primary_syndrome = syndrome_result.primary_syndrome
                secondary_syndromes = syndrome_result.secondary_syndromes
        
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
            
            # 4. ✅ 增強版證據覆蓋度（考慮舌脈加權）
            metrics['evidence_coverage'] = self._calculate_enhanced_evidence_coverage(
                session_history, current_symptoms, tongue_pulse_hits
            )
            
            # 5. ✅ 證型置信度（主證與次證分差）
            if primary_syndrome:
                metrics['syndrome_confidence'] = self._calculate_syndrome_confidence(
                    primary_syndrome, secondary_syndromes, current_result
                )
        else:
            # 首輪初始化
            metrics['case_stability'] = 0.0
            metrics['score_improvement'] = 0.0
            metrics['semantic_consistency'] = 1.0
            metrics['evidence_coverage'] = self._calculate_enhanced_evidence_coverage(
                [], current_symptoms, tongue_pulse_hits
            )
        
        # ✅ 計算綜合收斂度（新權重）
        metrics['overall_convergence'] = self._calculate_enhanced_overall_convergence(metrics)
        
        # 計算置信度
        metrics['confidence'] = self._calculate_confidence(metrics, len(session_history) + 1)
        
        # 記錄到歷史
        self.history[session_id].append({
            'timestamp': datetime.now().isoformat(),
            'case_id': current_case_id,
            'score': current_score,
            'symptoms': list(current_symptoms),
            'primary_syndrome': primary_syndrome,
            'metrics': metrics.copy()
        })
        
        logger.info(f"📈 增強版收斂度 [會話 {session_id}]: {metrics['overall_convergence']:.3f}")
        logger.info(f"   穩定性={metrics['case_stability']:.2f}, 覆蓋率={metrics['evidence_coverage']:.2f}, 證型置信={metrics['syndrome_confidence']:.2f}")
        
        return metrics
    
    def _calculate_enhanced_evidence_coverage(
        self,
        history: List[Dict[str, Any]],
        current_symptoms: set,
        tongue_pulse_hits: int
        ) -> float:
        """
        增強版證據覆蓋度：舌脈命中 ×1.3
        """
        all_symptoms = current_symptoms.copy()
        for h in history:
            all_symptoms.update(h.get('symptoms', []))
        
        tcm_symptoms = self.tcm_symptoms
        if not tcm_symptoms:
            return 0.5
        
        # 有效症狀
        valid_symptoms = all_symptoms & tcm_symptoms
        
        # 基礎覆蓋率
        base_coverage = len(valid_symptoms) / min(len(tcm_symptoms), 50)
        
        # ✅ 舌脈加權（每個舌脈命中 +0.05，最多 +0.15）
        tongue_pulse_bonus = min(tongue_pulse_hits * 0.05, 0.15)
        
        coverage = base_coverage + tongue_pulse_bonus
        
        logger.debug(f"   證據覆蓋: 基礎={base_coverage:.2f}, 舌脈加權=+{tongue_pulse_bonus:.2f}")
        
        return min(1.0, coverage)
    
    def _calculate_syndrome_confidence(
        self,
        primary_syndrome: str,
        secondary_syndromes: List[str],
        current_result: Dict[str, Any]
    ) -> float:
        """
        計算證型置信度：主證與次證分差的 sigmoid
        
        公式：sigmoid(主證分數 - 最高次證分數)
        """
        # 提取分數
        syndrome_result = current_result.get("syndrome_result")
        if not syndrome_result:
            return 0.5
        
        primary_score = syndrome_result.confidence
        
        # 獲取次證最高分
        secondary_score = 0.0
        if hasattr(syndrome_result, 'secondary_scores') and syndrome_result.secondary_scores:
            secondary_score = max(syndrome_result.secondary_scores.values())
        elif secondary_syndromes:
            # 假設次證分數為主證的 0.6-0.8
            secondary_score = primary_score * 0.7
        
        # 分差
        diff = primary_score - secondary_score
        
        # Sigmoid 轉換
        confidence = 1.0 / (1.0 + np.exp(-5 * diff))
        
        logger.debug(f"   證型置信: 主={primary_score:.2f}, 次={secondary_score:.2f}, 差={diff:.2f} → {confidence:.2f}")
        
        return confidence
    
    def _calculate_enhanced_overall_convergence(self, metrics: Dict[str, float]) -> float:
        """
        增強版綜合收斂度
        
        公式：Convergence = 0.4*Stability + 0.35*Coverage + 0.25*Confidence
        """
        # 新權重
        weights = {
            'case_stability': 0.4,
            'evidence_coverage': 0.35,
            'syndrome_confidence': 0.25 if metrics.get('syndrome_confidence', 0) > 0 else 0.0
        }
        
        # 如果沒有證型置信度，使用舊方案
        if weights['syndrome_confidence'] == 0:
            weights = {
                'case_stability': 0.4,
                'evidence_coverage': 0.4,
                'semantic_consistency': 0.2
            }
        
        weighted_sum = 0.0
        for key, weight in weights.items():
            value = metrics.get(key, 0.0)
            
            # 分數提升率特殊處理
            if key == 'score_improvement':
                value = (value + 1.0) / 2.0
            
            weighted_sum += value * weight
        
        return max(0.0, min(1.0, weighted_sum))