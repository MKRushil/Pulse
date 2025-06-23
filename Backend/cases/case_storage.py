# cases/case_storage.py
import os, json, time
from fastapi.responses import JSONResponse
from cases.case_diagnosis import diagnose_case
from vector.uploader import upload_case_vector

SAVE_DIR = './data'
os.makedirs(SAVE_DIR, exist_ok=True)

def nowstr():
    return time.strftime('%Y%m%d_%H%M%S')

def save_case_data(data: dict):
    # 1. 儲存病歷資料
    pid = data.get('basic', {}).get('id', 'xxxx')
    timestamp = nowstr()
    fname = f"{timestamp}_{pid}.json"
    fpath = os.path.join(SAVE_DIR, fname)
    with open(fpath, 'w', encoding='utf8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 2. 執行診斷與摘要生成
    diagnosis_input = {"file": fname}
    diagnosis_result = diagnose_case(diagnosis_input)

    # 3. 自動觸發向量上傳（含摘要與權重）
    upload_case_vector(fpath, diagnosis_result)

    return JSONResponse({
        "status": "ok",
        "file": fname,
        "path": fpath,
        "diagnosis_result": diagnosis_result
    })
