"""
測試修復後的搜尋功能
"""

import asyncio
from s_cbr.utils.api_manager import SCBRAPIManager

async def test_fixed_search():
    print("🔍 測試修復後的搜尋功能...")
    
    api_manager = SCBRAPIManager()
    
    # 測試與樣本數據匹配的查詢
    test_queries = [
        "失眠多夢",  # 應該匹配樣本案例
        "入睡困難",  # 樣本中的關鍵詞
        "心肝血虛",  # 樣本中的診斷
        "67歲男性"   # 樣本中的基本信息
    ]
    
    for query in test_queries:
        print(f"\n=== 測試查詢：{query} ===")
        
        # 測試 Case 搜尋（BM25）
        case_results = await api_manager.search_cases(query, limit=3)
        print(f"📋 Cases (BM25): {len(case_results)} 個")
        
        for case in case_results:
            print(f"  - {case['case_id']}: {case['chief_complaint']} (分數: {case['similarity']:.3f})")
        
        # 測試 PulsePJ 搜尋（向量）
        pulse_results = await api_manager.search_pulse_knowledge(query, limit=3)
        print(f"🔮 PulsePJ (向量): {len(pulse_results)} 個")
        
        for pulse in pulse_results:
            print(f"  - {pulse['name']}: {pulse['main_disease']} (相似度: {pulse['similarity']:.3f})")
    
    # 測試綜合搜尋
    print(f"\n=== 綜合搜尋測試 ===")
    comprehensive_results = await api_manager.comprehensive_search("失眠多夢")
    print(f"綜合結果：Cases: {comprehensive_results['total_cases_found']}, Pulse: {comprehensive_results['total_pulse_found']}")
    print(f"搜尋方法：{comprehensive_results.get('search_methods', {})}")
    
    if comprehensive_results['best_case']:
        print(f"最佳案例：{comprehensive_results['best_case']['chief_complaint']}")
    
    if comprehensive_results['best_pulse']:
        print(f"最佳脈診：{comprehensive_results['best_pulse']['name']}")

if __name__ == "__main__":
    asyncio.run(test_fixed_search())
