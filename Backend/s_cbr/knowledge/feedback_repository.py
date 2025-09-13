"""
反饋知識庫 v1.0

v1.0 功能：
- S-CBR 反饋案例存儲
- 脈診學習經驗記錄
- 學習洞察管理
- 知識更新追蹤

版本：v1.0
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from s_cbr.utils.api_manager import SCBRAPIManager
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger
from s_cbr.models.feedback_case import FeedbackCase

class FeedbackRepository:
    """
    反饋知識庫 v1.0
    
    v1.0 特色：
    - S-CBR 專用反饋存儲
    - 脈診學習經驗累積
    - 螺旋推理效果追蹤
    - 知識庫持續優化
    """
    
    def __init__(self):
        """初始化反饋知識庫 v1.0"""
        self.config = SCBRConfig()
        self.api_manager = SCBRAPIManager()
        self.logger = SpiralLogger.get_logger("FeedbackRepository")
        self.version = "1.0"
        
        # S-CBR 專用 Weaviate 類別
        self.feedback_class = "SCBRFeedbackCases"
        self.pulse_learning_class = "SCBRPulseLearning"
        self.spiral_sessions_class = "SCBRSpiralSessions"
        
        self.logger.info(f"反饋知識庫 v{self.version} 初始化完成")
    
    async def store_feedback_case_v1(self, feedback_case: FeedbackCase) -> Dict[str, Any]:
        """
        存儲反饋案例 v1.0
        
        將螺旋推理的反饋結果存儲到專用知識庫
        """
        self.logger.info(f"存儲反饋案例: {feedback_case.case_id}")
        
        try:
            # 構建存儲資料
            case_data = {
                "case_id": feedback_case.case_id,
                "original_case_id": feedback_case.original_case_id or "",
                "session_id": feedback_case.session_id or "",
                "patient_symptoms": json.dumps(feedback_case.patient_symptoms, ensure_ascii=False),
                "adapted_solution": json.dumps(feedback_case.adapted_solution, ensure_ascii=False),
                "treatment_result": feedback_case.treatment_result,
                "monitoring_data": json.dumps(feedback_case.monitoring_data, ensure_ascii=False),
                "feedback_score": feedback_case.feedback_score,
                "adaptation_details": json.dumps(feedback_case.adaptation_details, ensure_ascii=False),
                "pulse_integration": json.dumps(feedback_case.pulse_integration, ensure_ascii=False),  # v1.0
                "learning_insights": json.dumps(feedback_case.learning_insights, ensure_ascii=False),  # v1.0
                "created_at": feedback_case.created_at.isoformat(),
                "updated_at": feedback_case.updated_at.isoformat(),
                "version": self.version
            }
            
            # 使用 Weaviate 存儲
            result = self.api_manager.weaviate_client.data_object.create(
                data_object=case_data,
                class_name=self.feedback_class
            )
            
            if result:
                self.logger.info(f"反饋案例存儲成功: {feedback_case.case_id}")
                return {
                    "success": True,
                    "case_id": feedback_case.case_id,
                    "weaviate_id": result,
                    "storage_timestamp": datetime.now().isoformat()
                }
            else:
                raise Exception("Weaviate 存儲失敗")
                
        except Exception as e:
            self.logger.error(f"反饋案例存儲失敗: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "case_id": feedback_case.case_id
            }
    
    async def update_pulse_knowledge_v1(self, pulse_learning: List[Dict[str, Any]], 
                                       session_id: str) -> Dict[str, Any]:
        """
        更新脈診知識 v1.0
        
        基於治療回饋更新脈診知識庫的應用經驗
        """
        self.logger.info(f"更新脈診知識 - 會話: {session_id}")
        
        try:
            updated_count = 0
            
            for pulse_insight in pulse_learning:
                # 構建脈診學習記錄
                learning_record = {
                    "session_id": session_id,
                    "pulse_name": pulse_insight.get('pulse_name', ''),
                    "applied_knowledge": pulse_insight.get('applied_knowledge', ''),
                    "effectiveness": pulse_insight.get('effectiveness', 0.0),
                    "patient_match": pulse_insight.get('patient_match', 0.0),
                    "learning_insight": pulse_insight.get('insight', ''),
                    "success_pattern": pulse_insight.get('success_pattern', ''),
                    "improvement_needed": pulse_insight.get('improvement_needed', ''),
                    "created_at": datetime.now().isoformat(),
                    "version": self.version
                }
                
                # 存儲到脈診學習類別
                result = self.api_manager.weaviate_client.data_object.create(
                    data_object=learning_record,
                    class_name=self.pulse_learning_class
                )
                
                if result:
                    updated_count += 1
            
            self.logger.info(f"脈診知識更新完成 - 更新 {updated_count} 條記錄")
            
            return {
                "success": True,
                "updated_count": updated_count,
                "session_id": session_id,
                "update_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"脈診知識更新失敗: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    async def store_learning_insights_v1(self, learning_insights: Dict[str, Any], 
                                        session_id: str) -> Dict[str, Any]:
        """存儲學習洞察 v1.0"""
        self.logger.debug(f"存儲學習洞察 - 會話: {session_id}")
        
        try:
            # 構建學習洞察記錄
            insights_record = {
                "session_id": session_id,
                "case_learning": json.dumps(learning_insights.get('case_learning', []), ensure_ascii=False),
                "pulse_learning": json.dumps(learning_insights.get('pulse_learning', []), ensure_ascii=False),
                "adaptation_learning": json.dumps(learning_insights.get('adaptation_learning', []), ensure_ascii=False),
                "general_insights": json.dumps(learning_insights.get('general_insights', []), ensure_ascii=False),
                "success_factors": json.dumps(learning_insights.get('success_factors', []), ensure_ascii=False),
                "failure_factors": json.dumps(learning_insights.get('failure_factors', []), ensure_ascii=False),
                "overall_learning_value": learning_insights.get('overall_learning_value', 0.0),
                "created_at": datetime.now().isoformat(),
                "version": self.version
            }
            
            # 存儲學習洞察
            result = self.api_manager.weaviate_client.data_object.create(
                data_object=insights_record,
                class_name=self.spiral_sessions_class
            )
            
            return {"success": bool(result), "record_id": result}
            
        except Exception as e:
            self.logger.error(f"學習洞察存儲失敗: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def query_feedback_cases(self, filters: Dict[str, Any] = None, 
                                  limit: int = 10) -> List[Dict[str, Any]]:
        """查詢反饋案例 v1.0"""
        self.logger.debug(f"查詢反饋案例 - 限制: {limit}")
        
        try:
            # 構建查詢
            query_builder = (
                self.api_manager.weaviate_client.query
                .get(self.feedback_class, [
                    "case_id", "original_case_id", "treatment_result", 
                    "feedback_score", "created_at", "version"
                ])
                .with_limit(limit)
                .with_additional(["id"])
            )
            
            # 添加過濾條件
            if filters:
                where_filter = self._build_feedback_filter(filters)
                if where_filter:
                    query_builder = query_builder.with_where(where_filter)
            
            result = query_builder.do()
            
            # 處理查詢結果
            feedback_cases = result.get("data", {}).get("Get", {}).get(self.feedback_class, [])
            
            self.logger.debug(f"查詢到 {len(feedback_cases)} 個反饋案例")
            
            return feedback_cases
            
        except Exception as e:
            self.logger.error(f"反饋案例查詢失敗: {str(e)}")
            return []
    
    async def query_pulse_learning_history(self, pulse_name: str = None, 
                                          limit: int = 20) -> List[Dict[str, Any]]:
        """查詢脈診學習歷史 v1.0"""
        self.logger.debug(f"查詢脈診學習歷史 - 脈象: {pulse_name}")
        
        try:
            query_builder = (
                self.api_manager.weaviate_client.query
                .get(self.pulse_learning_class, [
                    "pulse_name", "effectiveness", "learning_insight", 
                    "success_pattern", "created_at", "version"
                ])
                .with_limit(limit)
                .with_additional(["id"])
            )
            
            # 按脈象名稱過濾
            if pulse_name:
                query_builder = query_builder.with_where({
                    "path": ["pulse_name"],
                    "operator": "Equal",
                    "valueString": pulse_name
                })
            
            result = query_builder.do()
            
            pulse_history = result.get("data", {}).get("Get", {}).get(self.pulse_learning_class, [])
            
            self.logger.debug(f"查詢到 {len(pulse_history)} 條脈診學習記錄")
            
            return pulse_history
            
        except Exception as e:
            self.logger.error(f"脈診學習歷史查詢失敗: {str(e)}")
            return []
    
    async def analyze_feedback_trends_v1(self, time_range_days: int = 30) -> Dict[str, Any]:
        """分析反饋趨勢 v1.0"""
        self.logger.info(f"分析反饋趨勢 - {time_range_days} 天")
        
        try:
            # 查詢最近的反饋案例
            recent_cases = await self.query_feedback_cases(
                filters={"time_range_days": time_range_days}, 
                limit=100
            )
            
            if not recent_cases:
                return {"trends": "insufficient_data", "analysis": "需要更多反饋資料"}
            
            # 分析趨勢
            total_cases = len(recent_cases)
            avg_feedback_score = sum(float(case.get('feedback_score', 0)) for case in recent_cases) / total_cases
            
            # 治療結果分佈
            result_distribution = {}
            for case in recent_cases:
                result = case.get('treatment_result', 'unknown')
                result_distribution[result] = result_distribution.get(result, 0) + 1
            
            # 成功率計算
            successful_cases = result_distribution.get('effective', 0) + result_distribution.get('good', 0)
            success_rate = successful_cases / total_cases if total_cases > 0 else 0
            
            trends_analysis = {
                "analysis_period_days": time_range_days,
                "total_cases_analyzed": total_cases,
                "average_feedback_score": avg_feedback_score,
                "success_rate": success_rate,
                "result_distribution": result_distribution,
                "trend_direction": self._determine_trend_direction(avg_feedback_score),
                "improvement_areas": self._identify_improvement_areas_v1(recent_cases),
                "pulse_integration_effectiveness": self._analyze_pulse_effectiveness_v1(recent_cases),
                "analysis_timestamp": datetime.now().isoformat(),
                "version": self.version
            }
            
            self.logger.info(f"反饋趨勢分析完成 - 成功率: {success_rate:.1%}")
            
            return trends_analysis
            
        except Exception as e:
            self.logger.error(f"反饋趨勢分析失敗: {str(e)}")
            return {"error": str(e), "trends": "analysis_failed"}
    
    async def generate_knowledge_update_recommendations_v1(self) -> Dict[str, Any]:
        """生成知識更新建議 v1.0"""
        self.logger.info("生成知識更新建議")
        
        try:
            # 分析最近的學習洞察
            recent_insights = await self.query_feedback_cases(
                filters={"recent": True}, limit=50
            )
            
            # 分析脈診學習效果
            pulse_learning = await self.query_pulse_learning_history(limit=50)
            
            recommendations = {
                "case_knowledge_updates": [],
                "pulse_knowledge_updates": [],
                "algorithm_improvements": [],
                "data_quality_improvements": [],
                "priority_areas": []
            }
            
            # 基於反饋案例的建議
            if recent_insights:
                effective_count = sum(1 for case in recent_insights 
                                    if case.get('treatment_result') in ['effective', 'good'])
                if effective_count / len(recent_insights) < 0.7:
                    recommendations["algorithm_improvements"].append("優化案例匹配算法")
            
            # v1.0 基於脈診學習的建議
            if pulse_learning:
                high_effective_pulses = [p for p in pulse_learning 
                                       if float(p.get('effectiveness', 0)) > 0.8]
                if high_effective_pulses:
                    recommendations["pulse_knowledge_updates"].append(
                        f"推廣 {len(high_effective_pulses)} 個高效脈診模式"
                    )
                
                low_effective_pulses = [p for p in pulse_learning 
                                      if float(p.get('effectiveness', 0)) < 0.4]
                if low_effective_pulses:
                    recommendations["pulse_knowledge_updates"].append(
                        f"改進 {len(low_effective_pulses)} 個低效脈診應用"
                    )
            
            # 優先級排序
            if recommendations["pulse_knowledge_updates"]:
                recommendations["priority_areas"].append("脈診知識優化")
            if recommendations["algorithm_improvements"]:
                recommendations["priority_areas"].append("算法改進")
            
            recommendations.update({
                "analysis_basis": f"{len(recent_insights)} 個反饋案例 + {len(pulse_learning)} 條脈診學習",
                "confidence_level": "medium" if len(recent_insights) > 20 else "low",
                "generated_at": datetime.now().isoformat(),
                "version": self.version
            })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"知識更新建議生成失敗: {str(e)}")
            return {"error": str(e), "recommendations": "generation_failed"}
    
    # 輔助方法
    def _build_feedback_filter(self, filters: Dict[str, Any]) -> Optional[Dict]:
        """構建反饋查詢過濾條件"""
        conditions = []
        
        # 時間範圍過濾
        if filters.get('time_range_days'):
            # 簡化實現：實際需要處理日期比較
            conditions.append({
                "path": ["version"],
                "operator": "Equal",
                "valueString": self.version
            })
        
        # 治療結果過濾
        if filters.get('treatment_result'):
            conditions.append({
                "path": ["treatment_result"],
                "operator": "Equal",
                "valueString": filters['treatment_result']
            })
        
        # 反饋分數範圍
        if filters.get('min_feedback_score'):
            conditions.append({
                "path": ["feedback_score"],
                "operator": "GreaterThan",
                "valueNumber": filters['min_feedback_score']
            })
        
        # 返回條件
        if len(conditions) == 1:
            return conditions[0]
        elif len(conditions) > 1:
            return {
                "operator": "And",
                "operands": conditions
            }
        
        return None
    
    def _determine_trend_direction(self, avg_feedback_score: float) -> str:
        """確定趨勢方向"""
        if avg_feedback_score > 7.5:
            return "positive"
        elif avg_feedback_score > 5.0:
            return "stable"
        else:
            return "needs_improvement"
    
    def _identify_improvement_areas_v1(self, cases: List[Dict]) -> List[str]:
        """識別改進領域 v1.0"""
        areas = []
        
        low_score_cases = [case for case in cases if float(case.get('feedback_score', 0)) < 5.0]
        if len(low_score_cases) > len(cases) * 0.3:
            areas.append("用戶滿意度需要提升")
        
        ineffective_cases = [case for case in cases if case.get('treatment_result') == 'ineffective']
        if len(ineffective_cases) > len(cases) * 0.2:
            areas.append("治療效果需要改善")
        
        return areas
    
    def _analyze_pulse_effectiveness_v1(self, cases: List[Dict]) -> Dict[str, Any]:
        """分析脈診有效性 v1.0"""
        pulse_cases = 0
        total_effectiveness = 0
        
        for case in cases:
            # 簡化判斷：如果案例包含脈診資訊
            case_data = case.get('pulse_integration', '{}')
            try:
                pulse_data = json.loads(case_data) if isinstance(case_data, str) else case_data
                if pulse_data and pulse_data != {}:
                    pulse_cases += 1
                    effectiveness = float(case.get('feedback_score', 0)) / 10.0
                    total_effectiveness += effectiveness
            except:
                continue
        
        if pulse_cases > 0:
            avg_effectiveness = total_effectiveness / pulse_cases
            return {
                "cases_with_pulse": pulse_cases,
                "average_effectiveness": avg_effectiveness,
                "pulse_integration_rate": pulse_cases / len(cases),
                "effectiveness_level": "high" if avg_effectiveness > 0.8 else "medium" if avg_effectiveness > 0.6 else "low"
            }
        
        return {
            "cases_with_pulse": 0,
            "pulse_integration_rate": 0.0,
            "effectiveness_level": "no_data"
        }
