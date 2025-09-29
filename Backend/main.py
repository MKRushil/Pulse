# -*- coding: utf-8 -*-
"""
TCM S-CBR Backend v2.1 - FastAPI main (compat shim for legacy /api/query)
"""

import os
import uvicorn
from typing import Any, Dict, Optional

from fastapi import FastAPI, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ====== S-CBR v2.1 (engine facade) ======
# NOTE: SCBREngine.diagnose(question, patient_ctx=None, session_id=None, continue_spiral=False)
from s_cbr.main import run_spiral_cbr  # noqa: E402

# ====== logging ======
from s_cbr.utils.logger import get_logger  # noqa: E402

log = get_logger("backend.main")

app = FastAPI(title="TCM S-CBR Backend v2.1", version="2.1")

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# 生命週期
# =========================================================
@app.on_event("startup")
async def on_startup():
    # 這裡僅做啟動訊息；Weaviate 連線與 LLM 初始化會在引擎內自管
    log.info("🚀 TCM S-CBR Backend v2.1 啟動")
    log.info("   - S-CBR 螺旋推理引擎: ✅ 已載入")
    log.info("   - API 端點 /api/scbr/v2/*: ✅ 可用")
    log.info("   - 病例存儲 /api/case/save: ✅ 可用")
    log.info("   - 健康檢查 /healthz: ✅ 可用")


# =========================================================
# 健康檢查
# =========================================================
@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "tcm-scbr-backend", "version": "2.1"}


# =========================================================
# 舊前端相容：/api/query
#  - 轉接舊 payload: {"question","session_id","continue","continue_dialog","patient_ctx"}
#  - 映射成 SCBREngine 需要的參數
#  - 統一回傳包含舊前端期望字段：text（對應 final_text）
# =========================================================
@app.post("/api/query")
async def api_query_compatibility(payload: Dict[str, Any] = Body(...)):
    try:
        log.error("/api/query payload debug type=%s, keys=%s",
                  type(payload).__name__, list(payload.keys()))

        question: str = payload.get("question", "") or ""
        if not question.strip():
            return JSONResponse(
                status_code=400,
                content={"detail": "question is required"}
            )

        session_id: Optional[str] = payload.get("session_id") or None

        # 兼容兩個舊鍵名 → continue_spiral（bool）
        continue_spiral: bool = bool(
            payload.get("continue")
            or payload.get("continue_dialog")
            or False
        )

        # patient_ctx 可以是 dict，也可能缺省或是 None
        patient_ctx: Optional[Dict[str, Any]] = None
        raw_ctx = payload.get("patient_ctx")
        if isinstance(raw_ctx, dict):
            patient_ctx = raw_ctx
        else:
            patient_ctx = None  # 非 dict 一律忽略，交由引擎處理預設

        log.info("🌀 啟動診斷 [相容模式] 問題: %s", question)

        # 執行一次螺旋推理
        result = await run_spiral_cbr(
            question=question,
            patient_ctx=patient_ctx,
            session_id=session_id,
            continue_spiral=continue_spiral,
        )

        # 兼容舊前端字段：text（對應 final_text）
        legacy = {
            "text": result.get("final_text", "") or "",
        }
        merged = {**result, **legacy}

        return JSONResponse(status_code=200, content=merged)

    except Exception as e:
        log.error("相容性查詢處理失敗: %r", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )


# =========================================================
# 1) 新增病例（由前端 TCMForm.jsx 送出表單 → DCIP 4 步完成去識別入庫）
#    *此區塊依你原本流程實作；下面留著簡易 stub，避免打斷既有路由*
# =========================================================
@app.post("/api/case/save")
async def save_case(payload: Dict[str, Any] = Body(...)):
    # TODO: 在這裡串接你現有的 DCIP 4 步流程
    # 目前僅回傳回顧用訊息，確保端點存在且可用
    return {"ok": True, "message": "case stub saved (replace with DCIP pipeline)"}


# =========================================================
# 主程式
# =========================================================
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("RELOAD", "1") == "1"),
        workers=int(os.getenv("WORKERS", "1")),
        log_level=os.getenv("LOG_LEVEL", "info"),
    )
