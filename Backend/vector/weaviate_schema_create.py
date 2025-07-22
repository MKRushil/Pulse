import weaviate
from weaviate.auth import AuthApiKey

# 直接寫入你的 Weaviate 設定（可換成你的實際值）
WEAVIATE_URL = "http://localhost:8080"  # 或遠端網址
WV_API_KEY = "key-admin"  # 如未啟用可設 None

client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=AuthApiKey(api_key=WV_API_KEY)
)

def create_case_schema():
    client.schema.create_class({
        "class": "Case",
        "description": "診斷摘要與向量資料",
        "vectorizer": "none",
        "properties": [
            {"name": "case_id", "dataType": ["string"]},
            {"name": "timestamp", "dataType": ["string"]},
            {"name": "summary", "dataType": ["text"]},
            {"name": "summary_segments", "dataType": ["text"]},
            {"name": "llm_struct", "dataType": ["text"]},
            {"name": "main_disease", "dataType": ["string"]},
            {"name": "sub_diseases", "dataType": ["text"]},
            {"name": "semantic_scores", "dataType": ["text"]},
            {"name": "embedding", "dataType": ["number[]"]},
            {"name": "raw_case", "dataType": ["text"]},
            {"name": "source_model", "dataType": ["string"]},
            {"name": "source_score_method", "dataType": ["string"]},
            {"name": "llm_main_disease", "dataType": ["string"]},
            {"name": "formula_main_disease", "dataType": ["string"]},
            {"name": "score_error_formula", "dataType": ["int"]}
        ]
    })

def create_pcd_schema():
    client.schema.create_class({
        "class": "PCD",
        "description": "病人身分與診斷資訊",
        "vectorizer": "none",
        "properties": [
            {"name": "case_id", "dataType": ["string"]},
            {"name": "timestamp", "dataType": ["string"]},
            {"name": "summary", "dataType": ["text"]},
            {"name": "llm_struct", "dataType": ["text"]},
            {"name": "patient_id", "dataType": ["string"]},
            {"name": "name", "dataType": ["string"]},
            {"name": "age", "dataType": ["string"]},
            {"name": "gender", "dataType": ["string"]},
            {"name": "phone", "dataType": ["string"]},
            {"name": "address", "dataType": ["string"]},
            {"name": "main_disease", "dataType": ["string"]},
            {"name": "sub_diseases", "dataType": ["text"]},
            {"name": "semantic_scores", "dataType": ["text"]},
            {"name": "embedding", "dataType": ["number[]"]},
            {"name": "source_model", "dataType": ["string"]},
            {"name": "source_score_method", "dataType": ["string"]},
            {"name": "llm_main_disease", "dataType": ["string"]},
            {"name": "formula_main_disease", "dataType": ["string"]},
            {"name": "score_error_formula", "dataType": ["int"]}
        ]
    })

if __name__ == "__main__":
    create_case_schema()
    create_pcd_schema()
    print("✅ Weaviate schema 已建立完畢")
