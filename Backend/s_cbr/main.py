"""
S-CBR 主引擎入口模組 v2.0 - 螺旋互動版

功能：
1. 提供螺旋推理統一接口
2. 管理會話狀態與案例使用記錄
3. 支援每輪推理結果即時回傳
4. 智能案例過濾與重用機制

版本：v2.0 - 螺旋互動版
"""

from Backend.s_cbr.engines.spiral_cbr_engine import SpiralCBREngine
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger
from typing import Dict, Any, Optional, List
import asyncio
import datetime
import uuid
import hashlib

class SpiralSession:
    """
    螺旋推理會話管理類
    
    管理單個用戶的螺旋推理狀態：
    - 已使用案例列表
    - 推理輪次記錄
    - 原始問題追蹤
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.original_query = ""  # 原始問題
        self.used_cases = []      # 已使用案例ID列表
        self.round_count = 0      # 推理輪數
        self.current_result = {}  # 當前推理結果
        self.created_at = datetime.datetime.now()
        self.last_updated = datetime.datetime.now()
        
    def is_query_updated(self, new_query: str) -> bool:
        """
        判斷問題是否有實質更新
        使用文本相似度判斷，相似度 < 80% 視為有更新
        """
        if not self.original_query:
            return True
            
        # 計算文本相似度（簡單實現）
        similarity = self._calculate_text_similarity(self.original_query, new_query)
        return similarity < 0.8
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """計算兩個文本的相似度"""
        # 簡單的字符級相似度計算
        set1 = set(text1.replace(" ", ""))
        set2 = set(text2.replace(" ", ""))
        
        if not set1 or not set2:
            return 0.0
            
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def update_query(self, new_query: str):
        """更新查詢，如果有變化則重置已使用案例"""
        if self.is_query_updated(new_query):
            self.original_query = new_query
            self.used_cases = []  # 重置已使用案例
            self.round_count = 0  # 重置輪次
            
    def add_used_case(self, case_id: str):
        """添加已使用的案例ID"""
        if case_id not in self.used_cases:
            self.used_cases.append(case_id)
        self.last_updated = datetime.datetime.now()
        
    def increment_round(self):
        """增加推理輪次"""
        self.round_count += 1
        self.last_updated = datetime.datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'session_id': self.session_id,
            'original_query': self.original_query,
            'used_cases': self.used_cases,
            'round_count': self.round_count,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }

class SpiralSessionManager:
    """
    螺旋推理會話管理器
    
    管理所有活躍的螺旋推理會話
    """
    
    def __init__(self):
        self.sessions = {}  # session_id -> SpiralSession
        self.logger = SpiralLogger.get_logger("SpiralSessionManager")
        
    def get_or_create_session(self, session_id: Optional[str], query: str) -> SpiralSession:
        """獲取或創建會話"""
        if not session_id:
            # 基於查詢生成新的session_id
            session_id = self._generate_session_id(query)
            
        if session_id not in self.sessions:
            session = SpiralSession(session_id)
            session.update_query(query)
            self.sessions[session_id] = session
            self.logger.info(f"創建新螺旋會話: {session_id}")
        else:
            session = self.sessions[session_id]
            session.update_query(query)  # 檢查查詢是否更新
            
        return self.sessions[session_id]
    
    def _generate_session_id(self, query: str) -> str:
        """基於查詢內容生成會話ID"""
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()[:8]
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"spiral_{timestamp}_{query_hash}"
    
    def reset_session(self, session_id: str):
        """重置指定會話"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.logger.info(f"重置螺旋會話: {session_id}")
            
    def reset_all_sessions(self):
        """重置所有會話"""
        count = len(self.sessions)
        self.sessions.clear()
        self.logger.info(f"重置所有螺旋會話: {count} 個會話")
        
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """清理超過指定時間的會話"""
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=max_age_hours)
        old_sessions = [
            sid for sid, session in self.sessions.items()
            if session.last_updated < cutoff_time
        ]
        
        for sid in old_sessions:
            del self.sessions[sid]
            
        if old_sessions:
            self.logger.info(f"清理過期螺旋會話: {len(old_sessions)} 個")
            
    def get_sessions_info(self) -> List[Dict[str, Any]]:
        """獲取所有會話資訊"""
        return [session.to_dict() for session in self.sessions.values()]

class SCBREngine:
    """
    S-CBR 螺旋推理引擎主控器 v2.0
    
    v2.0 特色：
    - 支援螺旋互動推理
    - 會話狀態管理
    - 案例使用記錄
    - 每輪結果即時回傳
    """
    
    def __init__(self):
        """初始化S-CBR引擎 v2.0"""
        self.config = SCBRConfig()
        self.logger = SpiralLogger.get_logger("SCBREngine")
        self.spiral_engine = SpiralCBREngine()
        self.version = "2.0"
        self.logger.info(f"S-CBR 引擎 v{self.version} 初始化完成")
    
    async def execute_spiral_round(self, query: Dict[str, Any], session: SpiralSession) -> Dict[str, Any]:
        """
        執行一輪螺旋推理
        
        v2.0 流程：
        1. 過濾已使用案例
        2. 執行 Step1-4
        3. 記錄使用案例
        4. 構建當前輪結果
        """
        self.logger.info(f"開始執行第 {session.round_count + 1} 輪螺旋推理")
        
        try:
            # 增加輪次
            session.increment_round()
            
            # 執行螺旋推理（帶已用案例過濾）
            query['used_cases'] = session.used_cases
            query['session_id'] = session.session_id
            query['round'] = session.round_count
            
            result = await self.spiral_engine.start_spiral_dialog(query)
            
            # 記錄使用的案例
            if result.get('case_used_id'):
                session.add_used_case(result['case_used_id'])
            
            # 構建當前輪診斷結果
            current_diagnosis = {
                'round': session.round_count,
                'session_id': session.session_id,
                'case_used': result.get('case_used', ''),
                'diagnosis': result.get('diagnosis', ''),
                'treatment_plan': result.get('treatment_plan', ''),
                'safety_score': result.get('safety_score', 0.0),
                'efficacy_score': result.get('efficacy_score', 0.0),
                'confidence': result.get('confidence', 0.0),
                'recommendations': result.get('recommendations', ''),
                'used_cases_count': len(session.used_cases),
                'continue_available': len(session.used_cases) < 10,  # 最多使用10個案例
                'dialog': self._format_round_dialog(result, session),
                'llm_struct': result.get('llm_struct', {})
            }
            
            # 更新會話當前結果
            session.current_result = current_diagnosis
            
            self.logger.info(f"第 {session.round_count} 輪螺旋推理完成")
            
            return current_diagnosis
            
        except Exception as e:
            self.logger.error(f"第 {session.round_count} 輪螺旋推理失敗: {str(e)}")
            return {
                'round': session.round_count,
                'session_id': session.session_id,
                'error': True,
                'error_message': str(e),
                'dialog': f"第 {session.round_count} 輪推理失敗: {str(e)}",
                'continue_available': True
            }
    
    def _format_round_dialog(self, result: Dict[str, Any], session: SpiralSession) -> str:
        """格式化當前輪對話回覆"""
        dialog_parts = [
            f"🌀 第{session.round_count}輪螺旋推理結果",
            "",
            f"📋 **診斷結果**",
            result.get('diagnosis', ''),
            "",
            f"💊 **治療方案**",
            result.get('treatment_plan', ''),
            "",
            f"📊 **評估指標**",
            f"- 安全評分: {result.get('safety_score', 0.0):.2f}/1.0",
            f"- 有效評分: {result.get('efficacy_score', 0.0):.2f}/1.0",
            f"- 信心度: {result.get('confidence', 0.0):.2f}/1.0",
            "",
            f"📝 **建議**",
            result.get('recommendations', ''),
            "",
            f"---",
            f"已使用案例數: {len(session.used_cases)}"
        ]
        
        return "\n".join(dialog_parts)

# 全域函數：執行螺旋推理 v2.0
async def run_spiral_cbr_v2(question: str, 
                           patient_ctx: Optional[Dict[str, Any]] = None,
                           session_id: Optional[str] = None,
                           continue_spiral: bool = False,
                           trace_id: Optional[str] = None,
                           session_manager: Optional[SpiralSessionManager] = None) -> Dict[str, Any]:
    """
    S-CBR 螺旋推理主入口函數 v2.0 - 互動版
    
    Args:
        question: 患者問題或症狀描述
        patient_ctx: 患者上下文資訊
        session_id: 會話ID（可選）
        continue_spiral: 是否繼續螺旋推理
        trace_id: 請求追蹤ID
        session_manager: 會話管理器
        
    Returns:
        Dict[str, Any]: 單輪螺旋推理結果
    """
    logger = SpiralLogger.get_logger("run_spiral_cbr_v2")
    
    try:
        # 生成 trace_id
        if trace_id is None:
            trace_id = f"SCBR-v2-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        
        logger.info(f"🚀 啟動 S-CBR v2.0 螺旋推理 [{trace_id}]")
        logger.info(f"   問題: {question[:100]}{'...' if len(question) > 100 else ''}")
        logger.info(f"   會話ID: {session_id}")
        logger.info(f"   繼續推理: {continue_spiral}")
        
        # 創建或獲取會話管理器
        if session_manager is None:
            session_manager = SpiralSessionManager()
        
        # 獲取或創建會話
        session = session_manager.get_or_create_session(session_id, question)
        
        # 創建 SCBREngine 實例
        engine = SCBREngine()
        
        # 構建查詢參數
        query = {
            "question": question,
            "patient_ctx": patient_ctx or {},
            "trace_id": trace_id,
            "continue_spiral": continue_spiral
        }
        
        # 執行單輪螺旋推理
        round_result = await engine.execute_spiral_round(query, session)
        
        # 格式化返回結果
        formatted_result = {
            "dialog": round_result.get("dialog", "推理完成"),
            "session_id": session.session_id,
            "round": session.round_count,
            "continue_available": round_result.get("continue_available", False),
            "llm_struct": round_result.get("llm_struct", {}),
            "spiral_rounds": session.round_count,
            "used_cases_count": len(session.used_cases),
            "total_steps": 4,
            "converged": not round_result.get("continue_available", False),
            "trace_id": trace_id,
            "processing_timestamp": datetime.datetime.now().isoformat()
        }
        
        logger.info(f"✅ S-CBR v2.0 螺旋推理完成 [{trace_id}]")
        logger.info(f"   會話: {session.session_id}")
        logger.info(f"   輪次: {session.round_count}")
        logger.info(f"   可繼續: {formatted_result['continue_available']}")
        
        return formatted_result
        
    except Exception as e:
        logger.error(f"❌ S-CBR v2.0 螺旋推理失敗 [{trace_id}]: {str(e)}")
        
        # 返回錯誤格式
        return {
            "dialog": f"很抱歉，螺旋推理過程發生錯誤：{str(e)}",
            "session_id": session_id or "error",
            "round": 0,
            "continue_available": False,
            "llm_struct": {
                "error": str(e),
                "confidence": 0.0
            },
            "spiral_rounds": 0,
            "used_cases_count": 0,
            "total_steps": 0,
            "converged": False,
            "trace_id": trace_id,
            "error": True
        }

# 導出所有類和函數
__all__ = ["SCBREngine", "SpiralSession", "SpiralSessionManager", "run_spiral_cbr_v2"]