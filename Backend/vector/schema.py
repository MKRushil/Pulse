"""
Weaviate 連線與 Case 類別名稱集中管理（僅保留 Case）。
加上 timeout 與環境變數覆寫，避免上傳卡住。
"""
import os
import weaviate
from config import WEAVIATE_URL as CFG_WEAVIATE_URL, WV_API_KEY as CFG_WV_API_KEY
from weaviate.auth import AuthApiKey

CASE_CLASS_NAME = "Case"

def get_weaviate_client():
    # 允許用環境變數覆寫設定，部署更彈性
    url = os.getenv("WEAVIATE_URL", CFG_WEAVIATE_URL)
    api_key = os.getenv("WV_API_KEY", CFG_WV_API_KEY)
    # 設定合理的連線/讀取逾時，避免請求卡住
    timeout = (
        int(os.getenv("WV_CONNECT_TIMEOUT", "5")),
        int(os.getenv("WV_READ_TIMEOUT", "10")),
    )
    client = weaviate.Client(
        url=url,
        auth_client_secret=AuthApiKey(api_key=api_key),
        timeout_config=timeout,
    )
    return client

def get_case_schema():
    return {"case": CASE_CLASS_NAME}
