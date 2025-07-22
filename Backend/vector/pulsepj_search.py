# pulsepj_search.py
# 用來替代語意比對通道中的 disease_vectors.json 流程

import weaviate
from weaviate.auth import AuthApiKey
from config import WEAVIATE_URL, WV_API_KEY
from vector.embedding import generate_embedding

def search_pulsepj_main_disease(summary: str, top_k: int = 1):
    """
    給定摘要內容，查詢 PulsePJ class，找出最相似的主病
    """
    vec = generate_embedding(summary, input_type="query")
    if vec is None:
        print("[PulsePJ] 向量嵌入失敗")
        return None

    client = weaviate.Client(
        url=WEAVIATE_URL,
        auth_client_secret=AuthApiKey(api_key=WV_API_KEY)
    )

    resp = client.query.get("PulsePJ", ["main_disease", "pulse_name", "symptoms", "knowledge_chain"]).with_near_vector({
        "vector": vec.tolist(),
        "certainty": 0.5
    }).with_limit(top_k).do()

    results = resp.get("data", {}).get("Get", {}).get("PulsePJ", [])
    if results:
        top = results[0]
        print(f"[PulsePJ] 最相似主病：{top.get('main_disease')} (脈: {top.get('pulse_name')})")
        return top.get("main_disease")
    else:
        print("[PulsePJ] 查無結果")
        return None

if __name__ == "__main__":
    test_text = "頭暈、怕冷、手腳冰冷、面色蒼白、舌淡脈細"  # 模擬五段摘要合成
    result = search_pulsepj_main_disease(test_text)
    print("主病推論結果：", result)
