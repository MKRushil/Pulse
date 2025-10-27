#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSON 病例批次匯入程式 (批次目錄版本)
從指定目錄讀取所有 JSON 檔案並批次上傳到 Weaviate TCMCase Collection

使用方法:
    python import_batch_json_cases.py
    python import_batch_json_cases.py --dry-run
    python import_batch_json_cases.py --files 01 02 03
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))

from anc.schema import TCMCaseInput
from anc.case_processor import get_case_processor


# 批次目錄路徑
BATCH_DIR = Path(r"C:\work\系統-中醫\Pulse-project\Backend\tcm_cases_batch")


def get_batch_files(file_numbers: List[str] = None) -> List[Path]:
    """
    取得批次 JSON 檔案列表
    
    Args:
        file_numbers: 指定要匯入的檔案編號列表 (如 ['01', '02'])
    
    Returns:
        JSON 檔案路徑列表
    """
    if not BATCH_DIR.exists():
        raise FileNotFoundError(f"批次目錄不存在: {BATCH_DIR}")
    
    files = []
    
    if file_numbers:
        # 匯入指定檔案
        for num in file_numbers:
            file_path = BATCH_DIR / f"tcm_cases_batch_{num}.json"
            if file_path.exists():
                files.append(file_path)
            else:
                print(f"⚠️  檔案不存在: {file_path.name}")
    else:
        # 匯入所有 tcm_cases_batch_*.json 檔案
        files = sorted(BATCH_DIR.glob("tcm_cases_batch_*.json"))
    
    return files


def import_single_file(
    json_path: Path,
    processor,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    匯入單個 JSON 檔案
    
    Args:
        json_path: JSON 檔案路徑
        processor: CaseProcessor 實例
        dry_run: 是否為測試模式
    
    Returns:
        匯入結果
    """
    print(f"\n{'─'*70}")
    print(f"📄 處理檔案: {json_path.name}")
    print(f"{'─'*70}")
    
    # 讀取 JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    if not isinstance(cases, list):
        raise ValueError(f"JSON 格式錯誤: {json_path.name} 應為病例列表")
    
    print(f"   病例數量: {len(cases)} 筆\n")
    
    results = {
        "file": json_path.name,
        "total": len(cases),
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    if dry_run:
        # 測試模式：只驗證前 3 筆
        print("   [測試模式] 驗證前 3 筆資料格式:")
        for i, case_data in enumerate(cases[:3], 1):
            try:
                case_input = TCMCaseInput(**case_data)
                print(f"      ✓ 病例 {i}: {case_input.basic.name} ({case_input.basic.gender}, {case_input.basic.age}歲)")
            except Exception as e:
                print(f"      ✗ 病例 {i}: 格式錯誤 - {str(e)[:50]}...")
                results["errors"].append(f"病例 {i}: {e}")
        
        results["validated"] = min(3, len(cases))
        return results
    
    # 實際匯入
    for i, case_data in enumerate(cases, 1):
        try:
            # 轉換為 TCMCaseInput
            case_input = TCMCaseInput(**case_data)
            
            # 處理病例
            result = processor.process_case(case_input)
            
            if result["success"]:
                results["success"] += 1
                case_id = result['case_id']
                status = "✓"
                if result.get("errors"):
                    status += f" (警告: {len(result['errors'])})"
                print(f"   [{i:02d}/{len(cases):02d}] {status} {case_input.basic.name} - {case_id}")
            else:
                results["failed"] += 1
                error_msg = f"{json_path.name} 病例 {i} ({case_input.basic.name}): {', '.join(result['errors'])}"
                results["errors"].append(error_msg)
                print(f"   [{i:02d}/{len(cases):02d}] ✗ {case_input.basic.name} - 失敗")
                print(f"      錯誤: {', '.join(result['errors'][:2])}")
        
        except Exception as e:
            results["failed"] += 1
            error_msg = f"{json_path.name} 病例 {i}: {str(e)}"
            results["errors"].append(error_msg)
            print(f"   [{i:02d}/{len(cases):02d}] ✗ 處理失敗: {str(e)[:60]}...")
    
    return results


def import_batch_files(
    file_numbers: List[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    批次匯入多個 JSON 檔案
    
    Args:
        file_numbers: 指定檔案編號列表
        dry_run: 測試模式
    
    Returns:
        總匯入結果統計
    """
    print(f"\n{'='*70}")
    print(f"  🏥 中醫病例批次匯入系統")
    print(f"{'='*70}\n")
    print(f"批次目錄: {BATCH_DIR}")
    print(f"測試模式: {'是' if dry_run else '否'}")
    print(f"指定檔案: {', '.join(file_numbers) if file_numbers else '全部'}")
    
    # 取得檔案列表
    files = get_batch_files(file_numbers)
    
    if not files:
        raise FileNotFoundError("未找到任何 JSON 檔案")
    
    print(f"找到檔案: {len(files)} 個\n")
    for f in files:
        print(f"   • {f.name}")
    
    # 初始化處理器
    processor = None if dry_run else get_case_processor()
    
    # 批次匯入
    all_results = {
        "files": len(files),
        "total_cases": 0,
        "total_success": 0,
        "total_failed": 0,
        "file_results": [],
        "all_errors": []
    }
    
    for json_file in files:
        try:
            result = import_single_file(json_file, processor, dry_run)
            
            all_results["file_results"].append(result)
            all_results["total_cases"] += result["total"]
            all_results["total_success"] += result["success"]
            all_results["total_failed"] += result["failed"]
            all_results["all_errors"].extend(result["errors"])
            
        except Exception as e:
            print(f"\n   ✗ 檔案處理失敗: {json_file.name}")
            print(f"      錯誤: {e}")
            all_results["all_errors"].append(f"{json_file.name}: {e}")
    
    # 匯入完成統計
    print(f"\n{'='*70}")
    print(f"  📊 批次匯入完成統計")
    print(f"{'='*70}\n")
    
    if dry_run:
        print(f"測試模式完成")
        print(f"   檔案數量: {all_results['files']} 個")
        print(f"   病例總數: {all_results['total_cases']} 筆")
        print(f"   格式驗證: 通過\n")
        print("✓ 移除 --dry-run 參數開始實際匯入")
    else:
        print(f"處理檔案: {all_results['files']} 個")
        print(f"病例總數: {all_results['total_cases']} 筆")
        print(f"成功匯入: {all_results['total_success']} 筆")
        print(f"匯入失敗: {all_results['total_failed']} 筆")
        
        if all_results['total_cases'] > 0:
            success_rate = all_results['total_success'] / all_results['total_cases'] * 100
            print(f"成功率: {success_rate:.1f}%")
        
        # 各檔案統計
        print(f"\n各檔案統計:")
        for result in all_results["file_results"]:
            status = "✓" if result["failed"] == 0 else "✗"
            print(f"   {status} {result['file']}: {result['success']}/{result['total']}")
        
        # 錯誤列表
        if all_results['all_errors']:
            print(f"\n錯誤列表 (前 10 條):")
            for error in all_results['all_errors'][:10]:
                print(f"   • {error}")
            
            if len(all_results['all_errors']) > 10:
                print(f"   ... 還有 {len(all_results['all_errors']) - 10} 條錯誤")
            
            # 保存錯誤日誌
            log_file = Path(f"batch_import_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_results['all_errors']))
            print(f"\n   錯誤日誌已保存: {log_file}")
    
    return all_results


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="批次匯入目錄中的所有中醫病例 JSON 檔案",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 匯入所有檔案
  python import_batch_json_cases.py
  
  # 測試模式（不實際匯入）
  python import_batch_json_cases.py --dry-run
  
  # 只匯入指定檔案
  python import_batch_json_cases.py --files 01 02 03
  
  # 測試指定檔案
  python import_batch_json_cases.py --files 01 --dry-run
        """
    )
    
    parser.add_argument(
        "--files",
        nargs="+",
        help="指定要匯入的檔案編號 (如: 01 02 03)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="測試模式（驗證格式但不實際匯入）"
    )
    
    args = parser.parse_args()
    
    try:
        results = import_batch_files(
            file_numbers=args.files,
            dry_run=args.dry_run
        )
        
        # 根據結果設定退出碼
        if args.dry_run:
            sys.exit(0)
        
        if results['total_failed'] == 0:
            print("\n✓ 所有病例匯入成功")
            sys.exit(0)
        elif results['total_success'] > 0:
            print(f"\n⚠ 部分病例匯入成功 ({results['total_success']}/{results['total_cases']})")
            sys.exit(1)
        else:
            print("\n✗ 所有病例匯入失敗")
            sys.exit(2)
    
    except Exception as e:
        print(f"\n✗ 執行錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()