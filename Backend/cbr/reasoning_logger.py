# cbr/reasoning_logger.py
"""
推理鏈紀錄工具：
- 統一記錄每次 CBR 查詢的 reasoning_chain、推理樹(tree)、meta等
- 供後端驗證、前端視覺化、批次分析
"""
import json
from datetime import datetime
import os

LOG_DIR = './result/reasoning_log/'
os.makedirs(LOG_DIR, exist_ok=True)

def log_reasoning(case_id, chain, tree=None, meta=None):
    """
    記錄推理鏈與樹狀結構
    case_id: 查詢識別（可用查詢內容hash或case_id）
    chain: 推理步驟list
    tree: 樹狀結構dict（選用）
    meta: 其他補充資訊dict（選用）
    """
    data = {
        "case_id": case_id,
        "timestamp": datetime.now().isoformat(),
        "reasoning_chain": chain,
        "tree": tree,
        "meta": meta or {}
    }
    log_file = os.path.join(LOG_DIR, f"{case_id}_reasoning.json")
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[ReasoningLogger] 記錄已存 {log_file}")
