# llm/llm_executor.py
"""
-----------------
1. 發送 prompt 給 LLM (NVIDIA/OpenAI chat api)
2. 支援正則化解析主病、次病、權重、推理說明 (extract_diagnosis_result)
3. 可回傳原始 response 及結構化資料，便於可視化、推理鏈存檔
"""
import requests
import re
from config import LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME

def run_llm_diagnosis(prompt: str):
    """
    發送 prompt 給 LLM，回傳 (原始回答, 結構化診斷 dict)
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
        content = content.strip()
        parsed = extract_diagnosis_result(content)
        return content, parsed
    except Exception as e:
        return f"[LLM 呼叫錯誤] {str(e)}", {}

def extract_diagnosis_result(response: str):
    """
    解析 LLM 回應，萃取主病/次病/權重/推理說明，回傳結構化 dict
    """
    result = {"主病": [], "次病": [], "推理說明": ""}
    # 主病正則
    main_pattern = r"主病[:：][\s\S]*?(- .+?\([\d.]+\)[\s\S]*?)(?:次病|推理說明|$)"
    # 次病正則
    sub_pattern = r"次病[:：][\s\S]*?(- .+?\([\d.]+\)[\s\S]*?)(?:主病|推理說明|$)"
    # 條列擷取
    item_pattern = r"- (.+?)\((0?\.?\d+)\)"
    # 推理說明
    reasoning_pattern = r"推理說明[:：]([\s\S]*)"

    main_match = re.search(main_pattern, response)
    sub_match = re.search(sub_pattern, response)
    reasoning_match = re.search(reasoning_pattern, response)

    if main_match:
        result["主病"] = re.findall(item_pattern, main_match.group(1))
    if sub_match:
        result["次病"] = re.findall(item_pattern, sub_match.group(1))
    if reasoning_match:
        result["推理說明"] = reasoning_match.group(1).strip()
    return result
