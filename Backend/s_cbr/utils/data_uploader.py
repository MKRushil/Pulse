"""
數據上傳與預處理工具 v2.0

提供文件上傳、數據驗證與預處理功能
支援多格式數據導入與自動清洗

版本：v2.0 - 螺旋互動版
更新：增強數據驗證與預處理能力
"""

from typing import Dict, Any, List, Optional, Union, Tuple
import logging
import os
import json
import csv
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import hashlib
import mimetypes

# 動態導入避免循環依賴
try:
    from ..utils.spiral_logger import SpiralLogger
    from ..config.scbr_config import SCBRConfig, get_config
    # 文件處理工具
    import openpyxl
    from PIL import Image
    import fitz  # PyMuPDF for PDF processing
    ADVANCED_PROCESSING = True
except ImportError:
    # 降級處理
    import logging as SpiralLogger
    SCBRConfig = None
    ADVANCED_PROCESSING = False

class DataUploader:
    """
    數據上傳器 v2.0
    
    v2.0 特色：
    - 多格式文件支援
    - 智能數據驗證
    - 自動預處理
    - 安全檢查
    """
    
    def __init__(self, config = None):
        """初始化數據上傳器 v2.0"""
        self.logger = SpiralLogger.get_logger("DataUploader") if hasattr(SpiralLogger, 'get_logger') else logging.getLogger("DataUploader")
        self.version = "2.0"
        
        # 配置管理
        self.config = config or (get_config() if SCBRConfig else self._get_default_config())
        
        # 上傳配置
        self.upload_config = self._get_upload_config()
        
        # 支援的文件類型
        self.supported_formats = {
            'text': ['.txt', '.md', '.json'],
            'data': ['.csv', '.xlsx', '.xls'],
            'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff'],
            'document': ['.pdf', '.doc', '.docx'],
            'archive': ['.zip', '.tar', '.gz']
        }
        
        # 上傳目錄
        self.upload_dir = Path(self.upload_config.get("upload_directory", "./uploads"))
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 處理統計
        self.processing_stats = {
            "files_uploaded": 0,
            "files_processed": 0,
            "files_failed": 0,
            "total_size_bytes": 0,
            "last_upload": None
        }
        
        self.logger.info(f"數據上傳器 v{self.version} 初始化完成")
    
    def _get_upload_config(self) -> Dict[str, Any]:
        """獲取上傳配置"""
        if self.config:
            return self.config.get_config("upload_config") or {}
        
        return {
            "upload_directory": "./uploads",
            "max_file_size_mb": 50,
            "max_files_per_batch": 10,
            "allowed_extensions": [".txt", ".csv", ".json", ".xlsx", ".pdf"],
            "auto_processing": True,
            "virus_scan": False,
            "backup_enabled": True,
            "encryption_enabled": False
        }
    
    async def upload_file(self, 
                         file_path: str, 
                         file_name: str = None,
                         metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        上傳單個文件
        
        Args:
            file_path: 文件路徑
            file_name: 自定義文件名（可選）
            metadata: 文件元數據
            
        Returns:
            Dict[str, Any]: 上傳結果
        """
        try:
            self.logger.info(f"開始上傳文件: {file_path}")
            
            # 文件存在性檢查
            source_path = Path(file_path)
            if not source_path.exists():
                return {
                    "success": False,
                    "error": "文件不存在",
                    "file_path": file_path
                }
            
            # 文件安全檢查
            security_check = await self._security_check(source_path)
            if not security_check["safe"]:
                return {
                    "success": False,
                    "error": f"安全檢查失敗: {security_check['reason']}",
                    "file_path": file_path
                }
            
            # 確定目標文件名
            if not file_name:
                file_name = source_path.name
            
            # 生成唯一文件名（避免衝突）
            target_name = self._generate_unique_filename(file_name)
            target_path = self.upload_dir / target_name
            
            # 複製文件
            import shutil
            shutil.copy2(source_path, target_path)
            
            # 生成文件信息
            file_info = await self._generate_file_info(target_path, metadata)
            
            # 自動處理
            processing_result = None
            if self.upload_config.get("auto_processing", True):
                processing_result = await self._auto_process_file(target_path, file_info)
            
            # 更新統計
            self.processing_stats["files_uploaded"] += 1
            self.processing_stats["total_size_bytes"] += file_info["size"]
            self.processing_stats["last_upload"] = datetime.now().isoformat()
            
            result = {
                "success": True,
                "file_info": file_info,
                "target_path": str(target_path),
                "processing_result": processing_result
            }
            
            self.logger.info(f"文件上傳成功: {target_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"文件上傳失敗 {file_path}: {str(e)}")
            self.processing_stats["files_failed"] += 1
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    async def upload_batch(self, 
                          file_paths: List[str], 
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        批量上傳文件
        
        Args:
            file_paths: 文件路徑列表
            metadata: 批次元數據
            
        Returns:
            Dict[str, Any]: 批量上傳結果
        """
        try:
            self.logger.info(f"開始批量上傳 {len(file_paths)} 個文件")
            
            # 檢查批次限制
            max_files = self.upload_config.get("max_files_per_batch", 10)
            if len(file_paths) > max_files:
                return {
                    "success": False,
                    "error": f"批次文件數超過限制 ({len(file_paths)} > {max_files})"
                }
            
            batch_result = {
                "success": True,
                "total_files": len(file_paths),
                "successful_uploads": [],
                "failed_uploads": [],
                "batch_id": self._generate_batch_id(),
                "batch_metadata": metadata or {},
                "upload_time": datetime.now().isoformat()
            }
            
            # 逐個上傳文件
            for file_path in file_paths:
                upload_result = await self.upload_file(file_path, metadata=metadata)
                
                if upload_result["success"]:
                    batch_result["successful_uploads"].append(upload_result)
                else:
                    batch_result["failed_uploads"].append(upload_result)
            
            # 更新批次成功狀態
            if len(batch_result["failed_uploads"]) == len(file_paths):
                batch_result["success"] = False
            
            self.logger.info(f"批量上傳完成: {len(batch_result['successful_uploads'])}/{len(file_paths)} 成功")
            return batch_result
            
        except Exception as e:
            self.logger.error(f"批量上傳失敗: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_files": len(file_paths)
            }
    
    async def _security_check(self, file_path: Path) -> Dict[str, Any]:
        """文件安全檢查"""
        try:
            # 檔案大小檢查
            file_size = file_path.stat().st_size
            max_size = self.upload_config.get("max_file_size_mb", 50) * 1024 * 1024
            
            if file_size > max_size:
                return {
                    "safe": False,
                    "reason": f"文件大小超過限制 ({file_size / 1024 / 1024:.1f}MB > {max_size / 1024 / 1024}MB)"
                }
            
            # 文件擴展名檢查
            file_extension = file_path.suffix.lower()
            allowed_extensions = self.upload_config.get("allowed_extensions", [])
            
            if allowed_extensions and file_extension not in allowed_extensions:
                return {
                    "safe": False,
                    "reason": f"不支持的文件類型: {file_extension}"
                }
            
            # MIME 類型檢查
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and mime_type.startswith('application/'):
                # 額外檢查可執行文件
                dangerous_types = ['application/x-executable', 'application/x-msdownload']
                if mime_type in dangerous_types:
                    return {
                        "safe": False,
                        "reason": f"危險文件類型: {mime_type}"
                    }
            
            # 文件內容檢查（簡單）
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(512)  # 讀取前512字節
                
                # 檢查可執行文件標誌
                exe_signatures = [b'MZ', b'\x7fELF', b'\xca\xfe\xba\xbe']
                for sig in exe_signatures:
                    if header.startswith(sig):
                        return {
                            "safe": False,
                            "reason": "檢測到可執行文件標誌"
                        }
                        
            except Exception:
                # 無法讀取文件內容，但不阻止上傳
                pass
            
            return {"safe": True, "reason": "安全檢查通過"}
            
        except Exception as e:
            return {
                "safe": False,
                "reason": f"安全檢查失敗: {str(e)}"
            }
    
    def _generate_unique_filename(self, original_name: str) -> str:
        """生成唯一文件名"""
        try:
            name_part = Path(original_name).stem
            extension = Path(original_name).suffix
            
            # 添加時間戳和隨機字符
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            hash_part = hashlib.md5(original_name.encode()).hexdigest()[:8]
            
            unique_name = f"{name_part}_{timestamp}_{hash_part}{extension}"
            
            # 確保文件不存在
            counter = 1
            while (self.upload_dir / unique_name).exists():
                unique_name = f"{name_part}_{timestamp}_{hash_part}_{counter}{extension}"
                counter += 1
            
            return unique_name
            
        except Exception as e:
            self.logger.error(f"生成唯一文件名失敗: {str(e)}")
            return f"file_{int(datetime.now().timestamp())}.dat"
    
    async def _generate_file_info(self, file_path: Path, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成文件信息"""
        try:
            stat_info = file_path.stat()
            
            file_info = {
                "filename": file_path.name,
                "original_name": metadata.get("original_name", file_path.name) if metadata else file_path.name,
                "size": stat_info.st_size,
                "created_time": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "file_type": self._determine_file_type(file_path),
                "mime_type": mimetypes.guess_type(str(file_path))[0],
                "extension": file_path.suffix.lower(),
                "md5_hash": self._calculate_md5(file_path),
                "upload_time": datetime.now().isoformat(),
                "metadata": metadata or {},
                "version": self.version
            }
            
            return file_info
            
        except Exception as e:
            self.logger.error(f"生成文件信息失敗: {str(e)}")
            return {
                "filename": file_path.name,
                "error": str(e),
                "upload_time": datetime.now().isoformat()
            }
    
    def _determine_file_type(self, file_path: Path) -> str:
        """確定文件類型"""
        extension = file_path.suffix.lower()
        
        for category, extensions in self.supported_formats.items():
            if extension in extensions:
                return category
        
        return "unknown"
    
    def _calculate_md5(self, file_path: Path) -> str:
        """計算文件MD5哈希"""
        try:
            md5_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception:
            return ""
    
    async def _auto_process_file(self, file_path: Path, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """自動處理文件"""
        try:
            file_type = file_info.get("file_type", "unknown")
            
            processing_result = {
                "processed": True,
                "file_type": file_type,
                "processing_time": datetime.now().isoformat(),
                "data": None,
                "summary": None,
                "errors": []
            }
            
            # 根據文件類型進行處理
            if file_type == "data":
                processing_result = await self._process_data_file(file_path, processing_result)
            elif file_type == "text":
                processing_result = await self._process_text_file(file_path, processing_result)
            elif file_type == "image":
                processing_result = await self._process_image_file(file_path, processing_result)
            elif file_type == "document":
                processing_result = await self._process_document_file(file_path, processing_result)
            else:
                processing_result["processed"] = False
                processing_result["reason"] = f"不支援自動處理文件類型: {file_type}"
            
            if processing_result.get("processed", False):
                self.processing_stats["files_processed"] += 1
            
            return processing_result
            
        except Exception as e:
            self.logger.error(f"自動處理文件失敗 {file_path}: {str(e)}")
            return {
                "processed": False,
                "error": str(e),
                "file_type": file_info.get("file_type", "unknown")
            }
    
    async def _process_data_file(self, file_path: Path, result: Dict[str, Any]) -> Dict[str, Any]:
        """處理數據文件（CSV, Excel等）"""
        try:
            if file_path.suffix.lower() == '.csv':
                # 處理CSV文件
                df = pd.read_csv(file_path, encoding='utf-8')
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                # 處理Excel文件
                if ADVANCED_PROCESSING:
                    df = pd.read_excel(file_path)
                else:
                    result["errors"].append("缺少Excel處理庫")
                    return result
            else:
                result["errors"].append("不支援的數據文件格式")
                return result
            
            # 數據摘要
            summary = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "data_types": df.dtypes.astype(str).to_dict(),
                "missing_values": df.isnull().sum().to_dict(),
                "sample_data": df.head(3).to_dict('records')
            }
            
            # 數據質量檢查
            quality_issues = self._check_data_quality(df)
            
            result["summary"] = summary
            result["quality_issues"] = quality_issues
            result["data_preview"] = df.head(10).to_dict('records')
            
            return result
            
        except Exception as e:
            result["errors"].append(f"處理數據文件失敗: {str(e)}")
            result["processed"] = False
            return result
    
    async def _process_text_file(self, file_path: Path, result: Dict[str, Any]) -> Dict[str, Any]:
        """處理文本文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 文本統計
            lines = content.split('\n')
            words = content.split()
            
            summary = {
                "character_count": len(content),
                "word_count": len(words),
                "line_count": len(lines),
                "encoding": "utf-8",
                "preview": content[:500] + "..." if len(content) > 500 else content
            }
            
            # JSON文件特殊處理
            if file_path.suffix.lower() == '.json':
                try:
                    json_data = json.loads(content)
                    summary["json_structure"] = self._analyze_json_structure(json_data)
                    result["data"] = json_data
                except json.JSONDecodeError as e:
                    result["errors"].append(f"JSON解析失敗: {str(e)}")
            
            result["summary"] = summary
            return result
            
        except Exception as e:
            result["errors"].append(f"處理文本文件失敗: {str(e)}")
            result["processed"] = False
            return result
    
    async def _process_image_file(self, file_path: Path, result: Dict[str, Any]) -> Dict[str, Any]:
        """處理圖像文件"""
        try:
            if not ADVANCED_PROCESSING:
                result["errors"].append("缺少圖像處理庫")
                result["processed"] = False
                return result
            
            with Image.open(file_path) as img:
                summary = {
                    "width": img.width,
                    "height": img.height,
                    "mode": img.mode,
                    "format": img.format,
                    "size": img.width * img.height,
                    "aspect_ratio": round(img.width / img.height, 2)
                }
            
            result["summary"] = summary
            return result
            
        except Exception as e:
            result["errors"].append(f"處理圖像文件失敗: {str(e)}")
            result["processed"] = False
            return result
    
    async def _process_document_file(self, file_path: Path, result: Dict[str, Any]) -> Dict[str, Any]:
        """處理文檔文件"""
        try:
            if file_path.suffix.lower() == '.pdf':
                if not ADVANCED_PROCESSING:
                    result["errors"].append("缺少PDF處理庫")
                    result["processed"] = False
                    return result
                
                # 處理PDF文件
                doc = fitz.open(file_path)
                
                summary = {
                    "page_count": doc.page_count,
                    "metadata": doc.metadata,
                    "text_preview": ""
                }
                
                # 提取前幾頁文本預覽
                preview_text = ""
                for page_num in range(min(3, doc.page_count)):
                    page = doc.load_page(page_num)
                    preview_text += page.get_text()
                
                summary["text_preview"] = preview_text[:1000] + "..." if len(preview_text) > 1000 else preview_text
                doc.close()
                
                result["summary"] = summary
            else:
                result["errors"].append("不支援的文檔格式")
                result["processed"] = False
            
            return result
            
        except Exception as e:
            result["errors"].append(f"處理文檔文件失敗: {str(e)}")
            result["processed"] = False
            return result
    
    def _check_data_quality(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """檢查數據質量"""
        issues = []
        
        try:
            # 檢查缺失值
            missing_ratio = df.isnull().sum() / len(df)
            high_missing_cols = missing_ratio[missing_ratio > 0.5].index.tolist()
            
            if high_missing_cols:
                issues.append({
                    "type": "high_missing_values",
                    "severity": "warning",
                    "message": f"以下列缺失值超過50%: {high_missing_cols}"
                })
            
            # 檢查重複行
            duplicate_count = df.duplicated().sum()
            if duplicate_count > 0:
                issues.append({
                    "type": "duplicate_rows",
                    "severity": "info",
                    "message": f"發現 {duplicate_count} 個重複行"
                })
            
            # 檢查空列
            empty_cols = df.columns[df.isnull().all()].tolist()
            if empty_cols:
                issues.append({
                    "type": "empty_columns",
                    "severity": "warning",
                    "message": f"以下列完全為空: {empty_cols}"
                })
            
            return issues
            
        except Exception as e:
            return [{
                "type": "quality_check_error",
                "severity": "error",
                "message": f"數據質量檢查失敗: {str(e)}"
            }]
    
    def _analyze_json_structure(self, json_data: Any, max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
        """分析JSON結構"""
        if current_depth >= max_depth:
            return {"type": "truncated", "reason": "max_depth_reached"}
        
        if isinstance(json_data, dict):
            return {
                "type": "object",
                "keys": list(json_data.keys()),
                "key_count": len(json_data),
                "structure": {
                    k: self._analyze_json_structure(v, max_depth, current_depth + 1)
                    for k, v in list(json_data.items())[:5]  # 限制顯示前5個鍵
                }
            }
        elif isinstance(json_data, list):
            return {
                "type": "array",
                "length": len(json_data),
                "sample_structure": self._analyze_json_structure(json_data[0], max_depth, current_depth + 1) if json_data else None
            }
        else:
            return {
                "type": type(json_data).__name__,
                "sample_value": str(json_data)[:100]
            }
    
    def _generate_batch_id(self) -> str:
        """生成批次ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"batch_{timestamp}_{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]}"
    
    def get_upload_statistics(self) -> Dict[str, Any]:
        """獲取上傳統計"""
        return self.processing_stats.copy()
    
    def list_uploaded_files(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出已上傳的文件"""
        try:
            files = []
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    stat_info = file_path.stat()
                    files.append({
                        "filename": file_path.name,
                        "size": stat_info.st_size,
                        "modified_time": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        "file_type": self._determine_file_type(file_path)
                    })
            
            # 按修改時間排序
            files.sort(key=lambda x: x["modified_time"], reverse=True)
            
            return files[:limit]
            
        except Exception as e:
            self.logger.error(f"列出文件失敗: {str(e)}")
            return []
    
    def _get_default_config(self) -> Dict[str, Any]:
        """獲取默認配置"""
        return {
            "upload_config": {
                "max_file_size_mb": 50,
                "allowed_extensions": [".txt", ".csv", ".json", ".xlsx"],
                "auto_processing": True
            }
        }

# 便捷函數
def create_data_uploader(config: Optional[SCBRConfig] = None) -> DataUploader:
    """創建數據上傳器實例"""
    return DataUploader(config)

async def upload_single_file(file_path: str, **kwargs) -> Dict[str, Any]:
    """便捷函數：上傳單個文件"""
    uploader = create_data_uploader()
    return await uploader.upload_file(file_path, **kwargs)

# 向後兼容的類別名稱
DataUploaderV2 = DataUploader

__all__ = [
    "DataUploader", "DataUploaderV2",
    "create_data_uploader", "upload_single_file"
]