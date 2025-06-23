"""
模組說明：
- 提供 Weaviate client 連線工具
- 定義各資料 class 名稱與 schema
"""
import weaviate
from config import WEAVIATE_URL, WV_API_KEY
from weaviate.auth import AuthApiKey


def get_weaviate_client():
    """
    初始化 Weaviate client，支援 API key 驗證
    """
    client = weaviate.Client(
        url=WEAVIATE_URL,
        auth_client_secret=weaviate.AuthApiKey(api_key=WV_API_KEY)
    )
    return client

def get_case_schema():
    """
    回傳所有使用中的 class 名稱（統一管理，方便維護）
    """
    return {
        "case": "Case",   # 通用病例向量
        "PCD": "PCD"      # 個人診斷向量
    }
