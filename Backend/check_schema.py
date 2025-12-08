import weaviate
from weaviate.auth import AuthApiKey

# 1. 連接到你的 Docker Weaviate
client = weaviate.connect_to_local(
    port=8080,
    grpc_port=50051,
    # 這裡必須填入 docker-compose.yml 裡設定的 key-admin
    auth_credentials=AuthApiKey("key-admin") 
)

try:
    # 2. 獲取所有的 Collections (Classes)
    collections = client.collections.list_all()
    
    print(f"目前資料庫連線狀態: {client.is_connected()}")
    
    if not collections:
        print("目前 Weaviate 中沒有任何 Class (Schema 為空)。")
    else:
        print("已存在的 Classes:")
        for name in collections:
            print(f"- {name}")
            
            # 如果你想看詳細結構，可以取消註解下面這行：
            # print(client.collections.get(name).config.get())

finally:
    client.close()