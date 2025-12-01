# -*- coding: utf-8 -*-
"""
SCBR 論文實驗執行器 v6.0 (Thesis Final Edition)
===========================================
修復紀錄：
1. [FIX] 修正 API 成功回傳時缺少 status_code 導致的提早中斷 Bug。
2. [FEAT] 新增論文實驗所需的進階指標欄位 (L1 策略、證據數、追問數)。
3. [FEAT] 增強錯誤處理，確保實驗不會因為單一案例失敗而全停。
"""

import requests
import yaml
import time
import pandas as pd
import uuid
import os
import json
import sys
from typing import List, Dict, Any, Optional

# ==================== 配置區域 ====================
class Config:
    # 請確保此 URL 與您啟動的後端位址一致
    API_URL = "http://localhost:8000/api/scbr/v2/diagnose"
    # 測試案例檔案
    YAML_FILE = "benchmark_cases_spiral.yaml"
    # 逾時設定 (秒)，避免 LLM 生成過久導致中斷
    TIMEOUT = 300 
    # 重試次數
    RETRY_COUNT = 2

# ==================== 1. 資料提取器 (增強版) ====================
class DataExtractor:
    @staticmethod
    def extract_pattern(l2_result: Dict) -> str:
        """從 L2 結果提取主要證型"""
        if not l2_result: return ""
        
        # 優先順序：tcm_inference -> 根目錄欄位
        if "tcm_inference" in l2_result:
            inf = l2_result["tcm_inference"]
            if isinstance(inf, dict):
                return inf.get("primary_pattern") or inf.get("primary_syndrome") or ""
        
        return l2_result.get("primary_pattern") or l2_result.get("primary_syndrome") or ""

    @staticmethod
    def extract_l1_metrics(l1_result: Dict) -> Dict[str, Any]:
        """提取 L1 檢索策略指標 (實驗五)"""
        metrics = {
            "L1_Strategy": "N/A",
            "L1_Alpha": 0.55, # Baseline 預設值
            "L1_Confidence": 0.0
        }
        if not l1_result: return metrics

        # 讀取策略
        strat = l1_result.get("retrieval_strategy", {})
        if isinstance(strat, dict):
            metrics["L1_Strategy"] = strat.get("strategy_type", "N/A")
            metrics["L1_Alpha"] = strat.get("decided_alpha", 0.55)
        
        # 讀取置信度
        metrics["L1_Confidence"] = l1_result.get("overall_confidence", 0.0)
        return metrics

    @staticmethod
    def extract_evidence_count(l2_result: Dict) -> int:
        """提取證據引用數量 (實驗三)"""
        if not l2_result: return 0
        count = 0
        # 檢查權威引用
        refs = l2_result.get("authority_references", [])
        if isinstance(refs, list): count += len(refs)
        # 檢查現代證據
        evi = l2_result.get("modern_evidence", [])
        if isinstance(evi, list): count += len(evi)
        # 檢查知識補充
        know = l2_result.get("knowledge_supplements", [])
        if isinstance(know, list): count += len(know)
        return count

# ==================== 2. 實驗執行核心 ====================
class ExperimentRunner:
    def __init__(self, yaml_path: str):
        self.yaml_path = yaml_path
        
    def load_cases(self) -> List[Dict]:
        if not os.path.exists(self.yaml_path):
            print(f"❌ 錯誤：找不到測試檔案 {self.yaml_path}")
            return []
            
        try:
            with open(self.yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data.get("test_cases", [])
        except Exception as e:
            print(f"❌ 讀取 YAML 失敗: {e}")
            return []

    def call_api(self, payload: Dict) -> Dict:
        headers = {"Content-Type": "application/json"}
        
        for attempt in range(Config.RETRY_COUNT + 1):
            try:
                response = requests.post(
                    Config.API_URL, 
                    json=payload, 
                    headers=headers, 
                    timeout=Config.TIMEOUT
                )
                
                # [FIX] 關鍵修正：將 HTTP 狀態碼注入回傳資料中
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict):
                        data["status_code"] = 200
                    return data
                
                # 處理 422 安全攔截
                if response.status_code == 422:
                    return {"status_code": 422, "error": response.json()}
                
                # 其他錯誤
                print(f"⚠️ API 回傳錯誤碼: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"⚠️ API 請求逾時 (嘗試 {attempt+1})")
            except Exception as e:
                print(f"⚠️ 連線錯誤: {e}")
                time.sleep(1)
        
        return {"status_code": 500, "error": "Connection Failed"}

    def run_experiment(self, mode: str):
        cases = self.load_cases()
        if not cases: return

        results = []
        # 加入 timestamp 避免覆蓋
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = f"experiment_results_{mode}_{timestamp}.csv"
        
        print(f"🚀 開始執行實驗 v6.0 | 模式: {mode} | 案例數: {len(cases)}")
        print(f"💾 結果將儲存至: {output_file}\n")

        for i, case in enumerate(cases):
            case_id = case["id"]
            expected = case["expected_diagnosis"]
            rounds_data = case.get("rounds", [])
            
            # 每個案例使用獨立的 Session ID
            session_id = str(uuid.uuid4())
            
            print(f"[{i+1}/{len(cases)}] {case_id} 正在執行 ({len(rounds_data)} 輪)...")
            
            for r_idx, round_input in enumerate(rounds_data):
                round_num = r_idx + 1
                question = round_input["question"]
                
                # 準備請求 Payload
                payload = {
                    "question": question,
                    "session_id": session_id,
                    "mode": mode,  # 傳遞模式給後端 (若後端支援)
                    "continue_spiral": True # 始終視為螺旋對話
                }
                
                # 記錄開始時間
                start_ts = time.time()
                
                # 呼叫 API
                resp = self.call_api(payload)
                
                # 計算延遲
                latency = time.time() - start_ts
                
                # 變數初始化
                error_msg = ""
                pred_pattern = ""
                evi_count = 0
                converged = False
                l1_metrics = {"L1_Strategy": "N/A", "L1_Alpha": 0.55, "L1_Confidence": 0.0}
                
                status_code = resp.get("status_code")

                if status_code == 200:
                    # 成功：提取各層數據
                    l1 = resp.get("l1", {})
                    l2 = resp.get("l2", {})
                    
                    pred_pattern = DataExtractor.extract_pattern(l2)
                    converged = resp.get("converged", False)
                    evi_count = DataExtractor.extract_evidence_count(l2)
                    l1_metrics = DataExtractor.extract_l1_metrics(l1)
                    
                elif status_code == 422:
                    # 安全攔截
                    error_msg = "Security_Block"
                    detail = resp.get("error", {}).get("detail", {})
                    if isinstance(detail, dict):
                        # 嘗試抓取具體的攔截原因 (如 input_sanitizer)
                        violations = detail.get("violations", [])
                        if violations:
                            error_msg = f"Blocked: {violations}"
                else:
                    # 其他 API 錯誤
                    error_msg = f"API_Error_{status_code}"

                # 整合該輪數據
                row = {
                    "CaseID": case_id,
                    "Mode": mode,
                    "Round": round_num,
                    "Question": question[:30] + "...", # 記錄問題摘要
                    "Latency": round(latency, 4),
                    "PredPattern": pred_pattern,
                    "Expected": expected,
                    "EvidenceCount": evi_count,
                    "L1_Strategy": l1_metrics["L1_Strategy"],
                    "L1_Alpha": l1_metrics["L1_Alpha"],
                    "L1_Confidence": l1_metrics["L1_Confidence"],
                    "Converged": converged,
                    "Error": error_msg,
                    "SessionID": session_id
                }
                results.append(row)
                
                # 進度條顯示
                status_icon = "✅" if not error_msg else "❌"
                print(f"   Round {round_num}: {status_icon} (Lat: {latency:.2f}s, Diag: {pred_pattern or 'N/A'})")

                # 如果遇到嚴重錯誤 (非安全攔截)，則中斷該案例後續回合
                # 註：安全攔截 (422) 有時是測試的一部分，不一定要中斷
                if status_code == 500: 
                    print("   ⚠️ 遇到系統錯誤，跳過此案例後續回合")
                    break
                
                # 避免請求過快
                time.sleep(0.5)
            
            print("-" * 50)
            
            # 實時存檔 (每跑完一個案例就存一次，避免崩潰全丟)
            try:
                df = pd.DataFrame(results)
                df.to_csv(output_file, index=False, encoding="utf-8-sig")
            except Exception as e:
                print(f"⚠️ 存檔失敗: {e}")

        print(f"\n🎉 實驗結束！共收集 {len(results)} 筆數據。")

if __name__ == "__main__":
    # 使用方式: python thesis_experiment_runner_v5.py [Agentic|Baseline]
    target_mode = sys.argv[1] if len(sys.argv) > 1 else "Agentic"
    runner = ExperimentRunner(Config.YAML_FILE)
    runner.run_experiment(target_mode)