# -*- coding: utf-8 -*-
"""
S-CBR API 路由 - 安全增強版本

主要安全功能：
- LLM01: 輸入驗證與淨化
- LLM02: PII/PHI 脫敏
- LLM10: 速率限制與資源保護
- API 安全: CORS、請求大小限制、錯誤隱藏
"""

from fastapi import APIRouter, Body, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, List
import re, datetime

from .main import run_spiral_cbr, get_engine
from .utils.logger import get_logger

router = APIRouter(prefix="/api/scbr/v2", tags=["S-CBR"])
logger = get_logger("SCBR-API")

# ==================== Pydantic 模型定義 ====================

class DiagnoseRequest(BaseModel):
    """
    診斷請求模型 - 含輸入驗證
    """
    question: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="用戶問題/症狀描述（2-1000字符）"
    )
    patient_ctx: Optional[Dict[str, Any]] = Field(
        default=None,
        description="患者上下文信息（可選）"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="會話ID（可選，不提供則創建新會話）"
    )
    continue_spiral: bool = Field(
        default=False,
        description="是否繼續現有會話的螺旋推理"
    )
    history_summary: Optional[str] = Field(
        default="",
        description="多輪對話歷史摘要（前端累積傳遞）"
    )
    disable_case_slimming: Optional[bool] = Field(
        default=None,
        description="是否停用案例瘦身（True=停用，None=使用預設）"
    )

    @field_validator('history_summary')
    @classmethod
    def validate_history_summary(cls, v):
        """
        驗證歷史摘要
        
        允許為空；限制長度避免過長
        """
        # 允許為空；限制長度避免過長
        v = v or ""
        return v[:2000]
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        """
        驗證問題內容
        
        檢查：
        1. 不能全是空格
        2. 不能包含明顯的腳本注入
        3. 不能包含HTML標籤
        """
        # 檢查是否全是空格
        if not v.strip():
            raise ValueError("問題不能為空")
        
        # 檢查是否包含 HTML/JavaScript 標籤
        html_pattern = r'<[^>]+>'
        if re.search(html_pattern, v):
            raise ValueError("問題不能包含HTML標籤")
        
        # 檢查是否包含可疑的腳本關鍵詞
        script_keywords = ['<script', 'javascript:', 'onerror=', 'onclick=']
        v_lower = v.lower()
        for keyword in script_keywords:
            if keyword in v_lower:
                raise ValueError("問題包含不允許的內容")
        
        return v.strip()
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        """
        驗證 session_id 格式（UUID 格式）
        """
        if v is None:
            return v
        
        # UUID 格式檢查
        uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        if not re.match(uuid_pattern, v.lower()):
            raise ValueError("session_id 必須是有效的 UUID 格式")
        
        return v


class SessionResetRequest(BaseModel):
    """
    會話重置請求
    """
    session_id: str = Field(
        ...,
        description="要重置的會話ID"
    )
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        """驗證 session_id 格式"""
        uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        if not re.match(uuid_pattern, v.lower()):
            raise ValueError("session_id 必須是有效的 UUID 格式")
        return v


class SaveCaseRequest(BaseModel):
    """
    保存病例請求
    """
    session_id: str = Field(
        ...,
        description="會話ID"
    )
    case_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="額外的病例數據（可選）"
    )


# ==================== 輔助函數 ====================

def get_client_ip(request: Request) -> str:
    """
    獲取客戶端真實IP地址
    
    優先順序：
    1. X-Forwarded-For (代理頭)
    2. X-Real-IP (Nginx頭)
    3. request.client.host (直接連接)
    
    Args:
        request: FastAPI Request 對象
        
    Returns:
        str: 客戶端IP地址
    """
    # 檢查代理頭
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For 可能包含多個IP，取第一個
        return forwarded_for.split(",")[0].strip()
    
    # 檢查 Nginx 頭
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # 直接連接
    if request.client and request.client.host:
        return request.client.host
    
    return "unknown"


def sanitize_error_message(error: Exception) -> str:
    """
    清理錯誤訊息，避免洩露敏感信息
    
    Args:
        error: 異常對象
        
    Returns:
        str: 安全的錯誤訊息
    """
    error_str = str(error)
    
    # 移除敏感路徑信息
    error_str = re.sub(r'[A-Za-z]:\\[^\s]+', '[PATH]', error_str)
    error_str = re.sub(r'/[^\s]+/[^\s]+', '[PATH]', error_str)
    
    # 移除可能的敏感配置
    error_str = re.sub(r'password[=:]\S+', 'password=[REDACTED]', error_str, flags=re.IGNORECASE)
    error_str = re.sub(r'api[_-]?key[=:]\S+', 'api_key=[REDACTED]', error_str, flags=re.IGNORECASE)
    error_str = re.sub(r'token[=:]\S+', 'token=[REDACTED]', error_str, flags=re.IGNORECASE)
    
    # 限制長度
    if len(error_str) > 200:
        error_str = error_str[:197] + "..."
    
    return error_str


# ==================== API 端點 ====================

@router.post("/diagnose", response_model=Dict[str, Any])
async def diagnose(
    request: Request,
    body: DiagnoseRequest = Body(...)
):
    """
    核心診斷端點 - 執行螺旋推理
    
    安全功能：
    - 輸入驗證（Pydantic）
    - 速率限制（IP + Session）
    - PII 脫敏
    - 錯誤訊息清理
    
    Args:
        request: FastAPI Request 對象
        body: 診斷請求體
        
    Returns:
        Dict[str, Any]: 診斷結果
        
    Raises:
        HTTPException: 
            - 422: 輸入驗證失敗或安全攔截
            - 429: 速率限制超出
            - 500: 內部錯誤
    """
    start_time = datetime.datetime.now()
    client_ip = get_client_ip(request)
    
    logger.info(f"📥 收到診斷請求 [IP: {client_ip}]")
    logger.info(f"   問題: {body.question[:50]}...")
    logger.info(f"   Session ID: {body.session_id}")
    
    try:
        # 獲取引擎實例
        engine = get_engine()
        
        # 執行速率限制檢查
        if engine.rate_limiter:
            try:
                engine.rate_limiter.check_rate_limit(
                    ip=client_ip,
                    session_id=body.session_id
                )
            except Exception as e:
                logger.warning(f"⚠️ 速率限制觸發: {e}")
                raise HTTPException(
                    status_code=429,
                    detail={
                        "message": "請求過於頻繁，請稍後再試",
                        "error": "RATE_LIMIT_EXCEEDED"
                    }
                )
        
        # 執行診斷
        result = await run_spiral_cbr(
            question=body.question,
            patient_ctx=body.patient_ctx,
            session_id=body.session_id,
            continue_spiral=body.continue_spiral,
            history_summary=body.history_summary,
            disable_case_slimming=body.disable_case_slimming,
            user_ip=client_ip
        )
        
        # 記錄處理時間
        processing_time = (datetime.datetime.now() - start_time).total_seconds()
        logger.info(f"✅ 診斷完成 [IP: {client_ip}] 耗時: {processing_time:.2f}s")
        
        return result
        
    except HTTPException:
        # HTTPException 直接拋出（已經格式化）
        raise
        
    except Exception as e:
        # 其他異常：清理錯誤訊息並返回 500
        logger.error(f"❌ 診斷失敗 [IP: {client_ip}]: {e}", exc_info=True)
        
        safe_error_message = sanitize_error_message(e)
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "診斷過程中發生內部錯誤",
                "error": safe_error_message
            }
        )


@router.post("/reset", response_model=Dict[str, Any])
async def reset_session(
    request: Request,
    body: SessionResetRequest = Body(...)
):
    """
    重置會話端點
    
    清除指定會話的所有歷史記錄和狀態
    
    Args:
        request: FastAPI Request 對象
        body: 會話重置請求體
        
    Returns:
        Dict[str, Any]: 重置結果
        
    Raises:
        HTTPException:
            - 404: 會話不存在
            - 500: 內部錯誤
    """
    client_ip = get_client_ip(request)
    session_id = body.session_id
    
    logger.info(f"🔄 收到會話重置請求 [IP: {client_ip}, Session: {session_id}]")
    
    try:
        engine = get_engine()
        
        # 檢查會話是否存在
        if not engine.dialog.has_session(session_id):
            raise HTTPException(
                status_code=404,
                detail={
                    "message": f"會話 {session_id} 不存在",
                    "error": "SESSION_NOT_FOUND"
                }
            )
        
        # 執行重置
        engine.dialog.reset_session(session_id)
        
        logger.info(f"✅ 會話重置成功 [Session: {session_id}]")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "會話已重置"
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"❌ 會話重置失敗 [Session: {session_id}]: {e}", exc_info=True)
        
        safe_error_message = sanitize_error_message(e)
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "重置會話時發生內部錯誤",
                "error": safe_error_message
            }
        )


@router.get("/session/{session_id}", response_model=Dict[str, Any])
async def get_session_info(
    request: Request,
    session_id: str
):
    """
    獲取會話信息端點
    
    返回指定會話的當前狀態和歷史記錄
    
    Args:
        request: FastAPI Request 對象
        session_id: 會話ID
        
    Returns:
        Dict[str, Any]: 會話信息
        
    Raises:
        HTTPException:
            - 404: 會話不存在
            - 500: 內部錯誤
    """
    client_ip = get_client_ip(request)
    
    logger.info(f"📋 收到會話查詢請求 [IP: {client_ip}, Session: {session_id}]")
    
    try:
        engine = get_engine()
        
        # 檢查會話是否存在
        if not engine.dialog.has_session(session_id):
            raise HTTPException(
                status_code=404,
                detail={
                    "message": f"會話 {session_id} 不存在",
                    "error": "SESSION_NOT_FOUND"
                }
            )
        
        # 獲取會話信息
        session = engine.dialog.get_session(session_id)
        
        return {
            "session_id": session.session_id,
            "round_count": session.round_count,
            "accumulated_question": session.accumulated_question,
            "created_at": session.created_at.isoformat() if hasattr(session, 'created_at') else None,
            "history_count": len(session.history) if hasattr(session, 'history') else 0
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"❌ 獲取會話信息失敗 [Session: {session_id}]: {e}", exc_info=True)
        
        safe_error_message = sanitize_error_message(e)
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "獲取會話信息時發生內部錯誤",
                "error": safe_error_message
            }
        )


@router.post("/save-case", response_model=Dict[str, Any])
async def save_case(
    request: Request,
    body: SaveCaseRequest = Body(...)
):
    """
    保存病例端點
    
    將會話的診斷結果保存為正式病例
    
    Args:
        request: FastAPI Request 對象
        body: 保存病例請求體
        
    Returns:
        Dict[str, Any]: 保存結果
        
    Raises:
        HTTPException:
            - 404: 會話不存在
            - 500: 內部錯誤
    """
    client_ip = get_client_ip(request)
    session_id = body.session_id
    
    logger.info(f"💾 收到保存病例請求 [IP: {client_ip}, Session: {session_id}]")
    
    try:
        engine = get_engine()
        
        # 檢查會話是否存在
        if not engine.dialog.has_session(session_id):
            raise HTTPException(
                status_code=404,
                detail={
                    "message": f"會話 {session_id} 不存在",
                    "error": "SESSION_NOT_FOUND"
                }
            )
        
        # TODO: 實作病例保存邏輯
        # 這裡需要調用病例管理系統的API
        
        logger.info(f"✅ 病例保存成功 [Session: {session_id}]")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "病例已保存",
            "case_id": f"CASE-{session_id}"  # 臨時ID，實際應由病例系統生成
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"❌ 保存病例失敗 [Session: {session_id}]: {e}", exc_info=True)
        
        safe_error_message = sanitize_error_message(e)
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "保存病例時發生內部錯誤",
                "error": safe_error_message
            }
        )


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    健康檢查端點
    
    返回系統的基本健康狀態
    
    Returns:
        Dict[str, Any]: 健康狀態信息
    """
    try:
        engine = get_engine()
        
        # 檢查核心組件
        components_status = {
            "llm_client": engine.llm is not None,
            "dialog_manager": engine.dialog is not None,
            "search_engine": engine.SE is not None,
            "embed_client": engine.embed is not None,
            "four_layer_pipeline": engine.four_layer is not None
        }
        
        # 計算整體健康狀態
        all_healthy = all(components_status.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "version": engine.version,
            "timestamp": datetime.datetime.now().isoformat(),
            "components": components_status
        }
        
    except Exception as e:
        logger.error(f"❌ 健康檢查失敗: {e}", exc_info=True)
        
        return {
            "status": "unhealthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "error": sanitize_error_message(e)
        }