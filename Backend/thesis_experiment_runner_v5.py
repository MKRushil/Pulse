# -*- coding: utf-8 -*-
"""
SCBR 論文實驗執行器 v5.0 (Robust & Debug Edition)
===========================================
修復：
1. 強健的 JSON 欄位抓取 (支援多種 LLM 輸出格式)。
2. 明確捕捉 L1/L3 安全攔截錯誤 (不會變成空值)。
3. 支援 LLM 評分預留欄位。
"""

import requests
import yaml
import time
import pandas as pd
import uuid
import os
import json
from typing import List, Dict, Any, Optional

# ==================== 配置區域 ====================
class Config:
    API_URL = "http://localhost:8000/api/scbr/v2/diagnose"
    YAML_FILE = "benchmark_cases_spiral.yaml"
    TIMEOUT = 240
    RETRY_COUNT = 2

# ==================== 1. 資料提取器 (核心修復) ====================
class DataExtractor:
    @staticmethod
    def extract_pattern(l2_result: Dict) -> str:
        """
        嘗試從各種可能的路徑提取診斷證型
        """
        if not l2_result: return ""
        
        # 路徑 1: 標準結構
        if "tcm_inference" in l2_result:
            inf = l2_result["tcm_inference"]
            if isinstance(inf, dict):
                return inf.get("primary_pattern") or inf.get("primary_syndrome") or ""
        
        # 路徑 2: 扁平結構
        if "primary_pattern" in l2_result:
            return l2_result["primary_pattern"]
        if "primary_syndrome" in l2_result:
            return l2_result["primary_syndrome"]
            
        # 路徑 3: 容錯 (從 reasoning 或 text 中找)
        # 若真的都沒有，回傳空
        return ""

# ==================== 2. 實驗執行核心 ====================
class ExperimentRunner:
    def __init__(self, yaml_path: str):
        self.yaml_path = yaml_path
        
    def load_cases(self) -> List[Dict]:
        try:
            with open(self.yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data.get("test_cases", [])
        except FileNotFoundError:
            print(f"❌ 找不到 {self.yaml_path}")
            return []

    def call_api(self, payload: Dict) -> Dict:
        headers = {"Content-Type": "application/json"}
        for attempt in range(Config.RETRY_COUNT + 1):
            try:
                response = requests.post(Config.API_URL, json=payload, headers=headers, timeout=Config.TIMEOUT)
                
                # 處理 422 安全攔截 (這是系統功能，不是 Bug)
                if response.status_code == 422:
                    return {"status_code": 422, "error": response.json()}
                
                if response.status_code == 200:
                    return response.json()
                    
            except Exception as e:
                time.sleep(1)
        return {"status_code": 500, "error": "Connection Failed"}

    def run_experiment(self, mode: str):
        cases = self.load_cases()
        results = []
        output_file = f"experiment_results_{mode}_v5.csv"
        
        print(f"🚀 開始執行 v5: {mode} 模式")

        for i, case in enumerate(cases):
            case_id = case["id"]
            expected = case["expected_diagnosis"]
            rounds_data = case.get("rounds", [])
            session_id = str(uuid.uuid4())
            
            print(f"[{i+1}/{len(cases)}] {case_id} ...", end="", flush=True)
            
            for r_idx, round_input in enumerate(rounds_data):
                round_num = r_idx + 1
                payload = {
                    "question": round_input["question"],
                    "session_id": session_id,
                    "continue_spiral": (round_num > 1)
                }
                
                start_ts = time.time()
                resp = self.call_api(payload)
                latency = time.time() - start_ts
                
                # 處理結果
                error_msg = ""
                pred_pattern = ""
                evi_count = 0
                converged = False
                
                if resp.get("status_code") == 422:
                    error_msg = "Security_Block"
                    # 嘗試讀取攔截原因
                    err_detail = resp.get("error", {}).get("detail", {})
                    if isinstance(err_detail, dict):
                        error_msg = f"Blocked: {err_detail.get('error', 'Unknown')}"
                elif resp.get("status_code") == 200:
                    l2 = resp.get("l2", {})
                    pred_pattern = DataExtractor.extract_pattern(l2)
                    converged = resp.get("converged", False)
                    # 簡單計算證據數
                    if "authority_references" in l2:
                        evi_count += len(l2["authority_references"])
                else:
                    error_msg = "API_Error"

                # 記錄 (不計算 Accuracy，交給後續 LLM)
                results.append({
                    "CaseID": case_id,
                    "Mode": mode,
                    "Round": round_num,
                    "Latency": latency,
                    "PredPattern": pred_pattern,
                    "Expected": expected,  # 記錄標準答案方便 LLM 評分
                    "EvidenceCount": evi_count,
                    "Converged": converged,
                    "Error": error_msg,
                    "SessionID": session_id
                })
                
                if error_msg: break # 出錯就跳下一案
                time.sleep(0.2)
            
            print(" Done")
            
            # 實時存檔
            pd.DataFrame(results).to_csv(output_file, index=False, encoding="utf-8-sig")

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "Agentic"
    ExperimentRunner(Config.YAML_FILE).run_experiment(mode)