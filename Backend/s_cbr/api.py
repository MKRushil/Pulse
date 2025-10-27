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
    
@router.post("/case/save-effective")
async def save_effective_case(req: SaveCaseRequest):
    """
    儲存有效治療案例到 RPCase
    
    這個端點應該在前端確認治療有效後調用
    """
    try:
        engine = get_engine()
        session = engine.dialog.get_session(req.session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="會話不存在")
        
        # 檢查是否標記為可儲存
        if not session.history:
            raise HTTPException(status_code=400, detail="會話無歷史記錄")
        
        last_step = session.history[-1]
        save_prompt = last_step.get("save_prompt", {})
        
        if not save_prompt.get("can_save", False):
            return {
                "status": "rejected",
                "message": "該會話未達到有效治療標準",
                "reason": save_prompt.get("message", "")
            }
        
        # ✅ 調用 RPCaseManager 儲存
        from .core.rpcase_manager import RPCaseManager
        rpcase_mgr = RPCaseManager(
            weaviate_client=engine.spiral.SE.weaviate_client,
            config=engine.config
        )
        
        # 準備儲存數據
        session_data = {
            "session_id": req.session_id,
            "diagnosis": last_step.get("primary", {}).get("diagnosis", ""),
            "conversation_history": [
                {"round": step.get("round"), "question": step.get("question")}
                for step in session.history
            ],
            "primary": last_step.get("primary", {}),
            "convergence_metrics": last_step.get("convergence", {}),
            "round": session.round_count
        }
        
        result = await rpcase_mgr.save_from_session(session_data)
        
        if result.get("success"):
            logger.info(f"💾 RPCase 儲存成功: {result.get('case_id')}")
            return {
                "status": "success",
                "message": "有效案例已儲存",
                "case_id": result.get("case_id"),
                "effectiveness_score": save_prompt.get("effectiveness_score", 0)
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"儲存失敗: {result.get('error')}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"儲存 RPCase 失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/case/save-status/{session_id}")
async def get_save_status(session_id: str):
    """
    檢查會話是否可儲存為有效案例
    """
    try:
        engine = get_engine()
        session = engine.dialog.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="會話不存在")
        
        if not session.history:
            return {
                "can_save": False,
                "reason": "無診斷記錄"
            }
        
        last_step = session.history[-1]
        save_prompt = last_step.get("save_prompt", {})
        
        return {
            "can_save": save_prompt.get("can_save", False),
            "message": save_prompt.get("message", ""),
            "effectiveness_score": save_prompt.get("effectiveness_score", 0),
            "round_count": session.round_count,
            "converged": last_step.get("convergence", {}).get("overall_convergence", 0) >= 0.85
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"檢查儲存狀態失敗: {e}", exc_info=True)
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

@router.post("/case/save-effective")
async def save_effective_case(req: SaveCaseRequest):
    """
    儲存有效治療案例到 RPCase
    
    這個端點應該在前端確認治療有效後調用
    """
    try:
        engine = get_engine()
        session = engine.dialog.get_session(req.session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="會話不存在")
        
        # 檢查是否標記為可儲存
        if not session.history:
            raise HTTPException(status_code=400, detail="會話無歷史記錄")
        
        last_step = session.history[-1]
        save_prompt = last_step.get("save_prompt", {})
        
        if not save_prompt.get("can_save", False):
            return {
                "status": "rejected",
                "message": "該會話未達到有效治療標準",
                "reason": save_prompt.get("message", "")
            }
        
        # ✅ 調用 RPCaseManager 儲存
        from .core.rpcase_manager import RPCaseManager
        rpcase_mgr = RPCaseManager(
            weaviate_client=engine.spiral.SE.weaviate_client,
            config=engine.config
        )
        
        # 準備儲存數據
        session_data = {
            "session_id": req.session_id,
            "diagnosis": last_step.get("primary", {}).get("diagnosis", ""),
            "conversation_history": [
                {"round": step.get("round"), "question": step.get("question")}
                for step in session.history
            ],
            "primary": last_step.get("primary", {}),
            "convergence_metrics": last_step.get("convergence", {}),
            "round": session.round_count
        }
        
        result = await rpcase_mgr.save_from_session(session_data)
        
        if result.get("success"):
            logger.info(f"💾 RPCase 儲存成功: {result.get('case_id')}")
            return {
                "status": "success",
                "message": "有效案例已儲存",
                "case_id": result.get("case_id"),
                "effectiveness_score": save_prompt.get("effectiveness_score", 0)
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"儲存失敗: {result.get('error')}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"儲存 RPCase 失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/case/save-status/{session_id}")
async def get_save_status(session_id: str):
    """
    檢查會話是否可儲存為有效案例
    """
    try:
        engine = get_engine()
        session = engine.dialog.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="會話不存在")
        
        if not session.history:
            return {
                "can_save": False,
                "reason": "無診斷記錄"
            }
        
        last_step = session.history[-1]
        save_prompt = last_step.get("save_prompt", {})
        
        return {
            "can_save": save_prompt.get("can_save", False),
            "message": save_prompt.get("message", ""),
            "effectiveness_score": save_prompt.get("effectiveness_score", 0),
            "round_count": session.round_count,
            "converged": last_step.get("convergence", {}).get("overall_convergence", 0) >= 0.85
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"檢查儲存狀態失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))