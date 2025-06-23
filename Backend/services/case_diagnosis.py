# services/case_diagnosis.py
import os, json, requests
from patient_case_diagnosis_module import process_case_and_generate_prompt
from config import LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME
from fastapi.responses import JSONResponse

SAVE_DIR = './data'
RESULT_DIR = './result'
os.makedirs(RESULT_DIR, exist_ok=True)

def diagnose_case(data: dict):
    file_name = data.get("file")
    file_path = os.path.join(SAVE_DIR, file_name)

    if not os.path.exists(file_path):
        return JSONResponse({"error": "檔案不存在"}, status_code=404)

    with open(file_path, 'r', encoding='utf-8') as f:
        case_data = json.load(f)

    result = process_case_and_generate_prompt(case_data)

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "user", "content": result["模型診斷Prompt"]}
        ]
    }
    try:
        response = requests.post(f"{LLM_API_URL}/chat/completions", headers=headers, json=body)
        response_data = response.json()
        result["模型診斷結果"] = response_data.get("choices", [{}])[0].get("message", {}).get("content", "無診斷結果")
    except Exception as e:
        result["模型診斷結果"] = f"呼叫模型失敗：{str(e)}"

    base_name = os.path.splitext(file_name)[0]
    result_file = f"{base_name}_summary.json"
    result_path = os.path.join(RESULT_DIR, result_file)
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return {
        "status": "ok",
        "summary": result["病歷摘要"],
        "prompt": result["模型診斷Prompt"],
        "llm_result": result["模型診斷結果"],
        "result_file": result_file,
        "result_path": result_path
    }