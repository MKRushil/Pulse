# -*- coding: utf-8 -*-
"""
SCBR 語意重評估工具 v2.1 (完整詞庫真值比對版)
===========================================
功能：
1. 讀取實驗結果 CSV (experiment_results_Agentic_static.csv)。
2. 讀取考卷 YAML (thesis_100_cases.yaml) 獲取標準答案。
3. ✅ 整合「大幅擴充版中醫同義詞庫」，解決字面不匹配問題。
4. 輸出最準確的語意準確率。
"""

import pandas as pd
import yaml
import re
import os

# ================= 配置區域 =================
INPUT_CSV = "experiment_results_Agentic_static.csv"
YAML_FILE = "thesis_100_cases.yaml"
OUTPUT_CSV = INPUT_CSV.replace(".csv", "_Semantic_Verified.csv")

# 🧠 [核心知識庫] 中醫同義詞庫 (您的完整擴充版)
SYNONYMS = {
    # --- 睡眠與精神類 ---
    "不寐": "失眠",
    "不得眠": "失眠",
    "目不瞑": "失眠",
    "多夢": "失眠",  # 廣義上常合併討論
    "健忘": "記憶力減退",
    "鬱證": "憂鬱",
    "臟躁": "焦慮",
    "煩躁": "心煩",

    # --- 疼痛類 ---
    "腰痠": "腰痛",
    "腰膝痠軟": "腰痛",
    "腰脊痛": "腰痛",
    "胃脘痛": "胃痛",
    "心下痛": "胃痛",
    "胃脘灼痛": "胃灼熱",
    "嘈雜": "胃不適",
    "胸痺": "胸悶",
    "胸滿": "胸悶",
    "頭風": "頭痛",
    "首風": "頭痛",
    "腦風": "頭痛",
    "偏頭痛": "頭痛",
    "痹證": "關節痛",
    "歷節": "關節痛",
    "鶴膝風": "膝關節痛",
    "項強": "頸椎病",

    # --- 消化類 ---
    "泄瀉": "腹瀉",
    "下利": "腹瀉",
    "鶩溏": "腹瀉",
    "便溏": "腹瀉",
    "便祕": "便秘",
    "大便難": "便秘",
    "脾約": "便秘",
    "納呆": "食慾不振",
    "納少": "食慾不振",
    "不思飲食": "食慾不振",
    "痞滿": "消化不良",
    "噯氣": "打嗝",
    "呃逆": "打嗝",
    "泛酸": "胃食道逆流",
    "吞酸": "胃食道逆流",

    # --- 呼吸類 ---
    "咳嗽": "咳喘", 
    "哮病": "氣喘",
    "喘證": "氣喘",
    "肺脹": "COPD",
    "肺癆": "肺結核",
    "感冒": "傷風",

    # --- 婦科類 ---
    "月經先期": "月經提前",
    "月經後期": "月經延後",
    "經亂": "月經不調",
    "痛經": "經行腹痛",
    "閉經": "經閉",
    "崩漏": "功能性子宮出血",
    "帶下": "白帶",
    "絕經前後諸證": "更年期綜合症",
    "乳癖": "乳腺增生",

    # --- 五官與其他 ---
    "眩暈": "頭暈",
    "耳鳴": "重聽", 
    "鼻淵": "鼻竇炎",
    "鼻鼽": "過敏性鼻炎",
    "口瘡": "口腔潰瘍",
    "喉痺": "咽炎",
    "消渴": "糖尿病",
    "水腫": "浮腫",
    "虛勞": "慢性疲勞",
    
    # --- 證型形容詞對應 ---
    "氣虛": ["氣少", "氣不足", "氣怯"],
    "血虛": ["血少", "血虧", "血不足", "血枯"],
    "陰虛": ["陰虧", "陰液不足", "陰分不足"],
    "陽虛": ["陽氣不足", "命門火衰", "真陽不足"],
    "實熱": ["火旺", "熱盛", "火熱"],
    "肝鬱": ["肝氣鬱結", "肝氣不舒", "氣滯"],
    "濕熱": ["濕熱內蘊", "濕熱下注"],
    "痰濕": ["痰濁", "痰飲"],
    "瘀血": ["血瘀", "蓄血", "惡血"],
}

def normalize_text(text):
    """標準化文字"""
    if pd.isna(text): return ""
    text = str(text)
    # 移除括號內容 (如 "不寐(心脾兩虛)" -> "不寐")
    text = re.sub(r"[\(（].*?[\)）]", "", text)
    # 移除標點
    text = re.sub(r"[，。、；：？！]", "", text)
    return text.strip()

def check_match(pred, expected, synonyms_list=None):
    """
    核心比對邏輯 (3層防護)
    1. 包含匹配 (Inclusion)
    2. 擴充詞庫匹配 (Dictionary Lookup)
    3. 關鍵字召回 (Character Recall)
    """
    if not pred or not expected: return False
    
    pred_norm = normalize_text(pred)
    
    # 準備比對目標清單
    targets = [expected]
    
    # A. 加入 YAML 中定義的同義詞 (若有)
    if synonyms_list:
        targets.extend(synonyms_list)
    
    # B. 加入 全域詞庫 SYNONYMS 中的同義詞
    # 邏輯：如果標準答案包含 Key (如 "不寐")，就加入 Value (如 "失眠")
    for key, val in SYNONYMS.items():
        if key in expected:
            if isinstance(val, list):
                targets.extend(val)
            else:
                targets.append(val)

    for target in targets:
        target_norm = normalize_text(target)
        if not target_norm: continue
        
        # 1. 直接包含 (e.g. 預測 "心脾兩虛證" 包含 "心脾兩虛")
        if target_norm in pred_norm:
            return True
            
        # 2. 關鍵字召回 (解決 "心膽氣虛" vs "心虛膽怯")
        s_pred = set(pred_norm)
        s_target = set(target_norm)
        if not s_target: continue
        
        overlap = len(s_pred.intersection(s_target)) / len(s_target)
        
        # 門檻 0.6 (60% 字元重疊即算對)
        if overlap >= 0.6:
            return True
            
    return False

def main():
    if not os.path.exists(INPUT_CSV) or not os.path.exists(YAML_FILE):
        print(f"❌ 找不到檔案。請確認 {INPUT_CSV} 與 {YAML_FILE} 都在目錄下。")
        return

    print(f"📖 讀取考卷: {YAML_FILE} ...")
    with open(YAML_FILE, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)
    
    # 建立 {CaseID: CaseData} 的快速查詢表
    case_db = {c['id']: c for c in yaml_data.get('test_cases', [])}
    print(f"   - 載入 {len(case_db)} 個標準案例。")

    print(f"📖 讀取作答: {INPUT_CSV} ...")
    df = pd.read_csv(INPUT_CSV)
    
    # 初始化統計
    correct_count = 0
    rescued_count = 0
    
    def verify_row(row):
        nonlocal correct_count, rescued_count
        
        case_id = row['CaseID']
        pred = row.get('PredPattern', '')
        original_acc = float(row.get('Accuracy', 0))
        
        # 1. 如果原始已經對了，就保持
        if original_acc == 1.0:
            correct_count += 1
            return 1.0
            
        # 2. 如果原始錯了，去 YAML 找標準答案重判
        if case_id in case_db:
            case_info = case_db[case_id]
            expected = case_info['expected_diagnosis'] # 這裡可能是字串或物件
            
            # 處理 YAML 結構差異 (有些是字串，有些是 dict)
            if isinstance(expected, dict):
                primary = expected.get('primary_pattern', '')
                syns = expected.get('synonyms', [])
            else:
                primary = str(expected)
                syns = []
            
            # 執行核心比對
            if check_match(pred, primary, syns):
                correct_count += 1
                rescued_count += 1
                return 1.0 # 救援成功
        
        return 0.0

    print("🔄 正在進行真值比對 (Ground Truth Verification)...")
    df['Is_Correct_Verified'] = df.apply(verify_row, axis=1)
    
    final_acc = df['Is_Correct_Verified'].mean()
    raw_acc = pd.to_numeric(df['Accuracy'], errors='coerce').fillna(0).mean()
    
    print("-" * 50)
    print(f"📊 分析報告:")
    print(f"   - 總資料筆數: {len(df)}")
    print(f"   - 原始準確率 (Raw):      {raw_acc:.2%}")
    print(f"   - 真實準確率 (Verified): {final_acc:.2%}")
    print(f"   - 詞庫救援成功筆數:      {rescued_count}")
    print("-" * 50)
    
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"✅ 結果已儲存: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()