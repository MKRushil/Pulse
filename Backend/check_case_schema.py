"""
檢查 Case 類的真實字段結構
"""

import asyncio
from s_cbr.utils.api_manager import SCBRAPIManager

async def check_case_schema():
    print("🔍 檢查 Case 類的真實結構...")
    
    api_manager = SCBRAPIManager()
    client = api_manager.weaviate_client
    
    # 檢查 Case 類的 schema
    try:
        schema = client.schema.get()
        
        for cls in schema['classes']:
            if cls['class'] == 'Case':
                print(f"\n📋 Case 類的完整 schema:")
                print(f"類名: {cls['class']}")
                
                properties = cls.get('properties', [])
                print(f"屬性數量: {len(properties)}")
                
                print("\n🔍 所有可用字段:")
                for prop in properties:
                    prop_name = prop['name']
                    prop_type = prop.get('dataType', ['unknown'])[0]
                    print(f"  - {prop_name} ({prop_type})")
                
                # 嘗試獲取一個樣本數據（使用所有字段）
                print(f"\n📄 樣本數據:")
                field_names = [prop['name'] for prop in properties]
                
                try:
                    result = client.query.get("Case", field_names[:10]).with_limit(1).do()  # 只取前10個字段避免太長
                    if result.get('data', {}).get('Get', {}).get('Case'):
                        sample = result['data']['Get']['Case'][0]
                        for key, value in sample.items():
                            if value is not None:
                                value_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                                print(f"  {key}: {value_str}")
                except Exception as e:
                    print(f"  獲取樣本失敗: {str(e)}")
                
                return field_names
                
        # 同時檢查 PatientCase 類
        for cls in schema['classes']:
            if cls['class'] == 'PatientCase':
                print(f"\n📋 PatientCase 類的完整 schema:")
                print(f"類名: {cls['class']}")
                
                properties = cls.get('properties', [])
                print(f"屬性數量: {len(properties)}")
                
                print("\n🔍 所有可用字段:")
                for prop in properties:
                    prop_name = prop['name']
                    prop_type = prop.get('dataType', ['unknown'])[0]
                    print(f"  - {prop_name} ({prop_type})")
                
                return [prop['name'] for prop in properties]
        
    except Exception as e:
        print(f"❌ 檢查失敗: {str(e)}")
        return []

if __name__ == "__main__":
    asyncio.run(check_case_schema())
