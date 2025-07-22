"""
模組說明：
- 提供 Weaviate client 連線工具
- 定義各資料 class 名稱與 schema
"""
import weaviate
from config import WEAVIATE_URL, WV_API_KEY
from weaviate.auth import AuthApiKey

# ⬇️ class 名稱集中管理
CASE_CLASS_NAME = "Case"
PCD_CLASS_NAME = "PCD"
PULSE_CLASS_NAME = "PulsePJ"

def get_weaviate_client():
    """
    初始化 Weaviate client，支援 API key 驗證
    """
    client = weaviate.Client(
        url=WEAVIATE_URL,
        auth_client_secret=AuthApiKey(api_key=WV_API_KEY)
    )
    return client

def get_case_schema():
    """
    回傳各資料類別的 class 名稱定義
    """
    return {
        "case": CASE_CLASS_NAME,
        "PCD": PCD_CLASS_NAME,
        "pulse": PULSE_CLASS_NAME
    }
