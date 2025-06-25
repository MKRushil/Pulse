# test_query_case_pcd.py
"""
快速查詢 Case/PCD 向量庫內容，驗證上傳資料是否正確
建議每次資料入庫後直接執行
"""

from vector.schema import get_weaviate_client
import sys, os
client = get_weaviate_client()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))




def print_objects(class_name, props, limit=2):
    client = get_weaviate_client()
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
    # 你可根據 schema 調整要看的欄位
    case_props = ["case_id", "timestamp", "summary", "llm_struct"]
    pcd_props = ["case_id", "timestamp", "summary", "llm_struct",'raw_case','name','phone','address','gender','age','patient_id']

    print_objects("Case", case_props, limit=2)
    print_objects("PCD", pcd_props, limit=2)
