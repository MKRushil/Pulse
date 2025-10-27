# -*- coding: utf-8 -*-
"""
對話品質評估器
"""

from typing import Dict, List, Any, Optional
import numpy as np
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger("DialogueEvaluator")

class DialogueEvaluator:
    """對話品質多維度評估"""
    
    def __init__(self, config):
        self.config = config
        self.history = {}
        
        # 評估維度權重
        self.dimension_weights = {
            "clinical_understanding": 0.25,  # 臨床理解深度
            "diagnostic_consistency": 0.25,  # 診斷一致性
            "convergence_quality": 0.20,     # 收斂品質
            "response_naturalness": 0.15,    # 回應自然度
            "improvement_rate": 0.15         # 改進率
        }
    
    def evaluate_dialogue_round(
        self,
        session_id: str,
        round_num: int,
        current_response: Dict[str, Any],
        previous_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """評估單輪對話品質"""
        
        evaluation = {
            "round": round_num,
            "timestamp": datetime.now().isoformat(),
            "dimensions": {},
            "overall_score": 0,
            "clinical_assessment": ""
        }
        
        # 1. 臨床理解深度 (CID - Clinical Insight Depth)
        cid_score = self._evaluate_clinical_understanding(current_response)
        evaluation["dimensions"]["clinical_understanding"] = {
            "name": "臨床理解深度",
            "score": cid_score,
            "level": self._get_level(cid_score),
            "description": "對症狀背後病機的理解程度"
        }
        
        # 2. 診斷一致性 (DCR - Diagnostic Consistency Rate)
        dcr_score = self._evaluate_diagnostic_consistency(
            current_response, previous_response
        )
        evaluation["dimensions"]["diagnostic_consistency"] = {
            "name": "診斷一致性",
            "score": dcr_score,
            "level": self._get_level(dcr_score),
            "description": "診斷邏輯的連貫性"
        }
        
        # 3. 收斂品質 (CQS - Convergence Quality Score)
        cqs_score = self._evaluate_convergence_quality(
            session_id, round_num, current_response
        )
        evaluation["dimensions"]["convergence_quality"] = {
            "name": "收斂品質",
            "score": cqs_score,
            "level": self._get_level(cqs_score),
            "description": "診斷趨向穩定的程度"
        }
        
        # 4. 回應自然度 (RNS - Response Naturalness Score)
        rns_score = self._evaluate_response_naturalness(current_response)
        evaluation["dimensions"]["response_naturalness"] = {
            "name": "回應自然度",
            "score": rns_score,
            "level": self._get_level(rns_score),
            "description": "語言表達的專業性與親和力"
        }
        
        # 5. 改進率 (IRS - Improvement Rate Score)
        irs_score = self._calculate_improvement_rate(
            current_response, previous_response
        )
        evaluation["dimensions"]["improvement_rate"] = {
            "name": "診斷改進率",
            "score": irs_score,
            "level": self._get_level(irs_score),
            "description": "相比前輪的進步程度"
        }
        
        # 計算綜合分數
        evaluation["overall_score"] = self._calculate_overall_score(
            evaluation["dimensions"]
        )
        
        # 生成臨床評語
        evaluation["clinical_assessment"] = self._generate_clinical_assessment(
            evaluation
        )
        
        # 記錄到歷史
        if session_id not in self.history:
            self.history[session_id] = []
        self.history[session_id].append(evaluation)
        
        return evaluation
    
    def _evaluate_clinical_understanding(self, response: Dict) -> float:
        """評估臨床理解深度"""
        score = 0.5  # 基礎分
        
        # 檢查是否包含病機分析
        if "病機" in response.get("final_text", ""):
            score += 0.2
        
        # 檢查症狀關聯性分析
        symptoms = response.get("primary", {}).get("_hits", [])
        if len(symptoms) >= 3:
            score += 0.15
        
        # 檢查證型判斷的準確性
        if response.get("primary", {}).get("diagnosis"):
            score += 0.15
        
        return min(1.0, score)
    
    def _evaluate_diagnostic_consistency(
        self,
        current: Dict,
        previous: Optional[Dict]
    ) -> float:
        """評估診斷一致性"""
        if not previous:
            return 0.8  # 首輪給基礎分
        
        # 比較診斷方向
        curr_diagnosis = current.get("primary", {}).get("diagnosis", "")
        prev_diagnosis = previous.get("primary", {}).get("diagnosis", "")
        
        if not curr_diagnosis or not prev_diagnosis:
            return 0.5
        
        # 完全一致
        if curr_diagnosis == prev_diagnosis:
            return 1.0
        
        # 部分一致（如風熱→風熱壅肺）
        if any(word in curr_diagnosis for word in prev_diagnosis.split()):
            return 0.8
        
        # 合理轉化（需要更複雜的規則）
        if self._is_reasonable_transition(prev_diagnosis, curr_diagnosis):
            return 0.7
        
        # 不一致
        return 0.3
    
    def _evaluate_convergence_quality(
        self,
        session_id: str,
        round_num: int,
        response: Dict
    ) -> float:
        """評估收斂品質"""
        # 從 response 中獲取收斂指標
        convergence_metrics = response.get("convergence_metrics", {})
        
        if convergence_metrics:
            return convergence_metrics.get("overall_convergence", 0.5)
        
        # 簡單的輪次遞增評分
        base_score = min(0.3 + (round_num * 0.15), 0.9)
        return base_score
    
    def _evaluate_response_naturalness(self, response: Dict) -> float:
        """評估回應自然度"""
        text = response.get("final_text", "")
        
        score = 0.5  # 基礎分
        
        # 檢查是否有中醫專業術語
        tcm_terms = ["證型", "病機", "辨證", "治則", "脈象", "舌象"]
        term_count = sum(1 for term in tcm_terms if term in text)
        score += min(0.2, term_count * 0.05)
        
        # 檢查是否有條理性（編號、分段）
        if any(marker in text for marker in ["1.", "2.", "：", "、"]):
            score += 0.15
        
        # 檢查語氣是否專業但親和
        if "建議" in text and "您" in text:
            score += 0.15
        
        return min(1.0, score)
    
    def _calculate_improvement_rate(
        self,
        current: Dict,
        previous: Optional[Dict]
    ) -> float:
        """計算改進率"""
        if not previous:
            return 0.5  # 首輪基準值
        
        # 比較置信度
        curr_confidence = current.get("primary", {}).get("_final", 0)
        prev_confidence = previous.get("primary", {}).get("_final", 0)
        
        if prev_confidence == 0:
            return 0.5
        
        improvement = (curr_confidence - prev_confidence) / prev_confidence
        
        # 轉換到 0-1 範圍
        return max(0, min(1, 0.5 + improvement))
    
    def _is_reasonable_transition(self, prev_diag: str, curr_diag: str) -> bool:
        """判斷是否為合理的證型轉化"""
        reasonable_transitions = {
            "風寒": ["風寒化熱", "寒濕"],
            "風熱": ["風熱壅肺", "熱入營血"],
            "氣虛": ["氣血兩虛", "脾腎陽虛"],
            "陰虛": ["陰虛火旺", "肝腎陰虛"]
        }
        
        for pattern, transitions in reasonable_transitions.items():
            if pattern in prev_diag:
                return any(t in curr_diag for t in transitions)
        
        return False
    
    def _calculate_overall_score(self, dimensions: Dict) -> float:
        """計算綜合分數"""
        total = 0
        for key, weight in self.dimension_weights.items():
            score = dimensions.get(key, {}).get("score", 0)
            total += score * weight
        
        return round(total * 100, 1)  # 轉為百分制
    
    def _get_level(self, score: float) -> str:
        """分數轉級別"""
        if score >= 0.9:
            return "優秀"
        elif score >= 0.75:
            return "良好"
        elif score >= 0.6:
            return "中等"
        elif score >= 0.4:
            return "尚可"
        else:
            return "待改進"
    
    def _generate_clinical_assessment(self, evaluation: Dict) -> str:
        """生成臨床評語"""
        overall = evaluation["overall_score"]
        dims = evaluation["dimensions"]
        
        # 找出最強和最弱的維度
        best_dim = max(dims.items(), key=lambda x: x[1]["score"])
        worst_dim = min(dims.items(), key=lambda x: x[1]["score"])
        
        assessment = f"""
🩺 第{evaluation['round']}輪診斷評估

綜合評分：{overall}/100（{self._get_level(overall/100)}）

優勢表現：{best_dim[1]['name']}（{best_dim[1]['level']}）
待改進項：{worst_dim[1]['name']}（{worst_dim[1]['level']}）

臨床判斷："""
        
        if overall >= 80:
            assessment += "診斷思路清晰，證型判斷準確，具備較高臨床參考價值。"
        elif overall >= 60:
            assessment += "診斷方向正確，但細節仍需完善，建議結合更多症狀資訊。"
        else:
            assessment += "診斷尚不夠明確，建議補充更多症狀描述以提高準確度。"
        
        return assessment
    
    def get_session_report(self, session_id: str) -> Dict[str, Any]:
        """獲取會話完整報告"""
        if session_id not in self.history:
            return {"error": "No evaluation history found"}
        
        evaluations = self.history[session_id]
        
        # 分析趨勢
        scores = [e["overall_score"] for e in evaluations]
        dimensions_trends = {}
        
        for dim in self.dimension_weights.keys():
            dim_scores = [
                e["dimensions"][dim]["score"] 
                for e in evaluations 
                if dim in e["dimensions"]
            ]
            dimensions_trends[dim] = {
                "trend": "improving" if len(dim_scores) > 1 and dim_scores[-1] > dim_scores[0] else "stable",
                "values": dim_scores
            }
        
        return {
            "session_id": session_id,
            "total_rounds": len(evaluations),
            "final_score": scores[-1] if scores else 0,
            "average_score": np.mean(scores) if scores else 0,
            "score_trend": scores,
            "dimensions_trends": dimensions_trends,
            "best_round": max(evaluations, key=lambda x: x["overall_score"])["round"],
            "clinical_summary": self._generate_session_summary(evaluations)
        }
    
    def _generate_session_summary(self, evaluations: List[Dict]) -> str:
        """生成會話總結"""
        avg_score = np.mean([e["overall_score"] for e in evaluations])
        total_rounds = len(evaluations)
        
        return f"""
📋 會話診斷總結

總輪次：{total_rounds}
平均評分：{avg_score:.1f}/100
診斷品質：{self._get_level(avg_score/100)}

臨床建議：
- 診斷過程{"穩定收斂" if avg_score > 70 else "仍需優化"}
- 建議{"可作為臨床參考" if avg_score > 75 else "需要更多資訊支持"}
"""