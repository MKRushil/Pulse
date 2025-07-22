# vector/uploader.py（同步更新欄位結構，對應 PulsePJ + LLM 雙軌推理結果）
import os
import json
from datetime import datetime
import time
from vector.embedding import generate_embedding
from vector.schema import get_weaviate_client, get_case_schema

UPLOAD_CASE_CLASS = True
UPLOAD_PCD_CLASS = True

def is_valid_llm_struct(llm_struct):
    if not llm_struct or not isinstance(llm_struct, dict):
        return False
    if any([
        llm_struct.get("主病"),
        llm_struct.get("次病"),
        llm_struct.get("推理說明"),
    ]):
        return True
    return False

def upload_case_vector(case_path: str, diagnosis_result: dict):
    start_time = time.time()
    print(f"[Uploader] 開始處理檔案：{case_path}")

    if not os.path.exists(case_path):
        print(f"[Uploader] 病歷檔案不存在: {case_path}")
        return

    with open(case_path, 'r', encoding='utf-8') as f:
        case_data = json.load(f)

    llm_struct = diagnosis_result.get("llm_struct", {})
    summary = diagnosis_result.get("summary_segments")
    summary_text = diagnosis_result.get("summary")
    timestamp = diagnosis_result.get("timestamp") or datetime.now().isoformat()

    if not summary_text or not is_valid_llm_struct(llm_struct):
        print(f"[Uploader] summary 或 llm_struct 為空或無效，不進行上傳: {os.path.basename(case_path)}")
        return

    print("[Uploader] 載入 diagnosis_result 完成，準備組合資料")

    case_raw_case = {
        "inspection": case_data.get("inspection", {}),
        "inquiry": case_data.get("inquiry", {}),
        "pulse": case_data.get("pulse", {})
    }

    record = {
        "case_id": os.path.basename(case_path),
        "timestamp": timestamp,
        "summary": summary_text,
        "summary_segments": json.dumps(summary, ensure_ascii=False),
        "llm_struct": json.dumps(llm_struct, ensure_ascii=False),
        "main_disease": diagnosis_result.get("main_disease", ""),
        "sub_diseases": json.dumps(diagnosis_result.get("sub_diseases", []), ensure_ascii=False),
        "semantic_scores": json.dumps(diagnosis_result.get("semantic_scores", {}), ensure_ascii=False),
        "embedding": diagnosis_result.get("embedding"),
        "raw_case": json.dumps(case_raw_case, ensure_ascii=False),
        "source_model": diagnosis_result.get("source_model", ""),
        "source_score_method": diagnosis_result.get("source_score_method", ""),
        "llm_main_disease": diagnosis_result.get("llm_main_disease", ""),
        "formula_main_disease": diagnosis_result.get("formula_main_disease", ""),
        "score_error_formula": diagnosis_result.get("score_error_formula", 0)
    }

    print("[Uploader] 整合 Case 向量資料完成，準備上傳")

    case_schema = get_case_schema()
    client = get_weaviate_client()

    if UPLOAD_CASE_CLASS:
        try:
            client.data_object.create(record, class_name=case_schema["case"])
            print(f"[Uploader] Case 上傳成功：{record['case_id']}\n")
        except Exception as e:
            print(f"[Uploader] Case 上傳失敗：{record['case_id']}，錯誤：{e}")

    if UPLOAD_PCD_CLASS:
        basic = case_data.get("basic", {})
        pcd_record = {
            "case_id": os.path.basename(case_path),
            "timestamp": timestamp,
            "summary": summary_text,
            "llm_struct": json.dumps(llm_struct, ensure_ascii=False),
            "patient_id": basic.get("id", ""),
            "name": basic.get("name", ""),
            "age": str(basic.get("age", "")),
            "gender": basic.get("gender", ""),
            "phone": basic.get("phone", ""),
            "address": basic.get("address", ""),
            "main_disease": diagnosis_result.get("main_disease", ""),
            "sub_diseases": json.dumps(diagnosis_result.get("sub_diseases", []), ensure_ascii=False),
            "semantic_scores": json.dumps(diagnosis_result.get("semantic_scores", {}), ensure_ascii=False),
            "embedding": diagnosis_result.get("embedding"),
            "source_model": diagnosis_result.get("source_model", ""),
            "source_score_method": diagnosis_result.get("source_score_method", ""),
            "llm_main_disease": diagnosis_result.get("llm_main_disease", ""),
            "formula_main_disease": diagnosis_result.get("formula_main_disease", ""),
            "score_error_formula": diagnosis_result.get("score_error_formula", 0)
        }
        try:
            client.data_object.create(pcd_record, class_name=case_schema["PCD"])
            print(f"[Uploader] PCD 上傳成功：{pcd_record['case_id']}\n")
        except Exception as e:
            print(f"[Uploader] PCD 上傳失敗：{pcd_record['case_id']}，錯誤：{e}")

    total_time = time.time() - start_time
    print(f"[Uploader] 上傳流程結束：{record['case_id']}，總耗時：{total_time:.2f} 秒\n")
