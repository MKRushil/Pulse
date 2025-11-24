# -*- coding: utf-8 -*-
"""
TCM S-CBR Backend v2.2 - FastAPI Main Application
整合 ANC (Archive & Normalize Cases) 與 S-CBR 引擎
"""

import os
import uvicorn
from typing import Any, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import warnings

from s_cbr.utils.error_handler import sanitize_error_message

# 隱藏第三方套件的警告
warnings.filterwarnings("ignore", category=ResourceWarning, module="jieba")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")
warnings.filterwarnings("ignore", message=".*Weaviate v3 client.*")
warnings.filterwarnings("ignore", message=".*weaviate-client version.*")
# ✅ 新增：隱藏 jieba 相關的 DeprecationWarning 和 ResourceWarning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="jieba._compat")
warnings.filterwarnings("ignore", category=ResourceWarning, module="jieba.analyse.tfidf")



# Import S-CBR engine
from s_cbr.main import run_spiral_cbr
from s_cbr.utils.logger import get_logger

# Import S-CBR router
from s_cbr.api import router as scbr_router

# Import ANC router
from anc.api import router as anc_router

log = get_logger("backend.main")

# ============================================
# Lifespan Event Handler
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理器
    
    使用 context manager 模式管理應用的啟動和關閉邏輯。
    """
    # ==================== Startup 啟動邏輯 ====================
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
    
    yield  # 應用開始運行
    
    # ==================== Shutdown 關閉邏輯 ====================
    # 如果未來需要添加清理邏輯，可以在這裡添加
    pass


app = FastAPI(
    title="TCM S-CBR Backend v2.2",
    version="2.2",
    description="中醫螺旋推理系統 with 病例管理",
    lifespan=lifespan
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
# Exception Handlers
# ============================================

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """
    處理 ValueError（通常是輸入驗證錯誤）
    """
    log.warning(f"⚠️ 輸入驗證錯誤: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_error",
            "message": str(exc)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    通用異常處理器 - 不洩露技術細節
    """
    log.error(f"❌ 未處理的異常: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": sanitize_error_message(exc)
        }
    )

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

        # Map engine signaled errors to HTTP status for legacy clients
        if isinstance(result, dict) and result.get("error"):
            err = (result.get("error") or "bad_request").lower()
            msg = result.get("message") or "請求被拒絕"
            status = 400
            if err == "rate_limit_exceeded":
                status = 429
            elif err == "security_violation":
                status = 403
            return JSONResponse(status_code=status, content={
                "detail": {
                    "error": err,
                    "message": msg,
                    **({"retry_after": result.get("retry_after")} if result.get("retry_after") else {})
                }
            })

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