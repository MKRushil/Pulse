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
from pydantic import BaseModel, Field, validator
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

    @validator('history_summary')
    def validate_history_summary(cls, v):
        # 允許為空；限制長度避免過長
        v = v or ""
        return v[:2000]
    
    @validator('question')
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
    
    @validator('session_id')
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
    
    @validator('session_id')
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
        客戶端IP地址
    """
    # 檢查代理頭
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # X-Forwarded-For 可能包含多個IP，取第一個
        return x_forwarded_for.split(",")[0].strip()
    
    # 檢查 X-Real-IP
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    
    # 直接連接
    if request.client and request.client.host:
        return request.client.host
    
    return "unknown"


from .utils.error_handler import sanitize_error_message


def mask_pii_in_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    在響應中脫敏 PII/PHI 資訊
    
    Args:
        data: 響應數據
        
    Returns:
        脫敏後的數據
    """
    # 深拷貝以避免修改原數據
    import copy
    masked_data = copy.deepcopy(data)
    
    # 需要脫敏的欄位
    pii_fields = ['patient_name', 'id_number', 'phone', 'email', 'address']
    
    def recursive_mask(obj):
        """遞歸脫敏"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in pii_fields and value:
                    obj[key] = "***masked***"
                elif isinstance(value, (dict, list)):
                    recursive_mask(value)
        elif isinstance(obj, list):
            for item in obj:
                recursive_mask(item)
    
    recursive_mask(masked_data)
    return masked_data


# ==================== API 端點 ====================

@router.post("/diagnose")
async def diagnose(req: DiagnoseRequest, request: Request):
    """
    執行螺旋推理診斷 - 安全增強版本
    
    安全措施：
    1. 輸入驗證（Pydantic）
    2. 速率限制（基於IP）
    3. 輸入淨化（在 main.py 中）
    4. 錯誤隱藏（不洩露技術細節）
    5. PII 脫敏（輸出中）
    
    Args:
        req: 診斷請求
        request: FastAPI Request（用於獲取IP）
        
    Returns:
        診斷結果（已脫敏）
    """
    # 獲取客戶端IP
    client_ip = get_client_ip(request)
    
    try:
        logger.info(f"📥 收到診斷請求: {req.question[:50]}... (IP: {client_ip})")
        
        # 調用主引擎（內部會進行安全檢查）
        # 將 history_summary 瘦身為結構化摘要（字串表示），避免長段原文逐輪膨脹
        structured_hist = structure_history_summary(req.history_summary or "")

        result = await run_spiral_cbr(
            question=req.question,
            patient_ctx=req.patient_ctx,
            session_id=req.session_id,
            continue_spiral=req.continue_spiral,
            user_ip=client_ip,  # ✅ 傳遞IP用於速率限制
            history_summary=structured_hist,
            disable_case_slimming=req.disable_case_slimming
        )
        
        # 檢查是否有錯誤（安全相關）
        if "error" in result:
            error_type = result.get("error")
            error_message = result.get("message", "處理失敗")
            
            # 根據錯誤類型返回適當的 HTTP 狀態碼
            if error_type == "rate_limit_exceeded":
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": error_type,
                        "message": error_message,
                        "retry_after": result.get("retry_after", 60)
                    }
                )
            elif error_type == "security_violation":
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": error_type,
                        "message": error_message
                    }
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": error_type,
                        "message": error_message
                    }
                )
        
        # ✅ 脫敏 PII/PHI
        masked_result = mask_pii_in_response(result)
        
        logger.info(f"✅ 診斷完成: session_id={masked_result.get('session_id', 'N/A')}")
        return masked_result
        
    except HTTPException:
        raise
    
    except ValueError as e:
        # 輸入驗證錯誤
        logger.warning(f"⚠️ 輸入驗證失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # 未預期的錯誤
        logger.error(f"❌ 診斷失敗: {e}", exc_info=True)
        
        # 不洩露技術細節
        safe_message = sanitize_error_message(e)
        raise HTTPException(status_code=500, detail=safe_message)


@router.post("/session/reset")
async def reset_session(req: SessionResetRequest):
    """
    重置會話
    
    Args:
        req: 重置請求
        
    Returns:
        操作結果
    """
    try:
        engine = get_engine()
        engine.reset_session(req.session_id)
        
        logger.info(f"🔄 會話已重置: {req.session_id}")
        return {
            "status": "success",
            "message": f"會話 {req.session_id[:8]}*** 已重置"
        }
        
    except Exception as e:
        logger.error(f"❌ 重置會話失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=sanitize_error_message(e)
        )


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    獲取會話資訊 - 已脫敏版本
    
    Args:
        session_id: 會話ID
        
    Returns:
        會話資訊（已脫敏PII）
    """
    try:
        # 驗證 session_id 格式
        uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        if not re.match(uuid_pattern, session_id.lower()):
            raise HTTPException(
                status_code=400,
                detail="無效的 session_id 格式"
            )
        
        engine = get_engine()
        session = engine.dialog.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="會話不存在")
        
        # 構建響應（不包含敏感信息）
        response = {
            "session_id": session_id,
            "round_count": session.round_count,
            "accumulated_question": session.accumulated_question[:100] + "...",  # 限制長度
            "history_count": len(session.history),
            "created_at": session.created_at.isoformat(),
            # ✅ 不返回完整的 patient_ctx（可能包含PII）
            "has_patient_context": bool(session.patient_ctx)
        }
        
        logger.info(f"📊 獲取會話資訊: {session_id[:8]}***")
        return response
        
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ 獲取會話資訊失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=sanitize_error_message(e)
        )


# @router.post("/case/save-effective")
# async def save_effective_case(req: SaveCaseRequest):
#     """
#     儲存有效治療案例到 RPCase
    
#     此端點應該在前端確認治療有效後調用
    
#     Args:
#         req: 保存請求
        
#     Returns:
#         保存結果
#     """
#     try:
#         engine = get_engine()
#         session = engine.dialog.get_session(req.session_id)
        
#         if not session:
#             raise HTTPException(status_code=404, detail="會話不存在")
        
#         # 檢查是否標記為可儲存
#         if not session.history:
#             raise HTTPException(status_code=400, detail="會話無歷史記錄")
        
#         last_step = session.history[-1]
#         save_prompt = last_step.get("save_prompt", {})
        
#         if not save_prompt.get("can_save", False):
#             return {
#                 "status": "rejected",
#                 "message": "該會話未達到有效治療標準",
#                 "reason": save_prompt.get("message", "")
#             }
        
#         # ✅ 調用 RPCaseManager 儲存
#         from .core.rpcase_manager import RPCaseManager
#         rpcase_mgr = RPCaseManager(
#             weaviate_client=engine.spiral.SE.weaviate_client,
#             config=engine.config
#         )
        
#         # 準備儲存數據（已脫敏）
#         session_data = {
#             "session_id": req.session_id,
#             "diagnosis": last_step.get("primary", {}).get("diagnosis", ""),
#             "conversation_history": [
#                 {
#                     "round": step.get("round"),
#                     "question": step.get("question", "")[:200]  # 限制長度
#                 }
#                 for step in session.history
#             ],
#             "primary": last_step.get("primary", {}),
#             "convergence_metrics": last_step.get("convergence", {}),
#             "round": session.round_count
#         }
        
#         result = await rpcase_mgr.save_from_session(session_data)
        
#         if result.get("success"):
#             logger.info(f"💾 RPCase 儲存成功: {result.get('case_id')}")
#             return {
#                 "status": "success",
#                 "message": "有效案例已儲存",
#                 "case_id": result.get("case_id"),
#                 "effectiveness_score": save_prompt.get("effectiveness_score", 0)
#             }
#         else:
#             raise HTTPException(
#                 status_code=500,
#                 detail=f"儲存失敗: {sanitize_error_message(Exception(result.get('error')))}"
#             )
        
#     except HTTPException:
#         raise
    
#     except Exception as e:
#         logger.error(f"❌ 儲存 RPCase 失敗: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=500,
#             detail=sanitize_error_message(e)
#         )


@router.get("/case/save-status/{session_id}")
async def get_save_status(session_id: str):
    """
    檢查會話是否可儲存為有效案例
    
    Args:
        session_id: 會話ID
        
    Returns:
        儲存狀態資訊
    """
    try:
        # 驗證格式
        uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        if not re.match(uuid_pattern, session_id.lower()):
            raise HTTPException(status_code=400, detail="無效的 session_id 格式")
        
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
        logger.error(f"❌ 檢查儲存狀態失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=sanitize_error_message(e)
        )


@router.get("/health")
async def health_check():
    """
    健康檢查端點
    
    用於監控系統是否正常運行
    
    Returns:
        健康狀態資訊
    """
    try:
        engine = get_engine()
        
        # 檢查關鍵組件
        components_status = {
            "dialog_manager": engine.dialog is not None,
            "spiral_engine": engine.spiral is not None,
            "llm_client": engine.llm is not None,
            "input_sanitizer": engine.input_sanitizer is not None,
            "output_validator": engine.output_validator is not None
        }
        
        all_healthy = all(components_status.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "version": engine.version,
            "service": "S-CBR API",
            "timestamp": datetime.now().isoformat(),
            "components": components_status
        }
        
    except Exception as e:
        logger.error(f"❌ 健康檢查失敗: {e}")
        return {
            "status": "unhealthy",
            "service": "S-CBR API",
            "error": "Health check failed"
        }


@router.get("/stats")
async def get_stats():
    """
    獲取系統統計資訊（不包含敏感數據）
    
    Returns:
        統計資訊
    """
    try:
        engine = get_engine()
        
        # 獲取基本統計（不洩露用戶數據）
        stats = {
            "active_sessions": len(engine.dialog.sessions),
            "system_version": engine.version,
            "features": {
                "llm_enabled": engine.llm is not None,
                "security_enabled": True
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ 獲取統計失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail="無法獲取統計資訊"
        )


def structure_history_summary(raw: str) -> str:
    """將前端傳來的 history_summary 文本壓縮為瘦版結構化摘要字串。

    規則（簡化）：
    - 以常見分隔（逗號/頓號/換行/空白）切詞
    - 以關鍵字包含判斷粗分為 tongue/pulse，其餘歸 symptoms
    - 回傳固定格式字串：symptoms=[...]; tongue=[...]; pulse=[...]
    """
    if not raw:
        return ""
    import re
    tokens = [t.strip() for t in re.split(r"[\s,，、\n]+", raw) if t.strip()]
    symptoms, tongue, pulse = [], [], []
    for t in tokens:
        if '舌' in t:
            tongue.append(t)
        elif '脈' in t:
            pulse.append(t)
        else:
            symptoms.append(t)
    # 去重保持順序
    def _dedup_keep_order(arr):
        return list(dict.fromkeys(arr))

    symptoms = _dedup_keep_order(symptoms)
    tongue = _dedup_keep_order(tongue)
    pulse = _dedup_keep_order(pulse)

    # 若三段合計長度超過 client 安全長度一半（約 1500 字），從最舊項目開始截斷
    def _render(sy, tg, pl):
        def _fmt(arr):
            return ", ".join(arr)
        return f"symptoms=[{_fmt(sy)}]; tongue=[{_fmt(tg)}]; pulse=[{_fmt(pl)}]"

    MAX_LEN = 1500
    while True:
        rendered = _render(symptoms, tongue, pulse)
        if len(rendered) <= MAX_LEN:
            break
        # 優先從 symptoms 刪，再從 tongue，再從 pulse（舊項目優先）
        if symptoms:
            symptoms.pop(0)
        elif tongue:
            tongue.pop(0)
        elif pulse:
            pulse.pop(0)
        else:
            break
    return _render(symptoms, tongue, pulse)
