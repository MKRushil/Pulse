# -*- coding: utf-8 -*-
"""
S-CBR API 路由
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from .main import run_spiral_cbr, get_engine
from .utils.logger import get_logger

router = APIRouter(prefix="/api/scbr/v2", tags=["S-CBR"])
logger = get_logger("SCBR-API")

class DiagnoseRequest(BaseModel):
    """診斷請求模型"""
    question: str
    patient_ctx: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    continue_spiral: bool = False

class SessionResetRequest(BaseModel):
    """會話重置請求"""
    session_id: str

class SaveCaseRequest(BaseModel):
    """保存病例請求"""
    session_id: str
    case_data: Dict[str, Any]

@router.post("/diagnose")
async def diagnose(req: DiagnoseRequest):
    """
    執行螺旋推理診斷
    """
    try:
        logger.info(f"收到診斷請求: {req.question[:50]}...")
        
        result = await run_spiral_cbr(
            question=req.question,
            patient_ctx=req.patient_ctx,
            session_id=req.session_id,
            continue_spiral=req.continue_spiral
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"診斷失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/reset")
async def reset_session(req: SessionResetRequest):
    """
    重置會話
    """
    try:
        engine = get_engine()
        engine.reset_session(req.session_id)
        return {"status": "success", "message": f"會話 {req.session_id} 已重置"}
        
    except Exception as e:
        logger.error(f"重置會話失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    獲取會話資訊
    """
    try:
        engine = get_engine()
        session = engine.dialog.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="會話不存在")
        
        return {
            "session_id": session_id,
            "round_count": session.round_count,
            "accumulated_question": session.accumulated_question,
            "history_count": len(session.history),
            "created_at": session.created_at,
            "patient_ctx": session.patient_ctx
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取會話資訊失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/case/save")
async def save_case(req: SaveCaseRequest):
    """
    保存病例到 RPCase
    """
    try:
        engine = get_engine()
        session = engine.dialog.get_session(req.session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="會話不存在")
        
        # TODO: 實作保存到 RPCase 的邏輯
        # 這裡需要整合 DCIP 流程
        
        logger.info(f"保存病例: session_id={req.session_id}")
        
        return {
            "status": "success",
            "message": "病例保存成功",
            "case_id": f"RP-{req.session_id[:8]}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存病例失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """
    健康檢查
    """
    return {
        "status": "healthy",
        "version": "2.1.0",
        "service": "S-CBR API"
    }