# pulsePJ_simple_query.py
"""
直接查詢 Weaviate PulsePJ 資料（排除 reference_links、支援向量查詢）
- 顯示 name, description, main_disease, symptoms, category, knowledge_chain
- 支援查詢 _additional.vector 以驗證嵌入成功
"""
import weaviate
import json

WEAVIATE_URL = "http://localhost:8080"
WV_API_KEY = "key-admin"

client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=weaviate.AuthApiKey(api_key=WV_API_KEY)
)

# 查詢 name, description, main_disease, symptoms, category, knowledge_chain 及向量
results = client.query.get(
    "PulsePJ",
    [
        "name", "description", "main_disease", "symptoms", "category", "knowledge_chain", "_additional { vector }"
    ]
).with_limit(5).do()

print("=== PulsePJ 前 5 筆資料（含向量） ===")
print(json.dumps(results, ensure_ascii=False, indent=2))
