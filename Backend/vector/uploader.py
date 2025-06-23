# vector/uploader.py
"""
模組說明：
本檔案負責將「病歷（原始資料）＋診斷摘要＋推理權重」整合後，自動上傳至 Weaviate 或其他向量庫。

流程：
1. 載入病歷原始檔（如 ./data/20250621_1234.json）
2. 解析診斷結果（摘要/主病/次病/權重等）
3. 呼叫 embedding.py 產生語意向量（支援 case/PCD 多種 class）
4. 調用 schema.py 取得向量庫 schema 及連線
5. 組合資料並上傳至 Weaviate
6. 支援附加時間戳、追蹤 ID，並保留所有原始資訊

套件需求：
- weaviate-client（Python 官方）
- numpy
- 自訂 embedding.py/schema.py

可配合 case_storage.py 自動觸發，每筆診斷即時入庫，支援語意檢索與 CBR。
"""
import os
import json
from datetime import datetime
from vector.embedding import generate_embedding
from vector.schema import get_weaviate_client, get_case_schema

# 設定：是否要同時存 PCD（個案）與 case（通用）兩種 class
UPLOAD_CASE_CLASS = True
UPLOAD_PCD_CLASS = True

# 上傳主流程

def upload_case_vector(case_path: str, diagnosis_result: dict):
    """
    將病歷原始資料 + 診斷摘要 + 推理權重結構整合，產生語意向量，
    並上傳至 Weaviate。
    參數：
    - case_path: 原始病歷 JSON 檔案路徑
    - diagnosis_result: 診斷結果 dict（來自 case_diagnosis.py）
    """
    if not os.path.exists(case_path):
        print(f"[Uploader] 病歷檔案不存在: {case_path}")
        return
    with open(case_path, 'r', encoding='utf-8') as f:
        case_data = json.load(f)

    # 取得摘要/推理結構
    llm_struct = diagnosis_result.get("llm_struct", {})
    summary = diagnosis_result.get("summary", "")
    timestamp = diagnosis_result.get("timestamp") or datetime.now().isoformat()

    # 1. 組合資料 (可根據 schema.py 動態擴充)
    record = {
        "case_id": os.path.basename(case_path),
        "timestamp": timestamp,
        "summary": summary,
        "llm_struct": llm_struct,
        "raw_case": case_data
    }

    # 2. 語意向量產生（可自定義：全文摘要/多欄合併/主次病分開）
    embed_text = summary or json.dumps(case_data, ensure_ascii=False)
    embedding = generate_embedding(embed_text, input_type="passage")

    # 3. 上傳到 Weaviate
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
