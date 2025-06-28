from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging

# 引入分層模組服務
from cases.case_storage import save_case_data
from cases.case_diagnosis import diagnose_case
#from cases.result_listing import list_all_results
#from cbr.query_router import route_query
from cbr.spiral_a import spiral_a_query


app = FastAPI()
logging.basicConfig(level=logging.INFO)

# 1. 儲存病歷
@app.post("/api/case/save")
async def save_case(request: Request):
    data = await request.json()
    return save_case_data(data)

# 2. 執行診斷並產生摘要與推理
@app.post("/api/diagnose")
async def diagnose_case_entry(request: Request):
    data = await request.json()
    return diagnose_case(data)

# 3. 歷史診斷摘要列出（未來可篩選）
# @app.get("/api/result/list")
# async def list_results():
#     return list_all_results()

# 4. 查詢診斷（使用案例推理）
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

app = FastAPI()
logging.basicConfig(level=logging.INFO)

@app.post("/api/query")
async def query_endpoint(request: Request):
    print("進入 /api/query")
    data = await request.json()
    print("收到資料:", data)
    patient_id = data.get("patient_id")
    question = data.get("question") or data.get("query")
    logging.info(f"收到查詢請求: patient_id={patient_id}, question={question}")

    if patient_id:
        logging.info(f"進行個案查詢，patient_id={patient_id}")
        return JSONResponse({
            "type": "case",
            "patient_id": patient_id,
            "answer": f"這是針對個案 {patient_id} 的回覆，問句為：{question}"
        })
    else:
        logging.info("進行一般診斷對話（spiral_a 查詢）")
        result = spiral_a_query(question)
        print("spiral_a return 結果:", result)
        return JSONResponse(result)


# 5. 掛載靜態網頁資料夾（前端 build 結果）
static_dir = os.path.join(os.path.dirname(__file__), "..", "ui")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 6. 前端入口頁
@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))
