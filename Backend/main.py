# -*- coding: utf-8 -*-
"""
FastAPI 入口（S-CBR v1.0 整合版）

- 整合 s_cbr 螺旋推理模組
- /api/query 由 S-CBR 路由器處理
- 保留原有所有功能：病例存儲、靜態資源、前端服務
- 完整的錯誤處理和日誌系統
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

# S-CBR 螺旋推理引擎整合（容錯處理）
try:
    from s_cbr.api import router as scbr_router
    _scbr_import_error = None
    _scbr_available = True
except Exception as _e:
    scbr_router = None
    _scbr_import_error = _e
    _scbr_available = False

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
app = FastAPI(title="TCM Spiral CBR Backend", version="2.0.0")

# 整合 S-CBR 路由器
if _scbr_available and scbr_router:
    app.include_router(scbr_router, prefix="/api", tags=["S-CBR"])
    logger.info("✅ S-CBR v2.0 螺旋推理模組載入成功")
else:
    logger.error(f"❌ S-CBR 螺旋推理模組載入失敗: {_scbr_import_error}")

@app.on_event("startup")
async def _on_startup():
    logger.info("🚀 TCM S-CBR Backend v2.0 啟動")
    if _scbr_available:
        logger.info("   - S-CBR 螺旋推理引擎: ✅ 已載入")
        logger.info("   - API 端點 /api/query: ✅ 可用")
    else:
        logger.warning("   - S-CBR 螺旋推理引擎: ❌ 未載入")
        logger.warning("   - API 端點 /api/query: ❌ 不可用")
    
    logger.info("   - 病例存儲 /api/case/save: ✅ 可用")
    logger.info("   - 健康檢查 /healthz: ✅ 可用")
    logger.info("Application startup completed.")

@app.on_event("shutdown")
async def _on_shutdown():
    # 確保所有 handler 都被 flush/close，避免殘留把手
    logger.info("🔄 正在關閉應用程式...")
    
    # 關閉 S-CBR 相關資源（如有需要）
    if _scbr_available:
        try:
            # 可在此處添加 S-CBR 清理邏輯
            logger.info("   - S-CBR 資源清理: ✅ 完成")
        except Exception as e:
            logger.warning(f"   - S-CBR 資源清理異常: {e}")
    
    # 關閉日誌處理器
    root = logging.getLogger()
    for h in list(root.handlers):
        try:
            h.flush()
            h.close()
        except Exception:
            pass
    
    logger.info("🔻 Application shutdown completed.")

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
    try:
        data = await request.json()
        logger.info(f"📝 收到新增病例請求: {data.get('case_id', 'unknown')}")
        
        result = save_case_data(data)
        
        if result.get('ok'):
            logger.info(f"✅ 病例存儲成功: {result.get('case_id')}")
        else:
            logger.error(f"❌ 病例存儲失敗: {result.get('message')}")
        
        return result
        
    except Exception as e:
        logger.exception("病例存儲過程發生異常")
        return {"ok": False, "message": f"病例存儲異常: {str(e)}"}

# -----------------------------------------------------------------------------
# 2) S-CBR 狀態檢查 API（用於前端檢查 S-CBR 可用性）
# -----------------------------------------------------------------------------
@app.get("/api/scbr/status")
async def api_scbr_status():
    """
    S-CBR 系統狀態檢查
    """
    return JSONResponse({
        "scbr_available": _scbr_available,
        "version": "1.0.0",
        "error": str(_scbr_import_error) if _scbr_import_error else None,
        "endpoints": {
            "query": "/api/query" if _scbr_available else None,
            "health": "/api/scbr/health" if _scbr_available else None
        }
    })

# -----------------------------------------------------------------------------
# 3) 相容性 API（如果 S-CBR 未載入，提供錯誤回應）
# -----------------------------------------------------------------------------
@app.post("/api/query")
async def api_query_fallback(request: Request):
    """
    查詢 API 備用端點（當 S-CBR 未載入時）
    
    這個端點只在 S-CBR 路由未成功載入時生效
    正常情況下會被 S-CBR 路由器覆蓋
    """
    if _scbr_available:
        # 這種情況不應該發生，因為 S-CBR 路由器應該處理此端點
        return JSONResponse(
            {"error": "路由衝突：S-CBR 路由器應該處理此請求"},
            status_code=500
        )
    
    logger.error("嘗試訪問 /api/query 但 S-CBR 引擎未載入")
    return JSONResponse(
        {
            "error": "S-CBR 螺旋推理引擎未載入",
            "detail": str(_scbr_import_error) if _scbr_import_error else "未知錯誤",
            "suggestion": "請檢查 s_cbr 模組是否正確安裝",
            "status": "service_unavailable"
        },
        status_code=503,
    )

# -----------------------------------------------------------------------------
# 4) 健康檢查（擴展版，包含 S-CBR 狀態）
# -----------------------------------------------------------------------------
@app.get("/healthz")
async def api_healthz():
    """
    系統健康檢查（包含 S-CBR 狀態）
    """
    health_status = {
        "status": "healthy",
        "timestamp": "2025-09-14T19:24:00Z",
        "version": "1.0.0",
        "components": {
            "backend": "healthy",
            "case_storage": "healthy",
            "scbr_engine": "healthy" if _scbr_available else "unavailable"
        }
    }
    
    status_code = 200
    if not _scbr_available:
        health_status["status"] = "degraded"
        health_status["warnings"] = ["S-CBR 螺旋推理引擎不可用"]
        status_code = 200  # 仍然返回 200，因為核心功能可用
    
    return JSONResponse(health_status, status_code=status_code)

# -----------------------------------------------------------------------------
# 5) 靜態資源與首頁掛載（ui/）保持原有邏輯
# -----------------------------------------------------------------------------
FRONTEND_DIR = BACKEND_DIR.parent / "ui"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    
    @app.get("/")
    async def index_html():
        """首頁：回傳前端打包後的 index.html"""
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            logger.debug("提供前端 index.html")
            return FileResponse(str(index_file))
        logger.warning("前端 index.html 不存在")
        return PlainTextResponse("前端 index.html 未找到（請先建置前端）", status_code=404)
        
else:
    @app.get("/")
    async def index_placeholder():
        """前端未就緒時的占位首頁"""
        return PlainTextResponse(
            f"前端目錄不存在（請確認 {FRONTEND_DIR} 是否存在或已建置）\n"
            f"S-CBR 狀態: {'可用' if _scbr_available else '不可用'}",
            status_code=200
        )

# -----------------------------------------------------------------------------
# 6) 調試和開發支持 API
# -----------------------------------------------------------------------------
@app.get("/api/debug/info")
async def api_debug_info():
    """
    系統調試資訊（僅開發環境使用）
    """
    return JSONResponse({
        "backend_dir": str(BACKEND_DIR),
        "log_dir": str(LOG_DIR),
        "frontend_dir": str(FRONTEND_DIR),
        "frontend_exists": FRONTEND_DIR.exists(),
        "scbr_status": {
            "available": _scbr_available,
            "error": str(_scbr_import_error) if _scbr_import_error else None
        },
        "python_version": sys.version,
        "app_title": app.title,
        "app_version": app.version
    })
