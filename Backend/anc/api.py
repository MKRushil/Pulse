# -*- coding: utf-8 -*-
"""
ANC API Routes
病例存檔與正規化 API 端點
"""

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
from pathlib import Path

from .schema import TCMCaseInput
from .case_processor import get_case_processor


router = APIRouter(prefix="/api/case", tags=["Case Management"])


@router.post("/save")
async def save_case(payload: Dict[str, Any] = Body(...)):
    """
    保存病例 API
    
    處理流程:
    1. 驗證資料格式
    2. 保存原始 JSON
    3. Jieba 分詞分析
    4. 生成 1024 維向量
    5. 上傳到 Weaviate
    6. 返回處理結果
    
    Request Body:
    {
        "basic": {...},
        "complaint": {...},
        "inspection": {...},
        "auscultation": {...},
        "inquiry": {...},
        "pulse": {...},
        "diagnosis": {...}
    }
    
    Response:
    {
        "success": true,
        "case_id": "CASE_20251002_1234_abcd1234",
        "json_path": "/path/to/case.json",
        "vectorized": true,
        "uploaded": true,
        "message": "病例已成功保存並上傳",
        "errors": []
    }
    """
    try:
        # 驗證資料格式
        try:
            case_input = TCMCaseInput(**payload)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"資料格式錯誤: {str(e)}"
            )
        
        # 處理病例
        processor = get_case_processor()
        result = processor.process_case(case_input)
        
        # 構建回應
        if result["success"]:
            status_code = 200
            message = "✅ 病例已成功保存並上傳"
            
            # 補充詳細狀態
            if not result["vectorized"]:
                message += " (向量化失敗)"
            if not result["uploaded"]:
                message += " (未上傳到資料庫)"
        else:
            status_code = 500
            message = "❌ 病例處理失敗"
        
        response_data = {
            **result,
            "message": message
        }
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"伺服器錯誤: {str(e)}"
        )


@router.get("/get/{case_id}")
async def get_case(case_id: str):
    """
    根據 case_id 查詢病例
    
    Response:
    {
        "success": true,
        "data": {...}
    }
    """
    try:
        processor = get_case_processor()
        case_data = processor.get_case_by_id(case_id)
        
        if case_data:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": case_data
                }
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"找不到病例: {case_id}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"查詢失敗: {str(e)}"
        )


@router.post("/search")
async def search_cases(
    query: str = Body(..., embed=True),
    limit: int = Body(10, embed=True),
    filters: Optional[Dict] = Body(None, embed=True)
):
    """
    搜索相似病例
    
    Request Body:
    {
        "query": "咳嗽發熱",
        "limit": 10,
        "filters": {
            "gender": "女",
            "age_min": 30,
            "age_max": 60
        }
    }
    
    Response:
    {
        "success": true,
        "results": [
            {
                "case_id": "...",
                "patient_id": "...",
                "chief_complaint": "...",
                "diagnosis": "...",
                "score": 0.95
            },
            ...
        ],
        "count": 10
    }
    """
    try:
        processor = get_case_processor()
        results = processor.search_cases(query, limit, filters)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "results": results,
                "count": len(results)
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜索失敗: {str(e)}"
        )


@router.get("/stats")
async def get_stats():
    """
    獲取病例統計資訊
    
    Response:
    {
        "total_cases": 150,
        "total_json_files": 150,
        "collection_exists": true
    }
    """
    try:
        from .config import RAW_CASES_DIR, CASE_COLLECTION_NAME
        import os
        
        # 統計 JSON 檔案數量
        json_count = 0
        for root, dirs, files in os.walk(RAW_CASES_DIR):
            json_count += len([f for f in files if f.endswith('.json')])
        
        # 檢查 Weaviate Collection
        processor = get_case_processor()
        collection_exists = processor.collection is not None
        
        # 統計向量資料庫中的病例數
        total_cases = 0
        if collection_exists:
            try:
                response = processor.collection.aggregate.over_all(total_count=True)
                total_cases = response.total_count
            except:
                total_cases = 0
        
        return JSONResponse(
            status_code=200,
            content={
                "total_cases": total_cases,
                "total_json_files": json_count,
                "collection_exists": collection_exists,
                "raw_cases_dir": str(RAW_CASES_DIR)
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"獲取統計失敗: {str(e)}"
        )