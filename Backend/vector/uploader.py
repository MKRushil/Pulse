"""
負責將病歷與診斷推理整合，並上傳到 Weaviate（支援 Case/PCD）
- 支援個人欄位展平，便於快查、匿名處理、向量查詢
- 支援 llm_struct, raw_case 以字串形式存入
"""

import os
import json
from datetime import datetime
from vector.embedding import generate_embedding
from vector.schema import get_weaviate_client, get_case_schema

UPLOAD_CASE_CLASS = True
UPLOAD_PCD_CLASS = True

def flatten_case_data(case_data):
    """
    將病歷中的 basic 欄位與常見欄位展平（以利儲存、查詢）
    """
    flat = {}
    # 基本資料
    for k in ["name", "gender", "age", "phone", "address"]:
        flat[k] = case_data.get("basic", {}).get(k, "")
    # 可擴充檢查、問診等欄位
    # ex: flat.update(case_data.get("inspection", {}))
    # id → patient_id
    flat["patient_id"] = case_data.get("basic", {}).get("id", "")
    return flat

def upload_case_vector(case_path: str, diagnosis_result: dict):
    """
    上傳病歷資料到 Weaviate，並支援個資展平與 llm_struct/json 字串化
    """
    if not os.path.exists(case_path):
        print(f"[Uploader] 病歷檔案不存在: {case_path}")
        return

    with open(case_path, 'r', encoding='utf-8') as f:
        case_data = json.load(f)

    llm_struct = diagnosis_result.get("llm_struct", {})
    summary = diagnosis_result.get("summary", "")
    timestamp = diagnosis_result.get("timestamp") or datetime.now().isoformat()

    # 展平個人資訊
    flat_person = flatten_case_data(case_data)

    # 組合資料
    record = {
        "case_id": os.path.basename(case_path),
        "timestamp": timestamp,
        "summary": summary,
        "llm_struct": json.dumps(llm_struct, ensure_ascii=False),  # 字串
        "raw_case": json.dumps(case_data, ensure_ascii=False),     # 字串
        **flat_person
    }

    # 語意向量產生
    embed_text = summary or json.dumps(case_data, ensure_ascii=False)
    embedding = generate_embedding(embed_text, input_type="passage")
    if hasattr(embedding, 'tolist'):
        embedding = embedding.tolist()

    # 上傳 Weaviate
    client = get_weaviate_client()
    case_schema = get_case_schema()
    if UPLOAD_CASE_CLASS:
        try:
            client.data_object.create({
                **record,
                "vector": embedding
            }, class_name=case_schema["case"])
        except Exception as e:
            print(f"[Uploader] case 上傳失敗: {e}")
    if UPLOAD_PCD_CLASS:
        try:
            client.data_object.create({
                **record,
                "vector": embedding
            }, class_name=case_schema["PCD"])
        except Exception as e:
            print(f"[Uploader] PCD 上傳失敗: {e}")

    print(f"[Uploader] 上傳完成: {record['case_id']}")
