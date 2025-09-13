# -*- coding: utf-8 -*-
"""
FastAPI 入口（單一路徑 S-CBR 版 / 路線B）
- /api/query 掛接 cbr/spiral.py 單一路徑推理引擎
- 完全移除舊流程 /api/diagnose
- PCD 已移除：/api/patient/info 先回 {found: False} 以相容前端
- 修復 ResourceWarning：TimedRotatingFileHandler(delay=True) + force=True + shutdown hook
- 掛載前端靜態資源與首頁（ui/）
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from pathlib import Path
import sys
import logging
from logging.handlers import TimedRotatingFileHandler

# ---- 專案內部匯入 ----
from cases.case_storage import save_case_data  # 新增病例處理鏈（DCIP）

# 螺旋推理引擎（若尚未完成，容錯處理以免整個 app 起不來）
try:
    from cbr.spiral import run as spiral_run  # 單一路徑 S-CBR 入口
    _spiral_import_error = None
except Exception as _e:
    spiral_run = None
    _spiral_import_error = _e

# -----------------------------------------------------------------------------
# 日誌設定（修復 ResourceWarning：延遲開檔 + force=True + 關閉 hook）
# -----------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
LOG_DIR = BACKEND_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "ingest.log"

console_handler = logging.StreamHandler(sys.stdout)
file_handler = TimedRotatingFileHandler(
    LOG_FILE, when="midnight", backupCount=7, encoding="utf-8", delay=True
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[console_handler, file_handler],
    force=True,  # 重載時重設 handlers，關閉舊把手
)

logger = logging.getLogger("backend.main")

# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(title="TCM Spiral CBR Backend", version="1.0.0")


@app.on_event("startup")
async def _on_startup():
    logger.info("Application startup.")


@app.on_event("shutdown")
async def _on_shutdown():
    # 確保所有 handler 都被 flush/close，避免殘留把手
    root = logging.getLogger()
    for h in list(root.handlers):
        try:
            h.flush()
            h.close()
        except Exception:
            pass
    logger.info("Application shutdown.")


# -----------------------------------------------------------------------------
# 1) 新增病例（由前端 TCMForm.jsx 送出表單 → DCIP 4 步完成去識別入庫）
# -----------------------------------------------------------------------------
@app.post("/api/case/save")
async def api_case_save(request: Request):
    """
    新增病例（去識別化入庫）
    入參：前端表單 JSON（基本資料、主訴、現病史、望問切、暫診…）
    出參：{ ok: bool, case_id?: str, message?: str }
    流程：save_case_data() 內部完成：
        [1/4] 寫原始 JSON → Backend/data/*.json
        [2/4] 去識別化視圖 normalizer.build_deidentified_view()
        [3/4] triage 簡化診斷（summary_text、主/次病 seed）
        [4/4] 向量上傳 uploader.upload_case_vector()（類別：Case）
    """
    data = await request.json()
    return save_case_data(data)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# 2) 問診/診斷查詢（單一路徑 S-CBR）
# -----------------------------------------------------------------------------
@app.post("/api/query")
async def api_query(request: Request):
    """
    問診查詢（S-CBR 單一路徑）
    入參 JSON：
      {
        "question": "...",
        "patient_ctx": {  // 可選：年齡、性別、主訴、暫診等，供 spiral 做過濾/seed
          "age": 35,
          "gender": "女",
          "chief_complaint": "...",
          "provisional_dx": "...",
          ...
        },
        "patient_id": "..."  // 可選：若仍從前端傳入，可包進 patient_ctx 以相容
      }
    出參 JSON（示例）：
      {
        "dialog": "...（可讀文字回答）",
        "llm_struct": {
          "main_dx": "...",
          "sub_dx": ["..."],
          "evidence": ["..."],
          "confidence": 0.86,
          "support_cases": ["uuid1","uuid2"],
          "missing_clues": ["..."]
        },
        "trace_id": "REQ-YYYYMMDD-xxxx"
      }
    """
    body = await request.json()
    question = body.get("question") or body.get("query")
    patient_ctx = body.get("patient_ctx")

    # 兼容：若仍收到 patient_id，把它塞進 patient_ctx，讓 spiral 視需要使用
    if not patient_ctx and body.get("patient_id"):
        patient_ctx = {"patient_id": body.get("patient_id")}

    if not question:
        return JSONResponse({"error": "缺少 question"}, status_code=400)

    # 螺旋引擎尚未就緒的安全回覆（不阻斷其他 API）
    if spiral_run is None:
        logger.error(f"Spiral engine not ready: {_spiral_import_error!r}")
        return JSONResponse(
            {
                "error": "Spiral 引擎尚未就緒，請檢查 cbr/spiral.py::run()",
                "detail": str(_spiral_import_error) if _spiral_import_error else None,
            },
            status_code=503,
        )

    logger.info(f"收到查詢：{question!r} | patient_ctx={patient_ctx!r}")
    try:
        # 建議 spiral_run 回傳 dict：{dialog, llm_struct, trace_id?}
        result = spiral_run(question, patient_ctx=patient_ctx)
        return JSONResponse(result)
    except Exception as e:
        logger.exception("Spiral 引擎處理時發生錯誤")
        return JSONResponse({"error": "Spiral 引擎處理失敗", "detail": str(e)}, status_code=500)


# -----------------------------------------------------------------------------
# 4) 健康檢查（可供外部監控）
# -----------------------------------------------------------------------------
@app.get("/healthz")
async def api_healthz():
    """健康檢查：回 200 OK"""
    return PlainTextResponse("ok")


# -----------------------------------------------------------------------------
# 5) 靜態資源與首頁掛載（ui/）
# -----------------------------------------------------------------------------
FRONTEND_DIR = BACKEND_DIR.parent / "ui"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def index_html():
        """首頁：回傳前端打包後的 index.html"""
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return PlainTextResponse("前端 index.html 未找到（請先建置前端）", status_code=404)
else:
    @app.get("/")
    async def index_placeholder():
        """前端未就緒時的占位首頁"""
        return PlainTextResponse("前端目錄不存在（請確認 ui/ 是否存在或已建置）", status_code=200)
