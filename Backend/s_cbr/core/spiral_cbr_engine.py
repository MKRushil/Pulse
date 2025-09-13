"""
螺旋CBR推理核心引擎 v1.0

v1.0 更新：
- 整合 Case 和 PulsePJ 知識庫
- 完整四步驟螺旋推理
- 增強錯誤處理和日誌

版本：v1.0
"""

from typing import Dict, Any, List
import asyncio
from datetime import datetime

from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.steps.step1_case_finder import Step1CaseFinder
from s_cbr.steps.step2_case_adapter import Step2CaseAdapter  
from s_cbr.steps.step3_monitor import Step3Monitor
from s_cbr.steps.step4_feedback import Step4Feedback
from s_cbr.core.agentive_coordinator import AgentiveCoordinator
from s_cbr.dialog.dialog_manager import DialogManager
from s_cbr.models.spiral_case import SpiralState
from s_cbr.utils.spiral_logger import SpiralLogger

class SpiralCBREngine:
    """
    螺旋CBR推理核心引擎 v1.0
    
    v1.0 特色：
    - 完整實現 Spiral CBR-V2 四步驟
    - 整合現有 Case 和 PulsePJ 知識庫
    - Agentive AI 多智能體協作
    - 自適應收斂控制
    """
    
    def __init__(self):
        """初始化螺旋CBR推理引擎 v1.0"""
        self.config = SCBRConfig()
        self.logger = SpiralLogger.get_logger("SpiralCBREngine")
        self.version = "1.0"
        
        # 初始化四個推理步驟
        self.step1_finder = Step1CaseFinder()
        self.step2_adapter = Step2CaseAdapter()
        self.step3_monitor = Step3Monitor()
        self.step4_feedback = Step4Feedback()
        
        # 初始化協調組件
        self.agentive_coordinator = AgentiveCoordinator()
        self.dialog_manager = DialogManager()
        
        # 螺旋推理狀態
        self.current_session_id = None
        self.spiral_state = None
        
        self.logger.info(f"螺旋CBR推理引擎 v{self.version} 初始化完成")
    
    async def start_spiral_dialog(self, initial_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        啟動螺旋對話推理主流程 v1.0
        
        v1.0 完整流程：
        1. 初始化螺旋狀態
        2. 啟動 Agentive AI 上下文
        3. 執行四步驟螺旋循環
        4. 生成最終結果報告
        """
        # 會話初始化
        self.current_session_id = f"spiral_v1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger.info(f"啟動螺旋對話推理 v1.0 - 會話ID: {self.current_session_id}")
        
        try:
            # Step 0: 初始化推理狀態
            self.spiral_state = self._initialize_spiral_state_v1(initial_query)
            agentive_context = await self.agentive_coordinator.initialize_context(
                initial_query, self.current_session_id
            )
            
            # 執行螺旋推理主循環
            spiral_result = await self._execute_spiral_loop_v1(agentive_context)
            
            # 生成最終結果報告
            final_result = self._generate_final_report_v1(spiral_result)
            
            self.logger.info(f"螺旋推理 v1.0 完成 - 會話ID: {self.current_session_id}")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"螺旋推理 v1.0 異常 - 會話ID: {self.current_session_id}, 錯誤: {str(e)}")
            return self._create_error_result_v1(str(e))
    
    def _initialize_spiral_state_v1(self, query: Dict[str, Any]) -> SpiralState:
        """初始化螺旋推理狀態 v1.0"""
        state = SpiralState(
            session_id=self.current_session_id,
            initial_query=query,
            max_iterations=self.config.SPIRAL_SETTINGS['max_spiral_iterations'],
            similarity_threshold=self.config.SPIRAL_SETTINGS['similarity_threshold'],
            version="1.0"  # v1.0 版本標識
        )
        
        self.logger.debug(f"螺旋狀態 v1.0 初始化完成")
        return state
    
    async def _execute_spiral_loop_v1(self, agentive_context: Dict[str, Any]) -> Dict[str, Any]:
        """執行螺旋推理主循環 v1.0"""
        
        while not self._should_terminate_spiral_v1():
            current_round = self.spiral_state.current_round + 1
            self.logger.info(f"=== 螺旋推理 v1.0 第 {current_round} 輪開始 ===")
            
            round_start_time = datetime.now()
            
            try:
                # STEP 1: 尋找高相關案例（整合 Case + PulsePJ）
                step1_result = await self._execute_step1_v1(agentive_context)
                
                if not step1_result.get('found_case'):
                    self.logger.warning(f"第 {current_round} 輪未找到合適案例")
                    # v1.0 備選策略
                    step1_result = await self._execute_step1_fallback_v1(agentive_context)
                
                # STEP 2: 案例適配與協商
                step2_result = await self._execute_step2_v1(step1_result, agentive_context)
                
                # STEP 3: 方案監控驗證
                step3_result = await self._execute_step3_v1(step2_result, agentive_context)
                
                # STEP 4: 用戶回饋處理
                step4_result = await self._execute_step4_v1(step3_result, agentive_context)
                
                # v1.0 評估本輪結果
                round_evaluation = self._evaluate_round_result_v1(step4_result)
                
                # 更新螺旋狀態
                self.spiral_state.add_round_result({
                    'round': current_round,
                    'step1_result': step1_result,
                    'step2_result': step2_result, 
                    'step3_result': step3_result,
                    'step4_result': step4_result,
                    'evaluation': round_evaluation,
                    'duration': (datetime.now() - round_start_time).total_seconds(),
                    'version': self.version
                })
                
                # 判斷是否收斂
                if round_evaluation.get('converged', False):
                    self.logger.info(f"螺旋推理 v1.0 收斂 - 第 {current_round} 輪")
                    return self._create_converged_result_v1(step4_result)
                
                # 更新 Agentive 上下文
                agentive_context = await self.agentive_coordinator.update_context(
                    agentive_context, step4_result
                )
                
                self.spiral_state.current_round = current_round
                
            except Exception as e:
                self.logger.error(f"第 {current_round} 輪推理異常: {str(e)}")
                self.spiral_state.add_error_round(current_round, str(e))
                
                if self.spiral_state.consecutive_errors >= 2:
                    break
        
        return self._create_timeout_result_v1()
    
    async def _execute_step1_v1(self, agentive_context: Dict[str, Any]) -> Dict[str, Any]:
        """執行 STEP 1 v1.0 (整合 Case + PulsePJ)"""
        self.logger.debug("執行 STEP 1 v1.0: 尋找高相關案例")
        
        # Agentive AI 協助患者特徵分析
        patient_analysis = await self.agentive_coordinator.analyze_patient_features(
            self.spiral_state.current_symptoms,
            self.spiral_state.medical_history,
            agentive_context
        )
        
        # 執行案例搜尋（整合 Case 和 PulsePJ）
        search_result = await self.step1_finder.find_most_similar_case(
            patient_analysis,
            self.spiral_state.get_refined_criteria()
        )
        
        # 生成對話回應
        dialog_response = await self.dialog_manager.generate_step1_dialog(
            search_result, patient_analysis
        )
        
        result = {
            'step': 1,
            'patient_analysis': patient_analysis,
            'search_result': search_result,
            'found_case': search_result.get('best_match'),
            'similarity_score': search_result.get('similarity', 0.0),
            'pulse_support': search_result.get('pulse_support', []),  # v1.0 新增
            'dialog_response': dialog_response,
            'timestamp': datetime.now().isoformat(),
            'version': self.version
        }
        
        self.logger.debug(f"STEP 1 v1.0 完成 - 相似度: {result['similarity_score']:.3f}")
        return result
    
    async def _execute_step1_fallback_v1(self, agentive_context: Dict[str, Any]) -> Dict[str, Any]:
        """STEP 1 v1.0 備選策略"""
        self.logger.debug("執行 STEP 1 v1.0 備選策略")
        
        relaxed_criteria = self.spiral_state.get_relaxed_criteria()
        search_result = await self.step1_finder.find_with_relaxed_criteria(relaxed_criteria)
        
        return {
            'step': 1,
            'search_result': search_result,
            'found_case': search_result.get('best_match'),
            'similarity_score': search_result.get('similarity', 0.0),
            'fallback_used': True,
            'dialog_response': "已放寬搜索條件，找到可參考案例",
            'timestamp': datetime.now().isoformat(),
            'version': self.version
        }
    
    async def _execute_step2_v1(self, step1_result: Dict[str, Any], 
                               agentive_context: Dict[str, Any]) -> Dict[str, Any]:
        """執行 STEP 2 v1.0 (案例適配 + 脈診整合)"""
        self.logger.debug("執行 STEP 2 v1.0: 案例適配與協商")
        
        base_case = step1_result.get('found_case')
        patient_analysis = step1_result.get('patient_analysis', {})
        pulse_support = step1_result.get('pulse_support', [])  # v1.0 脈診支持
        
        # Agentive AI 制定適配策略（整合脈診）
        adaptation_strategy = await self.agentive_coordinator.plan_adaptation_v1(
            base_case, patient_analysis, pulse_support, agentive_context
        )
        
        # 執行案例適配
        adapted_solution = await self.step2_adapter.adapt_case_v1(
            base_case,
            patient_analysis,
            pulse_support,  # v1.0 新參數
            adaptation_strategy,
            self.config.ADAPTATION_WEIGHTS
        )
        
        # 協商對話
        negotiation_result = await self.dialog_manager.conduct_negotiation(
            adapted_solution, 
            self.spiral_state
        )
        
        result = {
            'step': 2,
            'base_case': base_case,
            'pulse_support': pulse_support,  # v1.0 新增
            'adaptation_strategy': adaptation_strategy,
            'adapted_solution': adapted_solution,
            'negotiation_result': negotiation_result,
            'confidence_score': adapted_solution.get('confidence', 0.0),
            'dialog_response': negotiation_result.get('dialog_text'),
            'timestamp': datetime.now().isoformat(),
            'version': self.version
        }
        
        return result
    
    async def _execute_step3_v1(self, step2_result: Dict[str, Any],
                               agentive_context: Dict[str, Any]) -> Dict[str, Any]:
        """執行 STEP 3 v1.0 (方案監控 + 脈診驗證)"""
        self.logger.debug("執行 STEP 3 v1.0: 方案監控驗證")
        
        adapted_solution = step2_result.get('adapted_solution')
        pulse_support = step2_result.get('pulse_support', [])
        
        # Agentive AI 制定監控計劃（包含脈診驗證）
        monitoring_plan = await self.agentive_coordinator.create_monitoring_plan_v1(
            adapted_solution, pulse_support, agentive_context
        )
        
        # 執行方案驗證
        validation_result = await self.step3_monitor.validate_solution_v1(
            adapted_solution,
            monitoring_plan,
            self.spiral_state.patient_profile,
            pulse_support  # v1.0 新參數
        )
        
        # 生成監控對話
        monitoring_dialog = await self.dialog_manager.generate_monitoring_dialog(
            validation_result, adapted_solution
        )
        
        result = {
            'step': 3,
            'adapted_solution': adapted_solution,
            'pulse_support': pulse_support,
            'monitoring_plan': monitoring_plan,
            'validation_result': validation_result,
            'safety_score': validation_result.get('safety_score', 0.0),
            'effectiveness_score': validation_result.get('effectiveness_score', 0.0),
            'pulse_consistency': validation_result.get('pulse_consistency', 0.0),  # v1.0 新增
            'dialog_response': monitoring_dialog,
            'timestamp': datetime.now().isoformat(),
            'version': self.version
        }
        
        return result
    
    async def _execute_step4_v1(self, step3_result: Dict[str, Any],
                               agentive_context: Dict[str, Any]) -> Dict[str, Any]:
        """執行 STEP 4 v1.0 (回饋處理 + 知識更新)"""
        self.logger.debug("執行 STEP 4 v1.0: 用戶回饋處理")
        
        validation_result = step3_result.get('validation_result')
        adapted_solution = step3_result.get('adapted_solution')
        pulse_support = step3_result.get('pulse_support', [])
        
        # 收集用戶回饋
        user_feedback = await self.dialog_manager.collect_user_feedback(
            adapted_solution, validation_result, self.spiral_state
        )
        
        # Agentive AI 分析回饋（包含脈診分析）
        feedback_analysis = await self.agentive_coordinator.analyze_feedback_v1(
            user_feedback, validation_result, pulse_support, agentive_context
        )
        
        # 處理回饋並更新知識庫
        knowledge_update = await self.step4_feedback.process_feedback_v1(
            user_feedback,
            feedback_analysis,
            adapted_solution,
            pulse_support,  # v1.0 新參數
            self.current_session_id
        )
        
        result = {
            'step': 4,
            'user_feedback': user_feedback,
            'feedback_analysis': feedback_analysis,
            'knowledge_update': knowledge_update,
            'treatment_effective': feedback_analysis.get('is_effective', False),
            'user_satisfaction': feedback_analysis.get('satisfaction_score', 0.0),
            'pulse_learning': knowledge_update.get('pulse_insights', []),  # v1.0 新增
            'dialog_response': knowledge_update.get('dialog_response'),
            'timestamp': datetime.now().isoformat(),
            'version': self.version
        }
        
        return result
    
    def _should_terminate_spiral_v1(self) -> bool:
        """判斷是否應該終止螺旋推理 v1.0"""
        if self.spiral_state.current_round >= self.spiral_state.max_iterations:
            return True
        
        if self.spiral_state.consecutive_errors >= 3:
            return True
            
        return False
    
    def _evaluate_round_result_v1(self, step4_result: Dict[str, Any]) -> Dict[str, Any]:
        """評估本輪推理結果 v1.0"""
        user_satisfaction = step4_result.get('user_satisfaction', 0.0)
        treatment_effective = step4_result.get('treatment_effective', False)
        pulse_learning = step4_result.get('pulse_learning', [])
        
        # v1.0 收斂判斷（增加脈診因子）
        converged = (
            user_satisfaction >= self.config.SPIRAL_SETTINGS['feedback_score_threshold'] and
            treatment_effective and
            len(pulse_learning) > 0  # v1.0: 需要有脈診學習
        )
        
        return {
            'converged': converged,
            'user_satisfaction': user_satisfaction,
            'treatment_effective': treatment_effective,
            'pulse_integration': len(pulse_learning),  # v1.0 新增
            'quality_score': self._calculate_quality_score_v1(step4_result),
            'version': self.version
        }
    
    def _calculate_quality_score_v1(self, step4_result: Dict[str, Any]) -> float:
        """計算整體質量分數 v1.0"""
        satisfaction = step4_result.get('user_satisfaction', 0.0)
        safety = step4_result.get('validation_result', {}).get('safety_score', 0.0)
        pulse_consistency = step4_result.get('validation_result', {}).get('pulse_consistency', 0.0)
        
        # v1.0 質量算法（增加脈診一致性權重）
        quality_score = (
            satisfaction * 0.35 +
            safety * 0.25 +
            pulse_consistency * 0.25 +  # v1.0 新增脈診權重
            0.5 * 0.15  # 基礎創新分
        )
        
        return min(quality_score, 1.0)
    
    def _create_converged_result_v1(self, final_step_result: Dict[str, Any]) -> Dict[str, Any]:
        """創建收斂結果 v1.0"""
        return {
            'success': True,
            'converged': True,
            'version': self.version,
            'spiral_rounds': self.spiral_state.current_round,
            'final_solution': final_step_result.get('adapted_solution'),
            'pulse_insights': final_step_result.get('pulse_learning', []),  # v1.0 新增
            'effectiveness_score': final_step_result.get('user_satisfaction', 0.0),
            'knowledge_updated': final_step_result.get('knowledge_update', {}).get('updated', False),
            'session_id': self.current_session_id
        }
    
    def _create_timeout_result_v1(self) -> Dict[str, Any]:
        """創建超時結果 v1.0"""
        return {
            'success': False,
            'converged': False,
            'timeout': True,
            'version': self.version,
            'spiral_rounds': self.spiral_state.current_round,
            'message': f'S-CBR v1.0 經過 {self.spiral_state.current_round} 輪推理未完全收斂',
            'session_id': self.current_session_id
        }
    
    def _create_error_result_v1(self, error_message: str) -> Dict[str, Any]:
        """創建錯誤結果 v1.0"""
        return {
            'success': False,
            'error': True,
            'version': self.version,
            'error_message': error_message,
            'message': 'S-CBR v1.0 系統發生異常',
            'session_id': self.current_session_id
        }
    
    def _generate_final_report_v1(self, spiral_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成最終推理報告 v1.0"""
        report = spiral_result.copy()
        
        # v1.0 會話統計
        report['session_stats'] = {
            'version': self.version,
            'session_id': self.current_session_id,
            'total_rounds': self.spiral_state.current_round,
            'convergence_achieved': spiral_result.get('converged', False),
            'knowledge_bases_used': ['Case', 'PulsePJ']  # v1.0 使用的知識庫
        }
        
        return report
