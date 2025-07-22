# llm/llm_executor.py
"""
llm_executor.py
-----------------
1. 發送 prompt 給 LLM（支援 NVIDIA、OpenAI 等 chat api）
2. 支援兩類呼叫：
   - run_llm_text：單純送 prompt 得文字（適用各步驟/摘要）
   - run_llm_diagnosis：送 prompt 得回答，並正則解析主病/次病/權重/推理說明
3. extract_diagnosis_result：正則解析 LLM output，結構化診斷 dict
4. 回傳原始 response 及結構化資料，便於可視化、推理鏈存檔
"""

import requests
import re
from config import LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME

def run_llm_text(prompt: str):
    """
    發送 prompt 給 LLM，單純回傳原文
    適用於摘要、Chain 步驟一等純文字處理
    """
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        resp = requests.post(f"{LLM_API_URL}/chat/completions", headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        # 兼容 NVIDIA / OpenAI 回應格式
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            content = result.get("choices", [{}])[0].get("text", "")
        return content.strip()
    except Exception as e:
        return f"[LLM 呼叫錯誤] {str(e)}"

def run_llm_diagnosis(prompt: str):
    """
    發送 prompt 給 LLM，並正則解析主病、次病、權重、推理說明
    回傳 (原始回覆, 結構化 dict)
    """
    raw = run_llm_text(prompt)
    parsed = extract_diagnosis_result(raw)
    return raw, parsed

def extract_diagnosis_result(response: str):
    """
    用正則表達式解析 LLM 回應，萃取主病/次病/權重/推理說明
    適用於 Chain step2 或單步診斷 prompt
    """
    result = {"主病": [], "次病": [], "推理說明": ""}
    lines = response.strip().splitlines()
    phase = "主病"
    for line in lines:
        line = line.strip()
        if line.startswith("-") and "權重" in line:
            try:
                name = line.split("（權重")[0].replace("-", "").strip()
                weight = float(line.split("（權重")[-1].replace("）", ""))
                result[phase].append((name, weight))
            except:
                continue
        elif "推理說明" in line or "解釋" in line:
            phase = "推理說明"
        elif phase == "推理說明":
            result["推理說明"] += line + "\n"
    result["推理說明"] = result["推理說明"].strip()
    return result

# --- 範例：多步 Chain-of-Thought 整合自動推理 ---
def multi_stage_diagnosis(summary: str):
    """
    範例：兩階段 Chain of Thought 推理診斷（先摘要、再診斷）
    """
    from llm.prompt_builder import build_prompt_stage1, build_prompt_stage2
    # Step 1: 條列摘要
    prompt1 = build_prompt_stage1(summary)
    abstract = run_llm_text(prompt1)
    # Step 2: 推理診斷
    prompt2 = build_prompt_stage2(abstract)
    raw, struct = run_llm_diagnosis(prompt2)
    return {
        "prompt1": prompt1,
        "step1_output": abstract,
        "prompt2": prompt2,
        "step2_output": raw,
        "llm_struct": struct
    }



