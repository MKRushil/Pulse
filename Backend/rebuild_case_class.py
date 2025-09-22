# rebuild_case_class.py  
import weaviate
from vector.schema import get_weaviate_client

def rebuild_case_class():
    """完全重建 Case 類別"""
    client = get_weaviate_client()
    
    try:
        # 1. 刪除整個 Case 類別
        try:
            client.schema.delete_class("Case")
            print("✅ 刪除舊的 Case 類別")
        except:
            print("Case 類別不存在或已刪除")
        
        # 2. 重新創建 Case 類別（1024 維）
        case_schema = {
            "class": "Case",
            "description": "中醫病例案例",
            "vectorizer": "none",  # 不使用內建向量化器
            "properties": [
            {"name": "case_id", "dataType": ["text"]},
            {"name": "timestamp", "dataType": ["text"]},
            {"name": "age", "dataType": ["text"]},
            {"name": "gender", "dataType": ["text"]},
            {"name": "chief_complaint", "dataType": ["text"]},
            {"name": "present_illness", "dataType": ["text"]},
            {"name": "provisional_dx", "dataType": ["text"]},
            {"name": "pulse_text", "dataType": ["text"]},
            {"name": "inspection_tags", "dataType": ["text[]"]},
            {"name": "inquiry_tags", "dataType": ["text[]"]},
            {"name": "pulse_tags", "dataType": ["text[]"]},
            {"name": "summary_text", "dataType": ["text"]},
            {"name": "summary", "dataType": ["text"]},
            {"name": "diagnosis_main", "dataType": ["text"]},
            {"name": "diagnosis_sub", "dataType": ["text"]},
            {"name": "llm_struct", "dataType": ["text"]},
            ]
        }
        
        client.schema.create_class(case_schema)
        print("✅ 重新創建 Case 類別（支援 1024 維向量）")
        
    except Exception as e:
        print(f"❌ 重建失敗: {e}")

if __name__ == "__main__":
    print("⚠️  警告：此操作將刪除 Case 類別及所有數據！")
    confirm = input("確定要重建 Case 類別嗎？(yes/N): ")
    
    if confirm.lower() == "yes":
        rebuild_case_class()
        print("✅ 重建完成！現在可以新增病例。")
    else:
        print("取消操作")
