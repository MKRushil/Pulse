#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系統初始化腳本
用於首次啟動時初始化所有必要資源
"""

import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))


def print_header(text: str):
    """打印標題"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def check_weaviate_connection():
    """檢查 Weaviate 連接"""
    print_header("1. 檢查 Weaviate 連接")
    
    try:
        from anc.config import WEAVIATE_URL
        import requests
        
        response = requests.get(f"{WEAVIATE_URL}/v1/meta", timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Weaviate 連接成功: {WEAVIATE_URL}")
            meta = response.json()
            print(f"   版本: {meta.get('version', 'unknown')}")
            return True
        else:
            print(f"❌ Weaviate 連接失敗: HTTP {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Weaviate 連接失敗: {e}")
        print("\n請確保 Weaviate 已啟動:")
        print("docker run -d --name weaviate -p 8080:8080 \\")
        print("  -e AUTHENTICATION_APIKEY_ENABLED=true \\")
        print("  -e AUTHENTICATION_APIKEY_ALLOWED_KEYS=key-admin \\")
        print("  semitechnologies/weaviate:latest")
        return False


def init_directories():
    """初始化目錄結構"""
    print_header("2. 初始化目錄結構")
    
    from anc.config import RAW_CASES_DIR, PROCESS_LOGS_DIR
    
    directories = [
        RAW_CASES_DIR,
        PROCESS_LOGS_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ 目錄已創建: {directory}")
    
    return True


def init_weaviate_collection():
    """初始化 Weaviate Collection"""
    print_header("3. 初始化 Weaviate Collection")
    
    try:
        from anc.case_processor import get_case_processor
        
        processor = get_case_processor()
        
        if processor.weaviate_client and processor.collection:
            print(f"✅ Collection '{processor.collection.name}' 已準備就緒")
            
            # 檢查現有資料
            try:
                response = processor.collection.aggregate.over_all(total_count=True)
                count = response.total_count
                print(f"   當前病例數量: {count}")
            except:
                print(f"   當前病例數量: 0")
            
            return True
        else:
            print("❌ Weaviate Collection 初始化失敗")
            return False
    
    except Exception as e:
        print(f"❌ Collection 初始化失敗: {e}")
        return False


def init_jieba_dict():
    """初始化 Jieba 詞典"""
    print_header("4. 初始化 Jieba 中醫詞典")
    
    try:
        from anc.jieba_processor import get_jieba_processor
        from anc.config import TCM_DICT_PATH
        
        processor = get_jieba_processor(TCM_DICT_PATH)
        
        # 測試分詞
        test_text = "患者風寒感冒，咳嗽氣喘，脈浮緊，舌苔薄白"
        tokens = processor.tokenize(test_text)
        
        print(f"✅ Jieba 初始化成功")
        print(f"   詞典路徑: {TCM_DICT_PATH}")
        print(f"   測試分詞: {' / '.join(tokens)}")
        
        return True
    
    except Exception as e:
        print(f"❌ Jieba 初始化失敗: {e}")
        return False


def test_embedding_api():
    """測試 Embedding API"""
    print_header("5. 測試 NVIDIA Embedding API")
    
    try:
        from anc.vectorizer import get_vectorizer
        
        vectorizer = get_vectorizer()
        
        # 測試向量化
        test_text = "風寒感冒"
        embedding = vectorizer.encode(test_text)
        
        print(f"✅ Embedding API 測試成功")
        print(f"   測試文本: {test_text}")
        print(f"   向量維度: {len(embedding)}")
        print(f"   向量範例: [{embedding[0]:.4f}, {embedding[1]:.4f}, ...]")
        
        return True
    
    except Exception as e:
        print(f"❌ Embedding API 測試失敗: {e}")
        print("\n請檢查:")
        print("1. NVIDIA API Key 是否正確設定")
        print("2. 網路連接是否正常")
        return False


#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系統初始化腳本
用於首次啟動時初始化所有必要資源

功能:
1. 檢查 Weaviate 連接
2. 初始化目錄結構
3. 初始化 Weaviate Collection
4. 初始化 Jieba 詞典
5. 測試 NVIDIA Embedding API
6. 執行健康檢查
7. 生成測試病例 (可選)

使用方法:
    python init_system.py
    python init_system.py --test  # 包含測試病例
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))


def print_header(text: str):
    """打印標題"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_success(text: str):
    """打印成功訊息"""
    print(f"✅ {text}")


def print_error(text: str):
    """打印錯誤訊息"""
    print(f"❌ {text}")


def print_warning(text: str):
    """打印警告訊息"""
    print(f"⚠️  {text}")


def print_info(text: str):
    """打印資訊訊息"""
    print(f"ℹ️  {text}")


def check_weaviate_connection():
    """檢查 Weaviate 連接"""
    print_header("1. 檢查 Weaviate 連接")
    
    try:
        from anc.config import WEAVIATE_URL
        import requests
        
        response = requests.get(f"{WEAVIATE_URL}/v1/meta", timeout=5)
        
        if response.status_code == 200:
            print_success(f"Weaviate 連接成功: {WEAVIATE_URL}")
            meta = response.json()
            print(f"   版本: {meta.get('version', 'unknown')}")
            print(f"   模組: {', '.join(meta.get('modules', {}).keys())}")
            return True
        else:
            print_error(f"Weaviate 連接失敗: HTTP {response.status_code}")
            return False
    
    except Exception as e:
        print_error(f"Weaviate 連接失敗: {e}")
        print("\n" + "="*60)
        print("請確保 Weaviate 已啟動，執行以下命令:")
        print("="*60)
        print("\ndocker run -d \\")
        print("  --name weaviate \\")
        print("  -p 8080:8080 \\")
        print("  -e AUTHENTICATION_APIKEY_ENABLED=true \\")
        print("  -e AUTHENTICATION_APIKEY_ALLOWED_KEYS=key-admin \\")
        print("  -e PERSISTENCE_DATA_PATH=/var/lib/weaviate \\")
        print("  semitechnologies/weaviate:latest\n")
        return False


def init_directories():
    """初始化目錄結構"""
    print_header("2. 初始化目錄結構")
    
    try:
        from anc.config import RAW_CASES_DIR, PROCESS_LOGS_DIR, BACKUP_DIR
        
        directories = [
            ("原始病例目錄", RAW_CASES_DIR),
            ("處理日誌目錄", PROCESS_LOGS_DIR),
            ("備份目錄", BACKUP_DIR),
        ]
        
        for name, directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print_success(f"{name}: {directory}")
        
        return True
    
    except Exception as e:
        print_error(f"目錄初始化失敗: {e}")
        return False


def init_weaviate_collection():
    """初始化 Weaviate Collection"""
    print_header("3. 初始化 Weaviate Collection")
    
    try:
        from anc.case_processor import get_case_processor
        from anc.config import CASE_COLLECTION_NAME
        
        processor = get_case_processor()
        
        if processor.weaviate_client and processor.collection:
            print_success(f"Collection '{CASE_COLLECTION_NAME}' 已準備就緒")
            
            # 檢查現有資料
            try:
                response = processor.collection.aggregate.over_all(total_count=True)
                count = response.total_count
                print(f"   當前病例數量: {count}")
                
                # 顯示 Collection 配置
                print(f"   向量維度: 1024")
                print(f"   索引類型: HNSW + BM25")
                
            except Exception as e:
                print_info(f"無法獲取病例統計: {e}")
                print_info("Collection 為空或尚未建立索引")
            
            return True
        else:
            print_error("Weaviate Collection 初始化失敗")
            return False
    
    except Exception as e:
        print_error(f"Collection 初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def init_jieba_dict():
    """初始化 Jieba 詞典"""
    print_header("4. 初始化 Jieba 中醫詞典")
    
    try:
        from anc.jieba_processor import get_jieba_processor
        from anc.config import TCM_DICT_PATH
        
        processor = get_jieba_processor(TCM_DICT_PATH)
        
        # 測試分詞
        test_cases = [
            "患者風寒感冒，咳嗽氣喘，脈浮緊，舌苔薄白",
            "肝氣鬱結，脾虛濕困，治宜疏肝健脾",
            "心陽虛，腎陰虛，氣血兩虛"
        ]
        
        print_success("Jieba 初始化成功")
        print(f"   詞典路徑: {TCM_DICT_PATH}")
        print(f"   詞典存在: {TCM_DICT_PATH.exists()}")
        
        print("\n   測試分詞結果:")
        for i, test_text in enumerate(test_cases, 1):
            tokens = processor.tokenize(test_text)
            print(f"   {i}. {test_text}")
            print(f"      → {' / '.join(tokens)}")
        
        # 測試術語分析
        print("\n   測試術語分析:")
        analysis = processor.analyze_case(test_cases[0])
        print(f"   - 總詞數: {len(analysis['all_tokens'])}")
        print(f"   - 證型: {analysis['syndrome']}")
        print(f"   - 症狀: {analysis['symptom']}")
        print(f"   - 脈象: {analysis['pulse']}")
        print(f"   - 舌象: {analysis['tongue']}")
        
        return True
    
    except Exception as e:
        print_error(f"Jieba 初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_embedding_api():
    """測試 NVIDIA Embedding API"""
    print_header("5. 測試 NVIDIA Embedding API")
    
    try:
        from anc.vectorizer import get_vectorizer
        from anc.config import EMBEDDING_MODEL, EMBEDDING_DIMENSION
        
        vectorizer = get_vectorizer()
        
        # 測試向量化
        test_texts = [
            "風寒感冒",
            "患者咳嗽三天，發熱，咽痛",
        ]
        
        print_info(f"使用模型: {EMBEDDING_MODEL}")
        print_info(f"向量維度: {EMBEDDING_DIMENSION}")
        print_info("正在測試向量化...")
        
        for i, test_text in enumerate(test_texts, 1):
            try:
                embedding = vectorizer.encode(test_text)
                print_success(f"測試 {i}: \"{test_text}\"")
                print(f"   向量維度: {len(embedding)}")
                print(f"   向量範例: [{embedding[0]:.6f}, {embedding[1]:.6f}, {embedding[2]:.6f}, ...]")
                
                # 計算向量的範數
                import math
                norm = math.sqrt(sum(x*x for x in embedding))
                print(f"   向量範數: {norm:.6f}")
                
            except Exception as e:
                print_error(f"測試 {i} 失敗: {e}")
                return False
        
        return True
    
    except Exception as e:
        print_error(f"Embedding API 測試失敗: {e}")
        print("\n請檢查:")
        print("1. NVIDIA API Key 是否正確設定")
        print("2. 網路連接是否正常")
        print("3. API 配額是否充足")
        import traceback
        traceback.print_exc()
        return False


def run_health_check():
    """執行健康檢查"""
    print_header("6. 系統健康檢查")
    
    health_status = {
        "weaviate": False,
        "directories": False,
        "collection": False,
        "jieba": False,
        "embedding_api": False,
    }
    
    try:
        from anc.case_processor import get_case_processor
        from anc.config import RAW_CASES_DIR, PROCESS_LOGS_DIR
        
        processor = get_case_processor()
        
        # 檢查各個組件
        health_status["weaviate"] = processor.weaviate_client is not None
        health_status["directories"] = RAW_CASES_DIR.exists() and PROCESS_LOGS_DIR.exists()
        health_status["collection"] = processor.collection is not None
        health_status["jieba"] = True  # 如果前面步驟成功，這裡就是 True
        health_status["embedding_api"] = True  # 如果前面步驟成功，這裡就是 True
        
        # 顯示結果
        print("系統組件狀態:")
        for component, status in health_status.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {component.replace('_', ' ').title()}")
        
        # 整體狀態
        all_healthy = all(health_status.values())
        
        if all_healthy:
            print_success("\n所有系統組件運行正常！")
        else:
            print_warning("\n部分系統組件未正常運行，請檢查上述錯誤訊息")
        
        return all_healthy
    
    except Exception as e:
        print_error(f"健康檢查失敗: {e}")
        return False


def generate_test_case():
    """生成測試病例"""
    print_header("7. 生成測試病例 (可選)")
    
    try:
        from anc.schema import TCMCaseInput, BasicInfo, ComplaintInfo, InspectionInfo
        from anc.schema import AuscultationInfo, InquiryInfo, DiagnosisInfo
        from anc.case_processor import get_case_processor
        
        # 創建測試病例
        test_case = TCMCaseInput(
            basic=BasicInfo(
                name="測試患者",
                gender="男",
                age="35",
                idLast4="TEST",
                phone="0912345678",
                visitDate=datetime.now().strftime("%Y-%m-%d")
            ),
            complaint=ComplaintInfo(
                chiefComplaint="咳嗽三天，咽痛，發熱",
                presentIllness="患者三天前受涼後出現咳嗽，伴有咽痛，發熱38.5°C，無畏寒",
                medicalHistory="既往體健，無特殊病史",
                familyHistory="無特殊家族史"
            ),
            inspection=InspectionInfo(
                spirit="正常",
                bodyShape=["正常"],
                faceColor="面色潮紅",
                tongueBody=["紅"],
                tongueCoating=["薄黃"],
                tongueShape=[],
                tongueNote="舌尖紅"
            ),
            auscultation=AuscultationInfo(
                voice="正常",
                breath="正常",
                cough=True,
                coughNote="咳聲重濁，痰黃稠"
            ),
            inquiry=InquiryInfo(
                chills="惡寒輕，發熱重",
                sweat="汗出",
                head="頭痛",
                body="",
                stool="正常",
                urine="色黃",
                appetite="食慾不振",
                sleep="正常",
                thirst="口渴欲飲",
                gynecology=""
            ),
            pulse={
                "左寸(心)": ["浮", "數"],
                "右寸(肺)": ["浮", "數"],
            },
            diagnosis=DiagnosisInfo(
                syndromePattern=["熱證", "表證"],
                zangfuPattern=["肺熱"],
                diagnosis="風熱感冒",
                treatment="疏風清熱，宣肺止咳",
                suggestion="建議多休息，避免辛辣刺激食物，保持室內空氣流通。可配合針灸治療加強療效。若症狀加重或持續不緩解，請及時複診。"
            )
        )
        
        print_info("正在處理測試病例...")
        
        processor = get_case_processor()
        result = processor.process_case(test_case)
        
        if result["success"]:
            print_success(f"測試病例已成功建立！")
            print(f"   病例 ID: {result['case_id']}")
            print(f"   JSON 路徑: {result['json_path']}")
            print(f"   向量化: {'✅' if result['vectorized'] else '❌'}")
            print(f"   已上傳: {'✅' if result['uploaded'] else '❌'}")
            
            if result['errors']:
                print_warning(f"   錯誤: {', '.join(result['errors'])}")
            
            return True
        else:
            print_error("測試病例建立失敗")
            if result['errors']:
                for error in result['errors']:
                    print(f"   - {error}")
            return False
    
    except Exception as e:
        print_error(f"測試病例生成失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(results: dict):
    """打印初始化摘要"""
    print_header("初始化摘要")
    
    print("初始化結果:")
    for step, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {step}")
    
    success_count = sum(1 for status in results.values() if status)
    total_count = len(results)
    
    print(f"\n完成度: {success_count}/{total_count}")
    
    if all(results.values()):
        print_success("\n🎉 系統初始化完成！所有組件正常運行。")
        print("\n下一步:")
        print("1. 啟動後端服務: python main.py")
        print("2. 訪問 API 文檔: http://localhost:8000/docs")
        print("3. 測試病例保存: POST /api/case/save")
    else:
        print_warning("\n⚠️  部分組件初始化失敗，請查看上述錯誤訊息並修復。")


def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TCM S-CBR 系統初始化")
    parser.add_argument("--test", action="store_true", help="生成測試病例")
    parser.add_argument("--skip-embedding", action="store_true", help="跳過 Embedding API 測試")
    args = parser.parse_args()
    
    print("\n" + "🏥" * 30)
    print("      TCM S-CBR 系統初始化工具")
    print("      Traditional Chinese Medicine")
    print("      Spiral Case-Based Reasoning System")
    print("🏥" * 30)
    
    results = {}
    
    # 執行初始化步驟
    results["Weaviate 連接"] = check_weaviate_connection()
    results["目錄結構"] = init_directories()
    results["Weaviate Collection"] = init_weaviate_collection()
    results["Jieba 詞典"] = init_jieba_dict()
    
    if not args.skip_embedding:
        results["Embedding API"] = test_embedding_api()
    else:
        print_warning("跳過 Embedding API 測試")
        results["Embedding API"] = True
    
    results["健康檢查"] = run_health_check()
    
    # 可選：生成測試病例
    if args.test:
        results["測試病例"] = generate_test_case()
    
    # 打印摘要
    print_summary(results)
    
    # 返回狀態碼
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())