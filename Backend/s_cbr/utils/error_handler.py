# -*- coding: utf-8 -*-
"""
安全相關的輔助函數
"""

def sanitize_error_message(error: Exception) -> str:
    """
    淨化錯誤訊息，避免洩露技術細節
    
    Args:
        error: 異常對象
        
    Returns:
        安全的用戶友好錯誤訊息
    """
    error_str = str(error).lower()
    
    # 移除敏感關鍵詞
    sensitive_keywords = [
        'weaviate', 'database', 'config', 'api key', 'token',
        'traceback', 'exception', 'error at line', 'file "/"'
    ]
    
    for keyword in sensitive_keywords:
        if keyword in error_str:
            return "系統處理時發生錯誤，請稍後再試"
    
    # 如果沒有敏感信息，返回簡化的錯誤訊息
    return "請求處理失敗，請檢查輸入後重試"
