"""
螺旋推理記憶庫 v1.0

v1.0 功能：
- 螺旋推理會話記錄
- 推理軌跡追蹤
- 上下文記憶管理
- 收斂模式分析

版本：v1.0
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from s_cbr.utils.spiral_logger import SpiralLogger
from s_cbr.config.scbr_config import SCBRConfig

class SpiralMemory:
    """
    螺旋推理記憶庫 v1.0
    
    v1.0 特色：
    - 會話記憶持久化
    - 推理軌跡分析
    - 收斂模式學習
    - 上下文智能檢索
    """
    
    def __init__(self):
        """初始化螺旋記憶庫 v1.0"""
        self.config = SCBRConfig()
        self.logger = SpiralLogger.get_logger("SpiralMemory")
        self.version = "1.0"
        
        # 記憶存儲結構
        self.session_memories = {}  # 會話記憶
        self.reasoning_traces = {}  # 推理軌跡
        self.convergence_patterns = []  # 收斂模式
        self.context_cache = {}  # 上下文緩存
        
        # 記憶管理配置
        self.max_session_memory = 100  # 最大會話記憶數
        self.memory_retention_days = 30  # 記憶保留天數
        self.trace_compression_threshold = 50  # 軌跡壓縮閾值
        
        self.logger.info(f"螺旋記憶庫 v{self.version} 初始化完成")
    
    def store_session_memory(self, session_id: str, session_data: Dict[str, Any]):
        """存儲會話記憶 v1.0"""
        self.logger.debug(f"存儲會話記憶: {session_id}")
        
        memory_entry = {
            "session_id": session_id,
            "session_data": session_data,
            "stored_at": datetime.now(),
            "access_count": 0,
            "last_accessed": datetime.now(),
            "version": self.version,
            "memory_type": "session"
        }
        
        # 存儲記憶
        self.session_memories[session_id] = memory_entry
        
        # 記憶管理
        self._manage_memory_capacity()
        
        self.logger.debug(f"會話記憶存儲完成: {session_id}")
    
    def store_reasoning_trace(self, session_id: str, step_number: int, 
                            step_result: Dict[str, Any], spiral_state: Any = None):
        """存儲推理軌跡 v1.0"""
        self.logger.debug(f"存儲推理軌跡: {session_id} - STEP {step_number}")
        
        # 初始化會話軌跡
        if session_id not in self.reasoning_traces:
            self.reasoning_traces[session_id] = {
                "session_id": session_id,
                "traces": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "version": self.version
            }
        
        # 構建軌跡記錄
        trace_entry = {
            "step_number": step_number,
            "step_result": step_result,
            "spiral_round": getattr(spiral_state, 'current_round', 0) if spiral_state else 0,
            "timestamp": datetime.now(),
            "step_duration": step_result.get('duration', 0),
            "step_confidence": step_result.get('confidence_score', 0.0),
            "step_success": step_result.get('success', False),
            # v1.0 脈診追蹤
            "pulse_integration": {
                "pulse_support_count": len(step_result.get('pulse_support', [])),
                "pulse_consistency": step_result.get('pulse_consistency', 0.0),
                "pulse_insights": step_result.get('pulse_learning', [])
            }
        }
        
        # 添加軌跡
        self.reasoning_traces[session_id]["traces"].append(trace_entry)
        self.reasoning_traces[session_id]["updated_at"] = datetime.now()
        
        # 軌跡壓縮檢查
        if len(self.reasoning_traces[session_id]["traces"]) > self.trace_compression_threshold:
            self._compress_reasoning_traces(session_id)
    
    def store_convergence_pattern(self, session_id: str, convergence_data: Dict[str, Any]):
        """存儲收斂模式 v1.0"""
        self.logger.debug(f"存儲收斂模式: {session_id}")
        
        pattern_entry = {
            "session_id": session_id,
            "convergence_data": convergence_data,
            "pattern_type": convergence_data.get('convergence_type', 'standard'),
            "rounds_to_convergence": convergence_data.get('total_rounds', 0),
            "final_confidence": convergence_data.get('final_confidence', 0.0),
            "success_factors": convergence_data.get('success_factors', []),
            # v1.0 脈診收斂因素
            "pulse_contribution": convergence_data.get('pulse_contribution', 0.0),
            "pulse_patterns_used": convergence_data.get('pulse_patterns_used', []),
            "stored_at": datetime.now(),
            "version": self.version
        }
        
        self.convergence_patterns.append(pattern_entry)
        
        # 保持模式庫大小
        if len(self.convergence_patterns) > 200:
            self.convergence_patterns = self.convergence_patterns[-150:]  # 保留最近 150 個
        
        self.logger.debug("收斂模式存儲完成")
    
    def retrieve_session_memory(self, session_id: str) -> Optional[Dict[str, Any]]:
        """檢索會話記憶 v1.0"""
        if session_id in self.session_memories:
            memory = self.session_memories[session_id]
            
            # 更新訪問記錄
            memory["access_count"] += 1
            memory["last_accessed"] = datetime.now()
            
            self.logger.debug(f"檢索會話記憶: {session_id}")
            return memory["session_data"]
        
        return None
    
    def retrieve_reasoning_trace(self, session_id: str) -> Optional[Dict[str, Any]]:
        """檢索推理軌跡 v1.0"""
        if session_id in self.reasoning_traces:
            trace = self.reasoning_traces[session_id]
            self.logger.debug(f"檢索推理軌跡: {session_id} - {len(trace['traces'])} 個步驟")
            return trace
        
        return None
    
    def analyze_reasoning_patterns_v1(self, session_ids: List[str] = None) -> Dict[str, Any]:
        """分析推理模式 v1.0"""
        self.logger.info("分析推理模式 v1.0")
        
        # 確定分析範圍
        if session_ids:
            traces_to_analyze = {sid: trace for sid, trace in self.reasoning_traces.items() if sid in session_ids}
        else:
            # 分析最近的軌跡
            recent_traces = self._get_recent_traces(days=7)
            traces_to_analyze = recent_traces
        
        if not traces_to_analyze:
            return {"analysis": "no_data", "patterns": []}
        
        # 模式分析
        patterns_analysis = {
            "step_performance_patterns": self._analyze_step_performance(traces_to_analyze),
            "convergence_patterns": self._analyze_convergence_behaviors(traces_to_analyze),
            "pulse_integration_patterns": self._analyze_pulse_patterns_v1(traces_to_analyze),  # v1.0
            "failure_patterns": self._analyze_failure_patterns(traces_to_analyze),
            "efficiency_patterns": self._analyze_efficiency_patterns(traces_to_analyze),
            "temporal_patterns": self._analyze_temporal_patterns(traces_to_analyze)
        }
        
        # 生成洞察
        insights = self._generate_pattern_insights_v1(patterns_analysis)
        
        # 生成建議
        recommendations = self._generate_pattern_recommendations_v1(patterns_analysis, insights)
        
        return {
            "analysis_scope": {
                "sessions_analyzed": len(traces_to_analyze),
                "analysis_period": "recent" if not session_ids else "specified",
                "version": self.version
            },
            "patterns_analysis": patterns_analysis,
            "insights": insights,
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def find_similar_contexts_v1(self, current_context: Dict[str, Any], 
                                similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """尋找相似上下文 v1.0"""
        self.logger.debug(f"尋找相似上下文 - 閾值: {similarity_threshold}")
        
        similar_contexts = []
        
        for session_id, memory in self.session_memories.items():
            session_data = memory["session_data"]
            
            # 計算上下文相似度
            similarity = self._calculate_context_similarity_v1(current_context, session_data)
            
            if similarity >= similarity_threshold:
                similar_contexts.append({
                    "session_id": session_id,
                    "similarity": similarity,
                    "context_data": session_data,
                    "memory_metadata": {
                        "stored_at": memory["stored_at"].isoformat(),
                        "access_count": memory["access_count"]
                    }
                })
        
        # 按相似度排序
        similar_contexts.sort(key=lambda x: x["similarity"], reverse=True)
        
        self.logger.debug(f"找到 {len(similar_contexts)} 個相似上下文")
        
        return similar_contexts[:10]  # 返回前10個最相似的
    
    def get_convergence_recommendations_v1(self, current_session_context: Dict[str, Any]) -> Dict[str, Any]:
        """獲取收斂建議 v1.0"""
        self.logger.debug("生成收斂建議 v1.0")
        
        # 分析歷史收斂模式
        successful_patterns = [p for p in self.convergence_patterns 
                              if p["convergence_data"].get("successful", False)]
        
        if not successful_patterns:
            return {
                "recommendations": ["採用標準螺旋推理流程"],
                "confidence": 0.5,
                "basis": "no_historical_data"
            }
        
        # 尋找最相似的成功模式
        most_similar_pattern = None
        highest_similarity = 0.0
        
        for pattern in successful_patterns:
            # 簡化的相似度計算
            pattern_context = pattern.get("convergence_data", {})
            similarity = self._calculate_pattern_similarity(current_session_context, pattern_context)
            
            if similarity > highest_similarity:
                highest_similarity = similarity
                most_similar_pattern = pattern
        
        recommendations = []
        
        if most_similar_pattern and highest_similarity > 0.6:
            # 基於相似成功案例的建議
            pattern_data = most_similar_pattern["convergence_data"]
            recommendations.extend([
                f"預期需要 {most_similar_pattern['rounds_to_convergence']} 輪推理",
                "關注成功因素: " + ", ".join(most_similar_pattern["success_factors"][:2])
            ])
            
            # v1.0 脈診特定建議
            pulse_contrib = most_similar_pattern.get("pulse_contribution", 0.0)
            if pulse_contrib > 0.5:
                recommendations.append("重視脈診整合，歷史上對收斂有積極影響")
                pulse_patterns = most_similar_pattern.get("pulse_patterns_used", [])
                if pulse_patterns:
                    recommendations.append(f"建議重點關注: {', '.join(pulse_patterns[:2])}")
        
        else:
            # 一般性建議
            avg_rounds = sum(p["rounds_to_convergence"] for p in successful_patterns) / len(successful_patterns)
            recommendations.append(f"根據歷史平均，預期需要 {avg_rounds:.1f} 輪推理")
        
        return {
            "recommendations": recommendations,
            "confidence": highest_similarity if most_similar_pattern else 0.3,
            "basis": f"基於 {len(successful_patterns)} 個歷史成功模式",
            "similar_pattern_id": most_similar_pattern["session_id"] if most_similar_pattern else None,
            "version": self.version
        }
    
    # 記憶管理和分析輔助方法
    def _manage_memory_capacity(self):
        """管理記憶容量"""
        if len(self.session_memories) > self.max_session_memory:
            # 按最後訪問時間排序，移除最舊的
            sorted_memories = sorted(
                self.session_memories.items(),
                key=lambda x: x[1]["last_accessed"]
            )
            
            # 移除最舊的 20%
            remove_count = int(len(sorted_memories) * 0.2)
            for session_id, _ in sorted_memories[:remove_count]:
                del self.session_memories[session_id]
                
            self.logger.debug(f"記憶容量管理：移除 {remove_count} 個舊記憶")
    
    def _compress_reasoning_traces(self, session_id: str):
        """壓縮推理軌跡"""
        if session_id not in self.reasoning_traces:
            return
        
        traces = self.reasoning_traces[session_id]["traces"]
        
        # 保留關鍵軌跡點（開始、結束、轉折點）
        key_traces = []
        
        if traces:
            key_traces.append(traces[0])  # 開始
            
            # 找轉折點（成功/失敗變化）
            for i in range(1, len(traces) - 1):
                if traces[i]["step_success"] != traces[i-1]["step_success"]:
                    key_traces.append(traces[i])
            
            if len(traces) > 1:
                key_traces.append(traces[-1])  # 結束
        
        # 更新壓縮後的軌跡
        self.reasoning_traces[session_id]["traces"] = key_traces
        self.reasoning_traces[session_id]["compressed"] = True
        self.reasoning_traces[session_id]["original_length"] = len(traces)
        
        self.logger.debug(f"推理軌跡壓縮：{len(traces)} -> {len(key_traces)}")
    
    def _get_recent_traces(self, days: int = 7) -> Dict[str, Any]:
        """獲取最近的軌跡"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        recent_traces = {
            sid: trace for sid, trace in self.reasoning_traces.items()
            if trace["updated_at"] > cutoff_time
        }
        
        return recent_traces
    
    def _calculate_context_similarity_v1(self, context1: Dict[str, Any], 
                                        context2: Dict[str, Any]) -> float:
        """計算上下文相似度 v1.0"""
        similarity_factors = []
        
        # 患者特徵相似度
        if context1.get("patient_profile") and context2.get("patient_profile"):
            p1, p2 = context1["patient_profile"], context2["patient_profile"]
            
            # 年齡相似度
            age1, age2 = p1.get("age"), p2.get("age")
            if age1 and age2:
                try:
                    age_diff = abs(int(age1) - int(age2))
                    age_similarity = max(0, 1 - age_diff / 50.0)  # 50歲差距為0相似度
                    similarity_factors.append(age_similarity)
                except:
                    pass
            
            # 性別匹配
            if p1.get("gender") == p2.get("gender"):
                similarity_factors.append(1.0)
            else:
                similarity_factors.append(0.0)
        
        # 症狀相似度
        symptoms1 = context1.get("symptoms", "")
        symptoms2 = context2.get("symptoms", "")
        if symptoms1 and symptoms2:
            # 簡單詞彙重疊計算
            words1 = set(symptoms1.split())
            words2 = set(symptoms2.split())
            if words1 and words2:
                overlap = len(words1 & words2) / len(words1 | words2)
                similarity_factors.append(overlap)
        
        # v1.0 脈診相似度
        pulse1 = context1.get("pulse_info", "")
        pulse2 = context2.get("pulse_info", "")
        if pulse1 and pulse2:
            pulse_words1 = set(pulse1.split())
            pulse_words2 = set(pulse2.split())
            if pulse_words1 and pulse_words2:
                pulse_overlap = len(pulse_words1 & pulse_words2) / len(pulse_words1 | pulse_words2)
                similarity_factors.append(pulse_overlap)
        
        # 計算綜合相似度
        if similarity_factors:
            return sum(similarity_factors) / len(similarity_factors)
        else:
            return 0.0
    
    def _analyze_step_performance(self, traces: Dict[str, Any]) -> Dict[str, Any]:
        """分析步驟表現"""
        step_stats = {1: [], 2: [], 3: [], 4: []}
        
        for session_id, trace_data in traces.items():
            for trace in trace_data["traces"]:
                step_num = trace["step_number"]
                if step_num in step_stats:
                    step_stats[step_num].append({
                        "success": trace["step_success"],
                        "confidence": trace["step_confidence"],
                        "duration": trace["step_duration"]
                    })
        
        # 計算每個步驟的統計
        step_analysis = {}
        for step_num, stats in step_stats.items():
            if stats:
                success_rate = sum(1 for s in stats if s["success"]) / len(stats)
                avg_confidence = sum(s["confidence"] for s in stats) / len(stats)
                avg_duration = sum(s["duration"] for s in stats) / len(stats)
                
                step_analysis[f"step_{step_num}"] = {
                    "success_rate": success_rate,
                    "average_confidence": avg_confidence,
                    "average_duration": avg_duration,
                    "total_executions": len(stats)
                }
        
        return step_analysis
    
    def _analyze_pulse_patterns_v1(self, traces: Dict[str, Any]) -> Dict[str, Any]:
        """分析脈診模式 v1.0"""
        pulse_usage = {"total_sessions": 0, "sessions_with_pulse": 0, "pulse_effectiveness": []}
        
        for session_id, trace_data in traces.items():
            pulse_usage["total_sessions"] += 1
            session_has_pulse = False
            session_pulse_scores = []
            
            for trace in trace_data["traces"]:
                pulse_info = trace.get("pulse_integration", {})
                if pulse_info.get("pulse_support_count", 0) > 0:
                    session_has_pulse = True
                    pulse_consistency = pulse_info.get("pulse_consistency", 0.0)
                    session_pulse_scores.append(pulse_consistency)
            
            if session_has_pulse:
                pulse_usage["sessions_with_pulse"] += 1
                if session_pulse_scores:
                    avg_session_pulse = sum(session_pulse_scores) / len(session_pulse_scores)
                    pulse_usage["pulse_effectiveness"].append(avg_session_pulse)
        
        # 計算統計
        pulse_usage_rate = pulse_usage["sessions_with_pulse"] / pulse_usage["total_sessions"] if pulse_usage["total_sessions"] > 0 else 0
        avg_effectiveness = sum(pulse_usage["pulse_effectiveness"]) / len(pulse_usage["pulse_effectiveness"]) if pulse_usage["pulse_effectiveness"] else 0
        
        return {
            "pulse_usage_rate": pulse_usage_rate,
            "average_pulse_effectiveness": avg_effectiveness,
            "sessions_analyzed": pulse_usage["total_sessions"],
            "sessions_with_pulse": pulse_usage["sessions_with_pulse"],
            "effectiveness_distribution": pulse_usage["pulse_effectiveness"]
        }
    
    def _analyze_convergence_behaviors(self, traces: Dict[str, Any]) -> Dict[str, Any]:
        """分析收斂行為"""
        convergence_data = []
        
        for session_id, trace_data in traces.items():
            total_steps = len(trace_data["traces"])
            if total_steps > 0:
                final_confidence = trace_data["traces"][-1].get("step_confidence", 0.0)
                session_success = trace_data["traces"][-1].get("step_success", False)
                
                convergence_data.append({
                    "total_steps": total_steps,
                    "final_confidence": final_confidence,
                    "converged": session_success and final_confidence > 0.7
                })
        
        if convergence_data:
            convergence_rate = sum(1 for c in convergence_data if c["converged"]) / len(convergence_data)
            avg_steps = sum(c["total_steps"] for c in convergence_data) / len(convergence_data)
            avg_final_confidence = sum(c["final_confidence"] for c in convergence_data) / len(convergence_data)
            
            return {
                "convergence_rate": convergence_rate,
                "average_steps_to_completion": avg_steps,
                "average_final_confidence": avg_final_confidence,
                "total_sessions": len(convergence_data)
            }
        
        return {"convergence_rate": 0.0, "total_sessions": 0}
    
    def _analyze_failure_patterns(self, traces: Dict[str, Any]) -> Dict[str, Any]:
        """分析失敗模式"""
        failure_points = {1: 0, 2: 0, 3: 0, 4: 0}
        total_failures = 0
        
        for session_id, trace_data in traces.items():
            for trace in trace_data["traces"]:
                if not trace["step_success"]:
                    step_num = trace["step_number"]
                    if step_num in failure_points:
                        failure_points[step_num] += 1
                        total_failures += 1
        
        return {
            "failure_distribution": failure_points,
            "total_failures": total_failures,
            "most_problematic_step": max(failure_points, key=failure_points.get) if total_failures > 0 else None
        }
    
    def _analyze_efficiency_patterns(self, traces: Dict[str, Any]) -> Dict[str, Any]:
        """分析效率模式"""
        session_durations = []
        step_durations = {1: [], 2: [], 3: [], 4: []}
        
        for session_id, trace_data in traces.items():
            session_total = sum(trace["step_duration"] for trace in trace_data["traces"])
            session_durations.append(session_total)
            
            for trace in trace_data["traces"]:
                step_num = trace["step_number"]
                if step_num in step_durations:
                    step_durations[step_num].append(trace["step_duration"])
        
        avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0
        
        avg_step_durations = {}
        for step_num, durations in step_durations.items():
            avg_step_durations[f"step_{step_num}"] = sum(durations) / len(durations) if durations else 0
        
        return {
            "average_session_duration": avg_session_duration,
            "average_step_durations": avg_step_durations,
            "sessions_analyzed": len(session_durations)
        }
    
    def _analyze_temporal_patterns(self, traces: Dict[str, Any]) -> Dict[str, Any]:
        """分析時間模式"""
        # 簡化實現：分析一天中的使用模式
        hourly_usage = {str(i): 0 for i in range(24)}
        
        for session_id, trace_data in traces.items():
            if trace_data["traces"]:
                first_trace_time = trace_data["traces"][0]["timestamp"]
                hour = first_trace_time.hour
                hourly_usage[str(hour)] += 1
        
        peak_hour = max(hourly_usage, key=hourly_usage.get)
        
        return {
            "hourly_usage_distribution": hourly_usage,
            "peak_usage_hour": peak_hour,
            "analysis_note": "基於會話開始時間的小時分佈"
        }
    
    def _generate_pattern_insights_v1(self, patterns: Dict[str, Any]) -> List[str]:
        """生成模式洞察 v1.0"""
        insights = []
        
        # 步驟表現洞察
        step_perf = patterns.get("step_performance_patterns", {})
        if step_perf:
            weakest_step = min(step_perf.items(), key=lambda x: x[1].get("success_rate", 1))
            insights.append(f"{weakest_step[0]} 是表現最弱的步驟，成功率僅 {weakest_step[1]['success_rate']:.1%}")
        
        # v1.0 脈診洞察
        pulse_patterns = patterns.get("pulse_integration_patterns", {})
        if pulse_patterns.get("pulse_usage_rate", 0) > 0:
            usage_rate = pulse_patterns["pulse_usage_rate"]
            effectiveness = pulse_patterns["average_pulse_effectiveness"]
            insights.append(f"脈診使用率 {usage_rate:.1%}，平均效果 {effectiveness:.1%}")
        
        # 收斂洞察
        convergence = patterns.get("convergence_patterns", {})
        if convergence.get("total_sessions", 0) > 0:
            conv_rate = convergence["convergence_rate"]
            avg_steps = convergence["average_steps_to_completion"]
            insights.append(f"收斂率 {conv_rate:.1%}，平均需要 {avg_steps:.1f} 個步驟")
        
        return insights
    
    def _generate_pattern_recommendations_v1(self, patterns: Dict[str, Any], 
                                           insights: List[str]) -> List[str]:
        """生成模式建議 v1.0"""
        recommendations = []
        
        # 基於失敗模式的建議
        failure_patterns = patterns.get("failure_patterns", {})
        most_problematic = failure_patterns.get("most_problematic_step")
        if most_problematic:
            recommendations.append(f"重點優化 step_{most_problematic} 的處理邏輯")
        
        # v1.0 基於脈診模式的建議
        pulse_patterns = patterns.get("pulse_integration_patterns", {})
        if pulse_patterns.get("pulse_usage_rate", 0) < 0.5:
            recommendations.append("建議增加脈診資訊收集以提升診療精確度")
        elif pulse_patterns.get("average_pulse_effectiveness", 0) < 0.6:
            recommendations.append("脈診知識匹配算法需要改進")
        
        # 基於效率模式的建議
        efficiency = patterns.get("efficiency_patterns", {})
        if efficiency.get("average_session_duration", 0) > 300:  # 5分鐘
            recommendations.append("考慮優化推理效率，縮短處理時間")
        
        return recommendations
    
    def _calculate_pattern_similarity(self, context1: Dict[str, Any], context2: Dict[str, Any]) -> float:
        """計算模式相似度"""
        # 簡化實現
        similarity_score = 0.5  # 基礎相似度
        
        # 比較關鍵特徵
        if context1.get("main_symptoms") and context2.get("main_symptoms"):
            # 簡單文字相似度
            words1 = set(str(context1["main_symptoms"]).split())
            words2 = set(str(context2["main_symptoms"]).split())
            if words1 and words2:
                word_similarity = len(words1 & words2) / len(words1 | words2)
                similarity_score = (similarity_score + word_similarity) / 2
        
        return similarity_score
    
    def cleanup_expired_memories(self):
        """清理過期記憶"""
        cutoff_time = datetime.now() - timedelta(days=self.memory_retention_days)
        
        # 清理會話記憶
        expired_sessions = [
            sid for sid, memory in self.session_memories.items()
            if memory["stored_at"] < cutoff_time
        ]
        
        for session_id in expired_sessions:
            del self.session_memories[session_id]
        
        # 清理推理軌跡
        expired_traces = [
            sid for sid, trace in self.reasoning_traces.items()
            if trace["created_at"] < cutoff_time
        ]
        
        for session_id in expired_traces:
            del self.reasoning_traces[session_id]
        
        # 清理收斂模式
        self.convergence_patterns = [
            pattern for pattern in self.convergence_patterns
            if pattern["stored_at"] > cutoff_time
        ]
        
        if expired_sessions or expired_traces:
            self.logger.info(f"清理過期記憶: {len(expired_sessions)} 會話, {len(expired_traces)} 軌跡")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """獲取記憶庫統計 v1.0"""
        return {
            "session_memories": len(self.session_memories),
            "reasoning_traces": len(self.reasoning_traces),
            "convergence_patterns": len(self.convergence_patterns),
            "context_cache": len(self.context_cache),
            "memory_retention_days": self.memory_retention_days,
            "version": self.version,
            "last_cleanup": getattr(self, '_last_cleanup', 'never'),
            "capacity_utilization": {
                "session_memory": f"{len(self.session_memories)}/{self.max_session_memory}",
                "trace_compression_threshold": self.trace_compression_threshold
            }
        }
