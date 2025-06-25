# test_pulsePJ_debug.py
from vector.schema import get_weaviate_client
from vector.embedding import generate_embedding

client = get_weaviate_client()

schema = client.schema.get("PulsePJ")
print(schema)

results = client.query.get("PulsePJ", ["neo4j_id", "name", "main_disease", "description"]).with_limit(5).do()
print(results)

query = "腹痛、失眠、壓力大"
query_vec = generate_embedding(query)
results = client.query.get(
    "PulsePJ",
    ["name", "description", "main_disease", "neo4j_id"]
).with_near_vector({"vector": query_vec.tolist()}).with_limit(5).do()
print(results)


# # 1. 取全部 PulsePJ 資料
# results = client.query.get("PulsePJ", ["id", "name", "main_disease", "vector"]).with_limit(5).do()
# print("PulsePJ全部結果:", results)

# # 2. 取一筆 vector 長度
# if results['data']['Get']['PulsePJ']:
#     v = results['data']['Get']['PulsePJ'][0]['vector']
#     print('第一筆 vector 長度:', len(v))

# # 3. 產生查詢向量
# query = "腹痛、失眠、壓力大"
# query_vec = generate_embedding(query)
# print("查詢向量長度:", query_vec.shape)

# # 4. 語意查詢 PulsePJ
# results = client.query.get("PulsePJ", ["id", "name", "main_disease"]).with_near_vector({"vector": query_vec.tolist()}).with_limit(5).do()
# print("PulsePJ語意查詢結果:", results)
