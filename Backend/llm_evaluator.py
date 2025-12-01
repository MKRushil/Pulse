# -*- coding: utf-8 -*-
"""
SCBR LLM 評分系統 (LLM-based Evaluator)
===========================================
功能：
1. 讀取實驗產生的 CSV。
2. 調用外部 LLM (如 GPT-4, Claude, 或您的 Llama 3) 進行評分。
3. 評分標準：0.0 (完全錯誤) ~ 1.0 (完全正確)。
"""

import pandas as pd
import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

# ==================== LLM 配置 (請填入您的資訊) ====================
LLM_CONFIG = {
    "api_url": "https://integrate.api.nvidia.com/v1/chat/completions", # 您的 API URL
    "api_key": "nvapi-xxxx", # 您的 Key
    "model_name": "meta/llama-3.3-70b-instruct" # 您的 Model Name
}

INPUT_CSV = "experiment_results_Agentic_v5.csv"
OUTPUT_CSV = "experiment_results_Agentic_Scored.csv"

def get_llm_score(pred, expected):
    """
    呼叫 LLM 進行評分
    """
    if pd.isna(pred) or not pred: return 0.0
    
    prompt = f"""
    你是中醫診斷評估專家。請評估以下兩個診斷結果的語意相似度。
    
    標準診斷: "{expected}"
    模型預測: "{pred}"
    
    請給出一個 0.0 到 1.0 之間的分數：
    - 1.0: 完全一致或同義詞 (如 不寐=失眠, 肝鬱氣滯=肝氣鬱結)
    - 0.8: 高度相似，核心證型正確但有細微差異 (如 心脾兩虛 vs 心脾不足)
    - 0.5: 部分正確，命中部分關鍵字 (如 腎陰虛 vs 腎虛)
    - 0.0: 完全錯誤或不相關
    
    請只輸出分數數字，不要有其他文字。
    """
    
    payload = {
        "model": LLM_CONFIG["model_name"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 10
    }
    
    try:
        resp = requests.post(
            LLM_CONFIG["api_url"], 
            json=payload, 
            headers={"Authorization": f"Bearer {LLM_CONFIG['api_key']}"},
            timeout=10
        )
        content = resp.json()['choices'][0]['message']['content'].strip()
        return float(content)
    except Exception as e:
        print(f"⚠️ LLM 評分失敗: {e}")
        return 0.0

def process_row(row):
    # 如果有 Error，直接給 0 分
    if pd.notna(row.get('Error')) and row['Error']:
        return 0.0
        
    return get_llm_score(row['PredPattern'], row['Expected'])

def main():
    print(f"📖 讀取檔案: {INPUT_CSV} ...")
    df = pd.read_csv(INPUT_CSV)
    
    print("🚀 開始 LLM 評分 (這可能需要一點時間)...")
    
    # 使用多執行緒加速評分
    with ThreadPoolExecutor(max_workers=5) as executor:
        scores = list(executor.map(process_row, [row for _, row in df.iterrows()]))
    
    df['LLM_Score'] = scores
    
    avg_score = df['LLM_Score'].mean()
    print("-" * 40)
    print(f"📊 平均語意準確率 (LLM Score): {avg_score:.2%}")
    print("-" * 40)
    
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"✅ 評分完成，已儲存至: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()