# cases/case_diagnosis.py
"""
模組說明：
- 對原始病歷進行語意摘要與病情權重分析
- 產生語意向量存庫時，嵌入用 input_type="passage"
- 推理、摘要與存庫全流程
"""
import os, json, datetime
from llm.prompt_builder import build_prompt_from_case
from llm.llm_executor import run_llm_diagnosis
from vector.embedding import generate_embedding

DATA_DIR = './data'
SUMMARY_DIR = './result/summary'
CHAIN_DIR = './result/reasoning_chain'

os.makedirs(SUMMARY_DIR, exist_ok=True)
os.makedirs(CHAIN_DIR, exist_ok=True)

def nowstr():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def diagnose_case(data: dict):
    """
    主診斷流程（產生摘要、prompt、語意向量，input_type=passage）
    """
    file_name = data.get('file')
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        return {"error": "檔案不存在"}

    # 1. 載入原始病歷
    with open(file_path, 'r', encoding='utf-8') as f:
        case_data = json.load(f)
    # 2. 產生摘要
    summary = generate_case_summary(case_data)
    # 3. 建 prompt
    prompt = build_prompt_from_case(case_data, summary)
    # 4. 調用 LLM
    llm_output, llm_struct = run_llm_diagnosis(prompt)
    # 5. 儲存診斷主摘要
    base_name = os.path.splitext(file_name)[0]
    summary_path = os.path.join(SUMMARY_DIR, f"{base_name}_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            "case_file": file_name,
            "summary": summary,
            "prompt": prompt,
            "llm_output": llm_output,
            "llm_struct": llm_struct,
            "timestamp": nowstr()
        }, f, ensure_ascii=False, indent=2)
    # 6. 儲存推理鏈
    chain_path = os.path.join(CHAIN_DIR, f"{base_name}_chain.jsonl")
    chain_record = {
        "case_file": file_name,
        "summary": summary,
        "prompt": prompt,
        "llm_output": llm_output,
        "llm_struct": llm_struct,
        "timestamp": nowstr()
    }
    with open(chain_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(chain_record, ensure_ascii=False) + '\n')

    # 7. 產生語意向量（input_type = 'passage'，供進階應用/比對）
    case_vec = generate_embedding(summary, input_type="passage")

    return {
        "status": "ok",
        "summary_file": os.path.basename(summary_path),
        "chain_file": os.path.basename(chain_path),
        "llm_output": llm_output,
        "llm_struct": llm_struct,
        "embedding": case_vec.tolist() if case_vec is not None else None
    }

# --- 病歷摘要產生範例 ---
def generate_case_summary(case):
    basic = case.get('basic', {})
    inquiry = case.get('inquiry', {})
    lines = [
        f"{basic.get('gender','')}，{basic.get('age','')}歲，{basic.get('name','')}。主訴：{inquiry.get('mainSymptom','')}（嚴重度：{inquiry.get('mainSeverity','')})。"
    ]
    # 加入次要症狀、補充
    symptoms = inquiry.get('symptoms', []) + inquiry.get('spirit', [])
    if symptoms:
        lines.append("伴隨症狀：「" + "、".join(symptoms) + "」。")
    if inquiry.get('otherSymptom'):
        lines.append(f"其它補充：{inquiry['otherSymptom']}。")
    return " ".join(lines)
