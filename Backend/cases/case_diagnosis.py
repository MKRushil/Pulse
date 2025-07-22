# case_diagnosis.py（加入摘要空值防呆與修正 summary 擷取邏輯 + 全摘要餵入 prompt + 更強推理說明萃取）
import os, json, datetime
from llm.prompt_builder import build_prompt_stage1, build_prompt_stage2
from llm.llm_executor import run_llm_text, extract_diagnosis_result
from vector.embedding import generate_embedding
from vector.pulsepj_search import search_pulsepj_main_disease
from cases.parse_case_json import parse_case_json

DATA_DIR = './data'
SUMMARY_DIR = './result/summary'
os.makedirs(SUMMARY_DIR, exist_ok=True)

def nowstr():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def diagnose_case(data: dict):
    file_name = data.get('file')
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        return {"error": "檔案不存在"}

    with open(file_path, 'r', encoding='utf-8') as f:
        case_data = json.load(f)

    print("[Diagnosis] 載入病歷完成，開始摘要與推理流程")

    # 一、五段式摘要拆解
    summary_segments = parse_case_json(case_data)
    print(f"[Diagnosis] 分段摘要：{json.dumps(summary_segments, ensure_ascii=False)}")

    # 二、合併五段摘要成總結文字
    summary = generate_case_summary(case_data)
    if not summary.strip():
        print("[Diagnosis] ⚠️ 摘要為空，無法嵌入與診斷")
        return {"error": "摘要為空，診斷失敗"}

    print("[Diagnosis] 合併摘要完成，開始嵌入與主病查詢")

    # 三、查詢 PulsePJ 主病
    formula_main_disease = search_pulsepj_main_disease(summary)
    sub_diseases = []
    disease_scores = {}

    # 四、LLM 推理主病 + 次病（傳入完整摘要）
    prompt1 = build_prompt_stage1(summary)
    step1_output = run_llm_text(prompt1)
    prompt2 = build_prompt_stage2(step1_output)
    step2_output = run_llm_text(prompt2)

    # 加強推理說明萃取（保留原始全文備查）
    llm_struct = extract_diagnosis_result(step2_output)
    if not llm_struct.get("推理說明"):
        llm_struct["推理說明"] = step2_output  # fallback 使用整段輸出

    print("[LLM] 推理結構：", json.dumps(llm_struct, ensure_ascii=False))

    llm_main_disease = llm_struct.get("主病", [])[0][0] if llm_struct.get("主病") else ""
    score_error_formula = 0 if llm_main_disease == formula_main_disease else 1
    print(f"[Compare] LLM主病：{llm_main_disease} vs PulsePJ主病：{formula_main_disease} → 誤差：{score_error_formula}")

    base_name = os.path.splitext(file_name)[0]
    summary_path = os.path.join(SUMMARY_DIR, f"{base_name}_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            "case_file": file_name,
            "summary": summary,
            "step1_output": step1_output,
            "step2_output": step2_output,
            "llm_struct": llm_struct,
            "semantic_main_disease": formula_main_disease,
            "semantic_scores": disease_scores,
            "llm_main_disease": llm_main_disease,
            "formula_main_disease": formula_main_disease,
            "score_error_formula": score_error_formula,
            "timestamp": nowstr()
        }, f, ensure_ascii=False, indent=2)
    print(f"[Output] 已寫入摘要檔案：{summary_path}")

    # 五、產出嵌入向量
    case_vec = generate_embedding(summary, input_type="passage")
    print("[Embedding] Summary 嵌入向量已完成")

    return {
        "status": "ok",
        "summary_file": os.path.basename(summary_path),
        "llm_output": step2_output,
        "llm_struct": llm_struct,
        "main_disease": formula_main_disease,
        "sub_diseases": sub_diseases,
        "semantic_scores": disease_scores,
        "summary_segments": summary_segments,
        "summary": summary,
        "embedding": case_vec.tolist() if case_vec is not None else None,
        "llm_main_disease": llm_main_disease,
        "formula_main_disease": formula_main_disease,
        "score_error_formula": score_error_formula,
        "source_model": "llama-3-70b-instruct",
        "source_score_method": "PulsePJ向量相似度主病比對",
        "timestamp": nowstr()
    }

def generate_case_summary(case_data: dict) -> str:
    sections = []
    summary_block = case_data.get("summary", case_data)  # 支援 summary 或最外層
    chief = summary_block.get("主訴") or case_data.get("inquiry", {}).get("chiefComplaint", "")
    present = summary_block.get("現病史") or case_data.get("inquiry", {}).get("presentIllness", "")
    if chief.strip():
        sections.append(f"[主訴] {chief.strip()}")
    if present.strip():
        sections.append(f"[現病史] {present.strip()}")
    for key in ["望診", "問診", "脈診"]:
        val = summary_block.get(key, "")
        if val.strip():
            sections.append(f"[{key}] {val.strip()}")
    return "\n".join(sections)
