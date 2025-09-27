"""
反饋案例模型 v1.0

v1.0 功能：
- 用戶治療回饋資料結構
- 脈診整合支持追蹤
- 學習洞察記錄
- 完整的反饋生命週期管理

版本：v1.0
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class TreatmentResult(Enum):
    """治療結果枚舉"""
    EFFECTIVE = "effective"
    PARTIALLY_EFFECTIVE = "partially_effective"
    INEFFECTIVE = "ineffective"
    UNKNOWN = "unknown"
    ADVERSE_REACTION = "adverse_reaction"

class FeedbackQuality(Enum):
    """反饋品質枚舉"""
    HIGH = "high"          # 詳細且可靠
    MEDIUM = "medium"      # 基本完整
    LOW = "low"           # 資訊不足
    INSUFFICIENT = "insufficient"  # 無法使用

@dataclass
class FeedbackCase:
    """
    反饋案例資料模型 v1.0
    
    v1.0 特色：
    - 完整反饋資料結構
    - 脈診整合效果追蹤
    - 學習洞察自動提取
    - 多維度品質評估
    """
    
    # 基本識別資訊
    case_id: str
    original_case_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # 患者相關資訊
    patient_symptoms: Dict[str, Any] = field(default_factory=dict)
    patient_demographics: Dict[str, Any] = field(default_factory=dict)
    
    # 治療方案資訊
    adapted_solution: Dict[str, Any] = field(default_factory=dict)
    original_case_reference: Optional[Dict[str, Any]] = None
    
    # 治療結果
    treatment_result: TreatmentResult = TreatmentResult.UNKNOWN
    monitoring_data: Dict[str, Any] = field(default_factory=dict)
    feedback_score: float = 0.0  # 0-10 分
    
    # 適配詳情
    adaptation_details: Dict[str, Any] = field(default_factory=dict)
    adaptation_confidence: float = 0.0
    
    # v1.0 脈診整合資訊
    pulse_integration: Dict[str, Any] = field(default_factory=dict)
    pulse_effectiveness: float = 0.0
    pulse_consistency_score: float = 0.0
    
    # v1.0 學習洞察
    learning_insights: Dict[str, Any] = field(default_factory=dict)
    success_factors: List[str] = field(default_factory=list)
    failure_factors: List[str] = field(default_factory=list)
    
    # 反饋品質評估
    feedback_quality: FeedbackQuality = FeedbackQuality.MEDIUM
    feedback_completeness: float = 0.0
    feedback_reliability: float = 0.0
    
    # 時間戳與版本
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    
    # 額外元資料
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def update_treatment_result(self, result: TreatmentResult, feedback_score: float = None):
        """更新治療結果"""
        self.treatment_result = result
        if feedback_score is not None:
            self.feedback_score = max(0.0, min(10.0, feedback_score))
        self.updated_at = datetime.now()
    
    def set_pulse_integration_v1(self, pulse_data: Dict[str, Any], effectiveness: float = 0.0, 
                                consistency: float = 0.0):
        """設置脈診整合資料 v1.0"""
        self.pulse_integration = pulse_data
        self.pulse_effectiveness = max(0.0, min(1.0, effectiveness))
        self.pulse_consistency_score = max(0.0, min(1.0, consistency))
        self.updated_at = datetime.now()
    
    def add_learning_insight_v1(self, insight_type: str, insight_content: str, 
                               confidence: float = 1.0):
        """添加學習洞察 v1.0"""
        if 'insights' not in self.learning_insights:
            self.learning_insights['insights'] = []
        
        self.learning_insights['insights'].append({
            "type": insight_type,
            "content": insight_content,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def add_success_factor(self, factor: str):
        """添加成功因子"""
        if factor not in self.success_factors:
            self.success_factors.append(factor)
            self.updated_at = datetime.now()
    
    def add_failure_factor(self, factor: str):
        """添加失敗因子"""
        if factor not in self.failure_factors:
            self.failure_factors.append(factor)
            self.updated_at = datetime.now()
    
    def calculate_overall_quality_v1(self) -> float:
        """計算整體品質分數 v1.0"""
        quality_factors = []
        
        # 反饋完整性
        quality_factors.append(self.feedback_completeness)
        
        # 反饋可靠性
        quality_factors.append(self.feedback_reliability)
        
        # 治療結果明確性
        if self.treatment_result != TreatmentResult.UNKNOWN:
            quality_factors.append(0.8)
        else:
            quality_factors.append(0.2)
        
        # v1.0 脈診整合品質
        if self.pulse_integration:
            quality_factors.append(self.pulse_effectiveness)
        
        # 學習洞察豐富度
        insights_count = len(self.learning_insights.get('insights', []))
        insight_quality = min(1.0, insights_count / 3.0)  # 3個洞察算滿分
        quality_factors.append(insight_quality)
        
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """獲取反饋摘要"""
        return {
            "case_id": self.case_id,
            "session_id": self.session_id,
            "treatment_result": self.treatment_result.value,
            "feedback_score": self.feedback_score,
            "adaptation_confidence": self.adaptation_confidence,
            "pulse_effectiveness": self.pulse_effectiveness,  # v1.0
            "pulse_consistency": self.pulse_consistency_score,  # v1.0
            "success_factors_count": len(self.success_factors),
            "failure_factors_count": len(self.failure_factors),
            "learning_insights_count": len(self.learning_insights.get('insights', [])),
            "overall_quality": self.calculate_overall_quality_v1(),
            "feedback_quality": self.feedback_quality.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version
        }
    
    def is_treatment_successful(self) -> bool:
        """判斷治療是否成功"""
        return (
            self.treatment_result in [TreatmentResult.EFFECTIVE, TreatmentResult.PARTIALLY_EFFECTIVE] and
            self.feedback_score >= 6.0
        )
    
    def has_pulse_integration_v1(self) -> bool:
        """判斷是否有脈診整合 v1.0"""
        return bool(self.pulse_integration) and self.pulse_effectiveness > 0.0
    
    def get_learning_value_v1(self) -> float:
        """獲取學習價值評分 v1.0"""
        learning_factors = []
        
        # 治療結果明確性
        if self.treatment_result != TreatmentResult.UNKNOWN:
            learning_factors.append(0.8)
        
        # 反饋品質
        quality_scores = {
            FeedbackQuality.HIGH: 1.0,
            FeedbackQuality.MEDIUM: 0.7,
            FeedbackQuality.LOW: 0.4,
            FeedbackQuality.INSUFFICIENT: 0.1
        }
        learning_factors.append(quality_scores.get(self.feedback_quality, 0.5))
        
        # 成功/失敗因子明確性
        factors_clarity = min(1.0, (len(self.success_factors) + len(self.failure_factors)) / 5.0)
        learning_factors.append(factors_clarity)
        
        # v1.0 脈診學習價值
        if self.has_pulse_integration_v1():
            pulse_learning_value = (self.pulse_effectiveness + self.pulse_consistency_score) / 2
            learning_factors.append(pulse_learning_value)
        
        return sum(learning_factors) / len(learning_factors) if learning_factors else 0.0
    
    def add_tag(self, tag: str):
        """添加標籤"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "case_id": self.case_id,
            "original_case_id": self.original_case_id,
            "session_id": self.session_id,
            "patient_symptoms": self.patient_symptoms,
            "patient_demographics": self.patient_demographics,
            "adapted_solution": self.adapted_solution,
            "original_case_reference": self.original_case_reference,
            "treatment_result": self.treatment_result.value,
            "monitoring_data": self.monitoring_data,
            "feedback_score": self.feedback_score,
            "adaptation_details": self.adaptation_details,
            "adaptation_confidence": self.adaptation_confidence,
            "pulse_integration": self.pulse_integration,
            "pulse_effectiveness": self.pulse_effectiveness,
            "pulse_consistency_score": self.pulse_consistency_score,
            "learning_insights": self.learning_insights,
            "success_factors": self.success_factors,
            "failure_factors": self.failure_factors,
            "feedback_quality": self.feedback_quality.value,
            "feedback_completeness": self.feedback_completeness,
            "feedback_reliability": self.feedback_reliability,
            "overall_quality": self.calculate_overall_quality_v1(),
            "learning_value": self.get_learning_value_v1(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "metadata": self.metadata,
            "tags": self.tags
        }
