"""
S-CBR 主引擎入口模組 v1.0

功能：
1. 提供統一的S-CBR引擎接口
2. 管理螺旋推理生命週期
3. 協調各子系統運作
4. 整合現有 Case 和 PulsePJ 知識庫

版本：v1.0
更新：整合現有 Weaviate 知識庫結構
"""

from s_cbr.core.spiral_cbr_engine import SpiralCBREngine
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger
from typing import Dict, Any
import asyncio
import datetime

class SCBREngine:
    """
    S-CBR 螺旋推理引擎主控器 v1.0
    
    v1.0 特色：
    - 整合現有 Case 知識庫（真實案例）
    - 整合現有 PulsePJ 知識庫（脈診知識）
    - 四步驟螺旋推理
    - Agentive AI 協作
    """
    
    def __init__(self):
        """初始化S-CBR引擎 v1.0"""
        self.config = SCBRConfig()
        self.logger = SpiralLogger.get_logger("SCBREngine")
        self.spiral_engine = SpiralCBREngine()
        self.version = "1.0"
        
        self.logger.info(f"S-CBR 引擎 v{self.version} 初始化完成")
    
    async def start_spiral_dialog(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        啟動螺旋對話推理 v1.0
        
        v1.0 流程：
        1. 驗證輸入參數
        2. 啟動螺旋推理引擎
        3. 整合 Case 和 PulsePJ 知識庫
        4. 返回格式化結果
        """
        session_id = f"scbr_v1_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger.info(f"啟動螺旋對話推理 v1.0 - Session: {session_id}")
        
        try:
            # v1.0 輸入驗證
            if not self._validate_query_v1(query):
                return self._create_error_response_v1("輸入參數驗證失敗")
            
            # 執行螺旋推理（整合現有知識庫）
            result = await self.spiral_engine.start_spiral_dialog(query)
            
            # v1.0 結果後處理
            processed_result = self._post_process_result_v1(result, session_id)
            
            self.logger.info(f"螺旋推理 v1.0 完成 - Session: {session_id}")
            
            return processed_result
            
        except Exception as e:
            self.logger.error(f"螺旋推理 v1.0 異常 - Session: {session_id}, 錯誤: {str(e)}")
            return self._create_error_response_v1(f"S-CBR v1.0 引擎錯誤: {str(e)}")
    
    def _validate_query_v1(self, query: Dict[str, Any]) -> bool:
        """v1.0 查詢參數驗證"""
        required_fields = ["question"]
        
        for field in required_fields:
            if not query.get(field):
                self.logger.warning(f"v1.0 驗證失敗 - 缺少必要字段: {field}")
                return False
        
        return True
    
    def _post_process_result_v1(self, result: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """v1.0 結果後處理"""
        result["session_id"] = session_id
        result["engine_version"] = f"S-CBR-v{self.version}"
        result["knowledge_base"] = ["Case", "PulsePJ"]  # v1.0 使用的知識庫
        result["processing_timestamp"] = datetime.datetime.now().isoformat()
        
        return result
    
    def _create_error_response_v1(self, error_message: str) -> Dict[str, Any]:
        """v1.0 錯誤回應"""
        return {
            "success": False,
            "error": error_message,
            "version": f"v{self.version}",
            "spiral_rounds": 0,
            "message": "S-CBR v1.0 系統暫時無法處理您的請求",
            "suggestions": ["檢查輸入格式", "確認網路連接", "聯繫技術支援"]
        }
    
    def get_version_info(self) -> Dict[str, Any]:
        """獲取版本資訊"""
        return {
            "version": self.version,
            "release_date": "2025-09-13", 
            "features": [
                "整合現有 Case 知識庫",
                "整合現有 PulsePJ 知識庫",
                "四步驟螺旋推理",
                "Agentive AI 協作"
            ],
            "knowledge_bases": ["Case", "PulsePJ"]
        }
