# regenerate_vectors.py - 修正版
'''
負責刪除Case案例與修正維度
'''
import weaviate
from vector.embedding import generate_embedding
from vector.schema import get_weaviate_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def regenerate_case_vectors():
    """重新生成所有案例的語義向量 - 修正版"""
    client = get_weaviate_client()
    
    try:
        # 獲取所有案例（包含 UUID）
        result = client.query.get("Case", [
            "case_id", "summary_text", "chief_complaint", "present_illness"
        ]).with_additional(["id"]).with_limit(1000).do()
        
        cases = result.get("data", {}).get("Get", {}).get("Case", [])
        logger.info(f"找到 {len(cases)} 個案例需要更新")
        
        if not cases:
            logger.warning("沒有找到任何案例")
            return
        
        updated_count = 0
        error_count = 0
        
        for i, case in enumerate(cases):
            try:
                # 構建文本內容
                text_parts = []
                if case.get("summary_text"):
                    text_parts.append(case["summary_text"])
                if case.get("chief_complaint"):
                    text_parts.append(f"主訴: {case['chief_complaint']}")
                if case.get("present_illness"):
                    text_parts.append(f"現病史: {case['present_illness']}")
                
                text = " ".join(text_parts) if text_parts else "（無內容）"
                
                # 生成新的 1024 維語義向量
                new_vector = generate_embedding(text, input_type="passage")
                
                # 獲取 UUID
                uuid = case["_additional"]["id"]
                
                # 🔧 修正：使用正確的 Weaviate 更新語法
                client.data_object.replace(
                    uuid=uuid,
                    class_name="Case",
                    data_object=case,  # 需要提供完整的數據對象
                    vector=new_vector
                )
                
                updated_count += 1
                logger.info(f"✅ [{i+1}/{len(cases)}] 更新案例 {case.get('case_id', 'unknown')} 的向量 ({len(new_vector)}維)")
                
            except Exception as e:
                error_count += 1
                logger.error(f"❌ [{i+1}/{len(cases)}] 更新案例 {case.get('case_id', 'unknown')} 失敗: {e}")
        
        logger.info(f"🎯 更新完成 - 成功: {updated_count}, 失敗: {error_count}")
        
    except Exception as e:
        logger.error(f"重新生成向量失敗: {e}")

def delete_old_cases_and_restart():
    """刪除舊案例並重新開始（可選）"""
    client = get_weaviate_client()
    
    try:
        # 獲取所有案例
        result = client.query.get("Case", ["case_id"]).with_additional(["id"]).do()
        cases = result.get("data", {}).get("Get", {}).get("Case", [])
        
        logger.info(f"準備刪除 {len(cases)} 個舊案例...")
        
        deleted_count = 0
        for case in cases:
            try:
                uuid = case["_additional"]["id"]
                client.data_object.delete(uuid, class_name="Case")
                deleted_count += 1
                logger.info(f"✅ 刪除案例 {case.get('case_id', 'unknown')}")
            except Exception as e:
                logger.error(f"❌ 刪除案例失敗: {e}")
        
        logger.info(f"🎯 刪除完成 - 成功刪除: {deleted_count} 個案例")
        logger.info("現在可以重新新增病例，所有新案例都會使用 1024 維語義向量")
        
    except Exception as e:
        logger.error(f"刪除舊案例失敗: {e}")

def test_vector_similarity():
    """測試向量相似性"""
    logger.info("測試語義相似性...")
    
    texts = [
        "35歲女性壓力症狀失眠多夢",
        "中年女子工作壓力導致睡眠問題", 
        "年輕女性因為工作忙碌睡不好",
        "老年男性心臟病高血壓糖尿病"
    ]
    
    vectors = []
    for text in texts:
        vector = generate_embedding(text, input_type="query")
        vectors.append(vector)
        logger.info(f"文本: {text} -> 向量維度: {len(vector)}")
    
    import numpy as np
    
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    logger.info("\n📊 相似度矩陣:")
    for i, text_i in enumerate(texts):
        for j, text_j in enumerate(texts):
            if i < j:
                sim = cosine_similarity(vectors[i], vectors[j])
                logger.info(f"  {i+1} vs {j+1}: {sim:.4f}")
                logger.info(f"    '{text_i}' vs '{text_j}'")

if __name__ == "__main__":
    print("選擇操作：")
    print("1. 測試語義相似性")
    print("2. 更新現有案例向量 (修正版)")
    print("3. 刪除所有舊案例，重新開始")
    
    choice = input("請選擇 (1/2/3): ")
    
    if choice == "1":
        test_vector_similarity()
    elif choice == "2":
        regenerate_case_vectors()
    elif choice == "3":
        confirm = input("⚠️  確定要刪除所有現有案例嗎？(yes/N): ")
        if confirm.lower() == "yes":
            delete_old_cases_and_restart()
        else:
            print("取消刪除")
    else:
        print("無效選擇")
