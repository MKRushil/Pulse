# -*- coding: utf-8 -*-
"""
FastAPI 入口（S-CBR v2.1 整合版）
- 整合 s_cbr v2.1 螺旋推理模組
- 支援累積式多輪對話診斷
- 保留原有所有功能：病例存儲、靜態資源、前端服務
- 完整的錯誤處理和日誌系統
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path  # 修正：pathapi -> pathlib
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Mapping


def _safe_unwrap_payload(payload: Any) -> dict:
    """
    盡量把 payload 轉成 dict 並優先取用 payload['data']（若其為 dict）。
    若 payload 不是 dict，回傳空 dict 讓後續驗證擋下。
    """
    if isinstance(payload, Mapping):
        inner = payload.get("data", None)
        if isinstance(inner, Mapping):
            return dict(inner)
        # 沒有 data wrapper，就直接用本體，但必須是 Mapping
        return dict(payload)
    # 非 dict / mapping → 回傳空 dict，交由上層做 400 驗證
    return {}


# ---- 專案內部匯入 ----
from cases.case_storage import save_case_data  # 新增病例處理鏈（DCIP）

# S-CBR v2.1 螺旋推理引擎整合（容錯處理）
try:
    from s_cbr import run_spiral_cbr, scbr_router, SCBRConfig
    from s_cbr.utils.logger import get_logger as get_scbr_logger
    
    # 初始化 S-CBR 配置
    scbr_config = SCBRConfig()
    scbr_config.validate()
    
    _scbr_import_error = None
    _scbr_available = True
    scbr_logger = get_scbr_logger("Main")
    scbr_logger.info("✅ S-CBR v2.1 模組載入成功")
    
except Exception as _e:
    scbr_router = None
    run_spiral_cbr = None
    _scbr_import_error = _e
    _scbr_available = False

# -----------------------------------------------------------------------------
# 日誌設定
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
    force=True
)

logger = logging.getLogger("backend.main")

# -----------------------------------------------------------------------------
# 應用生命週期管理
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動
    logger.info("🚀 TCM S-CBR Backend v2.1 啟動")
    if _scbr_available:
        logger.info("   - S-CBR v2.1 螺旋推理引擎: ✅ 已載入")
        logger.info("   - API 端點 /api/scbr/v2/*: ✅ 可用")
        logger.info("   - 累積式多輪對話: ✅ 支援")
        logger.info("   - Hybrid 搜索引擎: ✅ 可用")
    else:
        logger.warning("   - S-CBR 螺旋推理引擎: ❌ 未載入")
        logger.warning("   - API 端點 /api/scbr/v2/*: ❌ 不可用")
        logger.error(f"   - 載入錯誤: {_scbr_import_error}")
    
    logger.info("   - 病例存儲 /api/case/save: ✅ 可用")
    logger.info("   - 健康檢查 /healthz: ✅ 可用")
    logger.info("Application startup completed.")
    
    yield
    
    # 關閉
    logger.info("🔄 正在關閉應用程式...")
    
    # 關閉 S-CBR 相關資源
    if _scbr_available:
        try:
            # S-CBR v2.1 清理邏輯
            logger.info("   - S-CBR v2.1 資源清理: ✅ 完成")
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
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    title="TCM Spiral CBR Backend", 
    version="2.1.0",
    lifespan=lifespan
)

# 整合 S-CBR v2.1 路由器
if _scbr_available and scbr_router:
    app.include_router(scbr_router, tags=["S-CBR v2.1"])
    logger.info("✅ S-CBR v2.1 路由器整合成功")
else:
    logger.error(f"❌ S-CBR v2.1 路由器整合失敗: {_scbr_import_error}")

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
# 2) S-CBR v2.1 狀態檢查 API
# -----------------------------------------------------------------------------
@app.get("/api/scbr/status")
async def api_scbr_status():
    """S-CBR v2.1 系統狀態檢查"""
    return JSONResponse({
        "scbr_available": _scbr_available,
        "version": "2.1.0",
        "error": str(_scbr_import_error) if _scbr_import_error else None,
        "features": {
            "spiral_reasoning": _scbr_available,
            "hybrid_search": _scbr_available,
            "accumulative_dialog": _scbr_available,
            "pulse_integration": _scbr_available,
            "feedback_learning": _scbr_available
        },
        "endpoints": {
            "diagnose": "/api/scbr/v2/diagnose" if _scbr_available else None,
            "feedback": "/api/scbr/v2/feedback" if _scbr_available else None,
            "health": "/api/scbr/v2/health" if _scbr_available else None,
            "info": "/api/scbr/v2/info" if _scbr_available else None
        }
    })

# -----------------------------------------------------------------------------
# 3) 相容性 API（向後兼容舊版本）
# -----------------------------------------------------------------------------
@app.post("/api/query")
async def api_query_compatibility(request: Request):
    if not _scbr_available:
        return JSONResponse({"error": "S-CBR v2.1 引擎未載入"}, status_code=503)
    try:
        payload = await request.json()
        logger.error(f"/api/query payload debug type={type(payload).__name__}, keys={(list(payload.keys()) if isinstance(payload, dict) else None)}")

        # 一律用 get + 型別檢查，不要用下標取值
        data = {}
        if isinstance(payload, Mapping):
            maybe = payload.get("data", None)
            data = maybe if isinstance(maybe, Mapping) else payload
        else:
            return JSONResponse(
                {"error": "無效的請求格式", "message": f"根節點必須是 JSON 物件，收到 {type(payload).__name__}"},
                status_code=400
            )

        # 兼容鍵名
        question = data.get("question") or data.get("query") or data.get("q")
        patient_ctx = data.get("patient_ctx") or data.get("patientCtx") or {}
        session_id = data.get("session_id") or data.get("sessionId")
        continue_spiral = bool(data.get("continue") or data.get("continue_spiral") or False)
        try:
            result = await run_spiral_cbr(
                question=question.strip(),
                patient_ctx=patient_ctx if isinstance(patient_ctx, dict) else {},
                session_id=session_id if isinstance(session_id, str) else None,
                continue_spiral=continue_spiral
            )
        except KeyError as ke:
            # 常見: GraphQL/搜尋結果無 'data'，或切到 Chroma 回傳無 'data'
            logger.exception("S-CBR 內部 KeyError（多半為搜尋結果缺 'data'）")
            return JSONResponse(
                {
                    "error": "上游查詢結果不相容",
                    "message": f"內部取鍵失敗: {str(ke)}；請檢查 Hybrid/向量/BM25 搜尋回傳結構是否含 data/Get",
                    "hint": "請開啟 s_cbr 搜尋 adapter 的結果打印，確認實際回傳結構"
                },
                status_code=502
            )
        
        if not isinstance(question, str) or not question.strip():
            return JSONResponse({"error": "參數缺失", "message": "question 不可為空"}, status_code=400)

        result = await run_spiral_cbr(
            question=question.strip(),
            patient_ctx=patient_ctx if isinstance(patient_ctx, dict) else {},
            session_id=session_id if isinstance(session_id, str) else None,
            continue_spiral=continue_spiral
        )

        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        legacy = {
            "dialog": f"診斷結果：{(result or {}).get('diagnosis','')}",
            "session_id": (result or {}).get("session_id"),
            "continue_available": (result or {}).get("continue_available", False),
            "round": (result or {}).get("round", 1),
            "llm_struct": {
                "main_dx": (result or {}).get("diagnosis",""),
                "confidence": (result or {}).get("confidence",0),
                "reasoning": (result or {}).get("reasoning","")
            },
            "evaluation_metrics": (result or {}).get("evaluation_metrics",{}),
            "trace_id": (result or {}).get("trace_id",""),
            "version": (result or {}).get("version","2.1.0")
        }
        return JSONResponse(legacy)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.exception(f"相容性查詢處理失敗: {e!r}")  # 會輸出 traceback
        return JSONResponse(
            {"error": "查詢處理失敗", "type": type(e).__name__, "message": str(e)},
            status_code=500
        )
# -----------------------------------------------------------------------------
# 4) 健康檢查（包含 S-CBR v2.1 狀態）
# -----------------------------------------------------------------------------
@app.get("/healthz")
async def api_healthz():
    """系統健康檢查（包含 S-CBR v2.1 狀態）"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.1.0",
        "components": {
            "backend": "healthy",
            "case_storage": "healthy",
            "scbr_engine": "healthy" if _scbr_available else "unavailable"
        }
    }
    
    status_code = 200
    if not _scbr_available:
        health_status["status"] = "degraded"
        health_status["warnings"] = ["S-CBR v2.1 螺旋推理引擎不可用"]
        # 仍返回 200，因為核心病例存儲功能可用
    
    return JSONResponse(health_status, status_code=status_code)

# -----------------------------------------------------------------------------
# 5) 靜態資源與首頁掛載
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
            f"S-CBR v2.1 狀態: {'可用' if _scbr_available else '不可用'}",
            status_code=200
        )

# -----------------------------------------------------------------------------
# 6) 調試和開發支持 API
# -----------------------------------------------------------------------------
@app.get("/api/debug/info")
async def api_debug_info():
    """系統調試資訊（僅開發環境使用）"""
    return JSONResponse({
        "backend_dir": str(BACKEND_DIR),
        "log_dir": str(LOG_DIR),
        "frontend_dir": str(FRONTEND_DIR),
        "frontend_exists": FRONTEND_DIR.exists(),
        "scbr_status": {
            "available": _scbr_available,
            "version": "2.1.0" if _scbr_available else None,
            "error": str(_scbr_import_error) if _scbr_import_error else None,
            "features_enabled": {
                "spiral_reasoning": _scbr_available,
                "hybrid_search": _scbr_available,
                "accumulative_dialog": _scbr_available,
                "pulse_integration": _scbr_available,
                "feedback_learning": _scbr_available
            }
        },
        "python_version": sys.version,
        "app_title": app.title,
        "app_version": app.version
    })

# -----------------------------------------------------------------------------
# 7) S-CBR v2.1 便捷測試接口
# -----------------------------------------------------------------------------
@app.post("/api/test/diagnose")
async def api_test_diagnose(request: Request):
    """S-CBR v2.1 快速測試接口"""
    if not _scbr_available:
        return JSONResponse(
            {"error": "S-CBR v2.1 引擎不可用"},
            status_code=503
        )
    
    try:
        data = await request.json()
        symptoms = data.get("symptoms", "")
        
        if not symptoms:
            return JSONResponse(
                {"error": "症狀描述不可為空"},
                status_code=400
            )
        
        result = await run_spiral_cbr(question=symptoms)
        
        return JSONResponse({
            "test_mode": True,
            "input_symptoms": symptoms,
            "diagnosis_result": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"測試診斷失敗: {e}")
        return JSONResponse(
            {"error": "測試診斷失敗", "message": str(e)},
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
