# vector/query_example.py
"""
查詢最相似的病例：根據語意向量在 Weaviate Case class 中找出 top-k 相似案例。
"""
import weaviate
import numpy as np
from weaviate.auth import AuthApiKey
from vector.embedding import generate_embedding
from config import WEAVIATE_URL, WV_API_KEY

client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=AuthApiKey(api_key=WV_API_KEY)
)

CASE_CLASS_NAME = "Case"


def query_similar_cases_by_text(text: str, k: int = 5):
    print("[Query] 正在將輸入文字轉換為嵌入向量...")
    vector = generate_embedding(text, input_type="query")
    if vector is None:
        print("[Query] 嵌入失敗，結束查詢。")
        return []

    print(f"[Query] 開始查詢相似案例 top-{k}...")
    response = client.query.get(CASE_CLASS_NAME, [
        "case_id",
        "main_disease",
        "summary",
        "semantic_scores"
    ]).with_near_vector({
        "vector": vector.tolist(),
        "certainty": 0.5
    }).with_limit(k).do()

    results = response.get("data", {}).get("Get", {}).get(CASE_CLASS_NAME, [])
    print(f"[Query] 查詢完成，共取得 {len(results)} 筆結果。\n")
    for i, item in enumerate(results):
        print(f"#{i+1} 案例編號: {item.get('case_id')}")
        print(f"主病: {item.get('main_disease')}")
        print(f"摘要: {item.get('summary')[:50]}...")
        print(f"語意分數: {item.get('semantic_scores')}")
        print("---")

    return results


if __name__ == "__main__":
    test_text = "膝蓋痠痛數日，夜晚加劇，伴隨有頭重、乏力"
    query_similar_cases_by_text(test_text, k=5)
