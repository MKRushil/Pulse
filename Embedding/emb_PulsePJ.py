# embedding_pulse_full_semantic_standalone.py
"""
本檔為「獨立版本」，直接連接 NVIDIA API，不依賴系統 vector/embedding.py
- 使用 NVIDIA 官方 REST API 批次產生嵌入向量
- 全語意嵌入：脈名、說明、分類、主病、現代症狀、知識鏈（中英合併）
- 直接寫入 Weaviate (PulsePJ)
"""
import json
import os
import requests
import weaviate

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME", "nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1"
)
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://integrate.api.nvidia.com/v1")

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WV_API_KEY = os.getenv("WV_API_KEY", "")

client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=weaviate.AuthApiKey(api_key=WV_API_KEY)
)

# ---- PulsePJ schema 註冊（必要時）----
pulse_schema = {
    "class": "PulsePJ",
    "description": "中醫28脈象，含中英、分類、主病、知識鏈等",
    "vectorizer": "none",
    "properties": [
        {"name": "name", "dataType": ["text"]},
        {"name": "name_en", "dataType": ["text"]},
        {"name": "description", "dataType": ["text"]},
        {"name": "description_en", "dataType": ["text"]},
        {"name": "category", "dataType": ["text"]},
        {"name": "category_en", "dataType": ["text"]},
        {"name": "main_disease", "dataType": ["text"]},
        {"name": "main_disease_en", "dataType": ["text"]},
        {"name": "symptoms", "dataType": ["text[]"]},
        {"name": "symptoms_en", "dataType": ["text[]"]},
        {"name": "knowledge_chain", "dataType": ["text"]},
        {"name": "knowledge_chain_en", "dataType": ["text"]},
        {"name": "category_id", "dataType": ["text"]},
        {"name": "main_disease_id", "dataType": ["text"]},
        {"name": "symptom_ids", "dataType": ["text[]"]},
        {"name": "neo4j_id", "dataType": ["text"]}
    ]
}

existing_classes = [x['class'] for x in client.schema.get()["classes"]]
if "PulsePJ" not in existing_classes:
    print("註冊 PulsePJ schema...")
    client.schema.create_class(pulse_schema)
else:
    print("PulsePJ schema 已存在，跳過註冊")

# ---- NVIDIA API 產生向量 ----
def nvidia_embedding(text):
    url = f"{EMBEDDING_BASE_URL}/embeddings"
    headers = {
        "Authorization": f"Bearer {EMBEDDING_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": EMBEDDING_MODEL_NAME,
        "input": [text],
        "truncate": "NONE",
        "input_type": "passage"    # <--- 新增這一行！
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    try:
        resp.raise_for_status()
    except Exception as e:
        print("payload:", json.dumps(payload, ensure_ascii=False))
        print("status_code:", resp.status_code)
        print("response text:", resp.text)
        raise
    data = resp.json()
    return data["data"][0]["embedding"]


# ---- 讀入資料 ----
with open("PulsePJ_vector.json", "r", encoding="utf-8") as f:
    pulses = json.load(f)

print(f"共載入 {len(pulses)} 筆脈象知識...\n開始寫入 Weaviate...")

for i, pulse in enumerate(pulses):
    uuid = pulse.get("neo4j_id", pulse.get("id"))
    if not uuid:
        print(f"第{i+1}筆無 neo4j_id/id，跳過。"); continue
    # 全語意嵌入
    text = (
        f"{pulse.get('name','')} {pulse.get('name_en','')} "
        f"{pulse.get('description','')} {pulse.get('description_en','')} "
        f"{pulse.get('category','')} {pulse.get('category_en','')} "
        f"{pulse.get('main_disease','')} {pulse.get('main_disease_en','')} "
        f"{','.join(pulse.get('symptoms', []))} {','.join(pulse.get('symptoms_en', []))} "
        f"{pulse.get('knowledge_chain','')} {pulse.get('knowledge_chain_en','')}"
    )
    vec = nvidia_embedding(text)
    # schema欄位過濾
    schema_keys = [
        "neo4j_id","name","name_en","description","description_en",
        "category","category_en","main_disease","main_disease_en",
        "symptoms","symptoms_en","knowledge_chain","knowledge_chain_en",
        "category_id","main_disease_id","symptom_ids","reference_links"
    ]
    data = {k: v for k, v in pulse.items() if k in schema_keys}
    client.data_object.create(
        data_object=data,
        class_name="PulsePJ",
        vector=vec
    )
    print(f"第{i+1}筆（{uuid}）已寫入。")

print("全部寫入完成！")
