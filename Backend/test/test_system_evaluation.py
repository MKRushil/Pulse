
import requests
import time
import json
import uuid
from typing import Dict, List, Any

# --- 配置 ---
BASE_URL = "http://127.0.0.1:8000"
API_ENDPOINT = f"{BASE_URL}/api/scbr/v2/diagnose"
HEADERS = {"Content-Type": "application/json"}

# --- 測試案例定義 ---

# 1. 功能與準確性測試案例 (TCM Scenarios)
TCM_CASES = [
    {
        "name": "心脾兩虛 (Heart & Spleen Deficiency)",
        "rounds": [
            {"question": "最近幾週都睡不好，很容易做夢，白天覺得非常疲倦。"},
            {"question": "補充一下，我食慾很差，而且常常忘記事情。"},
            {"question": "感覺心跳有時候會突然加快，有點心慌。"}
        ]
    },
    {
        "name": "肝鬱脾虛 (Liver Qi Stagnation & Spleen Deficiency)",
        "rounds": [
            {"question": "常常覺得胸口悶悶的，很喜歡嘆氣，心情不太好。"},
            {"question": "肚子總是脹脹的，不太想吃飯，大便有點稀。"}
        ]
    },
    {
        "name": "腎陽虛 (Kidney Yang Deficiency)",
        "rounds": [
            {"question": "我非常怕冷，特別是手腳，一年四季都是冰的。"},
            {"question": "腰很酸，晚上要起來上好幾次廁所，精神很差。"},
            {"question": "最近感覺性慾也減退了。"}
        ]
    },
    {
        "name": "陰虛火旺 (Yin Deficiency with Fire)",
        "rounds": [
            {"question": "手心腳心發熱，尤其下午和晚上，口很乾。"},
            {"question": "晚上睡覺會流汗，而且很容易失眠。"}
        ]
    },
    {
        "name": "痰濕內阻 (Phlegm-Dampness Obstruction)",
        "rounds": [
            {"question": "感覺身體很重，不清爽，喉嚨裡好像一直有痰。"},
            {"question": "胸口悶，頭也昏昏沉沉的，舌苔感覺很厚。"}
        ]
    },
    {
        "name": "血瘀 (Blood Stasis)",
        "rounds": [
            {"question": "身體某些地方有固定的刺痛感，晚上特別明顯。"},
            {"question": "我女朋友說我臉色很暗，沒什麼光澤，嘴唇顏色也偏紫。"}
        ]
    },
    {
        "name": "肝火上炎 (Liver Fire Blazing Upwards)",
        "rounds": [
            {"question": "頭痛欲裂，眼睛紅紅的，嘴巴裡很苦。"},
            {"question": "脾氣很暴躁，非常容易生氣，晚上都睡不著。"}
        ]
    },
    {
        "name": "肺氣虛 (Lung Qi Deficiency)",
        "rounds": [
            {"question": "稍微動一下就喘不過氣，很容易出汗，講話也沒什麼力氣。"},
            {"question": "天氣一變就容易感冒，抵抗力很差。"}
        ]
    },
    {
        "name": "胃陰虛 (Stomach Yin Deficiency)",
        "rounds": [
            {"question": "雖然不餓但嘴巴很乾，不想喝水，有時候會乾嘔。"},
            {"question": "大便很乾燥，舌頭紅紅的沒什麼舌苔。"}
        ]
    },
    {
        "name": "濕熱下注 (Damp-Heat in Lower Jiao)",
        "rounds": [
            {"question": "小便黃、味道重，陰囊潮濕。"},
            {"question": "小腿覺得腫脹，大便黏黏的沖不乾淨。"}
        ]
    }
]

# 2. 安全性測試案例 (OWASP & Security)
SECURITY_CASES = [
    {
        "name": "OWASP - XSS (Cross-Site Scripting)",
        "payload": {"question": "<script>alert('xss');</script>"},
        "expected_status": 400
    },
    {
        "name": "OWASP - SQL Injection",
        "payload": {"question": "失眠' OR 1=1; --"},
        "expected_status": 200  # 預期系統能處理，但不會執行SQL
    },
    {
        "name": "OWASP - Command Injection",
        "payload": {"question": "頭暈; ls -la"},
        "expected_status": 200  # 預期系統能處理，但不會執行指令
    },
    {
        "name": "OWASP - Long String (DoS)",
        "payload": {"question": "症狀" * 1000},
        "expected_status": 400 # Based on Pydantic model validation
    },
    {
        "name": "Invalid Characters (Null Byte)",
        "payload": {"question": "心悸\x00"},
        "expected_status": 200
    },
    {
        "name": "Empty Input",
        "payload": {"question": "   "},
        "expected_status": 400
    }
]

# --- 輔助函數 ---

def print_header(title: str):
    """打印標題"""
    print("\n" + "="*80)
    print(f"📋 {title}")
    print("="*80)

def print_subheader(title: str):
    """打印副標題"""
    print("\n" + "-"*60)
    print(f"▶️  {title}")
    print("-"*60)

def make_api_call(payload: Dict[str, Any]) -> (int, float, Dict[str, Any]):
    """發送 API 請求並記錄效能"""
    start_time = time.time()
    try:
        response = requests.post(API_ENDPOINT, headers=HEADERS, data=json.dumps(payload), timeout=60)
        duration = (time.time() - start_time) * 1000  # 轉換為毫秒
        return response.status_code, duration, response.json()
    except requests.exceptions.RequestException as e:
        duration = (time.time() - start_time) * 1000
        return 500, duration, {"error": "request_failed", "message": str(e)}

def analyze_response(response: Dict[str, Any]):
    """分析並打印回應中的關鍵指標"""
    if not response or "error" in response:
        print("  ❗️ 系統返回錯誤或空回應。" )
        return

    primary = response.get("primary")
    metrics = response.get("convergence_metrics", {})
    
    print(f"  - 主要診斷: {primary.get('diagnosis', 'N/A') if primary else 'N/A'}")
    print(f"  - 案例來源: {primary.get('source', 'N/A')}" + ("#" + primary.get('id', 'N/A')[:8] if primary and primary.get('id') else 'N/A'))
    
    scores = {
        "RCI": metrics.get("RCI", 0),
        "CMS": metrics.get("CMS", 0),
        "CSC": metrics.get("CSC", 0),
        "CAS": metrics.get("CAS", 0),
        "Final": metrics.get("Final", 0)
    }
    scores_str = ", ".join([f"{k}={v:.2f}" for k, v in scores.items()])
    print(f"  - 評估分數: {scores_str}")
    
    print_subheader("系統診斷輸出 (可信度分析)")
    print(response.get("final_text", "沒有診斷文本。"))


# --- 測試執行 ---

def run_tcm_tests():
    """執行功能與準確性測試"""
    print_header("功能與準確性測試 (TCM Scenarios)")
    
    for case in TCM_CASES:
        print_subheader(f"測試案例: {case['name']}")
        session_id = str(uuid.uuid4())
        
        for i, round_data in enumerate(case["rounds"]):
            round_num = i + 1
            is_first_round = (round_num == 1)
            
            payload = {
                "question": round_data["question"],
                "session_id": session_id,
                "continue_spiral": not is_first_round
            }
            
            print(f"\n--- Round {round_num} ---")
            print(f"  -輸入症狀: {payload['question']}")
            
            status, duration, response = make_api_call(payload)
            
            print(f"  - HTTP 狀態: {status}")
            print(f"  - 回應時間: {duration:.2f} ms")
            
            if status == 200:
                analyze_response(response)
            else:
                print(f"  ❗️ 請求失敗: {response}")

def run_security_tests():
    """執行安全性測試"""
    print_header("安全性測試 (OWASP & Security)")
    
    results = []
    for case in SECURITY_CASES:
        print_subheader(f"測試案例: {case['name']}")
        
        payload = case["payload"]
        expected_status = case["expected_status"]
        
        print(f"  - Payload: {str(payload)[:100]}...")
        print(f"  - 預期狀態: {expected_status}")
        
        status, duration, response = make_api_call(payload)
        
        print(f"  - 實際狀態: {status}")
        print(f"  - 回應時間: {duration:.2f} ms")
        
        # For security tests, a 422 is also an acceptable failure code if a 400 is expected
        if expected_status == 400 and status == 422:
            test_passed = True
        else:
            test_passed = (status == expected_status)
        results.append({"name": case['name'], "passed": test_passed, "status": status})
        
        if test_passed:
            print("  - ✅ 測試通過")
            if status != 200:
                print(f"  - 系統回應: {response.get('detail') or response.get('message', 'N/A')}")
        else:
            print(f"  - ❌ 測試失敗: 預期狀態 {expected_status}，但收到 {status}")

    print_header("安全性測試總結")
    for res in results:
        status_icon = "✅" if res["passed"] else "❌"
        print(f"  {status_icon} {res['name']:<30} | {'通過' if res['passed'] else '失敗'}")


if __name__ == "__main__":
    print("🚀 開始 S-CBR 系統全面評估...")
    run_tcm_tests()
    run_security_tests()
    print("\n" + "="*80)
    print("✅ 全面評估完成")
    print("="*80)
