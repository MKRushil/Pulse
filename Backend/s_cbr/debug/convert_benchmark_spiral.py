import json
import yaml
import os

def generate_spiral_benchmark_yaml():
    input_file = 'tcm_cases_dump.json'
    output_file = 'benchmark_cases_spiral.yaml'
    
    if not os.path.exists(input_file):
        print(f"❌ 找不到輸入檔案: {input_file}")
        return

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            cases = json.load(f)
    except Exception as e:
        print(f"❌ JSON 解析失敗: {e}")
        return

    benchmark_list = []

    for case in cases:
        # 解析 raw_data 以獲取結構化欄位
        try:
            raw_data = json.loads(case.get('raw_data', '{}'))
            complaint_data = raw_data.get('complaint', {})
            inspection_data = raw_data.get('inspection', {})
            pulse_data = raw_data.get('pulse', {})
        except:
            continue # 跳過資料不完整的

        # --- 構建螺旋測試 (Spiral Rounds) ---
        
        # Round 1: 僅提供主訴 (模擬初診)
        # 這會測試 L1 是否能處理短文本，以及 L2 是否會標記 need_more_info
        r1_query = complaint_data.get('chiefComplaint', '')
        if not r1_query: r1_query = case.get('chief_complaint', '不適')

        # Round 2: 補充現病史 (模擬患者詳述)
        r2_query = complaint_data.get('presentIllness', '')

        # Round 3: 補充舌脈 (模擬醫生望診/切診後輸入)
        # 這是確診的關鍵
        tongue = inspection_data.get('tongueBody', []) + inspection_data.get('tongueCoating', [])
        pulse_str = ", ".join([f"{k}:{v[0]}" for k,v in pulse_data.items() if v])
        r3_query = f"舌象：{' '.join(tongue)}。脈象：{pulse_str}"

        # 建立多輪測試案例
        benchmark_item = {
            "id": case.get('case_id'),
            "name": f"螺旋測試 - {case.get('diagnosis', '未知')}",
            "type": "benchmark_spiral",
            "expected_diagnosis": case.get('diagnosis'),
            "rounds": []
        }

        # 依序加入輪次 (若資料存在)
        if r1_query:
            benchmark_item['rounds'].append({"question": r1_query})
        if r2_query:
            benchmark_item['rounds'].append({"question": r2_query})
        if len(tongue) > 0 or len(pulse_str) > 0:
            benchmark_item['rounds'].append({"question": r3_query})

        benchmark_list.append(benchmark_item)

    # 寫入 YAML
    final_yaml = {"test_cases": benchmark_list}
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(final_yaml, f, allow_unicode=True, sort_keys=False, indent=2)

    print(f"✅ 已生成螺旋測試集: {len(benchmark_list)} 個案例")
    print(f"   每個案例平均 {sum(len(c['rounds']) for c in benchmark_list)/len(benchmark_list):.1f} 輪")
    print(f"💾 檔案位置: {output_file}")

if __name__ == "__main__":
    generate_spiral_benchmark_yaml()