import weaviate
import weaviate.classes.config as wvc
from weaviate.classes.query import MetadataQuery
from weaviate.auth import AuthApiKey
import json
import requests
import os
import time

# ==========================================
# 1. 配置區域 (根據您提供的資訊)
# ==========================================
JSON_FILE_PATH = 'scbr_syndromes_cleaned_verified.json'

# NVIDIA Embedding Config
NVIDIA_CONFIG = {
    "api_url": os.getenv("EMBEDDING_API_URL", "https://integrate.api.nvidia.com/v1/embeddings"),
    "api_key": os.getenv("NVIDIA_API_KEY", "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"),
    "model": os.getenv("EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5"),
    "dimension": int(os.getenv("EMBEDDING_DIMENSION", "1024")),
    "timeout": float(os.getenv("EMBEDDING_TIMEOUT", "30"))
}

# Weaviate Config (Docker)
WEAVIATE_CONFIG = {
    "url": "http://localhost:8080",
    "grpc_port": 50051,
    "api_key": "key-admin"
}

# ==========================================
# 2. NVIDIA Embedding 函數
# ==========================================
def get_nvidia_embedding(text):
    """
    呼叫 NVIDIA API 獲取向量
    """
    # 確保 URL 指向 embeddings endpoint
    endpoint = NVIDIA_CONFIG["api_url"]
    if not endpoint.endswith("/embeddings"):
        endpoint = f"{endpoint.rstrip('/')}/embeddings"

    headers = {
        "Authorization": f"Bearer {NVIDIA_CONFIG['api_key']}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "input": [text],
        "model": NVIDIA_CONFIG["model"],
        "encoding_format": "float",
        "input_type": "passage" #或者是 query，存庫通常用 passage
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=NVIDIA_CONFIG["timeout"])
        response.raise_for_status()
        data = response.json()
        # 回傳向量列表中的第一個
        return data['data'][0]['embedding']
    except Exception as e:
        print(f"⚠️ Embedding Error for text: {text[:30]}... | Error: {e}")
        return None

# ==========================================
# 3. 主程序
# ==========================================
def main():
    # 連接 Weaviate
    client = weaviate.connect_to_local(
        port=8080,
        grpc_port=50051,
        auth_credentials=AuthApiKey(WEAVIATE_CONFIG["api_key"])
    )

    try:
        if not client.is_ready():
            print("❌ 無法連接到 Weaviate，請檢查 Docker。")
            return
        
        print("✅ 成功連接到 Weaviate!")

        class_name = "TCM"

        # 重建 Class
        if client.collections.exists(class_name):
            print(f"⚠️ Class '{class_name}' 已存在，正在刪除重來...")
            client.collections.delete(class_name)

        print(f"🔨 正在建立 Class: {class_name} (使用 NVIDIA 外部向量)...")
        
        # 建立 Schema
        # 注意: vectorizer_config 設為 none()，因為我們要自己提供向量
        client.collections.create(
            name=class_name,
            vectorizer_config=wvc.Configure.Vectorizer.none(), 
            properties=[
                wvc.Property(name="tcm_id", data_type=wvc.DataType.TEXT),
                wvc.Property(name="definition", data_type=wvc.DataType.TEXT),
                wvc.Property(name="clinical_manifestations", data_type=wvc.DataType.TEXT_ARRAY),
                wvc.Property(name="name_zh", data_type=wvc.DataType.TEXT),
                wvc.Property(name="name_en", data_type=wvc.DataType.TEXT),
                wvc.Property(name="category", data_type=wvc.DataType.TEXT),
                wvc.Property(name="subcategory", data_type=wvc.DataType.TEXT),
                wvc.Property(name="gbt_code", data_type=wvc.DataType.TEXT),
                wvc.Property(name="associated_western_diseases", data_type=wvc.DataType.TEXT_ARRAY),
                wvc.Property(name="vector_text", data_type=wvc.DataType.TEXT),           
            ]
        )

        # 讀取資料
        print(f"📂 讀取檔案: {JSON_FILE_PATH}...")
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tcm_collection = client.collections.get(class_name)
        
        print(f"🚀 開始處理 {len(data)} 筆資料 (這可能需要一點時間)...")

        # 批次匯入
        with tcm_collection.batch.dynamic() as batch:
            for i, item in enumerate(data):
                # 1. 準備內容
                # 我們將「名稱 + 定義 + 症狀」組合成一個字串來做 Embedding，效果通常比單純 Embedding 定義好
                symptoms = " ".join(item.get('clinical_manifestations', []))
                vector_text = f"{item.get('name_zh')}。定義：{item.get('definition')}。症狀：{symptoms}"
                
                # 2. 呼叫 NVIDIA API 生成向量
                vector = get_nvidia_embedding(vector_text)
                
                if vector:
                    # 3. 資料整理
                    properties = item.copy()
                    if 'id' in properties:
                        properties['tcm_id'] = properties.pop('id') # 改名 id -> TCM_id
                    properties['vector_text'] = vector_text
                    # 移除不需要存入的暫存欄位
                    properties.pop('_validation_note', None)
                    properties.pop('_icd11_ref_removed', None)
                    properties.pop('icd11_code', None) # 若無值可移除，或保留

                    # 4. 匯入 Weaviate (帶入 vector)
                    batch.add_object(
                        properties=properties,
                        vector=vector  # 關鍵：直接傳入計算好的向量
                    )
                    
                    if (i + 1) % 10 == 0:
                        print(f"   已處理: {i + 1}/{len(data)} 筆...")
                else:
                    print(f"❌ 跳過資料 (向量生成失敗): {item.get('name_zh')}")
                
                # 避免 API Rate Limit (視情況調整)
                time.sleep(0.1)

        # 錯誤檢查
        if len(tcm_collection.batch.failed_objects) > 0:
            print(f"❌ 匯入過程中有 {len(tcm_collection.batch.failed_objects)} 筆錯誤。")
            for failed in tcm_collection.batch.failed_objects:
                print(f"  - {failed.message}")
        else:
            print(f"✅ 全數匯入成功！共 {len(data)} 筆。")

        # 簡單測試
        print("\n🔍 測試 NVIDIA 語意檢索 (Query: '眼睛乾澀')...")
        # 測試時也要將 Query 轉為向量
        query_vec = get_nvidia_embedding("眼睛乾澀")
        if query_vec:
            response = tcm_collection.query.near_vector(
                near_vector=query_vec,
                limit=2,
                return_metadata=MetadataQuery(distance=True) # <--- 修改這裡，使用 MetadataQuery
            )
            for obj in response.objects:
                print(f"  - 命中: {obj.properties['name_zh']} (ID: {obj.properties['tcm_id']})")
                # 這裡也要注意，新版 client 的 metadata 存取方式
                print(f"    距離: {obj.metadata.distance:.4f}")

    except Exception as e:
        print(f"❌ 發生嚴重錯誤: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()