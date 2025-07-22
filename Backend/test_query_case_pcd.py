# test_query_case_pcd.py
"""
快速查詢 Case/PCD 向量庫內容，驗證上傳資料是否正確
建議每次資料入庫後直接執行
"""

from vector.schema import get_weaviate_client
import sys, os
client = get_weaviate_client()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_all_properties(class_name):
    schema = client.schema.get()
    classes = schema.get("classes", [])
    for c in classes:
        if c.get("class") == class_name:
            return [prop["name"] for prop in c.get("properties", [])]
    return []

def print_objects(class_name, limit=5):
    props = get_all_properties(class_name)
    if not props:
        print(f"找不到 {class_name} 的 schema 或無 properties")
        return

    results = client.query.get(class_name, props).with_limit(limit).do()
    hits = results.get("data", {}).get("Get", {}).get(class_name, [])
    print(f"\n===== {class_name} (前{limit}筆) =====")
    if not hits:
        print("(查無資料)")
    for idx, obj in enumerate(hits, 1):
        print(f"\n--- 第{idx}筆 ---")
        for k, v in obj.items():
            print(f"{k}: {v}")

if __name__ == "__main__":
    print_objects("Case", limit=5)
    print_objects("PCD", limit=5)
