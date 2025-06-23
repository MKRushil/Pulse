# vector/weaviate_schema_create.py (全 string 欄位安全修正版)
"""
自動創建 Weaviate 所需的 Case 與 PCD 向量 class schema。
llm_struct, raw_case 一律設為 string，內容用 json.dumps(...) 存，最彈性、不限巢狀。
"""
import weaviate

# Weaviate API 設定（請自行補上你的實際值）
WEAVIATE_URL = "http://localhost:8080"
WV_API_KEY = "key-admin"

CASE_CLASS_NAME = "Case"
PCD_CLASS_NAME = "PCD"

case_properties = [
    {"name": "case_id", "dataType": ["string"]},
    {"name": "timestamp", "dataType": ["string"]},
    {"name": "summary", "dataType": ["string"]},
    {"name": "llm_struct", "dataType": ["string"]},   # 一律 string
    {"name": "raw_case", "dataType": ["string"]},     # 一律 string
]
pcd_properties = [
    {"name": "case_id", "dataType": ["string"]},
    {"name": "timestamp", "dataType": ["string"]},
    {"name": "summary", "dataType": ["string"]},
    {"name": "llm_struct", "dataType": ["string"]},
    {"name": "raw_case", "dataType": ["string"]},
]

client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=weaviate.AuthApiKey(api_key=WV_API_KEY)
)

def create_class_if_not_exists(class_name, properties, description=""):
    if client.schema.exists(class_name):
        print(f"[Weaviate] Class {class_name} 已存在，略過。")
        return
    class_obj = {
        "class": class_name,
        "description": description or class_name,
        "vectorizer": "none",
        "properties": properties
    }
    client.schema.create_class(class_obj)
    print(f"[Weaviate] 已創建 class: {class_name}")

if __name__ == "__main__":
    create_class_if_not_exists(CASE_CLASS_NAME, case_properties, "通用病例向量")
    create_class_if_not_exists(PCD_CLASS_NAME, pcd_properties, "個案診斷向量")
    print("[Weaviate] 全部 class 建立完畢！")
