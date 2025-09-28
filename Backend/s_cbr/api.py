# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict,Any,Optional
from .main import run_spiral_cbr, SCBREngine
from .utils.logger import get_logger

router = APIRouter(prefix="/scbr/v2")
logger = get_logger("SCBR-API")

class DiagnoseReq(BaseModel):
    question: str
    patient_ctx: Optional[Dict[str,Any]] = None
    session_id: Optional[str] = None
    continue_spiral: bool = False

@router.post("/diagnose")
async def diagnose(req: DiagnoseReq):
    try:
        res = await run_spiral_cbr(req.question, patient_ctx=req.patient_ctx,
                                   session_id=req.session_id, continue_spiral=req.continue_spiral)
        if "error" in res:
            raise HTTPException(500, res["error"])
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"診斷失敗: {e}")
        raise HTTPException(500, "Internal Error")

@router.post("/case/save")
async def save_case(req: Dict[str,Any]):
    SCBREngine().dialog.save_feedback_case(req)
    return {"status":"saved"}

@router.post("/session/reset")
async def reset_session(session_id: Dict[str,str]):
    SCBREngine().dialog.reset_session(session_id["session_id"])
    return {"status":"reset"}

@router.get("/health")
async def health():
    return {"status":"healthy","version":"2.1.0"}
