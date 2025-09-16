"""
診斷 Weaviate 數據庫內容
"""

import asyncio
from s_cbr.utils.api_manager import SCBRAPIManager

async def diagnose_weaviate():
    print("🔍 診斷 Weaviate 數據庫...")
    
    api_manager = SCBRAPIManager()
    
    # 檢查 Weaviate 連接
    try:
        client = api_manager.weaviate_client
        
        # 1. 檢查 Weaviate 狀態
        print(f"Weaviate 連接狀態: {client.is_ready()}")
        
        # 2. 列出所有類
        schema = client.schema.get()
        classes = schema.get('classes', [])
        print(f"\n📋 Weaviate 中的所有類: {len(classes)} 個")
        
        for cls in classes:
            class_name = cls['class']
            print(f"  - {class_name}")
            
            # 檢查每個類的數據量
            try:
                result = client.query.aggregate(class_name).with_meta_count().do()
                count = result['data']['Aggregate'][class_name][0]['meta']['count']
                print(f"    數據量: {count} 條")
                
                # 如果是 Case 或類似的類，顯示一些樣本
                if 'case' in class_name.lower() and count > 0:
                    print(f"    正在檢查 {class_name} 的樣本數據...")
                    sample = client.query.get(class_name).with_limit(1).do()
                    if sample.get('data', {}).get('Get', {}).get(class_name):
                        sample_data = sample['data']['Get'][class_name][0]
                        print(f"    樣本字段: {list(sample_data.keys())}")
                
            except Exception as e:
                print(f"    檢查失敗: {str(e)}")
        
        # 3. 特別檢查是否有包含 "case" 的類
        case_classes = [cls['class'] for cls in classes if 'case' in cls['class'].lower()]
        if case_classes:
            print(f"\n🎯 找到疑似案例類: {case_classes}")
        else:
            print(f"\n⚠️ 沒有找到包含 'case' 的類名")
        
        # 4. 檢查 PulsePJ 類（已知正常的）
        pulsepj_classes = [cls['class'] for cls in classes if 'pulse' in cls['class'].lower()]
        if pulsepj_classes:
            print(f"✅ 找到脈診類: {pulsepj_classes}")
        
    except Exception as e:
        print(f"❌ 診斷失敗: {str(e)}")

if __name__ == "__main__":
    asyncio.run(diagnose_weaviate())
