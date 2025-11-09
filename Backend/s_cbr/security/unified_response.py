# -*- coding: utf-8 -*-
"""
統一錯誤響應格式

功能：
1. 前端統一顯示友好錯誤訊息
2. 後端已記錄詳細 OWASP 分類（透過 owasp_mapper）
3. 區分使用者體驗與論文數據採集

設計原則：
- 前端：簡潔友好，不洩露技術細節
- 後端：詳細記錄，包含 OWASP 分類與攻擊樣本
- 論文：結構化數據，用於統計分析

使用範例：
    from s_cbr.security.unified_response import create_security_rejection_response
    
    # 在任何防禦模組拒絕後：
    return create_security_rejection_response(trace_id)
"""

from typing import Dict, Any

# ==================== 前端統一錯誤訊息 ====================

# 主要錯誤訊息（前端顯示）
USER_FRIENDLY_ERROR = "輸入內容違反系統安全政策，請重新嘗試。"

# 可選的詳細說明（可用於幫助文件）
USER_FRIENDLY_HINTS = {
    "zh-TW": {
        "main": "輸入內容違反系統安全政策，請重新嘗試。",
        "hints": [
            "請確保您的輸入是關於中醫症狀的描述",
            "避免包含個人敏感資訊（如身份證、電話）",
            "如需幫助，請聯繫客服"
        ]
    },
    "en": {
        "main": "Input violates system security policy. Please try again.",
        "hints": [
            "Ensure your input describes TCM symptoms",
            "Avoid personal sensitive information",
            "Contact support if you need help"
        ]
    }
}


# ==================== 響應創建函數 ====================

def create_security_rejection_response(
    trace_id: str,
    language: str = "zh-TW",
    include_hints: bool = False
) -> Dict[str, Any]:
    """
    創建安全拒絕響應（統一格式）
    
    功能：
    - 前端顯示友好訊息（不洩露技術細節）
    - 後端已記錄詳細日誌（透過 owasp_mapper.log_defense_success）
    - 提供 trace_id 用於追蹤（用戶可提供給客服）
    
    Args:
        trace_id: 追蹤 ID（格式：SCBR-YYYYMMDD-HHMMSS-XXXX）
        language: 語言（zh-TW/en，預設繁體中文）
        include_hints: 是否包含提示（預設否）
    
    Returns:
        統一格式的拒絕響應字典
    
    響應格式：
        {
            "status": "rejected",
            "error": "security_policy_violation",
            "message": "輸入內容違反系統安全政策，請重新嘗試。",
            "trace_id": "SCBR-20251107-143025-a1b2c3",
            "can_retry": true
        }
    
    使用範例：
        # 在 rate_limiter 中
        if not is_allowed:
            log_defense_success(...)  # 記錄後端日誌
            return create_security_rejection_response(trace_id)
        
        # 在 input_sanitizer 中
        if not sanitize_result.is_safe:
            log_defense_success(...)  # 記錄後端日誌
            return create_security_rejection_response(trace_id)
    
    前端收到的響應：
        {
            "status": "rejected",
            "error": "security_policy_violation",
            "message": "輸入內容違反系統安全政策，請重新嘗試。",
            "trace_id": "SCBR-20251107-143025-a1b2c3",
            "can_retry": true
        }
    
    前端處理範例（JavaScript）：
        if (response.status === "rejected" && 
            response.error === "security_policy_violation") {
            alert(response.message);  // "輸入內容違反系統安全政策，請重新嘗試。"
        }
    """
    # 獲取對應語言的錯誤訊息
    messages = USER_FRIENDLY_HINTS.get(language, USER_FRIENDLY_HINTS["zh-TW"])
    
    # 基本響應
    response = {
        "status": "rejected",
        "error": "security_policy_violation",
        "message": messages["main"],
        "trace_id": trace_id,
        "can_retry": True
    }
    
    # 可選：添加提示
    if include_hints:
        response["hints"] = messages["hints"]
    
    return response


def create_success_response(
    session_id: str,
    round: int,
    trace_id: str,
    processing_time: float,
    result: Dict[str, Any],
    security_checks: Dict[str, Any]
) -> Dict[str, Any]:
    """
    創建成功響應（統一格式）
    
    Args:
        session_id: 會話 ID
        round: 輪次
        trace_id: 追蹤 ID
        processing_time: 處理時間（秒）
        result: 診斷結果（包含 L1/L2/L3/L4）
        security_checks: 安全檢查摘要
    
    Returns:
        統一格式的成功響應字典
    
    響應格式：
        {
            "status": "success",
            "session_id": "abc-123-def",
            "round": 1,
            "trace_id": "SCBR-20251107-143025-a1b2c3",
            "processing_time": 6.8,
            "flow": "four_layer",
            "security_checks": {
                "input_sanitized": true,
                "output_validated": true,
                "threat_detected": false
            },
            "result": { ... }
        }
    """
    return {
        "status": "success",
        "session_id": session_id,
        "round": round,
        "trace_id": trace_id,
        "processing_time": processing_time,
        "flow": "four_layer",
        "security_checks": security_checks,
        "result": result
    }


def create_system_error_response(
    trace_id: str,
    language: str = "zh-TW"
) -> Dict[str, Any]:
    """
    創建系統錯誤響應（用於非安全類的系統錯誤）
    
    Args:
        trace_id: 追蹤 ID
        language: 語言
    
    Returns:
        系統錯誤響應字典
    
    響應格式：
        {
            "status": "error",
            "error": "system_error",
            "message": "系統錯誤，請稍後再試。",
            "trace_id": "SCBR-20251107-143025-a1b2c3",
            "can_retry": true
        }
    """
    messages = {
        "zh-TW": "系統錯誤，請稍後再試。",
        "en": "System error. Please try again later."
    }
    
    return {
        "status": "error",
        "error": "system_error",
        "message": messages.get(language, messages["zh-TW"]),
        "trace_id": trace_id,
        "can_retry": True
    }


# ==================== 錯誤類型常量 ====================

class ErrorType:
    """錯誤類型常量（用於統一錯誤處理）"""
    
    # 安全相關錯誤（使用 create_security_rejection_response）
    SECURITY_POLICY_VIOLATION = "security_policy_violation"
    
    # 系統相關錯誤（使用 create_system_error_response）
    SYSTEM_ERROR = "system_error"
    ENGINE_FAILED = "engine_failed"
    LLM_UNAVAILABLE = "llm_unavailable"
    
    # 業務相關錯誤
    INVALID_INPUT = "invalid_input"
    SESSION_NOT_FOUND = "session_not_found"


# ==================== 輔助函數 ====================

def is_security_rejection(response: Dict[str, Any]) -> bool:
    """
    判斷響應是否為安全拒絕
    
    Args:
        response: API 響應字典
    
    Returns:
        是否為安全拒絕
    
    使用範例：
        response = await engine.diagnose(...)
        if is_security_rejection(response):
            print("安全防禦已觸發")
    """
    return (
        response.get("status") == "rejected" and
        response.get("error") == ErrorType.SECURITY_POLICY_VIOLATION
    )


def extract_trace_id(response: Dict[str, Any]) -> str:
    """
    從響應中提取 trace_id
    
    Args:
        response: API 響應字典
    
    Returns:
        trace_id 字串（如不存在則返回空字串）
    
    使用範例：
        response = await engine.diagnose(...)
        trace_id = extract_trace_id(response)
        print(f"請求追蹤 ID: {trace_id}")
    """
    return response.get("trace_id", "")


# ==================== 模組測試 ====================

if __name__ == "__main__":
    # 測試範例
    print("=" * 60)
    print("Unified Response 測試")
    print("=" * 60)
    
    # 測試 1: 安全拒絕響應
    print("\n1. 安全拒絕響應:")
    rejection = create_security_rejection_response(
        trace_id="TEST-001",
        language="zh-TW"
    )
    import json
    print(json.dumps(rejection, ensure_ascii=False, indent=2))
    
    # 測試 2: 安全拒絕響應（帶提示）
    print("\n2. 安全拒絕響應（帶提示）:")
    rejection_with_hints = create_security_rejection_response(
        trace_id="TEST-002",
        language="zh-TW",
        include_hints=True
    )
    print(json.dumps(rejection_with_hints, ensure_ascii=False, indent=2))
    
    # 測試 3: 系統錯誤響應
    print("\n3. 系統錯誤響應:")
    error = create_system_error_response(
        trace_id="TEST-003",
        language="zh-TW"
    )
    print(json.dumps(error, ensure_ascii=False, indent=2))
    
    # 測試 4: 判斷是否為安全拒絕
    print("\n4. 判斷是否為安全拒絕:")
    print(f"rejection 是安全拒絕: {is_security_rejection(rejection)}")
    print(f"error 是安全拒絕: {is_security_rejection(error)}")
    
    # 測試 5: 提取 trace_id
    print("\n5. 提取 trace_id:")
    print(f"rejection trace_id: {extract_trace_id(rejection)}")
    print(f"error trace_id: {extract_trace_id(error)}")
    
    print("\n" + "=" * 60)
    print("✅ 測試完成")
    print("=" * 60)