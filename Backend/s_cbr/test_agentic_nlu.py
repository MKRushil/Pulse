# -*- coding: utf-8 -*-
"""
Agentic NLU 配置驗證測試 - 包模式版本
=====================================

此版本設計為從 Backend 目錄以模組模式執行：
    cd C:\work\系統-中醫\Pulse-project\Backend
    python -m s_cbr.test_agentic_config_pkg

或者直接在 s_cbr 目錄執行（會自動調整路徑）：
    cd C:\work\系統-中醫\Pulse-project\Backend\s_cbr
    python test_agentic_config_pkg.py
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# 智能路徑處理：支持兩種執行方式
current_file = Path(__file__).resolve()
if current_file.parent.name == 's_cbr':
    # 從 s_cbr 目錄直接執行
    sys.path.insert(0, str(current_file.parent.parent))  # Backend 目錄
    print(f"[路徑設定] 從 s_cbr 目錄執行，添加 Backend 到路徑")
else:
    # 從 Backend 目錄執行
    print(f"[路徑設定] 從 Backend 目錄執行")

print("=" * 60)
print("Agentic NLU 配置驗證測試")
print("=" * 60)
print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"執行目錄: {Path.cwd()}")
print(f"腳本位置: {current_file}")
print("=" * 60)

# 測試結果記錄
test_results = []

# ==================== 測試 1: 載入 config 模組 ====================
print("\n[測試 1/5] 載入 config 模組...")
try:
    from s_cbr.config import SCBRConfig
    print("✅ PASS - config 模組載入成功")
    test_results.append({"test": "config_import", "status": "PASS"})
except Exception as e:
    print(f"❌ FAIL - config 模組載入失敗: {e}")
    test_results.append({"test": "config_import", "status": "FAIL", "error": str(e)})
    print("\n測試中止 - 無法載入 config 模組")
    print("\n請確認:")
    print("  1. 當前在 Backend 目錄或 s_cbr 目錄")
    print("  2. s_cbr/config.py 檔案存在")
    print("  3. 使用正確的執行方式")
    sys.exit(1)

# ==================== 測試 2: 建立 SCBRConfig 實例 ====================
print("\n[測試 2/5] 建立 SCBRConfig 實例...")
try:
    config = SCBRConfig()
    print("✅ PASS - SCBRConfig 實例建立成功")
    test_results.append({"test": "config_instance", "status": "PASS"})
except Exception as e:
    print(f"❌ FAIL - SCBRConfig 實例建立失敗: {e}")
    test_results.append({"test": "config_instance", "status": "FAIL", "error": str(e)})
    sys.exit(1)

# ==================== 測試 3: 驗證 AgenticNLUConfig 存在 ====================
print("\n[測試 3/5] 驗證 AgenticNLUConfig 配置存在...")
try:
    assert hasattr(config, 'agentic_nlu'), "config 實例缺少 agentic_nlu 屬性"
    agentic_cfg = config.agentic_nlu
    print("✅ PASS - AgenticNLUConfig 配置存在")
    test_results.append({"test": "agentic_nlu_exists", "status": "PASS"})
except AssertionError as e:
    print(f"❌ FAIL - {e}")
    test_results.append({"test": "agentic_nlu_exists", "status": "FAIL", "error": str(e)})
    sys.exit(1)

# ==================== 測試 4: 驗證所有必要參數 ====================
print("\n[測試 4/5] 驗證 AgenticNLUConfig 參數完整性...")

required_params = {
    'enabled': bool,
    'alpha_min': (int, float),
    'alpha_max': (int, float),
    'alpha_default': (int, float),
    'confidence_high': (int, float),
    'confidence_mid': (int, float),
    'confidence_low': (int, float),
    'fallback_enabled': bool,
    'fallback_threshold': (int, float),
    'max_fallback_attempts': int,
    'llm_temperature': (int, float),
    'llm_timeout': (int, float)
}

missing_params = []
type_errors = []

for param, expected_type in required_params.items():
    if not hasattr(agentic_cfg, param):
        missing_params.append(param)
    else:
        value = getattr(agentic_cfg, param)
        if not isinstance(value, expected_type):
            type_errors.append(f"{param} (期望: {expected_type}, 實際: {type(value)})")

if not missing_params and not type_errors:
    print("✅ PASS - 所有參數完整且類型正確")
    test_results.append({"test": "params_completeness", "status": "PASS"})
else:
    if missing_params:
        print(f"❌ FAIL - 缺少參數: {', '.join(missing_params)}")
    if type_errors:
        print(f"❌ FAIL - 類型錯誤: {', '.join(type_errors)}")
    test_results.append({
        "test": "params_completeness",
        "status": "FAIL",
        "missing": missing_params,
        "type_errors": type_errors
    })

# ==================== 測試 5: 驗證參數值合理性 ====================
print("\n[測試 5/5] 驗證參數值合理性...")

validation_results = []

# Alpha 範圍檢查
if agentic_cfg.alpha_min < 0 or agentic_cfg.alpha_min > 1:
    validation_results.append(f"alpha_min ({agentic_cfg.alpha_min}) 應在 0-1 之間")
if agentic_cfg.alpha_max < 0 or agentic_cfg.alpha_max > 1:
    validation_results.append(f"alpha_max ({agentic_cfg.alpha_max}) 應在 0-1 之間")
if agentic_cfg.alpha_min >= agentic_cfg.alpha_max:
    validation_results.append(f"alpha_min 應小於 alpha_max")

# Confidence 範圍檢查
if not (0 <= agentic_cfg.confidence_low <= 1):
    validation_results.append(f"confidence_low 應在 0-1 之間")
if not (0 <= agentic_cfg.confidence_mid <= 1):
    validation_results.append(f"confidence_mid 應在 0-1 之間")
if not (0 <= agentic_cfg.confidence_high <= 1):
    validation_results.append(f"confidence_high 應在 0-1 之間")
if not (agentic_cfg.confidence_low < agentic_cfg.confidence_mid < agentic_cfg.confidence_high):
    validation_results.append(f"confidence 門檻應遞增")

# Fallback 參數檢查
if not (0 <= agentic_cfg.fallback_threshold <= 1):
    validation_results.append(f"fallback_threshold 應在 0-1 之間")
if agentic_cfg.max_fallback_attempts < 1:
    validation_results.append(f"max_fallback_attempts 應 >= 1")

# LLM 參數檢查
if agentic_cfg.llm_temperature < 0 or agentic_cfg.llm_temperature > 2:
    validation_results.append(f"llm_temperature 通常在 0-2 之間")
if agentic_cfg.llm_timeout <= 0:
    validation_results.append(f"llm_timeout 應 > 0")

if not validation_results:
    print("✅ PASS - 所有參數值合理")
    test_results.append({"test": "params_validation", "status": "PASS"})
else:
    print("❌ FAIL - 參數值驗證失敗:")
    for error in validation_results:
        print(f"   - {error}")
    test_results.append({
        "test": "params_validation",
        "status": "FAIL",
        "errors": validation_results
    })

# ==================== 顯示完整配置 ====================
print("\n" + "=" * 60)
print("AgenticNLUConfig 完整配置:")
print("=" * 60)

config_display = {
    "功能開關": {
        "enabled": agentic_cfg.enabled
    },
    "Alpha 值範圍": {
        "alpha_min": agentic_cfg.alpha_min,
        "alpha_max": agentic_cfg.alpha_max,
        "alpha_default": agentic_cfg.alpha_default
    },
    "置信度門檻": {
        "confidence_low": agentic_cfg.confidence_low,
        "confidence_mid": agentic_cfg.confidence_mid,
        "confidence_high": agentic_cfg.confidence_high
    },
    "Fallback 控制": {
        "fallback_enabled": agentic_cfg.fallback_enabled,
        "fallback_threshold": agentic_cfg.fallback_threshold,
        "max_fallback_attempts": agentic_cfg.max_fallback_attempts
    },
    "LLM 參數": {
        "llm_temperature": agentic_cfg.llm_temperature,
        "llm_timeout": agentic_cfg.llm_timeout
    }
}

for category, params in config_display.items():
    print(f"\n{category}:")
    for key, value in params.items():
        print(f"  {key:25} = {value}")

# ==================== 測試摘要 ====================
print("\n" + "=" * 60)
print("測試摘要:")
print("=" * 60)

passed = sum(1 for r in test_results if r['status'] == 'PASS')
failed = sum(1 for r in test_results if r['status'] == 'FAIL')
total = len(test_results)

print(f"總測試數: {total}")
print(f"✅ 通過: {passed}")
print(f"❌ 失敗: {failed}")
print(f"通過率: {(passed/total)*100:.1f}%")

# 保存結果到當前目錄
result_file = Path.cwd() / "agentic_config_test_result.json"
with open(result_file, 'w', encoding='utf-8') as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "execution_dir": str(Path.cwd()),
        "script_location": str(current_file),
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "test_results": test_results,
        "config": config_display
    }, f, ensure_ascii=False, indent=2)

print(f"\n💾 測試結果已保存至: {result_file}")

# ==================== 最終結論 ====================
print("\n" + "=" * 60)
if passed == total:
    print("🎉 結論: AgenticNLUConfig 配置完全正確!")
    print("=" * 60)
    print("\n✅ Phase 1 核心配置驗證完成")
    print("✅ 所有 Agentic NLU 參數設定正確")
    print("✅ 系統已準備好進行實際功能測試")
    print("\n📋 下一步: 透過 API 進行實際測試")
    print("   您的系統已在運行，現在可以:")
    print("   1. 使用 curl 或 Postman 發送診斷請求")
    print("   2. 觀察 L1 層是否使用 Agentic 模式")
    print("   3. 驗證檢索策略是否動態調整")
    print("   4. 參考 Agentic_NLU測試指南.md 進行完整測試")
else:
    print("⚠️  結論: 配置存在問題,需要修正")
    print("=" * 60)

print("\n" + "=" * 60)
print("測試完成")
print("=" * 60)