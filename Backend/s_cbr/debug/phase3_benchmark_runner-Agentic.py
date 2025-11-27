#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCBR Phase 3: 論文實驗數據自動化收集腳本 (Benchmark Runner)

用途：
1. 批量執行真實臨床案例 (Real-world Cases)
2. 自動比對模型診斷與標準答案 (Ground Truth Evaluation)
3. 收集關鍵實驗指標 (Accuracy, Latency, Tool Usage, Alpha)
4. 生成 CSV 格式的原始數據供論文繪圖使用

輸出：
- test_results/thesis_experiment_data.csv (原始數據)
- test_results/phase3_summary_report.txt (統計報告)
"""

import os
import sys
import json
import yaml
import time
import csv
import requests
from datetime import datetime
from typing import Dict, List, Any, Tuple

# ==================== 配置區域 ====================
class BenchmarkConfig:
    # API 設定
    API_URL = "http://localhost:8000/api/scbr/v2/diagnose"
    TIMEOUT = 240  # 4分鐘超時，容許完整 Agentic 推理
    
    # 檔案路徑
    INPUT_FILE = "benchmark_cases_spiral.yaml"  # 您的真實醫案庫
    OUTPUT_CSV = "test_results/thesis_experiment_data-Agentic.csv"
    OUTPUT_REPORT = "test_results/phase3_summary_report-Agentic.txt"
    
    # 實驗標籤 (每次執行前請修改此處以區分實驗組/對照組)
    # 例如: "Agentic_V1.5" 或 "Baseline_Traditional"
    EXPERIMENT_TAG = "Agentic_Spiral" 

    @staticmethod
    def ensure_dirs():
        os.makedirs("test_results", exist_ok=True)

# ==================== 評估邏輯 ====================
class DiagnosisEvaluator:
    """診斷準確度評估器"""
    
    @staticmethod
    def check_correctness(predicted: str, ground_truth: str) -> float:
        """
        計算診斷準確度 (0.0 - 1.0)
        採用關鍵字模糊匹配：只要 Ground Truth 的核心證型出現在預測中就算正確
        """
        if not predicted or not ground_truth:
            return 0.0
            
        pred_clean = predicted.replace("（", "(").replace("）", ")").strip()
        truth_clean = ground_truth.replace("（", "(").replace("）", ")").strip()
        
        # 1. 完全匹配
        if pred_clean == truth_clean:
            return 1.0
            
        # 2. 核心證型包含匹配 (例如 Truth="心脾兩虛", Pred="失眠(心脾兩虛)")
        # 提取括號內的證型，或直接比對字串
        if truth_clean in pred_clean:
            return 1.0
            
        # 3. 部分關鍵字重疊 (Fuzzy Match)
        # 將 Ground Truth 拆解為關鍵詞 (排除標點)
        keywords = [k for k in truth_clean if k not in "(),（） "]
        if not keywords: return 0.0
        
        hit_count = sum(1 for k in keywords if k in pred_clean)
        match_ratio = hit_count / len(keywords)
        
        # 門檻：重疊度超過 80% 視為正確
        return 1.0 if match_ratio >= 0.8 else 0.0

# ==================== 執行核心 ====================
class Phase3Runner:
    def __init__(self):
        BenchmarkConfig.ensure_dirs()
        self.results = []
        self.total_cases = 0
        
    def load_cases(self) -> List[Dict]:
        if not os.path.exists(BenchmarkConfig.INPUT_FILE):
            print(f"❌ 找不到測試檔案: {BenchmarkConfig.INPUT_FILE}")
            sys.exit(1)
            
        with open(BenchmarkConfig.INPUT_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            cases = data.get('test_cases', [])
            self.total_cases = len(cases)
            print(f"📖 已載入 {self.total_cases} 個真實案例")
            return cases

    def run_diagnosis(self, question: str, session_id: str = None) -> Dict:
        """呼叫 API 進行診斷"""
        payload = {
            "question": question,
            "session_id": session_id, # [修改] 使用傳入的 session_id
            "continue_spiral": session_id is not None # [修改] 自動判斷是否延續對話
        }
        
        start_time = time.time()
        try:
            resp = requests.post(BenchmarkConfig.API_URL, json=payload, timeout=BenchmarkConfig.TIMEOUT)
            latency = time.time() - start_time
            
            if resp.status_code == 200:
                return {"success": True, "data": resp.json(), "latency": latency}
            else:
                return {"success": False, "error": f"HTTP {resp.status_code}", "latency": latency}
                
        except Exception as e:
            return {"success": False, "error": str(e), "latency": time.time() - start_time}

    def execute(self):
        cases = self.load_cases()
        
        # 初始化 CSV 寫入
        file_exists = os.path.exists(BenchmarkConfig.OUTPUT_CSV)
        # 使用 utf-8-sig 以便 Excel 正確開啟中文
        csv_file = open(BenchmarkConfig.OUTPUT_CSV, 'a', newline='', encoding='utf-8-sig')
        
        # 定義 CSV 欄位 (增加了 Session_ID, Question)
        fieldnames = [
            'Experiment_Tag', 'Case_ID', 'Session_ID', 'Round', 'Time', 
            'Question', 'Ground_Truth', 'Predicted_Pattern', 'Is_Correct', 
            'L1_Alpha', 'L1_Strategy', 'L1_Confidence', 
            'Retrieval_Quality', 'Fallback_Triggered',
            'L2_Tool_Calls', 'L2_Confidence_Boost', 'Completeness_Score',
            'Latency_Total', 'Error_Msg'
        ]
        
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
            
        print(f"\n🚀 開始執行 Phase 3 Benchmark ({BenchmarkConfig.EXPERIMENT_TAG})...")
        print(f"   目標：{self.total_cases} 案例 (螺旋多輪模式) | 輸出: {BenchmarkConfig.OUTPUT_CSV}")
        print("-" * 80)

        total_correct_cases = 0 # 統計最終正確的案例數
        
        for idx, case in enumerate(cases, 1):
            case_id = case['id']
            ground_truth = case['expected_diagnosis']
            session_id = None # ⚠️ 重要：每個新案例開始前重置 Session
            
            print(f"\n[{idx}/{self.total_cases}] 案例 {case_id}: ", end="", flush=True)
            
            case_final_correct = False # 追蹤此案例最後一輪是否正確
            
            # --- 螺旋輪次迴圈 ---
            rounds = case.get('rounds', [])
            for round_idx, round_data in enumerate(rounds, 1):
                question = round_data['question']
                
                # 執行診斷 (傳入 session_id 以維持上下文)
                result = self.run_diagnosis(question, session_id)
                
                # 準備基礎數據
                row_data = {
                    'Experiment_Tag': BenchmarkConfig.EXPERIMENT_TAG,
                    'Case_ID': case_id,
                    'Session_ID': 'N/A',
                    'Round': round_idx,
                    'Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'Question': question[:30].replace("\n", " ") + "...",
                    'Ground_Truth': ground_truth,
                    'Latency_Total': round(result['latency'], 2)
                }
                
                if result['success']:
                    data = result['data']
                    
                    # 1. 更新 Session ID (供下一輪使用)
                    session_id = data.get('session_id')
                    row_data['Session_ID'] = session_id
                    
                    # 2. 提取關鍵指標
                    l1 = data.get('l1', {})
                    l2_meta = data.get('l2_agentic_metadata', {})
                    l2_infer = data.get('l2', {}).get('tcm_inference', {})
                    ret_meta = data.get('retrieval_metadata', {})
                    
                    # 3. 獲取預測結果
                    # 優先從 L2 inference 拿，如果沒有則拿 l2 root 的 primary_pattern
                    predicted = l2_infer.get('primary_pattern') or data.get('l2', {}).get('primary_pattern', 'N/A')
                    
                    # 4. 判斷準確度
                    is_correct = DiagnosisEvaluator.check_correctness(predicted, ground_truth)
                    
                    # 記錄本輪數據
                    row_data.update({
                        'Predicted_Pattern': predicted,
                        'Is_Correct': 1 if is_correct else 0,
                        'L1_Alpha': l1.get('retrieval_strategy', {}).get('decided_alpha'),
                        'L1_Strategy': l1.get('retrieval_strategy', {}).get('strategy_type'),
                        'L1_Confidence': l1.get('overall_confidence'),
                        'Retrieval_Quality': ret_meta.get('quality_score'),
                        'Fallback_Triggered': 1 if ret_meta.get('fallback_triggered') else 0,
                        'L2_Tool_Calls': l2_meta.get('tool_calls', 0),
                        'L2_Confidence_Boost': l2_meta.get('confidence_boost', 0),
                        'Completeness_Score': l2_meta.get('case_completeness', 0),
                        'Error_Msg': ''
                    })
                    
                    # 印出進度 (R1✅ R2⚠️)
                    status_icon = "✅" if is_correct else "⚠️"
                    print(f"R{round_idx}{status_icon} ", end="", flush=True)
                    
                    # 如果是最後一輪且正確，則標記此案例為成功
                    if round_idx == len(rounds) and is_correct:
                        case_final_correct = True

                else:
                    # 請求失敗處理
                    print(f"R{round_idx}❌ ", end="", flush=True)
                    row_data['Error_Msg'] = result['error']
                    row_data['Is_Correct'] = 0
                    writer.writerow(row_data)
                    csv_file.flush()
                    break # 這一輪失敗就跳出這個案例，不繼續跑下一輪

                # 寫入 CSV 並刷新緩衝區
                writer.writerow(row_data)
                csv_file.flush()
            
            # 該案例所有輪次結束後的統計
            if case_final_correct:
                total_correct_cases += 1

        # 關閉檔案並生成報告
        csv_file.close()
        print("\n" + "-" * 80)
        self._generate_report(total_correct_cases)

    def _generate_report(self, correct_count):
        """生成本次執行的統計摘要"""
        accuracy = (correct_count / self.total_cases) * 100 if self.total_cases > 0 else 0
        
        report = f"""
================================================
Phase 3 Benchmark 執行報告
================================================
實驗標籤: {BenchmarkConfig.EXPERIMENT_TAG}
執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
總案例數: {self.total_cases}
成功診斷: {correct_count} (準確率: {accuracy:.2f}%)
數據位置: {BenchmarkConfig.OUTPUT_CSV}
================================================
"""
        print(report)
        with open(BenchmarkConfig.OUTPUT_REPORT, 'a', encoding='utf-8') as f:
            f.write(report + "\n")

if __name__ == "__main__":
    try:
        runner = Phase3Runner()
        runner.execute()
    except KeyboardInterrupt:
        print("\n⚠️ 測試已由使用者中斷")