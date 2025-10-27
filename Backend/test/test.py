#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
測試 Weaviate 資料庫中的病例資料
檢查上傳是否成功、資料完整性、向量維度等
"""

import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))


def print_header(text: str):
    """打印標題"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_section(text: str):
    """打印小節標題"""
    print("\n" + "-" * 70)
    print(f"  {text}")
    print("-" * 70)


def test_connection():
    """測試 1: Weaviate 連接"""
    print_header("測試 1: Weaviate 連接狀態")
    
    try:
        from anc.case_processor import get_case_processor
        
        processor = get_case_processor()
        
        if processor.weaviate_client is None:
            print("❌ Weaviate 客戶端未連接")
            return False
        
        if processor.collection is None:
            print("❌ Collection 未初始化")
            return False
        
        print(f"✅ Weaviate 連接成功")
        print(f"   Collection 名稱: {processor.collection.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ 連接測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_total_count():
    """測試 2: 病例總數統計"""
    print_header("測試 2: 病例總數統計")
    
    try:
        from anc.case_processor import get_case_processor
        
        processor = get_case_processor()
        
        # 方法 1: 使用 aggregate
        try:
            response = processor.collection.aggregate.over_all(total_count=True)
            total_count = response.total_count
            print(f"✅ Collection 中的病例總數: {total_count}")
        except Exception as e:
            print(f"⚠️ 無法使用 aggregate 方法: {e}")
            
            # 方法 2: 使用 query 獲取所有對象
            try:
                response = processor.collection.query.fetch_objects(limit=10000)
                total_count = len(response.objects)
                print(f"✅ Collection 中的病例總數 (查詢方式): {total_count}")
            except Exception as e2:
                print(f"❌ 無法統計病例數: {e2}")
                return False
        
        if total_count == 0:
            print("⚠️ 警告: Collection 為空，沒有找到任何病例")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 統計失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_latest_cases(limit: int = 5):
    """測試 3: 查看最新病例"""
    print_header(f"測試 3: 查看最新 {limit} 筆病例")
    
    try:
        from anc.case_processor import get_case_processor
        
        processor = get_case_processor()
        
        # 獲取最新病例
        response = processor.collection.query.fetch_objects(
            limit=limit,
            return_properties=[
                "case_id",
                "patient_id", 
                "visit_date",
                "age",
                "gender",
                "chief_complaint",
                "diagnosis",
                "created_at"
            ]
        )
        
        if not response.objects:
            print("⚠️ 沒有找到任何病例")
            return False
        
        print(f"✅ 找到 {len(response.objects)} 筆病例:\n")
        
        for i, obj in enumerate(response.objects, 1):
            props = obj.properties
            print(f"📋 病例 #{i}")
            print(f"   Case ID: {props.get('case_id', 'N/A')}")
            print(f"   Patient ID: {props.get('patient_id', 'N/A')}")
            print(f"   就診日期: {props.get('visit_date', 'N/A')}")
            print(f"   年齡/性別: {props.get('age', 'N/A')}歲 / {props.get('gender', 'N/A')}")
            print(f"   主訴: {props.get('chief_complaint', 'N/A')[:50]}...")
            print(f"   診斷: {props.get('diagnosis', 'N/A')[:50]}...")
            print(f"   建立時間: {props.get('created_at', 'N/A')}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_data():
    """測試 4: 檢查向量資料"""
    print_header("測試 4: 檢查向量資料完整性")
    
    try:
        from anc.case_processor import get_case_processor
        
        processor = get_case_processor()
        
        # 獲取一筆病例並檢查向量
        response = processor.collection.query.fetch_objects(
            limit=1,
            include_vector=True,
            return_properties=["case_id", "full_text"]
        )
        
        if not response.objects:
            print("⚠️ 沒有找到任何病例")
            return False
        
        obj = response.objects[0]
        
        print(f"✅ 檢查病例: {obj.properties.get('case_id')}")
        
        # 檢查向量
        if hasattr(obj, 'vector') and obj.vector:
            vector = obj.vector['default']
            print(f"   向量維度: {len(vector)}")
            print(f"   向量範例: [{vector[0]:.6f}, {vector[1]:.6f}, {vector[2]:.6f}, ...]")
            
            # 檢查向量是否為零向量
            if all(v == 0.0 for v in vector):
                print("   ⚠️ 警告: 向量全為 0，可能向量化失敗")
            else:
                print("   ✅ 向量資料正常")
        else:
            print("   ❌ 沒有找到向量資料")
            return False
        
        # 檢查文本
        full_text = obj.properties.get('full_text', '')
        if full_text:
            print(f"   完整文本長度: {len(full_text)} 字符")
            print(f"   文本預覽: {full_text[:100]}...")
        else:
            print("   ⚠️ 警告: 完整文本為空")
        
        return True
        
    except Exception as e:
        print(f"❌ 向量檢查失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_jieba_terms():
    """測試 5: 檢查 Jieba 分詞結果"""
    print_header("測試 5: 檢查 Jieba 分詞術語")
    
    try:
        from anc.case_processor import get_case_processor
        
        processor = get_case_processor()
        
        response = processor.collection.query.fetch_objects(
            limit=1,
            return_properties=[
                "case_id",
                "jieba_tokens",
                "syndrome_terms",
                "zangfu_terms", 
                "symptom_terms",
                "pulse_terms",
                "tongue_terms",
                "treatment_terms"
            ]
        )
        
        if not response.objects:
            print("⚠️ 沒有找到任何病例")
            return False
        
        obj = response.objects[0]
        props = obj.properties
        
        print(f"✅ 檢查病例: {props.get('case_id')}\n")
        
        term_types = [
            ("Jieba 分詞", "jieba_tokens"),
            ("證型術語", "syndrome_terms"),
            ("臟腑術語", "zangfu_terms"),
            ("症狀術語", "symptom_terms"),
            ("脈象術語", "pulse_terms"),
            ("舌象術語", "tongue_terms"),
            ("治法術語", "treatment_terms")
        ]
        
        for label, key in term_types:
            terms = props.get(key, [])
            if terms:
                print(f"   {label} ({len(terms)} 個):")
                print(f"      {', '.join(terms[:10])}")
                if len(terms) > 10:
                    print(f"      ... 還有 {len(terms) - 10} 個")
            else:
                print(f"   {label}: (無)")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 術語檢查失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_functionality():
    """測試 6: 測試搜索功能"""
    print_header("測試 6: 測試搜索功能")
    
    try:
        from anc.case_processor import get_case_processor
        
        processor = get_case_processor()
        
        # 測試查詢
        test_queries = [
            "咳嗽發熱",
            "風寒感冒",
            "肝氣鬱結"
        ]
        
        for query in test_queries:
            print_section(f"搜索: {query}")
            
            try:
                results = processor.search_cases(query, limit=3)
                
                if results:
                    print(f"✅ 找到 {len(results)} 筆相關病例:\n")
                    
                    for i, result in enumerate(results, 1):
                        print(f"   {i}. {result['case_id']}")
                        print(f"      主訴: {result['chief_complaint'][:50]}...")
                        print(f"      診斷: {result['diagnosis'][:50]}...")
                        if result.get('score'):
                            print(f"      相似度分數: {result['score']:.4f}")
                        print()
                else:
                    print(f"⚠️ 沒有找到相關病例")
                    
            except Exception as e:
                print(f"❌ 搜索失敗: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 搜索測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_specific_case(case_id: str = None):
    """測試 7: 查詢特定病例"""
    if not case_id:
        # 如果沒有指定，查詢最新的一筆
        print_header("測試 7: 查詢最新病例詳細資料")
        
        try:
            from anc.case_processor import get_case_processor
            
            processor = get_case_processor()
            
            response = processor.collection.query.fetch_objects(
                limit=1,
                return_properties=["case_id"]
            )
            
            if not response.objects:
                print("⚠️ 沒有找到任何病例")
                return False
            
            case_id = response.objects[0].properties.get('case_id')
            
        except Exception as e:
            print(f"❌ 無法獲取病例 ID: {e}")
            return False
    else:
        print_header(f"測試 7: 查詢病例 {case_id}")
    
    try:
        from anc.case_processor import get_case_processor
        
        processor = get_case_processor()
        
        case_data = processor.get_case_by_id(case_id)
        
        if case_data:
            print(f"✅ 成功查詢病例: {case_id}\n")
            
            print(f"📋 基本資訊:")
            print(f"   Patient ID: {case_data.get('patient_id')}")
            print(f"   就診日期: {case_data.get('visit_date')}")
            print(f"   建立時間: {case_data.get('created_at')}")
            
            print(f"\n📋 病例摘要:")
            print(f"   主訴: {case_data.get('chief_complaint')}")
            print(f"   診斷: {case_data.get('diagnosis')}")
            
            if 'data' in case_data:
                data = case_data['data']
                print(f"\n📋 詳細資料:")
                print(f"   姓名: {data.get('basic', {}).get('name', 'N/A')}")
                print(f"   年齡: {data.get('basic', {}).get('age', 'N/A')} 歲")
                print(f"   性別: {data.get('basic', {}).get('gender', 'N/A')}")
            
            return True
        else:
            print(f"❌ 找不到病例: {case_id}")
            return False
        
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_json_files():
    """測試 8: 檢查本地 JSON 檔案"""
    print_header("測試 8: 檢查本地 JSON 檔案")
    
    try:
        from anc.config import RAW_CASES_DIR
        import os
        
        print(f"📁 原始病例目錄: {RAW_CASES_DIR}")
        
        if not RAW_CASES_DIR.exists():
            print("❌ 目錄不存在")
            return False
        
        # 統計 JSON 檔案
        json_files = []
        for root, dirs, files in os.walk(RAW_CASES_DIR):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
        
        print(f"✅ 找到 {len(json_files)} 個 JSON 檔案")
        
        if json_files:
            print(f"\n最新的 5 個檔案:")
            for filepath in sorted(json_files, reverse=True)[:5]:
                filename = os.path.basename(filepath)
                file_size = os.path.getsize(filepath)
                print(f"   - {filename} ({file_size} bytes)")
        
        return True
        
    except Exception as e:
        print(f"❌ 檢查失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """運行所有測試"""
    print("\n" + "🧪" * 35)
    print("      Weaviate 病例資料庫測試套件")
    print("🧪" * 35)
    
    results = {}
    
    # 執行所有測試
    results["連接測試"] = test_connection()
    
    if results["連接測試"]:
        results["病例統計"] = test_total_count()
        results["最新病例"] = test_latest_cases(5)
        results["向量資料"] = test_vector_data()
        results["Jieba 術語"] = test_jieba_terms()
        results["搜索功能"] = test_search_functionality()
        results["特定病例"] = test_specific_case()
        results["JSON 檔案"] = test_json_files()
    else:
        print("\n⚠️ 連接失敗，跳過其他測試")
    
    # 測試總結
    print_header("測試總結")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"測試結果:")
    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"   {status} - {test_name}")
    
    print(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("\n🎉 所有測試通過！資料庫運行正常。")
    else:
        print(f"\n⚠️ {total - passed} 個測試失敗，請檢查錯誤訊息。")
    
    return passed == total


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="測試 Weaviate 資料庫")
    parser.add_argument("--case-id", help="測試特定病例 ID")
    parser.add_argument("--quick", action="store_true", help="快速測試（僅連接和統計）")
    args = parser.parse_args()
    
    if args.quick:
        # 快速測試
        print("\n🚀 快速測試模式\n")
        test_connection()
        test_total_count()
    elif args.case_id:
        # 測試特定病例
        test_specific_case(args.case_id)
    else:
        # 完整測試
        success = run_all_tests()
        sys.exit(0 if success else 1)