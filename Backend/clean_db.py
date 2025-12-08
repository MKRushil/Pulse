import json
import re
import os

# ==========================================
# 配置區域：GB/T 16751.2-2021 編碼邏輯表
# ==========================================
# 這是驗證的核心依據，定義了每個代碼前綴應該對應的關鍵字
GBT_SEMANTIC_RULES = {
    "A01": ["氣虛", "氣陷", "氣不固", "血虛", "營衛", "陽氣"],
    "A02": ["風", "寒", "暑", "濕", "燥", "火", "熱", "陰虛", "陽虛", "亡"],
    "A03": ["氣滯", "氣逆", "氣閉", "鬱"],
    "A04": ["血瘀", "瘀", "血熱", "血寒", "出血"],
    "A05": ["痰", "飲", "水", "濕"],
    "A06": ["津", "液", "精", "髓"],
    
    "B01": ["心", "神", "小腸"],  # 心系
    "B02": ["肺", "大腸", "咳", "喘", "氣"], # 肺系
    "B03": ["肝", "膽", "脅", "怒", "鬱"],   # 肝系
    "B04": ["脾", "胃", "食", "納", "中焦"], # 脾系
    "B05": ["腎", "膀胱", "腰", "尿", "水", "遺", "陽痿"], # 腎系
    "B06": ["胃", "膽", "腸", "腑"], # 六腑病
    
    "C01": ["衝", "任", "督", "帶", "氣", "血"], # 奇經/氣血
    "C03": ["經", "帶", "胎", "產", "胞宮", "孕"], # 婦科
    
    "D01": ["經", "脈", "痺", "痛", "痿"], # 經絡/肢體
    "D02": ["腰", "背", "痛"],
    "D03": ["頸", "項", "痛"],
    "D04": ["兒", "驚", "風", "疳"], # 兒科
    
    "F00": ["太陽", "陽明", "少陽", "太陰", "少陰", "厥陰", "合病"], # 六經
}

# 需要移除 ICD 代碼的風險類別 (因為 ICD-11 傳統醫學章節未收錄或定義不同)
RISKY_ICD_CATEGORIES = ["現代文明病", "腫瘤病證", "飲食病證", "傷科證候", "複雜病理", "多臟腑虛損", "兒科證候"]
RISKY_ID_TAGS = ["_MOD_", "_ONCO_", "_TRAUMA_", "_DIET_", "_MULTI_", "_PED_", "_GER_", "_RARE_"]

# 絕對禁止的錯誤 ICD 代碼
BANNED_ICD_CODES = ["SD83"] # SD83 是焦慮症，不能用於血瘀

# ==========================================
# 核心功能函數
# ==========================================

def validate_gbt(entry):
    """
    驗證單筆資料的 GB/T 代碼格式與語意邏輯
    回傳: (is_valid, warning_message)
    """
    code = entry.get('gbt_code', '')
    name = entry.get('name_zh', '')
    entry_id = entry.get('id', '')
    
    # 1. 格式檢查 (Format Check)
    # 標準格式: A01.01.01 或 Z00.01 (體質)
    gbt_pattern = re.compile(r'^([A-Z][0-9]{2}\.[0-9]{2}(\.[0-9]{2})?)|(Z\d{2}\.\d{2})$')
    
    if not code:
        return False, "GB/T 代碼缺失"
    
    if not gbt_pattern.match(code):
        return False, f"GB/T 格式錯誤: {code}"

    # 2. 語意檢查 (Semantic Check)
    #如果是現代病或特殊借用代碼，跳過嚴格語意檢查，避免誤報
    if any(tag in entry_id for tag in RISKY_ID_TAGS):
        return True, None 

    prefix = code[:3] # 取前三碼 (如 B01)
    
    if prefix in GBT_SEMANTIC_RULES:
        keywords = GBT_SEMANTIC_RULES[prefix]
        # 檢查名稱中是否包含任一關鍵字
        # 寬容模式：如果是複合證型 (如心腎不交)，只要代碼對應其中一個臟腑即可
        if not any(k in name for k in keywords):
            # 特殊例外處理 (Hardcoded Exceptions)
            if "心腎不交" in name and (prefix == "B01" or prefix == "B05"):
                return True, None
            return True, f"[語意警告] 代碼 {code} ({prefix}類) 與名稱 '{name}' 可能不匹配，預期關鍵字: {keywords}"
            
    return True, None

def process_database(input_file, output_file):
    """
    主程序：讀取 JSON -> 清洗 ICD -> 驗證 GB/T -> 輸出 JSON
    """
    if not os.path.exists(input_file):
        print(f"錯誤：找不到檔案 {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("錯誤：JSON 檔案格式損毀，無法讀取。")
            return

    cleaned_data = []
    stats = {
        "total": 0,
        "icd_kept": 0,
        "icd_removed_banned": 0,
        "icd_removed_risky": 0,
        "gbt_warnings": 0
    }

    print(f"正在處理 {len(data)} 筆資料...\n")
    print("-" * 60)
    print(f"{'ID':<15} | {'GB/T 狀態':<10} | {'訊息'}")
    print("-" * 60)

    for entry in data:
        stats["total"] += 1
        
        # --- 步驟 1: ICD-11 清洗邏輯 ---
        original_icd = entry.get('icd11_code')
        should_remove_icd = False
        removal_reason = ""

        # A. 移除禁用代碼 (如 SD83)
        if original_icd in BANNED_ICD_CODES:
            should_remove_icd = True
            stats["icd_removed_banned"] += 1
            removal_reason = "Banned Code (SD83)"

        # B. 移除風險類別 (無精確對應)
        elif any(tag in entry.get('id', '') for tag in RISKY_ID_TAGS) or \
             any(cat in entry.get('category', '') for cat in RISKY_ICD_CATEGORIES):
            should_remove_icd = True
            stats["icd_removed_risky"] += 1
            removal_reason = "No Direct Mapping"

        # 執行 ICD 更新
        if should_remove_icd:
            entry['icd11_code'] = None
            entry['mapping_status'] = "no_direct_match"
            # 若原本有值被清空，可以保留一個 ref 欄位做參考 (選用)
            if original_icd:
                entry['_icd11_ref_removed'] = original_icd 
        else:
            entry['mapping_status'] = "exact_match"
            if original_icd:
                stats["icd_kept"] += 1

        # --- 步驟 2: GB/T 驗證邏輯 ---
        is_valid, warning = validate_gbt(entry)
        
        if warning:
            print(f"{entry['id']:<15} | ⚠️ 警告     | {warning}")
            stats["gbt_warnings"] += 1
            # 可以在此處將 warning 寫入 entry 做標記
            entry['_validation_note'] = warning
        
        cleaned_data.append(entry)

    # --- 步驟 3: 存檔 ---
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print("-" * 60)
    print("\n【處理完成報告】")
    print(f"總筆數: {stats['total']}")
    print(f"ICD-11 保留 (確信): {stats['icd_kept']}")
    print(f"ICD-11 移除 (禁用代碼): {stats['icd_removed_banned']}")
    print(f"ICD-11 移除 (模糊/無對應): {stats['icd_removed_risky']}")
    print(f"GB/T 邏輯警告: {stats['gbt_warnings']}")
    print(f"\n已輸出至檔案: {output_file}")

# ==========================================
# 執行入口
# ==========================================
if __name__ == "__main__":
    # 請確保你的檔案名稱正確
    input_filename = 'scbr_syndromes_core.json' 
    output_filename = 'scbr_syndromes_cleaned_verified.json'
    
    process_database(input_filename, output_filename)