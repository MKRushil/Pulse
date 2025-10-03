# -*- coding: utf-8 -*-
"""
NVIDIA Embedding Vectorizer
使用 NVIDIA API 生成 1024 維向量

支援功能:
- 單個文本向量化
- 批次文本向量化
- 自動重試機制
- 速率限制控制
- 錯誤處理與日誌
"""

import requests
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class NVIDIAVectorizer:
    """NVIDIA Embedding API 向量化器"""
    
    def __init__(
        self,
        api_url: str = None,
        api_key: str = None,
        model: str = None
    ):
        """
        初始化向量化器
        
        Args:
            api_url: NVIDIA API URL (None 則使用 config)
            api_key: NVIDIA API Key (None 則使用 config)
            model: Embedding 模型名稱 (None 則使用 config)
        """
        # 延遲導入避免循環依賴
        from .config import (
            EMBEDDING_API_URL,
            EMBEDDING_API_KEY,
            EMBEDDING_MODEL,
            EMBEDDING_REQUEST_CONFIG,
            EMBEDDING_MAX_RETRIES,
            EMBEDDING_RETRY_DELAY,
            EMBEDDING_RATE_LIMIT
        )
        
        self.api_url = (api_url or EMBEDDING_API_URL).rstrip("/")
        self.api_key = api_key or EMBEDDING_API_KEY
        self.model = model or EMBEDDING_MODEL
        
        self.embeddings_endpoint = f"{self.api_url}/embeddings"
        
        # 請求配置
        self.request_config = EMBEDDING_REQUEST_CONFIG
        self.max_retries = EMBEDDING_MAX_RETRIES
        self.retry_delay = EMBEDDING_RETRY_DELAY
        
        # 速率限制
        self.rate_limit = EMBEDDING_RATE_LIMIT
        self.request_times = []  # 記錄請求時間
        
        # 統計資訊
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_time": 0.0,
        }
    
    def _check_rate_limit(self):
        """檢查並控制速率限制"""
        now = datetime.now()
        
        # 清理 1 分鐘前的請求記錄
        self.request_times = [
            t for t in self.request_times
            if now - t < timedelta(minutes=1)
        ]
        
        # 檢查是否超過速率限制
        if len(self.request_times) >= self.rate_limit["requests_per_minute"]:
            # 計算需要等待的時間
            oldest_request = min(self.request_times)
            wait_time = 60 - (now - oldest_request).total_seconds()
            
            if wait_time > 0:
                print(f"⏳ 達到速率限制，等待 {wait_time:.1f} 秒...")
                time.sleep(wait_time)
                self.request_times.clear()
        
        # 請求間延遲
        if self.request_times:
            time.sleep(self.rate_limit["delay_between_requests"])
        
        # 記錄此次請求
        self.request_times.append(now)
    
    def encode(self, text: str, retry: int = None) -> List[float]:
        """
        將文本編碼為 1024 維向量
        
        Args:
            text: 輸入文本
            retry: 重試次數 (None 則使用配置值)
        
        Returns:
            1024 維向量
        
        Raises:
            ValueError: 文本為空
            Exception: 向量化失敗
        """
        if not text or not text.strip():
            raise ValueError("文本不能為空")
        
        max_retries = retry if retry is not None else self.max_retries
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": text,
            **self.request_config
        }
        
        last_error = None
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                # 速率限制檢查
                self._check_rate_limit()
                
                # 發送請求
                self.stats["total_requests"] += 1
                
                response = requests.post(
                    self.embeddings_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                # 處理成功響應
                if response.status_code == 200:
                    data = response.json()
                    embedding = data["data"][0]["embedding"]
                    
                    # 驗證維度
                    if len(embedding) != 1024:
                        raise ValueError(
                            f"向量維度錯誤: {len(embedding)}, 預期 1024"
                        )
                    
                    # 更新統計
                    self.stats["successful_requests"] += 1
                    self.stats["total_tokens"] += len(text.split())
                    self.stats["total_time"] += time.time() - start_time
                    
                    return embedding
                
                # 處理速率限制
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    print(f"⚠️  API 速率限制 (嘗試 {attempt + 1}/{max_retries})，等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                    continue
                
                # 處理其他錯誤
                else:
                    error_msg = f"API 錯誤 {response.status_code}: {response.text}"
                    last_error = Exception(error_msg)
                    
                    if attempt < max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        print(f"⚠️  {error_msg}, 重試中 ({attempt + 1}/{max_retries})...")
                        time.sleep(wait_time)
                    else:
                        raise last_error
            
            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠️  請求超時 (嘗試 {attempt + 1}/{max_retries})，等待 {wait_time} 秒後重試...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"向量化超時: {e}")
            
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠️  網路錯誤 (嘗試 {attempt + 1}/{max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"向量化失敗: {e}")
        
        # 所有重試都失敗
        self.stats["failed_requests"] += 1
        raise Exception(f"向量化失敗 (超過最大重試次數 {max_retries}): {last_error}")
    
    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 1,
        show_progress: bool = True
    ) -> List[List[float]]:
        """
        批次編碼多個文本
        
        Args:
            texts: 文本列表
            batch_size: 批次大小 (建議保持為 1 以避免速率限制)
            show_progress: 是否顯示進度
        
        Returns:
            向量列表
        """
        embeddings = []
        total = len(texts)
        failed_indices = []
        
        if show_progress:
            print(f"\n📊 開始批次向量化 ({total} 個文本)...")
        
        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            batch_start = i
            
            for j, text in enumerate(batch):
                text_index = batch_start + j
                
                try:
                    if show_progress and (text_index + 1) % 10 == 0:
                        print(f"   進度: {text_index + 1}/{total} ({(text_index + 1) / total * 100:.1f}%)")
                    
                    embedding = self.encode(text)
                    embeddings.append(embedding)
                    
                except Exception as e:
                    print(f"❌ 文本 [{text_index}] 向量化失敗: {text[:50]}... - {e}")
                    failed_indices.append(text_index)
                    # 使用零向量作為備用
                    embeddings.append([0.0] * 1024)
            
            # 批次間延遲
            if i + batch_size < total:
                time.sleep(0.5)
        
        if show_progress:
            success_rate = (total - len(failed_indices)) / total * 100
            print(f"✅ 批次向量化完成！")
            print(f"   成功: {total - len(failed_indices)}/{total} ({success_rate:.1f}%)")
            if failed_indices:
                print(f"   失敗索引: {failed_indices}")
        
        return embeddings
    
    def encode_query(self, query: str) -> List[float]:
        """
        將查詢文本編碼為向量 (使用 query 模式)
        
        Args:
            query: 查詢文本
        
        Returns:
            1024 維向量
        """
        # 暫存原配置
        original_input_type = self.request_config.get("input_type")
        
        # 設定為查詢模式
        self.request_config["input_type"] = "query"
        
        try:
            embedding = self.encode(query)
            return embedding
        finally:
            # 恢復原配置
            self.request_config["input_type"] = original_input_type
    
    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計資訊
        
        Returns:
            統計字典
        """
        stats = self.stats.copy()
        
        # 計算額外統計
        if stats["successful_requests"] > 0:
            stats["avg_time_per_request"] = (
                stats["total_time"] / stats["successful_requests"]
            )
            stats["avg_tokens_per_request"] = (
                stats["total_tokens"] / stats["successful_requests"]
            )
        else:
            stats["avg_time_per_request"] = 0.0
            stats["avg_tokens_per_request"] = 0.0
        
        if stats["total_requests"] > 0:
            stats["success_rate"] = (
                stats["successful_requests"] / stats["total_requests"] * 100
            )
        else:
            stats["success_rate"] = 0.0
        
        return stats
    
    def reset_stats(self):
        """重置統計資訊"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_time": 0.0,
        }
    
    def print_stats(self):
        """打印統計資訊"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("📊 向量化統計資訊")
        print("="*60)
        print(f"總請求數: {stats['total_requests']}")
        print(f"成功請求: {stats['successful_requests']}")
        print(f"失敗請求: {stats['failed_requests']}")
        print(f"成功率: {stats['success_rate']:.2f}%")
        print(f"總 Tokens: {stats['total_tokens']}")
        print(f"總時間: {stats['total_time']:.2f} 秒")
        print(f"平均每次請求時間: {stats['avg_time_per_request']:.3f} 秒")
        print(f"平均每次請求 Tokens: {stats['avg_tokens_per_request']:.1f}")
        print("="*60 + "\n")
    
    def test_connection(self) -> bool:
        """
        測試 API 連接
        
        Returns:
            是否連接成功
        """
        try:
            print("🔍 測試 NVIDIA Embedding API 連接...")
            embedding = self.encode("測試連接")
            print(f"✅ 連接成功！向量維度: {len(embedding)}")
            return True
        except Exception as e:
            print(f"❌ 連接失敗: {e}")
            return False


# ==================== 單例模式 ====================
_vectorizer_instance = None

def get_vectorizer(
    api_url: str = None,
    api_key: str = None,
    model: str = None
) -> NVIDIAVectorizer:
    """
    獲取全局向量化器實例 (單例模式)
    
    Args:
        api_url: API URL (None 則使用配置)
        api_key: API Key (None 則使用配置)
        model: 模型名稱 (None 則使用配置)
    
    Returns:
        NVIDIAVectorizer 實例
    """
    global _vectorizer_instance
    
    if _vectorizer_instance is None:
        _vectorizer_instance = NVIDIAVectorizer(api_url, api_key, model)
    
    return _vectorizer_instance


def reset_vectorizer():
    """重置向量化器單例 (用於測試或重新配置)"""
    global _vectorizer_instance
    _vectorizer_instance = None


# ==================== 輔助函數 ====================

def vectorize_text(text: str) -> List[float]:
    """
    快速向量化文本的輔助函數
    
    Args:
        text: 輸入文本
    
    Returns:
        1024 維向量
    """
    vectorizer = get_vectorizer()
    return vectorizer.encode(text)


def vectorize_batch(texts: List[str]) -> List[List[float]]:
    """
    快速批次向量化的輔助函數
    
    Args:
        texts: 文本列表
    
    Returns:
        向量列表
    """
    vectorizer = get_vectorizer()
    return vectorizer.encode_batch(texts)


# ==================== 測試函數 ====================

def test_vectorizer():
    """測試向量化器功能"""
    print("\n" + "🧪" * 30)
    print("      向量化器功能測試")
    print("🧪" * 30 + "\n")
    
    vectorizer = get_vectorizer()
    
    # 測試 1: 單個文本
    print("測試 1: 單個文本向量化")
    try:
        text = "風寒感冒，咳嗽氣喘，脈浮緊"
        embedding = vectorizer.encode(text)
        print(f"✅ 文本: {text}")
        print(f"   向量維度: {len(embedding)}")
        print(f"   向量範例: [{embedding[0]:.6f}, {embedding[1]:.6f}, ...]")
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
    
    # 測試 2: 批次文本
    print("\n測試 2: 批次文本向量化")
    try:
        texts = [
            "風寒感冒",
            "肝氣鬱結",
            "脾虛濕困",
            "腎陽虛",
        ]
        embeddings = vectorizer.encode_batch(texts, show_progress=False)
        print(f"✅ 批次大小: {len(texts)}")
        print(f"   成功數量: {len([e for e in embeddings if e[0] != 0.0])}")
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
    
    # 測試 3: 查詢模式
    print("\n測試 3: 查詢模式向量化")
    try:
        query = "咳嗽發熱"
        embedding = vectorizer.encode_query(query)
        print(f"✅ 查詢: {query}")
        print(f"   向量維度: {len(embedding)}")
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
    
    # 顯示統計
    print("\n測試完成！")
    vectorizer.print_stats()


if __name__ == "__main__":
    # 直接運行此文件時執行測試
    test_vectorizer()