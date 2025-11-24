# -*- coding: utf-8 -*-
"""
診斷腳本 - 確認 s_cbr 專案環境配置

這個腳本會檢查：
1. 當前工作目錄
2. Python 路徑設定
3. 必要模組的存在性
4. 模組導入測試
"""

import sys
from pathlib import Path

print("=" * 60)
print("S-CBR 專案環境診斷")
print("=" * 60)

# 1. 檢查當前工作目錄
print("\n[1] 當前工作目錄:")
current_dir = Path.cwd()
print(f"   {current_dir}")

# 2. 檢查腳本所在目錄
print("\n[2] 腳本所在目錄:")
script_dir = Path(__file__).parent
print(f"   {script_dir}")

# 3. 檢查關鍵檔案和目錄
print("\n[3] 關鍵檔案和目錄檢查:")
items_to_check = {
    "config.py": script_dir / "config.py",
    "main.py": script_dir / "main.py",
    "core/": script_dir / "core",
    "core/search_engine.py": script_dir / "core" / "search_engine.py",
    "core/agentic_retrieval.py": script_dir / "core" / "agentic_retrieval.py",
    "core/four_layer_pipeline.py": script_dir / "core" / "four_layer_pipeline.py",
    "llm/": script_dir / "llm",
    "llm/client.py": script_dir / "llm" / "client.py",
    "llm/embedding.py": script_dir / "llm" / "embedding.py",
    "prompts/": script_dir / "prompts",
}

for name, path in items_to_check.items():
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"   {status} {name}: {path}")

# 4. 檢查 Python 路徑
print("\n[4] Python 搜尋路徑 (sys.path 前 5 項):")
for i, path in enumerate(sys.path[:5], 1):
    print(f"   {i}. {path}")

# 5. 測試模組導入（方法一：直接導入）
print("\n[5] 模組導入測試 - 方法一（當前路徑）:")
print(f"   將 {script_dir} 加入 sys.path")
sys.path.insert(0, str(script_dir))

import_results = {}

# 測試 config.py
try:
    from config import SCBRConfig
    import_results['config'] = "✅ 成功"
except Exception as e:
    import_results['config'] = f"❌ 失敗: {e}"

# 測試 llm.client
try:
    from llm.client import LLMClient
    import_results['llm.client'] = "✅ 成功"
except Exception as e:
    import_results['llm.client'] = f"❌ 失敗: {e}"

# 測試 llm.embedding
try:
    from llm.embedding import EmbedClient
    import_results['llm.embedding'] = "✅ 成功"
except Exception as e:
    import_results['llm.embedding'] = f"❌ 失敗: {e}"

# 測試 core.search_engine
try:
    from core.search_engine import SearchEngine
    import_results['core.search_engine'] = "✅ 成功"
except Exception as e:
    import_results['core.search_engine'] = f"❌ 失敗: {e}"

# 測試 core.agentic_retrieval
try:
    from core.agentic_retrieval import AgenticRetrieval
    import_results['core.agentic_retrieval'] = "✅ 成功"
except Exception as e:
    import_results['core.agentic_retrieval'] = f"❌ 失敗: {e}"

# 測試 core.four_layer_pipeline
try:
    from core.four_layer_pipeline import FourLayerSCBR
    import_results['core.four_layer_pipeline'] = "✅ 成功"
except Exception as e:
    import_results['core.four_layer_pipeline'] = f"❌ 失敗: {e}"

for module, result in import_results.items():
    print(f"   {module}: {result}")

# 6. 檢查 AgenticNLUConfig
print("\n[6] AgenticNLUConfig 配置檢查:")
if import_results['config'].startswith("✅"):
    try:
        from config import SCBRConfig
        config = SCBRConfig()
        
        if hasattr(config, 'agentic_nlu'):
            print("   ✅ agentic_nlu 配置存在")
            agentic_cfg = config.agentic_nlu
            print(f"      - enabled: {agentic_cfg.enabled}")
            print(f"      - alpha_min: {agentic_cfg.alpha_min}")
            print(f"      - alpha_max: {agentic_cfg.alpha_max}")
            print(f"      - confidence_mid: {agentic_cfg.confidence_mid}")
            print(f"      - fallback_enabled: {agentic_cfg.fallback_enabled}")
        else:
            print("   ❌ agentic_nlu 配置不存在")
            print("      config.py 中缺少 AgenticNLUConfig 類別")
    except Exception as e:
        print(f"   ❌ 配置檢查失敗: {e}")
else:
    print("   ⏭️  跳過（config 模組無法載入）")

# 7. 診斷結論
print("\n" + "=" * 60)
print("診斷結論:")
print("=" * 60)

# 統計成功和失敗
success_count = sum(1 for r in import_results.values() if r.startswith("✅"))
total_count = len(import_results)

if success_count == total_count:
    print("✅ 所有模組導入成功！")
    print("\n建議：")
    print("   您的環境配置正確，test_agentic_nlu.py 應該可以正常運行。")
    print("   如果測試腳本仍然失敗，可能是腳本本身的路徑設定問題。")
    print("\n解決方案：")
    print("   請確認 test_agentic_nlu.py 第 27 行是：")
    print("   sys.path.insert(0, str(Path(__file__).parent))")
    print("   而不是：")
    print("   sys.path.insert(0, str(Path(__file__).parent.parent))")
    
elif success_count > 0:
    print(f"⚠️  部分模組導入成功 ({success_count}/{total_count})")
    print("\n失敗的模組：")
    for module, result in import_results.items():
        if result.startswith("❌"):
            print(f"   - {module}")
            print(f"     {result}")
    
    print("\n建議：")
    print("   檢查失敗模組的檔案是否存在且沒有語法錯誤。")
    
else:
    print("❌ 所有模組導入失敗")
    print("\n可能的原因：")
    print("   1. 目錄結構不正確")
    print("   2. 缺少必要的檔案")
    print("   3. Python 版本不相容")
    
    print("\n建議：")
    print("   1. 確認當前目錄是 s_cbr/")
    print("   2. 確認 core/ 和 llm/ 目錄存在")
    print("   3. 確認各目錄下有 __init__.py 檔案")

print("\n" + "=" * 60)
print("診斷完成")
print("=" * 60)