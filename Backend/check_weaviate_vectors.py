"""
檢查 Weaviate 向量配置
"""

import asyncio
from s_cbr.utils.api_manager import SCBRAPIManager

async def check_vector_config():
    print("🔍 檢查 Weaviate 向量配置...")
    
    api_manager = SCBRAPIManager()
    client = api_manager.weaviate_client
    
    try:
        # 檢查 Case 類的向量配置
        schema = client.schema.get()
        
        for cls in schema['classes']:
            if cls['class'] == 'Case':
                print(f"\n📋 Case 類向量配置:")
                
                vectorizer = cls.get('vectorizer', 'none')
                print(f"向量化器: {vectorizer}")
                
                vector_index_config = cls.get('vectorIndexConfig', {})
                print(f"向量索引配置: {vector_index_config}")
                
                # 檢查向量索引狀態
                try:
                    # 嘗試獲取一個對象的向量
                    result = client.data_object.get(
                        class_name="Case", 
                        limit=1,
                        with_vector=True
                    )
                    
                    if result.get('objects') and result['objects']:
                        obj = result['objects'][0]
                        has_vector = 'vector' in obj
                        vector_dim = len(obj.get('vector', [])) if has_vector else 0
                        
                        print(f"對象是否有向量: {has_vector}")
                        print(f"向量維度: {vector_dim}")
                        
                        if has_vector:
                            print("✅ Case 類有向量索引")
                        else:
                            print("❌ Case 類沒有向量索引")
                    else:
                        print("⚠️ 無法獲取 Case 對象")
                        
                except Exception as e:
                    print(f"檢查向量狀態失敗: {str(e)}")
                    
    except Exception as e:
        print(f"❌ 檢查失敗: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_vector_config())
