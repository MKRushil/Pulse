#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCBR Agentic NLU 決策邏輯驗證測試框架
Phase 1.5 系統測試與驗證

版本: v1.0
日期: 2025-11-24
位置: s_cbr/debug/agentic_test_runner.py

測試目標：
1. L1 Agentic Gate 決策邏輯驗證
   - Alpha 值選擇是否符合輸入特性
   - 置信度評估是否合理
   - 追問決策是否適當

2. L2 Agentic 診斷層工具調用驗證
   - 工具調用時機是否正確
   - 工具選擇是否符合邏輯
   - 結果整合是否有效

3. 檢索品質與 Fallback 機制驗證
   - 品質評估是否準確
   - Fallback 觸發是否及時
   - 重試策略是否有效

測試指標：
- 決策邏輯符合率（Logic Compliance Rate）
- 工具調用準確率（Tool Call Accuracy）
- 檢索品質穩定性（Retrieval Quality Stability）
"""

import os
import sys
import json
import yaml
import time
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import statistics

# ============================================
# 測試配置
# ============================================

class TestConfig:
    """測試配置管理類"""
    
    # API 端點配置
    API_BASE_URL = os.environ.get('SCBR_API_URL', 'http://localhost:8000')
    API_HEALTH_ENDPOINT = '/healthz'
    API_DIAGNOSE_ENDPOINT = '/api/scbr/v2/diagnose'
    
    # 檔案路徑配置（相對於 s_cbr/debug 目錄）
    TEST_CASES_FILE = 'agentic_test_cases.yaml'
    REPORT_DIR = 'test_results/reports'
    LOG_DIR = 'test_results/logs'
    
    # 測試行為配置
    ENABLE_DEBUG = os.environ.get('SCBR_DEBUG', 'false').lower() == 'true'
    MAX_ROUNDS_PER_CASE = 7
    REQUEST_TIMEOUT = 240
    ROUND_INTERVAL = 0.5
    CASE_INTERVAL = 1.0
    
    # Agentic 決策邏輯評估標準
    ALPHA_LOW_THRESHOLD = 0.4      # 關鍵字為主策略的 alpha 上限
    ALPHA_HIGH_THRESHOLD = 0.6     # 向量為主策略的 alpha 下限
    CONFIDENCE_LOW_THRESHOLD = 0.55  # 需要追問的置信度門檻
    QUALITY_ACCEPTABLE = 0.65      # 可接受的檢索品質門檻
    
    # 工具調用評估標準
    KNOWLEDGE_GAP_THRESHOLD = 0.6   # 案例完整度門檻
    VALIDATION_THRESHOLD = 0.7      # 診斷置信度門檻
    
    @staticmethod
    def ensure_dirs():
        """確保必要的目錄存在"""
        os.makedirs(TestConfig.REPORT_DIR, exist_ok=True)
        os.makedirs(TestConfig.LOG_DIR, exist_ok=True)


# ============================================
# 測試結果數據結構
# ============================================

class AgenticDecisionMetrics:
    """Agentic 決策邏輯評估指標集合"""
    
    def __init__(self):
        # L1 決策指標
        self.alpha_decisions = []
        self.confidence_scores = []
        self.strategy_types = []
        self.follow_up_triggered = 0
        self.search_triggered = 0
        
        # L2 工具調用指標
        self.tool_a_calls = 0
        self.tool_b_calls = 0
        self.tool_c_calls = 0
        self.total_tool_calls = 0
        self.validation_status_counts = defaultdict(int)
        self.case_completeness_scores = []
        self.diagnosis_confidence_scores = []
        
        # 檢索品質指標
        self.quality_scores = []
        self.fallback_triggered = 0
        self.fallback_attempts = []
        self.alpha_adjustments = []
        
        # 決策邏輯符合度評估
        self.logic_checks = {
            'alpha_selection': [],
            'confidence_action': [],
            'tool_decision': [],
            'retrieval_quality': []
        }
        
        # 安全測試指標
        self.security_blocks = 0
        self.security_passed = 0


class TestCaseResult:
    """單一測試案例的結果記錄"""
    
    def __init__(self, case_id: str, case_name: str, case_type: str):
        self.case_id = case_id
        self.case_name = case_name
        self.case_type = case_type
        self.description = ""
        self.rounds = []
        self.success = False
        self.error_message = None
        self.total_time = 0
        self.metrics = AgenticDecisionMetrics()


class RoundResult:
    """單輪測試結果詳細記錄"""
    
    def __init__(self, round_num: int, question: str):
        self.round_num = round_num
        self.question = question  # 單輪問題（向後兼容）
        self.accumulated_question = question  # 🆕 累積後的完整問題
        self.original_question = question     # 🆕 原始單輪問題
        self.response = None
        self.response_time = 0
        self.http_status = None
        
        # L1 決策資訊
        self.l1_overall_confidence = None
        self.l1_decided_alpha = None
        self.l1_strategy_type = None
        self.l1_next_action = None
        self.l1_expected_quality = None
        
        # L2 Agentic 資訊
        self.l2_case_completeness = None
        self.l2_diagnosis_confidence = None
        self.l2_validation_status = None
        self.l2_tool_calls = 0
        self.l2_confidence_boost = 0
        
        # 檢索資訊
        self.retrieval_initial_alpha = None
        self.retrieval_final_alpha = None
        self.retrieval_quality_score = None
        self.retrieval_fallback_triggered = False
        self.retrieval_attempts = 0
        
        # 安全資訊
        self.security_blocked = False
        self.security_flags = []
        
        # 決策邏輯評估結果
        self.logic_evaluations = {}


# ============================================
# JSONL 日誌記錄器
# ============================================

class JSONLLogger:
    """JSONL 格式日誌記錄器，用於詳細的測試數據追蹤"""
    
    def __init__(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.detail_log = os.path.join(
            TestConfig.LOG_DIR,
            f'test_details_{timestamp}.jsonl'
        )
        self.decision_log = os.path.join(
            TestConfig.LOG_DIR,
            f'agentic_decisions_{timestamp}.jsonl'
        )
        self.evaluation_log = os.path.join(
            TestConfig.LOG_DIR,
            f'logic_evaluations_{timestamp}.jsonl'
        )
        
    def log_test_detail(self, data: Dict):
        """記錄測試執行詳細資訊"""
        self._append_to_file(self.detail_log, data)
    
    def log_decision(self, data: Dict):
        """記錄 Agentic 決策資訊"""
        self._append_to_file(self.decision_log, data)
    
    def log_evaluation(self, data: Dict):
        """記錄邏輯評估結果"""
        self._append_to_file(self.evaluation_log, data)
    
    def _append_to_file(self, filepath: str, data: Dict):
        """追加 JSONL 記錄到檔案"""
        try:
            data['timestamp'] = datetime.now().isoformat()
            with open(filepath, 'a', encoding='utf-8') as f:
                json_line = json.dumps(data, ensure_ascii=False)
                f.write(json_line + '\n')
        except Exception as e:
            print(f"⚠️  寫入日誌失敗 {filepath}: {e}")


# ============================================
# 決策邏輯評估器
# ============================================

class DecisionLogicEvaluator:
    """
    Agentic 決策邏輯評估器
    
    職責：
    1. 評估 L1 的 alpha 值選擇是否合理
    2. 評估 L1 的置信度評估與動作決策是否正確
    3. 評估 L2 的工具調用決策是否符合邏輯
    4. 評估檢索品質與 Fallback 機制是否有效
    """
    
    @staticmethod
    def evaluate_l1_alpha_selection(
        input_text: str,
        decided_alpha: float,
        strategy_type: str,
        case_type: str
    ) -> Dict[str, Any]:
        """
        評估 L1 的 alpha 值選擇邏輯
        
        評估標準：
        - l1_terminology: 標準術語輸入 → 應選擇低 alpha（≤0.4）
        - l1_oral: 口語化描述 → 應選擇高 alpha（≥0.6）
        - l1_insufficient: 資訊不足 → alpha 值次要，重點是追問
        """
        evaluation = {
            'case_type': case_type,
            'input_style': None,
            'input_length': len(input_text),
            'decided_alpha': decided_alpha,
            'strategy_type': strategy_type,
            'expected_alpha_range': None,
            'is_compliant': False,
            'compliance_score': 0.0,
            'reasoning': '',
            'suggestions': []
        }
        
        # 基於測試案例類型的評估
        if case_type == 'l1_terminology':
            # 標準術語輸入
            tcm_terms = ['失眠', '心悸', '氣短', '乏力', '舌淡', '脈細', '舌紅', '苔黃',
                         '頭痛', '眩暈', '咳嗽', '痰多', '胸悶', '納差', '便溏', '胸脅',
                         '脅痛', '太息', '噯氣', '胃脘', '冷痛', '喜溫', '喜按', '五心',
                         '煩熱', '盜汗', '腰膝', '痠軟']
            
            term_count = sum(1 for term in tcm_terms if term in input_text)
            
            evaluation['input_style'] = 'terminology'
            evaluation['expected_alpha_range'] = (0.0, TestConfig.ALPHA_LOW_THRESHOLD)
            evaluation['is_compliant'] = decided_alpha <= TestConfig.ALPHA_LOW_THRESHOLD
            evaluation['compliance_score'] = max(0, 1.0 - decided_alpha / TestConfig.ALPHA_LOW_THRESHOLD)
            evaluation['reasoning'] = f"標準術語輸入（檢測到 {term_count} 個術語），應選擇關鍵字為主策略"
            
            if not evaluation['is_compliant']:
                evaluation['suggestions'].append(
                    f"Alpha 值 {decided_alpha:.2f} 超過關鍵字為主策略閾值 {TestConfig.ALPHA_LOW_THRESHOLD}，"
                    "建議降低以提升關鍵字匹配權重"
                )
                
        elif case_type == 'l1_oral':
            # 口語化描述
            evaluation['input_style'] = 'oral'
            evaluation['expected_alpha_range'] = (TestConfig.ALPHA_HIGH_THRESHOLD, 1.0)
            evaluation['is_compliant'] = decided_alpha >= TestConfig.ALPHA_HIGH_THRESHOLD
            evaluation['compliance_score'] = min(1.0, decided_alpha / TestConfig.ALPHA_HIGH_THRESHOLD)
            evaluation['reasoning'] = "口語化描述輸入，應選擇向量為主策略以理解語義"
            
            if not evaluation['is_compliant']:
                evaluation['suggestions'].append(
                    f"Alpha 值 {decided_alpha:.2f} 低於向量為主策略閾值 {TestConfig.ALPHA_HIGH_THRESHOLD}，"
                    "建議提高以增強語義理解能力"
                )
                
        elif case_type == 'l1_insufficient':
            # 資訊不足
            evaluation['input_style'] = 'insufficient'
            evaluation['expected_alpha_range'] = (0.0, 1.0)  # alpha 值次要
            evaluation['is_compliant'] = True  # 主要看追問邏輯
            evaluation['compliance_score'] = 0.5  # 中性評分
            evaluation['reasoning'] = "資訊不足輸入，alpha 值選擇次要，重點在於是否生成適當追問"
            
        else:
            # 其他類型（混合或未分類）
            evaluation['input_style'] = 'mixed'
            evaluation['expected_alpha_range'] = (
                TestConfig.ALPHA_LOW_THRESHOLD,
                TestConfig.ALPHA_HIGH_THRESHOLD
            )
            evaluation['is_compliant'] = (
                TestConfig.ALPHA_LOW_THRESHOLD <= decided_alpha <= TestConfig.ALPHA_HIGH_THRESHOLD
            )
            evaluation['compliance_score'] = 0.5 if evaluation['is_compliant'] else 0.0
            evaluation['reasoning'] = "混合輸入或未明確分類，應選擇均衡策略"
        
        return evaluation
    
    @staticmethod
    def evaluate_l1_confidence_action(
        overall_confidence: float,
        next_action: str,
        input_length: int,
        case_type: str
    ) -> Dict[str, Any]:
        """
        評估 L1 的置信度評估與下一步動作決策
        
        評估標準：
        - 置信度 < 0.55 且輸入簡短 → 應生成追問（ask_more）
        - 置信度 >= 0.55 → 應執行搜索（vector_search）
        - 資訊不足類型 → 無論置信度都傾向追問
        """
        evaluation = {
            'case_type': case_type,
            'confidence_score': overall_confidence,
            'input_length': input_length,
            'next_action': next_action,
            'expected_action': None,
            'is_compliant': False,
            'compliance_score': 0.0,
            'reasoning': '',
            'suggestions': []
        }
        
        # 根據案例類型和置信度判斷預期動作
        if case_type == 'l1_insufficient':
            # 資訊不足類型，應傾向追問
            evaluation['expected_action'] = 'ask_more'
            evaluation['is_compliant'] = next_action == 'ask_more'
            evaluation['compliance_score'] = 1.0 if evaluation['is_compliant'] else 0.0
            evaluation['reasoning'] = f"資訊不足輸入（長度 {input_length}），應生成追問以補充資訊"
            
            if not evaluation['is_compliant']:
                evaluation['suggestions'].append(
                    f"系統選擇了 {next_action}，但對於資訊不足的輸入應優先追問"
                )
                
        elif overall_confidence < TestConfig.CONFIDENCE_LOW_THRESHOLD:
            # 低置信度
            if input_length < 30:
                evaluation['expected_action'] = 'ask_more'
                evaluation['is_compliant'] = next_action == 'ask_more'
                evaluation['reasoning'] = f"置信度 {overall_confidence:.2f} 偏低且輸入簡短，應生成追問"
            else:
                evaluation['expected_action'] = 'vector_search'
                evaluation['is_compliant'] = next_action == 'vector_search'
                evaluation['reasoning'] = f"置信度 {overall_confidence:.2f} 偏低但輸入充足，應執行搜索"
            
            evaluation['compliance_score'] = 1.0 if evaluation['is_compliant'] else 0.0
            
            if not evaluation['is_compliant']:
                evaluation['suggestions'].append(
                    f"置信度 {overall_confidence:.2f} 較低，建議 {evaluation['expected_action']}"
                )
                
        else:
            # 正常置信度
            evaluation['expected_action'] = 'vector_search'
            evaluation['is_compliant'] = next_action == 'vector_search'
            evaluation['compliance_score'] = 1.0 if evaluation['is_compliant'] else 0.0
            evaluation['reasoning'] = f"置信度 {overall_confidence:.2f} 足夠，應執行搜索"
            
            if not evaluation['is_compliant']:
                evaluation['suggestions'].append(
                    f"置信度 {overall_confidence:.2f} 已達標，無需追問"
                )
        
        return evaluation
    
    @staticmethod
    def evaluate_l2_tool_decision(
        case_completeness: float,
        diagnosis_confidence: float,
        tool_calls: int,
        validation_status: str,
        case_type: str
    ) -> Dict[str, Any]:
        """
        評估 L2 的工具調用決策邏輯
        
        評估標準：
        - 案例完整度 < 0.6 → 應調用 Tool B（知識補充）
        - 診斷置信度 < 0.7 → 應調用 Tool C（幻覺校驗）
        - 有明確證型 → 應調用 Tool A（權威背書）
        """
        evaluation = {
            'case_type': case_type,
            'case_completeness': case_completeness,
            'diagnosis_confidence': diagnosis_confidence,
            'tool_calls': tool_calls,
            'validation_status': validation_status,
            'expected_min_calls': 0,
            'expected_tools': [],
            'is_compliant': False,
            'compliance_score': 0.0,
            'reasoning': [],
            'suggestions': []
        }
        
        # 基於案例類型的預期
        if case_type == 'l2_knowledge_gap':
            # 知識補充場景，應調用 Tool B
            evaluation['expected_min_calls'] = 1
            evaluation['expected_tools'].append('Tool B (A+百科)')
            evaluation['reasoning'].append("知識補充場景，預期調用 Tool B 補充病機分析")
            
        elif case_type == 'l2_validation':
            # 驗證場景，應調用 Tool C 或多個工具
            if diagnosis_confidence is not None and diagnosis_confidence < TestConfig.VALIDATION_THRESHOLD:
                evaluation['expected_min_calls'] = 1
                evaluation['expected_tools'].append('Tool C (ETCM)')
                evaluation['reasoning'].append("診斷置信度較低，預期調用 Tool C 進行科學驗證")
        
        # 基於指標的動態評估
        if case_completeness is not None and case_completeness < TestConfig.KNOWLEDGE_GAP_THRESHOLD:
            if 'Tool B' not in ' '.join(evaluation['expected_tools']):
                evaluation['expected_min_calls'] += 1
                evaluation['expected_tools'].append('Tool B (A+百科)')
                evaluation['reasoning'].append(
                    f"案例完整度 {case_completeness:.2f} < {TestConfig.KNOWLEDGE_GAP_THRESHOLD}，"
                    "應調用 Tool B 補充知識"
                )
        
        if diagnosis_confidence is not None and diagnosis_confidence < TestConfig.VALIDATION_THRESHOLD:
            if 'Tool C' not in ' '.join(evaluation['expected_tools']):
                evaluation['expected_min_calls'] += 1
                evaluation['expected_tools'].append('Tool C (ETCM)')
                evaluation['reasoning'].append(
                    f"診斷置信度 {diagnosis_confidence:.2f} < {TestConfig.VALIDATION_THRESHOLD}，"
                    "應調用 Tool C 校驗"
                )
        
        # 判斷符合度
        evaluation['is_compliant'] = tool_calls >= evaluation['expected_min_calls']
        
        if evaluation['expected_min_calls'] > 0:
            evaluation['compliance_score'] = min(1.0, tool_calls / evaluation['expected_min_calls'])
        else:
            # 無需調用工具的情況
            evaluation['compliance_score'] = 1.0 if tool_calls == 0 else 0.5
            evaluation['reasoning'].append("條件未觸發工具調用門檻，無需調用工具")
        
        # 生成建議
        if not evaluation['is_compliant']:
            evaluation['suggestions'].append(
                f"實際調用 {tool_calls} 個工具，預期至少 {evaluation['expected_min_calls']} 個"
            )
            if evaluation['expected_tools']:
                evaluation['suggestions'].append(
                    f"建議調用: {', '.join(evaluation['expected_tools'])}"
                )
        
        return evaluation
    
    @staticmethod
    def evaluate_retrieval_quality(
        quality_score: float,
        fallback_triggered: bool,
        attempts: int,
        final_alpha: float,
        initial_alpha: float
    ) -> Dict[str, Any]:
        """
        評估檢索品質與 Fallback 機制
        
        評估標準：
        - 品質評分 < 0.65 → 應觸發 Fallback
        - Fallback 應嘗試不同的 alpha 值
        - 最終品質應提升
        """
        evaluation = {
            'quality_score': quality_score,
            'fallback_triggered': fallback_triggered,
            'attempts': attempts,
            'initial_alpha': initial_alpha,
            'final_alpha': final_alpha,
            'alpha_adjusted': abs(final_alpha - initial_alpha) > 0.05 if initial_alpha and final_alpha else False,
            'is_compliant': False,
            'compliance_score': 0.0,
            'reasoning': '',
            'suggestions': []
        }
        
        if quality_score is not None:
            if quality_score < TestConfig.QUALITY_ACCEPTABLE:
                # 品質不足
                evaluation['is_compliant'] = fallback_triggered
                evaluation['compliance_score'] = 1.0 if fallback_triggered else 0.0
                evaluation['reasoning'] = (
                    f"品質評分 {quality_score:.2f} 低於門檻 {TestConfig.QUALITY_ACCEPTABLE}，"
                    f"{'已' if fallback_triggered else '未'}觸發 Fallback"
                )
                
                if not fallback_triggered:
                    evaluation['suggestions'].append(
                        "品質不足但未觸發 Fallback，建議檢查品質評估門檻設定"
                    )
                elif attempts == 1:
                    evaluation['suggestions'].append(
                        "Fallback 僅嘗試 1 次，建議增加重試次數以提升品質"
                    )
                    
            else:
                # 品質可接受
                evaluation['is_compliant'] = True
                evaluation['compliance_score'] = min(1.0, quality_score / TestConfig.QUALITY_ACCEPTABLE)
                evaluation['reasoning'] = (
                    f"品質評分 {quality_score:.2f} 達標，"
                    f"{'經過' if fallback_triggered else '未經過'} Fallback"
                )
        else:
            # 無品質評分資訊
            evaluation['is_compliant'] = False
            evaluation['compliance_score'] = 0.0
            evaluation['reasoning'] = "缺少檢索品質評分資訊"
            evaluation['suggestions'].append("無法取得檢索元數據，請確認 Agentic 檢索層是否正常運作")
        
        return evaluation


# ============================================
# API 測試執行器
# ============================================

class AgenticTestRunner:
    """Agentic NLU 測試執行器主控類"""
    
    def __init__(self):
        self.logger = JSONLLogger()
        self.evaluator = DecisionLogicEvaluator()
        TestConfig.ensure_dirs()
        print(f"\n📁 測試結果將保存至:")
        print(f"   報告: {TestConfig.REPORT_DIR}")
        print(f"   日誌: {TestConfig.LOG_DIR}")
        
    def _accumulate_questions(self, rounds: List[Dict], current_round: int) -> Tuple[str, str]:
        """
        累積問題 - 實現 SCBR 螺旋式收斂邏輯
        
        這是 SCBR（Spiral Case-Based Reasoning）的核心特性：
        每一輪都累積前面所有輪次的問題，實現逐步收斂的診斷過程。
        
        Args:
            rounds: 所有輪次的問題列表
            current_round: 當前輪次（1-based，從 1 開始）
        
        Returns:
            Tuple[累積後的完整問題, 原始單輪問題]
        
        Example:
            rounds = [
                {"question": "心悸氣短，動則加重"},
                {"question": "神疲乏力，舌淡脈弱"},
                {"question": "自汗，面色淡白"}
            ]
            
            第1輪: "心悸氣短，動則加重"
            第2輪: "心悸氣短，動則加重。補充：神疲乏力，舌淡脈弱"
            第3輪: "心悸氣短，動則加重。補充：神疲乏力，舌淡脈弱。再補充：自汗，面色淡白"
        """
        if current_round < 1 or current_round > len(rounds):
            raise ValueError(f"無效的輪次: {current_round}，有效範圍: 1-{len(rounds)}")
        
        # 提取原始單輪問題
        original_question = rounds[current_round - 1]['question']
        
        # 第一輪：直接返回第一個問題
        if current_round == 1:
            return original_question, original_question
        
        # 第二輪以後：累積所有前面的問題
        accumulated = rounds[0]['question']
        
        for i in range(1, current_round):
            # [修改] 使用逗號自然連接，而非 "補充：" 標籤
            # 這能減少 Token 消耗，並讓語意更連貫
            accumulated += f"，{rounds[i]['question']}"
        
        return accumulated, original_question
    
    def check_api_health(self) -> bool:
        """檢查 API 健康狀態"""
        try:
            url = TestConfig.API_BASE_URL + TestConfig.API_HEALTH_ENDPOINT
            print(f"\n🔍 檢查 API 健康狀態: {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                print("✅ API 健康檢查通過")
                print(f"   版本: {health_data.get('version', 'N/A')}")
                print(f"   服務: {health_data.get('service', 'N/A')}")
                return True
            else:
                print(f"❌ API 健康檢查失敗: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API 連接失敗: {e}")
            return False
    
    def run_test_case(self, test_case: Dict) -> TestCaseResult:
        """執行單一測試案例"""
        case_id = test_case['id']
        case_name = test_case['name']
        case_type = test_case['type']
        description = test_case.get('description', '')
        rounds = test_case['rounds']
        
        print(f"\n{'='*70}")
        print(f"📋 測試案例: {case_id}")
        print(f"名稱: {case_name}")
        print(f"類型: {case_type}")
        if description:
            print(f"說明: {description}")
        print(f"輪數: {len(rounds)}")
        print(f"{'='*70}")
        
        result = TestCaseResult(case_id, case_name, case_type)
        result.description = description
        session_id = None
        start_time = time.time()
        
        try:
            for round_num, round_data in enumerate(rounds, 1):
                # 🆕 螺旋累積邏輯：累積所有前面輪次的問題
                accumulated_question, original_question = self._accumulate_questions(rounds, round_num)
                
                print(f"\n[輪次 {round_num}/{len(rounds)}]")
                # 顯示累積後的問題（如果太長則截斷顯示）
                display_question = accumulated_question[:80] + '...' if len(accumulated_question) > 80 else accumulated_question
                print(f"問題: {display_question}")
                if len(accumulated_question) > 80:
                    print(f"      (完整問題長度: {len(accumulated_question)} 字元)")
                if round_num > 1:
                    print(f"      本輪新增: {original_question}")
                
                round_result = self._execute_round(
                    question=accumulated_question,  # 🆕 發送累積後的完整問題
                    session_id=session_id,
                    round_num=round_num,
                    case_type=case_type
                )
                
                result.rounds.append(round_result)
                
                # 更新 session_id
                if round_result.response and round_result.http_status == 200:
                    session_id = round_result.response.get('session_id')
                    
                    # 記錄決策資訊
                    self._log_decision_info(case_id, round_num, round_result)
                    
                    # 執行邏輯評估
                    self._evaluate_round_logic(round_result, case_type)
                    
                    # 記錄評估結果
                    self._log_evaluation_info(case_id, round_num, round_result)
                    
                    # 輸出關鍵指標
                    self._print_round_metrics(round_result)
                
                # 輪次間隔
                if round_num < len(rounds):
                    time.sleep(TestConfig.ROUND_INTERVAL)
            
            result.success = True
            result.total_time = time.time() - start_time
            
            # 聚合統計指標
            self._aggregate_metrics(result)
            
            print(f"\n✅ 測試案例完成")
            print(f"   總耗時: {result.total_time:.2f}秒")
            print(f"   成功輪次: {sum(1 for r in result.rounds if r.response is not None)}/{len(rounds)}")
            
        except KeyboardInterrupt:
            print(f"\n⚠️  測試被用戶中斷")
            result.success = False
            result.error_message = "用戶中斷測試"
            result.total_time = time.time() - start_time
            raise
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.total_time = time.time() - start_time
            print(f"\n❌ 測試案例失敗")
            print(f"   錯誤: {e}")
        
        return result
    
    def _execute_round(
        self,
        question: str,
        session_id: Optional[str],
        round_num: int,
        case_type: str
    ) -> RoundResult:
        """執行單輪診斷請求"""
        round_result = RoundResult(round_num, question)
        
        url = TestConfig.API_BASE_URL + TestConfig.API_DIAGNOSE_ENDPOINT
        payload = {
            'question': question,
            'session_id': session_id,
            'continue_spiral': session_id is not None
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                url,
                json=payload,
                timeout=TestConfig.REQUEST_TIMEOUT
            )
            round_result.response_time = time.time() - start_time
            round_result.http_status = response.status_code
            
            if response.status_code == 200:
                round_result.response = response.json()
                self._extract_metrics_from_response(round_result)
                print(f"   ✅ HTTP 200 | 響應時間: {round_result.response_time:.2f}s")
            elif response.status_code == 422:
                # 安全攔截
                round_result.security_blocked = True
                error_detail = response.json().get('detail', {})
                if isinstance(error_detail, dict):
                    round_result.security_flags = error_detail.get('l1_flags', [])
                print(f"   🛡️  HTTP 422 | 安全攔截: {error_detail.get('error', 'SECURITY_BLOCK')}")
            else:
                print(f"   ⚠️  HTTP {response.status_code}: {response.text[:100]}")
                
        except requests.Timeout:
            print(f"   ⚠️  請求超時（{TestConfig.REQUEST_TIMEOUT}秒）")
        except Exception as e:
            print(f"   ⚠️  請求錯誤: {e}")
        
        return round_result
    
    def _extract_metrics_from_response(self, round_result: RoundResult):
        """從 API 回應中提取 Agentic 決策指標"""
        response = round_result.response
        
        # 提取 L1 決策資訊
        l1 = response.get('l1', {})
        round_result.l1_overall_confidence = l1.get('overall_confidence')
        round_result.l1_next_action = l1.get('next_action')
        
        retrieval_strategy = l1.get('retrieval_strategy', {})
        round_result.l1_decided_alpha = retrieval_strategy.get('decided_alpha')
        round_result.l1_strategy_type = retrieval_strategy.get('strategy_type')
        round_result.l1_expected_quality = retrieval_strategy.get('expected_quality')
        
        # 提取 L2 Agentic 資訊
        l2_agentic = response.get('l2_agentic_metadata', {})
        if l2_agentic:
            round_result.l2_case_completeness = l2_agentic.get('case_completeness')
            round_result.l2_diagnosis_confidence = l2_agentic.get('diagnosis_confidence')
            round_result.l2_validation_status = l2_agentic.get('validation_status')
            round_result.l2_tool_calls = l2_agentic.get('tool_calls', 0)
            round_result.l2_confidence_boost = l2_agentic.get('confidence_boost', 0)
        
        # 提取檢索元數據
        retrieval_meta = response.get('retrieval_metadata', {})
        if retrieval_meta:
            round_result.retrieval_initial_alpha = retrieval_meta.get('initial_alpha')
            round_result.retrieval_final_alpha = retrieval_meta.get('final_alpha')
            round_result.retrieval_quality_score = retrieval_meta.get('quality_score')
            round_result.retrieval_fallback_triggered = retrieval_meta.get('fallback_triggered', False)
            round_result.retrieval_attempts = retrieval_meta.get('attempts', 1)
    
    def _evaluate_round_logic(self, round_result: RoundResult, case_type: str):
        """執行本輪的決策邏輯評估"""
        # 評估 L1 Alpha 選擇
        if round_result.l1_decided_alpha is not None:
            round_result.logic_evaluations['alpha_selection'] = (
                self.evaluator.evaluate_l1_alpha_selection(
                    round_result.question,
                    round_result.l1_decided_alpha,
                    round_result.l1_strategy_type,
                    case_type
                )
            )
        
        # 評估 L1 置信度與動作
        if round_result.l1_overall_confidence is not None:
            round_result.logic_evaluations['confidence_action'] = (
                self.evaluator.evaluate_l1_confidence_action(
                    round_result.l1_overall_confidence,
                    round_result.l1_next_action,
                    len(round_result.question),
                    case_type
                )
            )
        
        # 評估 L2 工具決策
        if round_result.l2_case_completeness is not None or round_result.l2_diagnosis_confidence is not None:
            round_result.logic_evaluations['tool_decision'] = (
                self.evaluator.evaluate_l2_tool_decision(
                    round_result.l2_case_completeness,
                    round_result.l2_diagnosis_confidence,
                    round_result.l2_tool_calls,
                    round_result.l2_validation_status,
                    case_type
                )
            )
        
        # 評估檢索品質
        if round_result.retrieval_quality_score is not None:
            round_result.logic_evaluations['retrieval_quality'] = (
                self.evaluator.evaluate_retrieval_quality(
                    round_result.retrieval_quality_score,
                    round_result.retrieval_fallback_triggered,
                    round_result.retrieval_attempts,
                    round_result.retrieval_final_alpha,
                    round_result.retrieval_initial_alpha
                )
            )
    
    def _log_decision_info(self, case_id: str, round_num: int, round_result: RoundResult):
        """記錄決策資訊到 JSONL"""
        decision_data = {
            'case_id': case_id,
            'round_num': round_num,
            'question': round_result.accumulated_question,  # 🆕 記錄累積問題
            'original_question': round_result.original_question,  # 🆕 記錄原始問題
            'response_time': round_result.response_time,
            'l1': {
                'confidence': round_result.l1_overall_confidence,
                'alpha': round_result.l1_decided_alpha,
                'strategy': round_result.l1_strategy_type,
                'action': round_result.l1_next_action,
                'expected_quality': round_result.l1_expected_quality
            },
            'l2': {
                'case_completeness': round_result.l2_case_completeness,
                'diagnosis_confidence': round_result.l2_diagnosis_confidence,
                'tool_calls': round_result.l2_tool_calls,
                'validation_status': round_result.l2_validation_status,
                'confidence_boost': round_result.l2_confidence_boost
            },
            'retrieval': {
                'initial_alpha': round_result.retrieval_initial_alpha,
                'final_alpha': round_result.retrieval_final_alpha,
                'quality': round_result.retrieval_quality_score,
                'fallback': round_result.retrieval_fallback_triggered,
                'attempts': round_result.retrieval_attempts
            },
            'security': {
                'blocked': round_result.security_blocked,
                'flags': round_result.security_flags
            }
        }
        
        self.logger.log_decision(decision_data)
    
    def _log_evaluation_info(self, case_id: str, round_num: int, round_result: RoundResult):
        """記錄邏輯評估結果到 JSONL"""
        evaluation_data = {
            'case_id': case_id,
            'round_num': round_num,
            'evaluations': round_result.logic_evaluations
        }
        
        self.logger.log_evaluation(evaluation_data)
    
    def _print_round_metrics(self, round_result: RoundResult):
        """輸出輪次關鍵指標（簡化版）"""
        # L1 指標
        if round_result.l1_decided_alpha is not None:
            print(f"\n   🎯 L1 決策:")
            print(f"      Alpha: {round_result.l1_decided_alpha:.2f} | "
                  f"策略: {round_result.l1_strategy_type} | "
                  f"置信度: {round_result.l1_overall_confidence:.2f}")
            
            # Alpha 評估結果
            if 'alpha_selection' in round_result.logic_evaluations:
                eval_result = round_result.logic_evaluations['alpha_selection']
                status = "✅" if eval_result['is_compliant'] else "❌"
                score = eval_result['compliance_score']
                print(f"      評估: {status} 符合度 {score:.0%} - {eval_result['reasoning']}")
        
        # L2 指標
        if round_result.l2_tool_calls > 0:
            print(f"\n   🔧 L2 工具:")
            print(f"      調用數: {round_result.l2_tool_calls} | "
                  f"驗證: {round_result.l2_validation_status} | "
                  f"提升: +{round_result.l2_confidence_boost:.2f}")
            
            # 工具決策評估結果
            if 'tool_decision' in round_result.logic_evaluations:
                eval_result = round_result.logic_evaluations['tool_decision']
                status = "✅" if eval_result['is_compliant'] else "❌"
                score = eval_result['compliance_score']
                print(f"      評估: {status} 符合度 {score:.0%}")
        
        # 檢索 Fallback
        if round_result.retrieval_fallback_triggered:
            print(f"\n   🔄 檢索 Fallback:")
            print(f"      嘗試: {round_result.retrieval_attempts} 次 | "
                  f"品質: {round_result.retrieval_quality_score:.2f}")
    
    def _aggregate_metrics(self, result: TestCaseResult):
        """聚合測試案例的統計指標"""
        metrics = result.metrics
        
        for round_result in result.rounds:
            # 安全指標
            if round_result.security_blocked:
                metrics.security_blocks += 1
            elif round_result.response is not None:
                metrics.security_passed += 1
            
            # L1 指標
            if round_result.l1_decided_alpha is not None:
                metrics.alpha_decisions.append(round_result.l1_decided_alpha)
            if round_result.l1_overall_confidence is not None:
                metrics.confidence_scores.append(round_result.l1_overall_confidence)
            if round_result.l1_strategy_type:
                metrics.strategy_types.append(round_result.l1_strategy_type)
            if round_result.l1_next_action == 'ask_more':
                metrics.follow_up_triggered += 1
            elif round_result.l1_next_action == 'vector_search':
                metrics.search_triggered += 1
            
            # L2 指標
            if round_result.l2_tool_calls > 0:
                metrics.total_tool_calls += round_result.l2_tool_calls
                # 簡化統計（實際應從詳細日誌解析）
                metrics.tool_b_calls += 1
            if round_result.l2_validation_status:
                metrics.validation_status_counts[round_result.l2_validation_status] += 1
            if round_result.l2_case_completeness is not None:
                metrics.case_completeness_scores.append(round_result.l2_case_completeness)
            if round_result.l2_diagnosis_confidence is not None:
                metrics.diagnosis_confidence_scores.append(round_result.l2_diagnosis_confidence)
            
            # 檢索指標
            if round_result.retrieval_quality_score is not None:
                metrics.quality_scores.append(round_result.retrieval_quality_score)
            if round_result.retrieval_fallback_triggered:
                metrics.fallback_triggered += 1
                metrics.fallback_attempts.append(round_result.retrieval_attempts)
            if round_result.retrieval_initial_alpha and round_result.retrieval_final_alpha:
                adjustment = abs(round_result.retrieval_final_alpha - round_result.retrieval_initial_alpha)
                metrics.alpha_adjustments.append(adjustment)
            
            # 邏輯符合度
            for eval_type, eval_result in round_result.logic_evaluations.items():
                metrics.logic_checks[eval_type].append({
                    'is_compliant': eval_result.get('is_compliant', False),
                    'compliance_score': eval_result.get('compliance_score', 0.0)
                })


# ============================================
# 測試報告生成器
# ============================================

class AgenticTestReporter:
    """Agentic NLU 測試報告生成器"""
    
    @staticmethod
    def generate_summary_report(all_results: List[TestCaseResult]) -> str:
        """生成測試摘要報告"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 基本統計
        total_cases = len(all_results)
        success_cases = sum(1 for r in all_results if r.success)
        total_rounds = sum(len(r.rounds) for r in all_results)
        total_time = sum(r.total_time for r in all_results)
        
        # 案例類型分佈
        type_counts = defaultdict(int)
        for result in all_results:
            type_counts[result.case_type] += 1
        
        # 聚合所有指標
        all_metrics = AgenticDecisionMetrics()
        for result in all_results:
            m = result.metrics
            all_metrics.alpha_decisions.extend(m.alpha_decisions)
            all_metrics.confidence_scores.extend(m.confidence_scores)
            all_metrics.strategy_types.extend(m.strategy_types)
            all_metrics.follow_up_triggered += m.follow_up_triggered
            all_metrics.search_triggered += m.search_triggered
            all_metrics.tool_a_calls += m.tool_a_calls
            all_metrics.tool_b_calls += m.tool_b_calls
            all_metrics.tool_c_calls += m.tool_c_calls
            all_metrics.total_tool_calls += m.total_tool_calls
            for status, count in m.validation_status_counts.items():
                all_metrics.validation_status_counts[status] += count
            all_metrics.case_completeness_scores.extend(m.case_completeness_scores)
            all_metrics.diagnosis_confidence_scores.extend(m.diagnosis_confidence_scores)
            all_metrics.quality_scores.extend(m.quality_scores)
            all_metrics.fallback_triggered += m.fallback_triggered
            all_metrics.fallback_attempts.extend(m.fallback_attempts)
            all_metrics.alpha_adjustments.extend(m.alpha_adjustments)
            all_metrics.security_blocks += m.security_blocks
            all_metrics.security_passed += m.security_passed
            for check_type, checks in m.logic_checks.items():
                all_metrics.logic_checks[check_type].extend(checks)
        
        # 計算統計值
        def safe_mean(values):
            return statistics.mean(values) if values else 0
        
        def safe_stdev(values):
            return statistics.stdev(values) if len(values) > 1 else 0
        
        avg_alpha = safe_mean(all_metrics.alpha_decisions)
        std_alpha = safe_stdev(all_metrics.alpha_decisions)
        avg_confidence = safe_mean(all_metrics.confidence_scores)
        std_confidence = safe_stdev(all_metrics.confidence_scores)
        avg_quality = safe_mean(all_metrics.quality_scores)
        std_quality = safe_stdev(all_metrics.quality_scores)
        
        # 計算決策邏輯符合率
        total_checks = sum(len(checks) for checks in all_metrics.logic_checks.values())
        total_compliant = sum(
            sum(1 for c in checks if c['is_compliant'])
            for checks in all_metrics.logic_checks.values()
        )
        overall_compliance_rate = (total_compliant / total_checks * 100) if total_checks > 0 else 0
        
        # 計算平均符合度評分
        total_score = sum(
            sum(c['compliance_score'] for c in checks)
            for checks in all_metrics.logic_checks.values()
        )
        avg_compliance_score = (total_score / total_checks) if total_checks > 0 else 0
        
        # 生成報告
        report = f"""
{'='*80}
SCBR Agentic NLU 決策邏輯驗證測試報告
Phase 1.5 系統測試與驗證
{'='*80}

測試時間: {timestamp}
測試版本: v1.0

{'='*80}
一、測試執行摘要
{'='*80}

1.1 基本統計
--------------------------------------------------
總測試案例數: {total_cases}
成功執行案例: {success_cases} ({success_cases/total_cases*100:.1f}%)
失敗案例數: {total_cases - success_cases}
總測試輪次: {total_rounds}
總測試時間: {total_time:.2f}秒
平均每案例時間: {total_time/total_cases:.2f}秒

1.2 案例類型分佈
--------------------------------------------------
"""
        
        for case_type, count in sorted(type_counts.items()):
            report += f"{case_type}: {count} 個案例\n"
        
        report += f"""
{'='*80}
二、L1 Agentic Gate 決策分析
{'='*80}

2.1 Alpha 值選擇統計
--------------------------------------------------
平均 Alpha: {avg_alpha:.3f} ± {std_alpha:.3f}
Alpha 範圍: [{min(all_metrics.alpha_decisions) if all_metrics.alpha_decisions else 0:.2f}, {max(all_metrics.alpha_decisions) if all_metrics.alpha_decisions else 0:.2f}]

Alpha 分佈:
  低值 (≤{TestConfig.ALPHA_LOW_THRESHOLD}, 關鍵字為主): {sum(1 for a in all_metrics.alpha_decisions if a <= TestConfig.ALPHA_LOW_THRESHOLD)} 次 ({sum(1 for a in all_metrics.alpha_decisions if a <= TestConfig.ALPHA_LOW_THRESHOLD)/len(all_metrics.alpha_decisions)*100 if all_metrics.alpha_decisions else 0:.1f}%)
  中值 ({TestConfig.ALPHA_LOW_THRESHOLD}-{TestConfig.ALPHA_HIGH_THRESHOLD}, 均衡): {sum(1 for a in all_metrics.alpha_decisions if TestConfig.ALPHA_LOW_THRESHOLD < a < TestConfig.ALPHA_HIGH_THRESHOLD)} 次 ({sum(1 for a in all_metrics.alpha_decisions if TestConfig.ALPHA_LOW_THRESHOLD < a < TestConfig.ALPHA_HIGH_THRESHOLD)/len(all_metrics.alpha_decisions)*100 if all_metrics.alpha_decisions else 0:.1f}%)
  高值 (≥{TestConfig.ALPHA_HIGH_THRESHOLD}, 向量為主): {sum(1 for a in all_metrics.alpha_decisions if a >= TestConfig.ALPHA_HIGH_THRESHOLD)} 次 ({sum(1 for a in all_metrics.alpha_decisions if a >= TestConfig.ALPHA_HIGH_THRESHOLD)/len(all_metrics.alpha_decisions)*100 if all_metrics.alpha_decisions else 0:.1f}%)

2.2 置信度評估統計
--------------------------------------------------
平均置信度: {avg_confidence:.3f} ± {std_confidence:.3f}
置信度範圍: [{min(all_metrics.confidence_scores) if all_metrics.confidence_scores else 0:.2f}, {max(all_metrics.confidence_scores) if all_metrics.confidence_scores else 0:.2f}]

置信度分佈:
  高 (≥0.75): {sum(1 for c in all_metrics.confidence_scores if c >= 0.75)} 次 ({sum(1 for c in all_metrics.confidence_scores if c >= 0.75)/len(all_metrics.confidence_scores)*100 if all_metrics.confidence_scores else 0:.1f}%)
  中 (0.55-0.75): {sum(1 for c in all_metrics.confidence_scores if 0.55 <= c < 0.75)} 次 ({sum(1 for c in all_metrics.confidence_scores if 0.55 <= c < 0.75)/len(all_metrics.confidence_scores)*100 if all_metrics.confidence_scores else 0:.1f}%)
  低 (<{TestConfig.CONFIDENCE_LOW_THRESHOLD}): {sum(1 for c in all_metrics.confidence_scores if c < TestConfig.CONFIDENCE_LOW_THRESHOLD)} 次 ({sum(1 for c in all_metrics.confidence_scores if c < TestConfig.CONFIDENCE_LOW_THRESHOLD)/len(all_metrics.confidence_scores)*100 if all_metrics.confidence_scores else 0:.1f}%)

2.3 決策動作統計
--------------------------------------------------
執行搜索次數: {all_metrics.search_triggered} ({all_metrics.search_triggered/total_rounds*100:.1f}%)
生成追問次數: {all_metrics.follow_up_triggered} ({all_metrics.follow_up_triggered/total_rounds*100:.1f}%)

{'='*80}
三、L2 Agentic 診斷層分析
{'='*80}

3.1 工具調用統計
--------------------------------------------------
Tool A (ICD-11) 調用: {all_metrics.tool_a_calls} 次
Tool B (A+百科) 調用: {all_metrics.tool_b_calls} 次
Tool C (ETCM) 調用: {all_metrics.tool_c_calls} 次
總工具調用次數: {all_metrics.total_tool_calls}
平均每案例調用: {all_metrics.total_tool_calls/total_cases:.2f} 次

3.2 驗證狀態分佈
--------------------------------------------------
"""
        
        if all_metrics.validation_status_counts:
            for status, count in sorted(all_metrics.validation_status_counts.items()):
                report += f"{status}: {count} 次 ({count/sum(all_metrics.validation_status_counts.values())*100:.1f}%)\n"
        else:
            report += "無驗證狀態數據\n"
        
        report += f"""
3.3 案例完整度與診斷置信度
--------------------------------------------------
平均案例完整度: {safe_mean(all_metrics.case_completeness_scores):.3f}
平均診斷置信度: {safe_mean(all_metrics.diagnosis_confidence_scores):.3f}

{'='*80}
四、檢索品質與 Fallback 機制分析
{'='*80}

4.1 檢索品質統計
--------------------------------------------------
平均品質評分: {avg_quality:.3f} ± {std_quality:.3f}
品質範圍: [{min(all_metrics.quality_scores) if all_metrics.quality_scores else 0:.2f}, {max(all_metrics.quality_scores) if all_metrics.quality_scores else 0:.2f}]

品質分佈:
  優秀 (≥0.80): {sum(1 for q in all_metrics.quality_scores if q >= 0.80)} 次 ({sum(1 for q in all_metrics.quality_scores if q >= 0.80)/len(all_metrics.quality_scores)*100 if all_metrics.quality_scores else 0:.1f}%)
  良好 (0.65-0.80): {sum(1 for q in all_metrics.quality_scores if 0.65 <= q < 0.80)} 次 ({sum(1 for q in all_metrics.quality_scores if 0.65 <= q < 0.80)/len(all_metrics.quality_scores)*100 if all_metrics.quality_scores else 0:.1f}%)
  不足 (<{TestConfig.QUALITY_ACCEPTABLE}): {sum(1 for q in all_metrics.quality_scores if q < TestConfig.QUALITY_ACCEPTABLE)} 次 ({sum(1 for q in all_metrics.quality_scores if q < TestConfig.QUALITY_ACCEPTABLE)/len(all_metrics.quality_scores)*100 if all_metrics.quality_scores else 0:.1f}%)

4.2 Fallback 機制統計
--------------------------------------------------
Fallback 觸發次數: {all_metrics.fallback_triggered}
Fallback 觸發率: {all_metrics.fallback_triggered/total_rounds*100:.1f}%
平均 Fallback 嘗試: {safe_mean(all_metrics.fallback_attempts):.1f} 次
平均 Alpha 調整幅度: {safe_mean(all_metrics.alpha_adjustments):.3f}

{'='*80}
五、決策邏輯符合度評估（核心指標）
{'='*80}

5.1 整體符合度
--------------------------------------------------
總邏輯檢查次數: {total_checks}
符合預期次數: {total_compliant}
決策邏輯符合率: {overall_compliance_rate:.1f}%
平均符合度評分: {avg_compliance_score:.2f} / 1.00

5.2 分項符合度統計
--------------------------------------------------
"""
        
        for check_type, checks in sorted(all_metrics.logic_checks.items()):
            if checks:
                compliant_count = sum(1 for c in checks if c['is_compliant'])
                total_count = len(checks)
                avg_score = safe_mean([c['compliance_score'] for c in checks])
                report += f"{check_type}:\n"
                report += f"  符合率: {compliant_count}/{total_count} ({compliant_count/total_count*100:.1f}%)\n"
                report += f"  平均評分: {avg_score:.2f}\n"
        
        report += f"""
{'='*80}
六、安全測試結果
{'='*80}

安全攔截次數: {all_metrics.security_blocks}
正常通過次數: {all_metrics.security_passed}
攔截率: {all_metrics.security_blocks/(all_metrics.security_blocks + all_metrics.security_passed)*100 if (all_metrics.security_blocks + all_metrics.security_passed) > 0 else 0:.1f}%

{'='*80}
七、測試結論與建議
{'='*80}

7.1 測試結論
--------------------------------------------------
"""
        
        # 根據符合率給出結論
        if overall_compliance_rate >= 85:
            report += """
✅ 優秀：Agentic 決策邏輯運作良好，高度符合預期設計

核心優勢：
- L1 決策邏輯準確，能夠根據輸入特性選擇合適策略
- L2 工具調用時機恰當，有效提升診斷品質
- 檢索品質穩定，Fallback 機制運作正常
"""
        elif overall_compliance_rate >= 70:
            report += """
⚠️  良好：Agentic 決策邏輯基本符合預期，存在改進空間

需要關注：
- 部分決策邏輯與預期存在偏差
- 建議進行參數微調和優化
"""
        else:
            report += """
❌ 待改進：Agentic 決策邏輯與預期存在較大差距

主要問題：
- 決策邏輯符合率偏低
- 需要深入分析問題根源並進行重大調整
"""
        
        report += """
7.2 參數調整建議
--------------------------------------------------
"""
        
        # 基於統計數據給出參數調整建議
        if avg_alpha < 0.3:
            report += f"- Alpha 平均值 {avg_alpha:.2f} 偏低，建議檢查是否過度偏好關鍵字匹配\n"
        elif avg_alpha > 0.7:
            report += f"- Alpha 平均值 {avg_alpha:.2f} 偏高，建議檢查是否過度依賴向量相似度\n"
        
        if all_metrics.fallback_triggered > total_rounds * 0.3:
            report += f"- Fallback 觸發率 {all_metrics.fallback_triggered/total_rounds*100:.1f}% 偏高，建議降低品質門檻或改善檢索策略\n"
        elif all_metrics.fallback_triggered < total_rounds * 0.05:
            report += f"- Fallback 觸發率 {all_metrics.fallback_triggered/total_rounds*100:.1f}% 偏低，建議檢查品質評估是否過於寬鬆\n"
        
        if all_metrics.total_tool_calls > 0:
            tool_call_rate = all_metrics.total_tool_calls / total_rounds
            if tool_call_rate > 0.5:
                report += f"- 工具調用頻率 {tool_call_rate:.2f} 次/輪 偏高，建議提高調用門檻以減少開銷\n"
            elif tool_call_rate < 0.1:
                report += f"- 工具調用頻率 {tool_call_rate:.2f} 次/輪 偏低，建議檢查門檻設定是否過於嚴格\n"
        
        report += """
7.3 下一步行動建議
--------------------------------------------------
"""
        
        if overall_compliance_rate >= 85:
            report += """
✅ 建議進入下一階段：
   1. 部署小範圍試運行（Production Pilot）
   2. 收集真實用戶使用數據
   3. 持續監控 Agentic 決策品質
   4. 建立長期優化機制
"""
        elif overall_compliance_rate >= 70:
            report += """
⚠️  建議先進行優化：
   1. 針對符合率較低的決策邏輯進行調整
   2. 微調相關門檻參數（參考上述建議）
   3. 進行重點案例的深入分析
   4. 優化後重新執行測試驗證
"""
        else:
            report += """
❌ 建議深入分析問題：
   1. 詳細審查決策邏輯不符合的具體案例
   2. 分析 Prompt 設計是否需要改進
   3. 檢查配置參數是否合理
   4. 考慮調整 Agentic 決策的核心邏輯
   5. 完成改進後進行全面重測
"""
        
        report += f"""
{'='*80}
八、測試數據說明
{'='*80}

8.1 數據來源
--------------------------------------------------
- 測試案例: {TestConfig.TEST_CASES_FILE}
- 測試時間: {timestamp}
- 測試環境: {TestConfig.API_BASE_URL}

8.2 詳細日誌位置
--------------------------------------------------
- 測試詳情: {TestConfig.LOG_DIR}/test_details_*.jsonl
- 決策記錄: {TestConfig.LOG_DIR}/agentic_decisions_*.jsonl
- 評估結果: {TestConfig.LOG_DIR}/logic_evaluations_*.jsonl

{'='*80}
報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}
"""
        
        return report
    
    @staticmethod
    def save_report(report: str, filename: str):
        """保存報告到檔案"""
        filepath = os.path.join(TestConfig.REPORT_DIR, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n📄 測試報告已保存: {filepath}")
        except Exception as e:
            print(f"\n⚠️  保存報告失敗: {e}")


# ============================================
# 主測試流程
# ============================================

def main():
    """主測試流程控制"""
    print("\n" + "="*80)
    print("SCBR Agentic NLU 決策邏輯驗證測試")
    print("Phase 1.5 系統測試與驗證")
    print("="*80 + "\n")
    
    # 初始化測試執行器
    runner = AgenticTestRunner()
    
    # 檢查 API 健康狀態
    if not runner.check_api_health():
        print("\n❌ API 健康檢查失敗，無法繼續測試")
        print("   請確認:")
        print("   1. 後端服務已啟動")
        print("   2. API 端點配置正確")
        print("   3. 網路連接正常")
        return 1
    
    # 載入測試案例
    test_cases_file = TestConfig.TEST_CASES_FILE
    if not os.path.exists(test_cases_file):
        print(f"\n❌ 測試案例檔案不存在: {test_cases_file}")
        print(f"   請確認檔案位於當前目錄: {os.getcwd()}")
        return 1
    
    try:
        with open(test_cases_file, 'r', encoding='utf-8') as f:
            test_data = yaml.safe_load(f)
            test_cases = test_data.get('test_cases', [])
    except Exception as e:
        print(f"\n❌ 載入測試案例失敗: {e}")
        return 1
    
    if not test_cases:
        print("\n❌ 沒有找到測試案例")
        return 1
    
    print(f"\n📋 載入了 {len(test_cases)} 個測試案例")
    print(f"   案例檔案: {test_cases_file}")
    
    # 詢問是否繼續
    try:
        user_input = input("\n是否開始測試？[Y/n]: ").strip().lower()
        if user_input and user_input != 'y':
            print("測試已取消")
            return 0
    except KeyboardInterrupt:
        print("\n測試已取消")
        return 0
    
    # 執行所有測試案例
    all_results = []
    start_time = time.time()
    
    try:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'#'*80}")
            print(f"進度: [{i}/{len(test_cases)}]")
            print(f"{'#'*80}")
            
            result = runner.run_test_case(test_case)
            all_results.append(result)
            
            # 測試案例間隔
            if i < len(test_cases):
                time.sleep(TestConfig.CASE_INTERVAL)
                
    except KeyboardInterrupt:
        print("\n\n⚠️  測試被用戶中斷")
        print(f"已完成 {len(all_results)}/{len(test_cases)} 個測試案例")
    
    total_test_time = time.time() - start_time
    
    # 生成測試報告
    print("\n" + "="*80)
    print("生成測試報告...")
    print("="*80)
    
    report = AgenticTestReporter.generate_summary_report(all_results)
    print(report)
    
    # 保存報告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f'agentic_test_report_{timestamp}.txt'
    AgenticTestReporter.save_report(report, report_filename)
    
    print(f"\n{'='*80}")
    print("測試完成")
    print(f"{'='*80}")
    print(f"總測試時間: {total_test_time:.2f}秒")
    print(f"成功案例: {sum(1 for r in all_results if r.success)}/{len(all_results)}")
    print(f"{'='*80}\n")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n測試已中斷")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 測試執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)