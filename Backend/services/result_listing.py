# services/result_listing.py
# ---掃描 ./result/ 中所有 _summary.json 結果檔案，供前端顯示---
import os
from fastapi.responses import JSONResponse

RESULT_DIR = './result'

def list_all_results():
    files = [f for f in os.listdir(RESULT_DIR) if f.endswith('_summary.json')]
    return JSONResponse({"files": sorted(files)})
