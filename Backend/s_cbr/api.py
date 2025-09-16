"""
S-CBR API 路由器 v2.0 - 螺旋互動版

提供 FastAPI 路由器，支援螺旋推理互動模式
- 每輪推理結果即時回傳
- 用戶決定是否繼續推理
- 案例使用記錄管理
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from .main import run_spiral_cbr_v2, SpiralSessionManager
from .utils.spiral_logger import SpiralLogger

# 創建路由器
router = APIRouter()
logger = SpiralLogger.get_logger("S-CBR-API")

# 全局會話管理器
session_manager = SpiralSessionManager()

@router.post("/query")
async def api_query(request: Request):
    """
    S-CBR 螺旋推理查詢 v2.0 - 互動版
    
    入參 JSON:
    {
        "question": "患者症狀描述...",
        "patient_ctx": { // 可選患者上下文
            "age": 35,
            "gender": "女",
            "chief_complaint": "主訴...",
            "pulse_text": "脈診描述..."
        },
        "session_id": "session_uuid", // 可選，用於續接會話
        "continue": false, // 可選，是否繼續推理
        "patient_id": "compatibility_field" // 兼容性欄位
    }
    
    出參 JSON:
    {
        "dialog": "🌀 第X輪螺旋推理結果\n診斷: ...",
        "session_id": "session_uuid",
        "continue_available": true,
        "round": 2,
        "llm_struct": {
            "main_dx": "主要診斷",
            "confidence": 0.86,
            "case_used": "使用的案例摘要",
            "safety_score": 0.82,
            "efficacy_score": 0.76
        },
        "trace_id": "REQ-20250914-xxxx",
        "session_info": {
            "spiral_rounds": 2,
            "used_cases_count": 2,
            "processing_time_ms": 1250
        },
        "version": "2.0"
    }
    """
    start_time = datetime.now()
    trace_id = f"REQ-{start_time.strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
    
    try:
        # 解析請求
        body = await request.json()
        question = body.get("question") or body.get("query")
        patient_ctx = body.get("patient_ctx") or {}
        session_id = body.get("session_id")
        continue_spiral = body.get("continue", False)
        
        # 兼容性處理
        if body.get("patient_id") and not patient_ctx.get("patient_id"):
            patient_ctx["patient_id"] = body.get("patient_id")
        
        # 驗證必要參數
        if not question or not question.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "缺少必要參數",
                    "message": "請提供 'question' 欄位",
                    "trace_id": trace_id
                }
            )
        
        # 記錄請求
        logger.info(f"🔄 S-CBR 螺旋查詢請求 [{trace_id}]")
        logger.info(f"   問題: {question[:100]}{'...' if len(question) > 100 else ''}")
        logger.info(f"   會話ID: {session_id}")
        logger.info(f"   繼續推理: {continue_spiral}")
        logger.info(f"   患者上下文: {len(patient_ctx)} 個欄位")
        
        # 調用螺旋推理引擎 v2.0
        logger.info(f"🧠 啟動螺旋推理引擎 v2.0 [{trace_id}]")
        spiral_result = await run_spiral_cbr_v2(
            question=question,
            patient_ctx=patient_ctx,
            session_id=session_id,
            continue_spiral=continue_spiral,
            trace_id=trace_id,
            session_manager=session_manager
        )
        
        # 計算處理時間
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # 構建回應 v2.0
        response = {
            "dialog": spiral_result.get("dialog", "推理完成，請查看結構化結果。"),
            "session_id": spiral_result.get("session_id"),
            "continue_available": spiral_result.get("continue_available", False),
            "round": spiral_result.get("round", 1),
            "llm_struct": spiral_result.get("llm_struct", {}),
            "trace_id": trace_id,
            "session_info": {
                "spiral_rounds": spiral_result.get("spiral_rounds", 1),
                "used_cases_count": spiral_result.get("used_cases_count", 0),
                "total_steps": spiral_result.get("total_steps", 4),
                "processing_time_ms": int(processing_time),
                "converged": spiral_result.get("converged", False)
            },
            "version": "2.0",
            "timestamp": start_time.isoformat()
        }
        
        # 記錄成功
        logger.info(f"✅ S-CBR v2.0 查詢完成 [{trace_id}]")
        logger.info(f"   處理時間: {processing_time:.0f}ms")
        logger.info(f"   推理輪數: {response['session_info']['spiral_rounds']}")
        logger.info(f"   會話ID: {response['session_id']}")
        logger.info(f"   可繼續: {response['continue_available']}")
        
        return JSONResponse(response)
        
    except HTTPException:
        # FastAPI HTTPException 直接拋出
        raise
        
    except Exception as e:
        # 記錄錯誤
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.error(f"❌ S-CBR v2.0 處理失敗 [{trace_id}]: {str(e)}")
        logger.exception("詳細錯誤資訊")
        
        # 構建錯誤回應
        error_response = {
            "error": "S-CBR v2.0 螺旋推理引擎處理失敗",
            "detail": str(e),
            "trace_id": trace_id,
            "processing_time_ms": int(processing_time),
            "timestamp": start_time.isoformat(),
            "version": "2.0"
        }
        
        raise HTTPException(
            status_code=500,
            detail=error_response
        )

@router.post("/spiral-reset")
async def reset_spiral_session(request: Request):
    """
    重置螺旋推理會話
    
    入參 JSON:
    {
        "session_id": "session_uuid" // 可選，不提供則重置所有會話
    }
    """
    try:
        body = await request.json()
        session_id = body.get("session_id")
        
        if session_id:
            session_manager.reset_session(session_id)
            message = f"會話 {session_id} 已重置"
        else:
            session_manager.reset_all_sessions()
            message = "所有螺旋推理會話已重置"
        
        logger.info(f"🔄 {message}")
        
        return JSONResponse({
            "status": "success",
            "message": message,
            "version": "2.0",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"重置螺旋會話失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"重置失敗: {str(e)}",
                "version": "2.0",
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/spiral-sessions")
async def get_spiral_sessions():
    """
    獲取當前活躍的螺旋推理會話
    """
    try:
        sessions_info = session_manager.get_sessions_info()
        
        return JSONResponse({
            "active_sessions": len(sessions_info),
            "sessions": sessions_info,
            "version": "2.0",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"獲取螺旋會話資訊失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"無法獲取會話資訊: {str(e)}",
                "version": "2.0",
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/scbr/health")
async def scbr_health_check():
    """
    S-CBR 系統詳細健康檢查 v2.0
    """
    try:
        from .config.scbr_config import SCBRConfig
        from .utils.api_manager import SCBRAPIManager
        
        config = SCBRConfig()
        api_manager = SCBRAPIManager()
        
        # 執行健康檢查
        health_result = await api_manager.health_check()
        
        return JSONResponse({
            "status": "healthy" if health_result.get("overall_status") == "healthy" else "unhealthy",
            "version": "2.0",
            "module": "S-CBR-Spiral",
            "components": {
                "config": "loaded",
                "api_manager": "initialized",
                "session_manager": "active",
                "llm_client": health_result.get("llm_client", False),
                "embedding_client": health_result.get("embedding_client", False),
                "weaviate_client": health_result.get("weaviate_client", False)
            },
            "active_sessions": len(session_manager.get_sessions_info()),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"S-CBR v2.0 健康檢查失敗: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": f"S-CBR v2.0 系統異常: {str(e)}",
                "version": "2.0",
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/scbr/stats")
async def scbr_statistics():
    """
    S-CBR 系統統計資訊 v2.0
    """
    try:
        from .knowledge.spiral_memory import SpiralMemory
        
        # 獲取記憶庫統計
        spiral_memory = SpiralMemory()
        memory_stats = spiral_memory.get_memory_stats()
        
        # 獲取會話統計
        sessions_info = session_manager.get_sessions_info()
        
        return JSONResponse({
            "version": "2.0",
            "module": "S-CBR-Spiral",
            "statistics": {
                "memory_stats": memory_stats,
                "system_uptime": "運行中",
                "active_sessions": len(sessions_info),
                "total_rounds_processed": sum([s.get('round_count', 0) for s in sessions_info]),
                "total_cases_used": sum([len(s.get('used_cases', [])) for s in sessions_info])
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"獲取 S-CBR v2.0 統計資訊失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"無法獲取統計資訊: {str(e)}",
                "version": "2.0",
                "timestamp": datetime.now().isoformat()
            }
        )

@router.post("/scbr/reset")
async def scbr_reset_memory():
    """
    重置 S-CBR 記憶庫（開發和調試用）v2.0
    """
    try:
        from .knowledge.spiral_memory import SpiralMemory
        
        spiral_memory = SpiralMemory()
        
        # 清理過期記憶
        spiral_memory.cleanup_expired_memories()
        
        # 重置會話管理器
        session_manager.reset_all_sessions()
        
        logger.info("🔄 S-CBR v2.0 記憶庫與會話已重置")
        
        return JSONResponse({
            "status": "success",
            "message": "S-CBR v2.0 記憶庫與螺旋會話已重置",
            "version": "2.0",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"S-CBR v2.0 記憶庫重置失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"重置失敗: {str(e)}",
                "version": "2.0",
                "timestamp": datetime.now().isoformat()
            }
        )

# 導出路由器
__all__ = ["router"]