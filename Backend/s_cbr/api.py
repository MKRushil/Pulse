"""
S-CBR API 路由器 v2.0 - 螺旋互動版

提供 FastAPI 路由器，支援螺旋推理互動模式
- 每輪推理結果即時回傳
- 用戶決定是否繼續推理
- 案例使用記錄管理
- 修正循環導入問題，使用懶載入模式
- 支援回饋案例儲存到 RPCase 知識庫
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import json

# 創建路由器
router = APIRouter()

# 懶載入模組 - 避免循環導入
def _get_spiral_components():
    """
    懶載入螺旋推理組件
    
    Returns:
    tuple: (run_spiral_cbr_v2, SpiralSessionManager, SpiralLogger)
    """
    try:
        # 🔧 修正：分別從正確路徑導入
        from s_cbr.main import run_spiral_cbr_v2
        from s_cbr.sessions.spiral_session_manager import SpiralSessionManager
        from s_cbr.utils.spiral_logger import SpiralLogger
        return run_spiral_cbr_v2, SpiralSessionManager, SpiralLogger
    except ImportError as e:
        logging.error(f"無法載入 S-CBR 組件: {e}")
        return None, None, None



def _get_config_components():
    """懶載入配置組件"""
    try:
        from s_cbr.config.scbr_config import SCBRConfig
        from s_cbr.utils.api_manager import SCBRAPIManager
        return SCBRConfig, SCBRAPIManager
    except ImportError as e:
        logging.error(f"無法載入配置組件: {e}")
        return None, None

def _get_memory_components():
    """懶載入記憶組件"""
    try:
        from s_cbr.knowledge.spiral_memory import SpiralMemory
        return SpiralMemory
    except ImportError as e:
        logging.error(f"無法載入記憶組件: {e}")
        return None

def _get_rpcase_components():
    """懶載入 RPCase 組件"""
    try:
        from s_cbr.knowledge.rpcase_manager import RPCaseManager
        return RPCaseManager
    except ImportError as e:
        logging.error(f"無法載入 RPCase 組件: {e}")
        return None

# 初始化日誌（優先使用螺旋日誌器）
_, _, SpiralLogger = _get_spiral_components()
logger = SpiralLogger.get_logger("S-CBR-API") if SpiralLogger else logging.getLogger("S-CBR-API")

# 全域會話管理器 (單例)
_session_manager = None

def _get_session_manager():
    """
    獲取會話管理器實例（懶載入）
    
    Returns:
    SpiralSessionManager: 會話管理器實例
    """
    global _session_manager
    if _session_manager is None:
        _, SpiralSessionManager, _ = _get_spiral_components()
        if SpiralSessionManager:
            try:
                _session_manager = SpiralSessionManager.get_instance()
                logger.info("✅ 螺旋會話管理器就緒 (單例)")
            except Exception as e:
                logger.error(f"❌ 螺旋會話管理器初始化失敗: {e}")
                _session_manager = None
        else:
            logger.error("❌ SpiralSessionManager 類別為 None")
    return _session_manager

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
    "dialog": "🌀 第X輪螺旋推理結果\\n診斷: ...",
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
    "evaluation_metrics": {
      "cms": {"name": "案例匹配相似性", "score": 7.5, "max_score": 10},
      "rci": {"name": "推理一致性指標", "score": 8.2, "max_score": 10},
      "sals": {"name": "系統自適應學習", "score": 6.8, "max_score": 10}
    },
    "version": "2.0"
    }
    """
    start_time = datetime.now()
    trace_id = f"REQ-{start_time.strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
    
    try:
        run_spiral_cbr_v2, _, _ = _get_spiral_components()
        session_manager = _get_session_manager()

        if run_spiral_cbr_v2 is None or session_manager is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "會話管理器不可用",
                    "message": "無法初始化會話管理器",
                    "trace_id": trace_id,
                    "version": "2.1"
                }
            )

        body = await request.json()
        question = body.get("question") or body.get("query")
        patient_ctx = body.get("patient_ctx") or {}
        session_id = body.get("session_id")
        continue_spiral = body.get("continue", False)

        if not question or not question.strip():
            raise HTTPException(
                status_code=400,
                detail={"error": "缺少必要參數", "trace_id": trace_id, "version": "2.1"}
            )

        spiral_result = await run_spiral_cbr_v2(
            question=question,
            patient_ctx=patient_ctx,
            session_id=session_id,
            continue_spiral=continue_spiral,
            trace_id=trace_id,
            session_manager=session_manager
        )

        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        response = {
            "dialog": spiral_result.get("dialog"),
            "session_id": spiral_result.get("session_id"),
            "continue_available": spiral_result.get("continue_available", False),
            "round": spiral_result.get("round", 1),
            "llm_struct": spiral_result.get("llm_struct", {}),
            "trace_id": trace_id,
            "session_info": {
                "spiral_rounds": spiral_result.get("spiral_rounds", 1),
                "used_cases_count": spiral_result.get("used_cases_count", 0),
                "total_steps": spiral_result.get("total_steps", 4),
                "processing_time_ms": int(processing_time)
            },
            "version": "2.1",
            "timestamp": start_time.isoformat()
        }
        return JSONResponse(response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ S-CBR v2.1 處理失敗 [{trace_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e), "trace_id": trace_id, "version": "2.1"})

@router.post("/case/save-feedback")
async def save_feedback_case(request: Request):
    """
    儲存螺旋推理回饋案例到 RPCase 知識庫 v2.0
    """
    start_time = datetime.now()
    trace_id = f"SAVE-{start_time.strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
    
    try:
        body = await request.json()
        session_id = body.get("session_id")
        diagnosis = body.get("diagnosis", {})
        conversation_history = body.get("conversation_history", [])
        user_feedback = body.get("user_feedback", "用戶儲存為有效案例")
        save_as_rpcase = body.get("save_as_rpcase", True)
        
        if not session_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "缺少必要參數",
                    "message": "請提供 session_id",
                    "trace_id": trace_id
                }
            )
        
        # 記錄請求
        logger.info(f"💾 S-CBR 案例儲存請求 [{trace_id}]")
        logger.info(f" 會話ID: {session_id}")
        logger.info(f" 診斷數據: {len(str(diagnosis))} 個字符")
        logger.info(f" 對話記錄: {len(conversation_history)} 條")
        
        # 從會話管理器獲取會話信息
        session_manager = _get_session_manager()
        if not session_manager:
            # 如果沒有會話管理器，創建模擬會話信息
            session_mock = type('Session', (), {
                'original_query': body.get("original_question", ""),
                'round_count': 1,
                'used_cases': []
            })()
        else:
            sessions = getattr(session_manager, 'sessions', {})
            if session_id in sessions:
                session_mock = sessions[session_id]
            else:
                # 創建模擬會話信息
                session_mock = type('Session', (), {
                    'original_query': body.get("original_question", ""),
                    'round_count': 1,
                    'used_cases': []
                })()
        
        # 生成 RPCase ID
        rpcase_id = f"RP_{start_time.strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # 構建回饋案例數據
        rpcase_data = {
            "rpcase_id": rpcase_id,
            "original_question": getattr(session_mock, 'original_query', ''),
            "patient_context": json.dumps({
                "conversation_messages": len(conversation_history),
                "spiral_rounds": getattr(session_mock, 'round_count', 1),
                "used_cases": getattr(session_mock, 'used_cases', [])
            }, ensure_ascii=False),
            "spiral_rounds": getattr(session_mock, 'round_count', 1),
            "used_cases": getattr(session_mock, 'used_cases', []),
            "final_diagnosis": diagnosis.get("main_dx", "") or str(diagnosis.get("diagnosis", "")),
            "treatment_plan": str(diagnosis.get("treatment_plan", "")),
            "reasoning_process": json.dumps(diagnosis, ensure_ascii=False),
            "user_feedback": user_feedback,
            "effectiveness_score": float(diagnosis.get("efficacy_score", 0.8)),
            "confidence_score": float(diagnosis.get("confidence", 0.8)),
            "safety_score": float(diagnosis.get("safety_score", 0.8)),
            "session_id": session_id,
            "conversation_history": json.dumps(conversation_history, ensure_ascii=False),
            "created_timestamp": start_time.isoformat(),
            "updated_timestamp": start_time.isoformat(),
            "tags": ["user_approved", "spiral_reasoning", f"round_{getattr(session_mock, 'round_count', 1)}"],
            "complexity_level": min(getattr(session_mock, 'round_count', 1), 5),
            "success_rate": 1.0, # 用戶主動儲存，視為成功
            "reuse_count": 0,
            "source_type": "spiral_feedback"
        }
        
        # 儲存到 RPCase 向量庫
        if save_as_rpcase:
            RPCaseManager = _get_rpcase_components()
            if RPCaseManager:
                try:
                    rpcase_manager = RPCaseManager()
                    save_result = await rpcase_manager.save_rpcase(rpcase_data)
                    logger.info(f"✅ RPCase 儲存成功: {rpcase_id}")
                except Exception as e:
                    logger.error(f"RPCase 儲存失敗: {str(e)}")
                    # 不拋出異常，讓其他流程繼續
                    rpcase_data["rpcase_save_error"] = str(e)
            else:
                logger.warning("RPCase 管理器不可用，僅記錄數據")
        
        # 構建回應
        response = {
            "status": "success",
            "message": "回饋案例儲存成功",
            "case_id": rpcase_id,
            "rpcase_info": {
                "spiral_rounds": rpcase_data["spiral_rounds"],
                "used_cases_count": len(rpcase_data["used_cases"]),
                "confidence_score": rpcase_data["confidence_score"],
                "complexity_level": rpcase_data["complexity_level"],
                "created_timestamp": rpcase_data["created_timestamp"]
            },
            "trace_id": trace_id,
            "timestamp": start_time.isoformat(),
            "version": "2.0"
        }
        
        # 記錄成功
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"✅ S-CBR v2.0 案例儲存完成 [{trace_id}]")
        logger.info(f" 案例ID: {rpcase_id}")
        logger.info(f" 處理時間: {processing_time:.0f}ms")
        logger.info(f" 螺旋輪數: {rpcase_data['spiral_rounds']}")
        logger.info(f" 信心度: {rpcase_data['confidence_score']:.2f}")
        
        return JSONResponse(response)
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.error(f"❌ S-CBR v2.0 案例儲存失敗 [{trace_id}]: {str(e)}")
        logger.exception("詳細錯誤資訊")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "案例儲存失敗",
                "detail": str(e),
                "trace_id": trace_id,
                "processing_time_ms": int(processing_time),
                "timestamp": start_time.isoformat(),
                "version": "2.0"
            }
        )

@router.post("/spiral-reset")
async def reset_spiral_session(request: Request):
    """重置螺旋推理會話"""
    try:
        body = await request.json()
        session_id = body.get("session_id")
        
        session_manager = _get_session_manager()
        if not session_manager:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "會話管理器不可用",
                    "version": "2.0"
                }
            )
        
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
    """獲取當前活躍的螺旋推理會話"""
    try:
        session_manager = _get_session_manager()
        if not session_manager:
            return JSONResponse({
                "active_sessions": 0,
                "sessions": [],
                "error": "會話管理器不可用",
                "version": "2.0",
                "timestamp": datetime.now().isoformat()
            })
        
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
    """S-CBR 系統詳細健康檢查 v2.0"""
    try:
        SCBRConfig, SCBRAPIManager = _get_config_components()
        
        health_data = {
            "status": "healthy",
            "version": "2.0",
            "module": "S-CBR-Spiral",
            "timestamp": datetime.now().isoformat()
        }
        
        # 基本組件檢查
        run_spiral_cbr_v2, SpiralSessionManager, _ = _get_spiral_components()
        RPCaseManager = _get_rpcase_components()
        
        components = {
            "spiral_engine": "loaded" if run_spiral_cbr_v2 else "failed",
            "session_manager": "loaded" if SpiralSessionManager else "failed",
            "config": "loaded" if SCBRConfig else "failed",
            "api_manager": "loaded" if SCBRAPIManager else "failed",
            "rpcase_manager": "loaded" if RPCaseManager else "failed"
        }
        
        # 如果配置組件可用，執行詳細檢查
        if SCBRConfig and SCBRAPIManager:
            try:
                config = SCBRConfig()
                api_manager = SCBRAPIManager()
                
                # 執行健康檢查
                health_result = await api_manager.health_check_v2()
                components.update({
                    "llm_client": health_result.get("checks", {}).get("external_apis", {}).get("status") == "healthy",
                    "embedding_client": health_result.get("checks", {}).get("memory_system", {}).get("status") == "healthy",
                    "weaviate_client": health_result.get("checks", {}).get("database", {}).get("status") == "healthy"
                })
                
            except Exception as e:
                logger.warning(f"詳細健康檢查失敗: {e}")
                components.update({
                    "llm_client": False,
                    "embedding_client": False,
                    "weaviate_client": False
                })
        
        health_data["components"] = components
        
        # 會話統計
        session_manager = _get_session_manager()
        if session_manager:
            try:
                sessions_info = session_manager.get_sessions_info()
                health_data["active_sessions"] = len(sessions_info)
            except Exception:
                health_data["active_sessions"] = 0
        else:
            health_data["active_sessions"] = 0
        
        # 判斷總體健康狀態
        critical_components = ["spiral_engine", "session_manager"]
        if any(components.get(comp) == "failed" for comp in critical_components):
            health_data["status"] = "unhealthy"
        
        return JSONResponse(health_data)
        
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
    """S-CBR 系統統計資訊 v2.0"""
    try:
        SpiralMemory = _get_memory_components()
        
        stats_data = {
            "version": "2.0",
            "module": "S-CBR-Spiral",
            "timestamp": datetime.now().isoformat()
        }
        
        # 記憶庫統計
        if SpiralMemory:
            try:
                spiral_memory = SpiralMemory()
                memory_stats = await spiral_memory.get_memory_stats_v2()
                stats_data["memory_stats"] = memory_stats
            except Exception as e:
                logger.warning(f"記憶統計獲取失敗: {e}")
                stats_data["memory_stats"] = {"error": str(e)}
        else:
            stats_data["memory_stats"] = {"error": "記憶組件不可用"}
        
        # 會話統計
        session_manager = _get_session_manager()
        if session_manager:
            try:
                sessions_info = session_manager.get_sessions_info()
                stats_data["statistics"] = {
                    "system_uptime": "運行中",
                    "active_sessions": len(sessions_info),
                    "total_rounds_processed": sum([s.get('round_count', 0) for s in sessions_info]),
                    "total_cases_used": sum([len(s.get('used_cases', [])) for s in sessions_info])
                }
            except Exception as e:
                logger.warning(f"會話統計獲取失敗: {e}")
                stats_data["statistics"] = {
                    "system_uptime": "運行中",
                    "active_sessions": 0,
                    "total_rounds_processed": 0,
                    "total_cases_used": 0,
                    "error": str(e)
                }
        else:
            stats_data["statistics"] = {
                "system_uptime": "運行中",
                "active_sessions": 0,
                "total_rounds_processed": 0,
                "total_cases_used": 0,
                "error": "會話管理器不可用"
            }
        
        return JSONResponse(stats_data)
        
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
    """重置 S-CBR 記憶庫（開發和調試用）v2.0"""
    try:
        SpiralMemory = _get_memory_components()
        
        reset_results = []
        
        # 重置記憶庫
        if SpiralMemory:
            try:
                spiral_memory = SpiralMemory()
                cleanup_stats = await spiral_memory.cleanup_expired_memories_v2()
                reset_results.append(f"記憶庫清理: {cleanup_stats.get('total_cleaned', 0)} 個記錄")
            except Exception as e:
                reset_results.append(f"記憶庫重置失敗: {str(e)}")
        else:
            reset_results.append("記憶庫組件不可用")
        
        # 重置會話管理器
        session_manager = _get_session_manager()
        if session_manager:
            try:
                session_manager.reset_all_sessions()
                reset_results.append("所有螺旋會話已重置")
            except Exception as e:
                reset_results.append(f"會話重置失敗: {str(e)}")
        else:
            reset_results.append("會話管理器不可用")
        
        logger.info(f"🔄 S-CBR v2.0 重置完成: {'; '.join(reset_results)}")
        
        return JSONResponse({
            "status": "success",
            "message": "S-CBR v2.0 記憶庫與螺旋會話重置完成",
            "details": reset_results,
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

# 向後兼容端點
@router.get("/health")
async def health_check_compatibility():
    """向後兼容的健康檢查端點"""
    return await scbr_health_check()

# 導出路由器
__all__ = ["router"]
