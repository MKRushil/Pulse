"""
測試相容向量的 Case 搜尋
"""

import asyncio
import hashlib
from s_cbr.utils.api_manager import SCBRAPIManager

def generate_compatible_embedding(text: str, input_type: str = "passage", dim: int = 384):
    """生成與原始上傳相容的向量"""
    def _deterministic_vector(seed: str, dim: int = 384):
        out = []
        i = 0
        while len(out) < dim:
            h = hashlib.sha256(f"{seed}:{i}".encode("utf-8")).digest()
            for j in range(0, len(h), 4):
                chunk = h[j:j+4]
                if len(chunk) < 4:
                    break
                n = int.from_bytes(chunk, byteorder="big", signed=False)
                out.append((n % 2000000) / 1000000.0 - 1.0)
                if len(out) >= dim:
                    break
            i += 1
        return out
    
    seed = f"{input_type}|{text}"
    return _deterministic_vector(seed, dim)

async def test_compatible_search():
    print("🔍 測試相容向量的 Case 搜尋...")
    
    api_manager = SCBRAPIManager()
    client = api_manager.weaviate_client
    
    # 直接測試相容向量搜尋
    test_queries = [
        "失眠多夢",
        "67歲男性",
        "心肝血虛",
        "入睡困難"
    ]
    
    for query in test_queries:
        print(f"\n=== 測試查詢：{query} ===")
        
        try:
            # 生成相容向量
            query_vector = generate_compatible_embedding(query, "passage")
            print(f"查詢向量維度：{len(query_vector)}")
            
            # 執行向量搜尋
            result = client.query.get(
                "Case",
                ["case_id", "chief_complaint", "age", "gender", "diagnosis_main"]
            ).with_near_vector({
                "vector": query_vector
            }).with_limit(3).with_additional(['certainty']).do()
            
            cases = result.get("data", {}).get("Get", {}).get("Case", [])
            print(f"找到 {len(cases)} 個案例")
            
            for case in cases:
                certainty = case.get('_additional', {}).get('certainty', 0)
                print(f"  - {case.get('case_id', '')}: {case.get('chief_complaint', '')} (相似度: {certainty:.3f})")
            
        except Exception as e:
            print(f"❌ 查詢失敗: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_compatible_search())
