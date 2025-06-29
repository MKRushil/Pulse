from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import logging

from cases.case_storage import save_case_data
from cases.case_diagnosis import diagnose_case
# from cases.result_listing import list_all_results
from cbr.spiral_a import spiral_a_query
from cbr.spiral_b import spiral_b_query
from vector.schema import get_weaviate_client

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# 1. 儲存病歷（由前端表單送出）
@app.post("/api/case/save")
async def save_case(request: Request):
    data = await request.json()
    return save_case_data(data)

# 2. 執行診斷，產生摘要/推理（給表單結果回存用）
@app.post("/api/diagnose")
async def diagnose_case_entry(request: Request):
    data = await request.json()
    return diagnose_case(data)

# 3. 查詢個案資訊（前端 CaseChat 專用，查 PCD class by patient_id）
@app.post("/api/patient/info")
async def get_patient_info(request: Request):
    data = await request.json()
    patient_id = data.get("patient_id")
    client = get_weaviate_client()
    res = client.query.get(
        "PCD",
        ["patient_id", "name", "gender", "age", "timestamp"]
    ).with_where({
        "path": ["patient_id"], "operator": "Equal", "valueString": patient_id
    }).with_limit(1).do()
    hits = res.get("data", {}).get("Get", {}).get("PCD", [])
    if not hits:
        return JSONResponse({"found": False})
    p = hits[0]
    patient = {
        "id": p.get("patient_id"),
        "name": p.get("name"),
        "gender": p.get("gender"),
        "age": p.get("age"),
        "lastVisit": (p.get("timestamp") or "")[:10]
    }
    return JSONResponse({"found": True, "patient": patient})

# 4. 問診查詢診斷（自動分流 spiral_a/spiral_b）
@app.post("/api/query")
async def query_endpoint(request: Request):
    data = await request.json()
    patient_id = data.get("patient_id")
    question = data.get("question") or data.get("query")
    logging.info(f"收到查詢請求: patient_id={patient_id}, question={question}")
    if patient_id:
        logging.info(f"進行個案查詢（spiral_b），patient_id={patient_id}")
        result = spiral_b_query(patient_id, question)
        logging.info(f"spiral_b return 結果: {result}")
        return JSONResponse(result)
    else:
        logging.info("進行一般診斷對話（spiral_a 查詢）")
        result = spiral_a_query(question)
        logging.info(f"spiral_a return 結果: {result}")
        return JSONResponse(result)

# 5. 掛載靜態檔案（React/Vite打包後的前端）
static_dir = os.path.join(os.path.dirname(__file__), "..", "ui")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 6. 首頁 index.html
@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))
