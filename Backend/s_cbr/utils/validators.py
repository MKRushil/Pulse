# -*- coding: utf-8 -*-
"""
數據驗證器
"""

import re
from typing import Any, Dict, List, Optional
from .logger import get_logger

logger = get_logger("Validators")

class ValidationError(Exception):
    """驗證錯誤"""
    pass

def validate_question(question: Any) -> str:
    """驗證問題"""
    
    if not question:
        raise ValidationError("問題不能為空")
    
    if not isinstance(question, str):
        question = str(question)
    
    question = question.strip()
    
    if not question:
        raise ValidationError("問題不能為空白")
    
    # 長度限制
    if len(question) > 1000:
        raise ValidationError("問題長度不能超過1000字符")
    
    if len(question) < 2:
        raise ValidationError("問題太短，請提供更多資訊")
    
    # 檢查是否包含有效中文
    if not re.search(r'[\u4e00-\u9fff]', question):
        logger.warning(f"問題不包含中文: {question[:50]}")
    
    return question

def validate_session_id(session_id: Any) -> Optional[str]:
    """驗證會話ID"""
    
    if not session_id:
        return None
    
    session_id = str(session_id).strip()
    
    if not session_id:
        return None
    
    # UUID 格式驗證
    uuid_pattern = r'^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$'
    if not re.match(uuid_pattern, session_id, re.IGNORECASE):
        logger.warning(f"無效的會話ID格式: {session_id}")
        return None
    
    return session_id

def validate_patient_context(ctx: Any) -> Dict[str, Any]:
    """驗證患者上下文"""
    
    if not ctx:
        return {}
    
    if not isinstance(ctx, dict):
        logger.warning(f"患者上下文不是字典: {type(ctx)}")
        return {}
    
    # 清理和驗證各字段
    validated = {}
    
    # 年齡
    if "age" in ctx:
        try:
            age = int(ctx["age"])
            if 0 < age < 150:
                validated["age"] = age
        except (ValueError, TypeError):
            logger.warning(f"無效年齡: {ctx['age']}")
    
    # 性別
    if "gender" in ctx:
        gender = str(ctx["gender"]).strip().lower()
        if gender in ["男", "女", "male", "female", "m", "f"]:
            validated["gender"] = gender
    
    # 主訴
    if "chief_complaint" in ctx:
        cc = str(ctx["chief_complaint"]).strip()
        if cc and len(cc) < 500:
            validated["chief_complaint"] = cc
    
    # 既往史
    if "medical_history" in ctx:
        mh = ctx["medical_history"]
        if isinstance(mh, list):
            validated["medical_history"] = [str(h).strip() for h in mh if h]
        elif isinstance(mh, str):
            validated["medical_history"] = [mh.strip()]
    
    return validated

def validate_vector(vector: Any, expected_dim: int = 1024) -> List[float]:
    """驗證向量"""
    
    if not vector:
        raise ValidationError("向量為空")
    
    if not isinstance(vector, (list, tuple)):
        raise ValidationError(f"向量類型錯誤: {type(vector)}")
    
    # 轉換為浮點數列表
    try:
        float_vector = [float(x) for x in vector]
    except (ValueError, TypeError) as e:
        raise ValidationError(f"向量包含非數值元素: {e}")
    
    # 檢查維度
    if len(float_vector) != expected_dim:
        logger.warning(
            f"向量維度不匹配: expected={expected_dim}, got={len(float_vector)}"
        )
    
    # 檢查是否全為零
    if all(x == 0 for x in float_vector):
        logger.warning("向量全為零")
    
    return float_vector

def validate_search_results(results: Any) -> List[Dict]:
    """驗證搜索結果"""
    
    if not results:
        return []
    
    if not isinstance(results, list):
        logger.warning(f"搜索結果不是列表: {type(results)}")
        return []
    
    validated = []
    
    for item in results:
        if not isinstance(item, dict):
            logger.warning(f"搜索項不是字典: {type(item)}")
            continue
        
        # 確保有基本字段
        if not item.get("id") and not item.get("case_id") and not item.get("rid"):
            logger.warning("搜索項缺少ID")
            continue
        
        validated.append(item)
    
    return validated

def validate_convergence_metrics(metrics: Any) -> Dict[str, float]:
    """驗證收斂指標"""
    
    if not isinstance(metrics, dict):
        return {}
    
    validated = {}
    
    required_keys = [
        'case_stability',
        'score_improvement', 
        'semantic_consistency',
        'evidence_coverage',
        'overall_convergence'
    ]
    
    for key in required_keys:
        if key in metrics:
            try:
                value = float(metrics[key])
                # 限制範圍
                if key == 'score_improvement':
                    value = max(-1.0, min(1.0, value))
                else:
                    value = max(0.0, min(1.0, value))
                validated[key] = value
            except (ValueError, TypeError):
                validated[key] = 0.0
        else:
            validated[key] = 0.0
    
    return validated