import weaviate
from Backend.anc.config import WEAVIATE_URL, WV_API_KEY

def get_weaviate_client():
    return weaviate.Client(
        url=WEAVIATE_URL,
        auth_client_secret=weaviate.AuthApiKey(api_key=WV_API_KEY)
    )

def delete_class(class_name):
    client = get_weaviate_client()
    try:
        client.schema.delete_class(class_name)
        print(f"[{class_name}] 已刪除整個 class（包含 schema 和所有資料）！")
    except Exception as e:
        print(f"刪除 {class_name} 發生錯誤：{e}")

if __name__ == "__main__":
    for class_name in ["PCD", "Case"]:
        delete_class(class_name)
