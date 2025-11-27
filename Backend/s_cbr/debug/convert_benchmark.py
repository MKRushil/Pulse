import json
import yaml
import os

def generate_benchmark_yaml():
    # 1. 設定檔案路徑
    input_file = 'C:\work\系統-中醫\Pulse-project\Backend\s_cbr\debug/tcm_cases_dump.json'
    output_file = 'C:\work\系統-中醫\Pulse-project\Backend\s_cbr\debug/benchmark_cases.yaml'
    
    if not os.path.exists(input_file):
        print(f"❌ 找不到輸入檔案: {input_file}")
        return

    print(f"📖 正在讀取 {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            cases = json.load(f)
    except Exception as e:
        print(f"❌ JSON 解析失敗: {e}")
        return

    benchmark_list = []

    # 2. 轉換邏輯
    for case in cases:
        # 嘗試解析 raw_data 以獲取更詳細的現病史 (Present Illness)
        # 這樣模擬的使用者輸入會更真實
        try:
            raw_data = json.loads(case.get('raw_data', '{}'))
            present_illness = raw_data.get('complaint', {}).get('presentIllness', '')
            # 如果沒有現病史，就只用 full_text 裡面的主訴
        except:
            present_illness = ""

        # 組合出模擬的使用者問題 (User Query)
        # 格式：主訴 + 現病史 (模擬真實患者的敘述)
        chief_complaint = case.get('chief_complaint', '')
        
        # 構建查詢字串
        if present_illness and present_illness != chief_complaint:
            query = f"{chief_complaint}。{present_illness}"
        else:
            query = chief_complaint

        # 建立測試項目
        benchmark_item = {
            "id": case.get('case_id'),
            "name": f"真實醫案 - {case.get('diagnosis', '未知診斷')}",
            "type": "benchmark_real_world",
            "expected_diagnosis": case.get('diagnosis'), # 這是標準答案 (Ground Truth)
            "rounds": [
                {
                    "question": query
                }
            ]
        }
        benchmark_list.append(benchmark_item)

    # 3. 包裝成 agentic_test_runner 可讀的格式
    final_yaml = {
        "test_cases": benchmark_list
    }

    # 4. 寫入 YAML
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(final_yaml, f, allow_unicode=True, sort_keys=False, indent=2)

    print(f"✅ 成功轉換 {len(benchmark_list)} 個案例！")
    print(f"💾 已儲存至: {output_file}")
    print("👉 您現在可以使用 'python agentic_test_runner.py' 並修改 Config 讀取此檔案來進行大規模回測。")

if __name__ == "__main__":
    generate_benchmark_yaml()