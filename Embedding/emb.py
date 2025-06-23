import json
import weaviate
import time
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

# ---- Weaviate連線參數 ----
WV_HTTP_HOST   = "localhost"
WV_HTTP_PORT   = 8080
WV_HTTP_SECURE = False
WV_HEADERS     = {"Authorization": "Bearer key-admin"}

client = weaviate.Client(
    url = f"http{'s' if WV_HTTP_SECURE else ''}://{WV_HTTP_HOST}:{WV_HTTP_PORT}",
    additional_headers=WV_HEADERS
)

# ---- NVIDIA Embedding client ----
emb_client = NVIDIAEmbeddings(
    model="nvidia/llama-3.2-nv-embedqa-1b-v2",
    api_key="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",   # <--- 請改成你自己的金鑰
    truncate="NONE",
)

# ---- 註冊Pulse Schema ----
pulse_schema = {
    "class": "PulsePJ",
    "description": "中醫28脈象，含中英、分類、主病、知識鏈等",
    "vectorizer": "none",
    "properties": [
        {"name": "name", "dataType": ["text"], "description": "中文脈名"},
        {"name": "name_en", "dataType": ["text"], "description": "英文脈名"},
        {"name": "description", "dataType": ["text"], "description": "中文說明"},
        {"name": "description_en", "dataType": ["text"], "description": "英文說明"},
        {"name": "category", "dataType": ["text"], "description": "中文分類"},
        {"name": "category_en", "dataType": ["text"], "description": "英文分類"},
        {"name": "main_disease", "dataType": ["text"], "description": "中文主病"},
        {"name": "main_disease_en", "dataType": ["text"], "description": "英文主病"},
        {"name": "symptoms", "dataType": ["text[]"], "description": "中文症狀"},
        {"name": "symptoms_en", "dataType": ["text[]"], "description": "英文症狀"},
        {"name": "knowledge_chain", "dataType": ["text"], "description": "中文知識鏈"},
        {"name": "knowledge_chain_en", "dataType": ["text"], "description": "英文知識鏈"},
        {"name": "category_id", "dataType": ["text"], "description": "分類ID"},
        {"name": "main_disease_id", "dataType": ["text"], "description": "主病ID"},
        {"name": "symptom_ids", "dataType": ["text[]"], "description": "症狀ID清單"},
        {"name": "neo4j_id", "dataType": ["text"], "description": "Neo4j對應ID"}
    ]
}

existing_classes = [x['class'] for x in client.schema.get()["classes"]]
if "PulsePJ" not in existing_classes:
    print("註冊 Pulse schema...")
    client.schema.create_class(pulse_schema)
else:
    print("PulsePJ schema 已存在，跳過")

# ---- 讀入資料 ----
with open("Pulse-project/Embedding/vector_pulse.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# ---- 批次匯入 ----
for i, entry in enumerate(data):
    emb_text = (entry.get("knowledge_chain") or "") + "\n" + (entry.get("knowledge_chain_en") or "")
    # 產生向量 (用 .embed_documents，回傳list of embedding)
    vector = emb_client.embed_documents([emb_text.strip()])[0]
    # 過濾不能上傳的屬性（如 id, reference_links）
    pulse_obj = {k: v for k, v in entry.items() if k not in ("reference_links", "id")}
    pulse_obj["symptom_ids"] = entry.get("symptom_ids", [])
    print(f"({i+1}/{len(data)}) 上傳: {pulse_obj.get('name', '')} / {pulse_obj.get('name_en', '')}")
    client.data_object.create(
        data_object=pulse_obj,
        class_name="PulsePJ",
        vector=vector
    )
    time.sleep(1.0)

print("全部匯入完成！")

# ---- 查詢並印出前五筆 ----
print("\n--- 匯入完成，PulsePJ前五筆資料如下 ---")
results = client.query.get(
    "PulsePJ",
    [
        "neo4j_id", "name", "name_en",
        "description", "description_en",
        "category", "category_en",
        "main_disease", "main_disease_en",
        "symptoms", "symptoms_en",
        "knowledge_chain", "knowledge_chain_en"
    ]
).with_limit(5).do()

for i, obj in enumerate(results['data']['Get']['PulsePJ']):
    print(f"\n== 第{i+1}筆 ==")
    print(json.dumps(obj, ensure_ascii=False, indent=2))
