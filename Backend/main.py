from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# 引入分層模組服務
from cases.case_storage import save_case_data
from cases.case_diagnosis import diagnose_case
#from cases.result_listing import list_all_results
from cbr.query_router import route_query

app = FastAPI()

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
@app.post("/api/query")
async def query_entry(request: Request):
    data = await request.json()
    return route_query(data)

# 5. 掛載靜態網頁資料夾（前端 build 結果）
static_dir = os.path.join(os.path.dirname(__file__), "..", "ui")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 6. 前端入口頁
@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))
