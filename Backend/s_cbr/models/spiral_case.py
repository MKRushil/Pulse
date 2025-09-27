"""
螺旋案例模型 v1.0

v1.0 功能：
- 螺旋推理案例資料結構
- 推理狀態管理
- 脈診整合資料模型
- 案例生命週期追蹤

版本：v1.0
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

class SpiralStatus(Enum):
    """螺旋推理狀態枚舉"""
    INITIALIZED = "initialized"
    STEP1_SEARCHING = "step1_searching"
    STEP1_COMPLETED = "step1_completed"
    STEP2_ADAPTING = "step2_adapting"
    STEP2_COMPLETED = "step2_completed"
    STEP3_MONITORING = "step3_monitoring"
    STEP3_COMPLETED = "step3_completed"
    STEP4_FEEDBACK = "step4_feedback"
    STEP4_COMPLETED = "step4_completed"
    CONVERGED = "converged"
    TERMINATED = "terminated"
    ERROR = "error"

class ConvergenceType(Enum):
    """收斂類型枚舉 v1.0"""
    SUCCESSFUL = "successful"           # 成功收斂
    PARTIAL = "partial"                 # 部分收斂
    TIMEOUT = "timeout"                 # 超時終止
    USER_TERMINATED = "user_terminated" # 用戶終止
    ERROR_TERMINATED = "error_terminated" # 錯誤終止

@dataclass
class SpiralCase:
    """
    螺旋案例資料模型 v1.0
    
    v1.0 特色：
    - 完整的案例資料結構
    - 脈診資訊整合
    - 推理過程追蹤
    - 版本控制支援
    """
    
    # 基本資訊
    case_id: str
    session_id: str
    original_query: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    
    # 患者資訊
    patient_profile: Dict[str, Any] = field(default_factory=dict)
    patient_symptoms: List[str] = field(default_factory=list)
    patient_context: Dict[str, Any] = field(default_factory=dict)
    
    # v1.0 脈診整合資訊
    pulse_information: Dict[str, Any] = field(default_factory=dict)
    pulse_support_data: List[Dict[str, Any]] = field(default_factory=list)
    pulse_integration_quality: float = 0.0
    
    # 推理過程資訊
    spiral_status: SpiralStatus = SpiralStatus.INITIALIZED
    current_step: int = 0
    max_iterations: int = 5
    similarity_threshold: float = 0.75
    
    # 案例匹配資訊
    matched_case: Optional[Dict[str, Any]] = None
    case_similarity: float = 0.0
    matching_confidence: float = 0.0
    
    # 適配資訊
    adapted_solution: Optional[Dict[str, Any]] = None
    adaptation_confidence: float = 0.0
    adaptation_details: Dict[str, Any] = field(default_factory=dict)
    
    # 監控資訊
    monitoring_result: Optional[Dict[str, Any]] = None
    validation_passed: bool = False
    safety_score: float = 0.0
    effectiveness_score: float = 0.0
    
    # 反饋資訊
    user_feedback: Optional[Dict[str, Any]] = None
    feedback_analysis: Dict[str, Any] = field(default_factory=dict)
    treatment_outcome: str = "unknown"
    
    # 收斂資訊
    convergence_achieved: bool = False
    convergence_type: Optional[ConvergenceType] = None
    convergence_confidence: float = 0.0
    final_recommendation: str = ""
    
    # 元資料
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_errors: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def update_patient_profile(self, profile_data: Dict[str, Any]):
        """更新患者檔案"""
        self.patient_profile.update(profile_data)
        self.updated_at = datetime.now()
    
    def add_pulse_information_v1(self, pulse_data: Dict[str, Any]):
        """添加脈診資訊 v1.0"""
        self.pulse_information.update(pulse_data)
        
        # 提取脈診支持資料
        if pulse_data.get('pulse_support'):
            self.pulse_support_data.extend(pulse_data['pulse_support'])
        
        # 更新整合品質
        if pulse_data.get('integration_quality'):
            self.pulse_integration_quality = pulse_data['integration_quality']
        
        self.updated_at = datetime.now()
    
    def set_matched_case(self, case_data: Dict[str, Any], similarity: float, confidence: float):
        """設置匹配案例"""
        self.matched_case = case_data
        self.case_similarity = similarity
        self.matching_confidence = confidence
        self.updated_at = datetime.now()
    
    def set_adapted_solution(self, solution_data: Dict[str, Any], confidence: float, details: Dict[str, Any] = None):
        """設置適配方案"""
        self.adapted_solution = solution_data
        self.adaptation_confidence = confidence
        if details:
            self.adaptation_details.update(details)
        self.updated_at = datetime.now()
    
    def set_monitoring_result(self, monitoring_data: Dict[str, Any]):
        """設置監控結果"""
        self.monitoring_result = monitoring_data
        self.validation_passed = monitoring_data.get('validation_passed', False)
        self.safety_score = monitoring_data.get('safety_score', 0.0)
        self.effectiveness_score = monitoring_data.get('effectiveness_score', 0.0)
        self.updated_at = datetime.now()
    
    def set_user_feedback(self, feedback_data: Dict[str, Any], analysis: Dict[str, Any] = None):
        """設置用戶反饋"""
        self.user_feedback = feedback_data
        if analysis:
            self.feedback_analysis = analysis
        
        # 更新治療結果
        if feedback_data.get('treatment_effective'):
            self.treatment_outcome = "effective"
        elif feedback_data.get('treatment_ineffective'):
            self.treatment_outcome = "ineffective"
        
        self.updated_at = datetime.now()
    
    def set_convergence_v1(self, convergence_type: ConvergenceType, confidence: float, recommendation: str = ""):
        """設置收斂狀態 v1.0"""
        self.convergence_achieved = True
        self.convergence_type = convergence_type
        self.convergence_confidence = confidence
        self.final_recommendation = recommendation
        self.spiral_status = SpiralStatus.CONVERGED
        self.updated_at = datetime.now()
    
    def advance_step(self):
        """推進到下一步驟"""
        if self.current_step < 4:
            self.current_step += 1
            
            # 更新狀態
            status_mapping = {
                1: SpiralStatus.STEP1_SEARCHING,
                2: SpiralStatus.STEP2_ADAPTING,
                3: SpiralStatus.STEP3_MONITORING,
                4: SpiralStatus.STEP4_FEEDBACK
            }
            
            self.spiral_status = status_mapping.get(self.current_step, self.spiral_status)
            self.updated_at = datetime.now()
    
    def complete_step(self):
        """完成當前步驟"""
        if self.current_step > 0:
            completion_mapping = {
                1: SpiralStatus.STEP1_COMPLETED,
                2: SpiralStatus.STEP2_COMPLETED,
                3: SpiralStatus.STEP3_COMPLETED,
                4: SpiralStatus.STEP4_COMPLETED
            }
            
            self.spiral_status = completion_mapping.get(self.current_step, self.spiral_status)
            self.updated_at = datetime.now()
    
    def add_error(self, error_message: str):
        """添加處理錯誤"""
        self.processing_errors.append({
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "step": self.current_step
        })
        self.spiral_status = SpiralStatus.ERROR
        self.updated_at = datetime.now()
    
    def update_performance_metrics(self, metrics: Dict[str, Any]):
        """更新效能指標"""
        self.performance_metrics.update(metrics)
        self.performance_metrics['last_updated'] = datetime.now().isoformat()
        self.updated_at = datetime.now()
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """獲取進度摘要"""
        return {
            "case_id": self.case_id,
            "session_id": self.session_id,
            "current_status": self.spiral_status.value,
            "current_step": self.current_step,
            "progress_percentage": (self.current_step / 4) * 100,
            "case_matched": self.matched_case is not None,
            "solution_adapted": self.adapted_solution is not None,
            "monitoring_completed": self.monitoring_result is not None,
            "feedback_collected": self.user_feedback is not None,
            "convergence_achieved": self.convergence_achieved,
            "pulse_integration_quality": self.pulse_integration_quality,  # v1.0
            "overall_confidence": self._calculate_overall_confidence(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version
        }
    
    def get_detailed_summary(self) -> Dict[str, Any]:
        """獲取詳細摘要"""
        summary = self.get_progress_summary()
        
        summary.update({
            "patient_profile": self.patient_profile,
            "pulse_information": self.pulse_information,  # v1.0
            "matched_case_info": {
                "similarity": self.case_similarity,
                "confidence": self.matching_confidence,
                "case_preview": str(self.matched_case)[:100] + "..." if self.matched_case else None
            },
            "adaptation_info": {
                "confidence": self.adaptation_confidence,
                "details_available": bool(self.adaptation_details)
            },
            "monitoring_info": {
                "validation_passed": self.validation_passed,
                "safety_score": self.safety_score,
                "effectiveness_score": self.effectiveness_score
            },
            "feedback_info": {
                "treatment_outcome": self.treatment_outcome,
                "feedback_available": self.user_feedback is not None
            },
            "convergence_info": {
                "achieved": self.convergence_achieved,
                "type": self.convergence_type.value if self.convergence_type else None,
                "confidence": self.convergence_confidence,
                "recommendation": self.final_recommendation
            },
            "error_info": {
                "has_errors": len(self.processing_errors) > 0,
                "error_count": len(self.processing_errors),
                "latest_error": self.processing_errors[-1] if self.processing_errors else None
            },
            "performance_info": self.performance_metrics
        })
        
        return summary
    
    def _calculate_overall_confidence(self) -> float:
        """計算整體信心度"""
        confidence_factors = []
        
        if self.matching_confidence > 0:
            confidence_factors.append(self.matching_confidence)
        
        if self.adaptation_confidence > 0:
            confidence_factors.append(self.adaptation_confidence)
        
        if self.safety_score > 0:
            confidence_factors.append(self.safety_score)
        
        if self.effectiveness_score > 0:
            confidence_factors.append(self.effectiveness_score)
        
        # v1.0 脈診整合信心度
        if self.pulse_integration_quality > 0:
            confidence_factors.append(self.pulse_integration_quality)
        
        if self.convergence_confidence > 0:
            confidence_factors.append(self.convergence_confidence)
        
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "case_id": self.case_id,
            "session_id": self.session_id,
            "original_query": self.original_query,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "patient_profile": self.patient_profile,
            "patient_symptoms": self.patient_symptoms,
            "patient_context": self.patient_context,
            "pulse_information": self.pulse_information,  # v1.0
            "pulse_support_data": self.pulse_support_data,  # v1.0
            "pulse_integration_quality": self.pulse_integration_quality,  # v1.0
            "spiral_status": self.spiral_status.value,
            "current_step": self.current_step,
            "max_iterations": self.max_iterations,
            "similarity_threshold": self.similarity_threshold,
            "matched_case": self.matched_case,
            "case_similarity": self.case_similarity,
            "matching_confidence": self.matching_confidence,
            "adapted_solution": self.adapted_solution,
            "adaptation_confidence": self.adaptation_confidence,
            "adaptation_details": self.adaptation_details,
            "monitoring_result": self.monitoring_result,
            "validation_passed": self.validation_passed,
            "safety_score": self.safety_score,
            "effectiveness_score": self.effectiveness_score,
            "user_feedback": self.user_feedback,
            "feedback_analysis": self.feedback_analysis,
            "treatment_outcome": self.treatment_outcome,
            "convergence_achieved": self.convergence_achieved,
            "convergence_type": self.convergence_type.value if self.convergence_type else None,
            "convergence_confidence": self.convergence_confidence,
            "final_recommendation": self.final_recommendation,
            "metadata": self.metadata,
            "processing_errors": self.processing_errors,
            "performance_metrics": self.performance_metrics
        }

@dataclass
class SpiralState:
    """
    螺旋推理狀態管理 v1.0
    
    管理整個螺旋推理過程的狀態變化
    """
    
    session_id: str
    initial_query: Dict[str, Any]
    max_iterations: int = 5
    similarity_threshold: float = 0.75
    version: str = "1.0"
    
    # 狀態變數
    current_round: int = 0
    current_symptoms: List[str] = field(default_factory=list)
    medical_history: List[str] = field(default_factory=list)
    patient_profile: Dict[str, Any] = field(default_factory=dict)
    
    # 推理結果記錄
    round_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # 錯誤處理
    consecutive_errors: int = 0
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # v1.0 脈診相關狀態
    pulse_knowledge_used: List[str] = field(default_factory=list)
    pulse_consistency_history: List[float] = field(default_factory=list)
    
    def add_round_result(self, result: Dict[str, Any]):
        """添加輪次結果"""
        result['round_number'] = len(self.round_results) + 1
        result['timestamp'] = datetime.now().isoformat()
        result['version'] = self.version
        self.round_results.append(result)
        
        # v1.0 更新脈診追蹤
        if result.get('pulse_learning'):
            pulse_names = [p.get('pulse_name', '') for p in result['pulse_learning']]
            self.pulse_knowledge_used.extend(pulse_names)
        
        if result.get('pulse_consistency'):
            self.pulse_consistency_history.append(result['pulse_consistency'])
    
    def add_error_round(self, round_number: int, error_message: str):
        """添加錯誤輪次"""
        self.consecutive_errors += 1
        self.error_history.append({
            'round': round_number,
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        })
    
    def reset_error_count(self):
        """重置錯誤計數"""
        self.consecutive_errors = 0
    
    def get_refined_criteria(self) -> Dict[str, Any]:
        """獲取優化的搜尋條件"""
        criteria = {
            'symptoms': self.current_symptoms,
            'medical_history': self.medical_history,
            'similarity_threshold': self.similarity_threshold
        }
        
        # 基於歷史結果調整條件
        if self.round_results:
            last_result = self.round_results[-1]
            if last_result.get('similarity_score', 0) < self.similarity_threshold:
                criteria['similarity_threshold'] = max(0.5, self.similarity_threshold - 0.1)
        
        return criteria
    
    def get_relaxed_criteria(self) -> Dict[str, Any]:
        """獲取放寬的搜尋條件"""
        return {
            'query_text': ' '.join(self.current_symptoms),
            'context': self.patient_profile,
            'relaxed_mode': True,
            'similarity_threshold': max(0.3, self.similarity_threshold - 0.2)
        }
    
    def get_spiral_summary(self) -> Dict[str, Any]:
        """獲取螺旋推理摘要"""
        return {
            'session_id': self.session_id,
            'total_rounds': len(self.round_results),
            'current_round': self.current_round,
            'max_iterations': self.max_iterations,
            'consecutive_errors': self.consecutive_errors,
            'pulse_knowledge_count': len(set(self.pulse_knowledge_used)),  # v1.0 去重計數
            'avg_pulse_consistency': sum(self.pulse_consistency_history) / len(self.pulse_consistency_history) if self.pulse_consistency_history else 0.0,  # v1.0
            'has_errors': len(self.error_history) > 0,
            'version': self.version
        }
