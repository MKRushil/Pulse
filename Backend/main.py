# -*- coding: utf-8 -*-
"""
TCM S-CBR Backend v2.2 - FastAPI Main Application
整合 ANC (Archive & Normalize Cases) 與 S-CBR 引擎
"""

import os
import uvicorn
from typing import Any, Dict

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import warnings

# 隱藏第三方套件的警告
warnings.filterwarnings("ignore", category=ResourceWarning, module="jieba")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")
warnings.filterwarnings("ignore", message=".*Weaviate v3 client.*")
warnings.filterwarnings("ignore", message=".*weaviate-client version.*")



# Import S-CBR engine
from s_cbr.main import run_spiral_cbr
from s_cbr.utils.logger import get_logger

# Import S-CBR router
from s_cbr.api import router as scbr_router

# Import ANC router
from anc.api import router as anc_router

log = get_logger("backend.main")

app = FastAPI(
    title="TCM S-CBR Backend v2.2",
    version="2.2",
    description="中醫螺旋推理系統 with 病例管理"
)

# ============================================
# CORS Configuration
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Include Routers
# ============================================
# S-CBR 螺旋推理引擎路由
app.include_router(scbr_router)

# ANC 病例管理路由
app.include_router(anc_router)

# ============================================
# Startup Event
# ============================================
@app.on_event("startup")
async def on_startup():
    log.info("🚀 TCM S-CBR Backend v2.2 啟動")
    log.info("=" * 60)
    log.info("📦 已載入模組:")
    log.info("   ✅ S-CBR 螺旋推理引擎")
    log.info("   ✅ ANC 病例管理系統")
    log.info("")
    log.info("🔗 可用端點:")
    log.info("   - 螺旋推理: /api/scbr/v2/*")
    log.info("   - 病例保存: POST /api/case/save")
    log.info("   - 病例查詢: GET /api/case/get/{case_id}")
    log.info("   - 病例搜索: POST /api/case/search")
    log.info("   - 病例統計: GET /api/case/stats")
    log.info("   - 健康檢查: GET /healthz")
    log.info("=" * 60)
    
    # 初始化 ANC 系統
    try:
        from anc.case_processor import get_case_processor
        processor = get_case_processor()
        log.info("✅ ANC 病例處理器初始化成功")
    except Exception as e:
        log.error(f"❌ ANC 初始化失敗: {e}")


# ============================================
# Health Check
# ============================================
@app.get("/healthz")
async def healthz():
    """健康檢查端點"""
    try:
        from anc.case_processor import get_case_processor
        processor = get_case_processor()
        weaviate_status = "connected" if processor.weaviate_client else "disconnected"
    except:
        weaviate_status = "error"
    
    return {
        "ok": True,
        "service": "tcm-scbr-backend",
        "version": "2.2",
        "modules": {
            "scbr": "active",
            "anc": "active",
            "weaviate": weaviate_status
        }
    }


# ============================================
# Legacy Compatibility Endpoint
# ============================================
@app.post("/api/query")
async def api_query_compatibility(payload: Dict[str, Any] = Body(...)):
    """
    Legacy API compatibility endpoint
    保留舊版相容性
    """
    try:
        question = payload.get("question", "").strip()
        if not question:
            return JSONResponse(
                status_code=400,
                content={"detail": "question is required"}
            )

        session_id = payload.get("session_id")
        continue_spiral = bool(payload.get("continue") or payload.get("continue_dialog"))
        patient_ctx = payload.get("patient_ctx") if isinstance(payload.get("patient_ctx"), dict) else None

        log.info(f"🌀 啟動診斷 [相容模式] 問題: {question}")

        result = await run_spiral_cbr(
            question=question,
            patient_ctx=patient_ctx,
            session_id=session_id,
            continue_spiral=continue_spiral,
        )

        # Legacy field compatibility
        result["text"] = result.get("final_text", "")
        return JSONResponse(status_code=200, content=result)

    except Exception as e:
        log.error(f"相容性查詢處理失敗: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": str(e)})


# ============================================
# Documentation Redirect
# ============================================
@app.get("/")
async def root():
    """根路徑重定向"""
    return {
        "message": "TCM S-CBR Backend v2.2",
        "docs": "/docs",
        "health": "/healthz",
        "endpoints": {
            "scbr": "/api/scbr/v2/",
            "case_management": "/api/case/"
        }
    }


# ============================================
# Main Entry Point
# ============================================
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("RELOAD", "1") == "1"),
        workers=int(os.getenv("WORKERS", "1")),
        log_level=os.getenv("LOG_LEVEL", "info"),
    )