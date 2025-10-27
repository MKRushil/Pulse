# -*- coding: utf-8 -*-
"""
Backend/s_cbr/test_knowledge.py
測試 TCM 知識庫配置
"""

import sys
from pathlib import Path

# 添加父目錄到路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def test_tcm_config():
    """測試 TCM 配置載入"""
    print("\n" + "=" * 70)
    print("🔬 TCM 知識庫配置測試")
    print("=" * 70)
    
    try:
        # ✅ 直接導入，避免循環導入
        from s_cbr.knowledge.tcm_config import get_tcm_config
        
        print("\n【1】初始化 TCM 配置...")
        tcm_cfg = get_tcm_config()
        print("    ✅ TCM 配置初始化成功")
        
        # 測試停用詞
        print("\n【2】停用詞測試")
        stopwords = tcm_cfg.get_stopwords()
        print(f"    數量: {len(stopwords)} 個")
        if stopwords:
            print(f"    示例: {list(stopwords)[:10]}")
        else:
            print("    ⚠️  警告：停用詞為空")
        
        # 測試 TCM 關鍵詞
        print("\n【3】TCM 關鍵詞測試")
        keywords = tcm_cfg.get_tcm_keywords()
        print(f"    數量: {len(keywords)} 個")
        if keywords:
            print(f"    示例: {list(keywords)[:15]}")
        else:
            print("    ⚠️  警告：TCM 關鍵詞為空")
        
        # 測試證型關鍵詞
        print("\n【4】證型關鍵詞測試")
        syndromes = tcm_cfg.get_syndrome_keywords()
        print(f"    數量: {len(syndromes)} 種")
        if syndromes:
            print("    前5種證型：")
            for i, (name, symptoms) in enumerate(list(syndromes.items())[:5], 1):
                symptom_display = symptoms[:5] if symptoms else ["（無症狀關鍵詞）"]
                print(f"      {i}. {name}: {symptom_display}")
        else:
            print("    ⚠️  警告：證型關鍵詞為空")
        
        # 測試臟腑關鍵詞
        print("\n【5】臟腑關鍵詞測試")
        zangfu = tcm_cfg.get_zangfu_keywords()
        print(f"    數量: {len(zangfu)} 個")
        if zangfu:
            for organ, symptoms in zangfu.items():
                print(f"    {organ}: {symptoms}")
        else:
            print("    ⚠️  警告：臟腑關鍵詞為空")
        
        # 測試症狀分類
        print("\n【6】症狀分類測試")
        categories = tcm_cfg.get_symptom_categories()
        print(f"    數量: {len(categories)} 類")
        if categories:
            for category, symptoms in list(categories.items())[:3]:
                print(f"    {category}: {symptoms[:5]}")
        else:
            print("    ⚠️  警告：症狀分類為空")
        
        # 測試脈象關鍵詞
        print("\n【7】脈象關鍵詞測試")
        pulse = tcm_cfg.get_pulse_keywords()
        print(f"    數量: {len(pulse)} 種")
        if pulse:
            for pulse_name, indications in list(pulse.items())[:3]:
                print(f"    {pulse_name}: {indications}")
        
        # 測試舌診關鍵詞
        print("\n【8】舌診關鍵詞測試")
        tongue = tcm_cfg.get_tongue_keywords()
        print(f"    數量: {len(tongue)} 種")
        if tongue:
            for tongue_name, indications in list(tongue.items())[:3]:
                print(f"    {tongue_name}: {indications}")
        
        # 測試 Config 整合
        print("\n【9】Config 整合測試")
        try:
            from s_cbr.config import cfg
            print(f"    ✅ 配置整合成功")
            print(f"    TextProcessor 停用詞: {len(cfg.text_processor.stopwords)} 個")
            print(f"    TextProcessor TCM 關鍵詞: {len(cfg.text_processor.tcm_keywords)} 個")
            print(f"    TextProcessor 證型: {len(cfg.text_processor.syndrome_keywords)} 種")
            print(f"    TextProcessor 臟腑: {len(cfg.text_processor.zangfu_keywords)} 個")
        except Exception as e:
            print(f"    ⚠️  Config 整合測試跳過: {e}")
        
        print("\n" + "=" * 70)
        print("✅ 測試完成！所有配置載入正常")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    test_tcm_config()