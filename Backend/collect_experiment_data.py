# Backend/collect_experiment_data.py
"""
實驗數據收集器
自動化執行實驗並記錄所有數據
"""

import asyncio
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import time

from s_cbr.main import SCBREngine

class ExperimentDataCollector:
    """實驗數據收集器"""
    
    def __init__(self, output_dir: str = "experiment_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.engine = SCBREngine()
        self.results = []
        
    async def run_experiment(
        self,
        experiment_name: str,
        test_cases: List[Dict],
        config: Dict = None
    ):
        """
        執行實驗
        
        Args:
            experiment_name: 實驗名稱（如 "baseline", "full_system"）
            test_cases: 測試案例列表
            config: 實驗配置（用於消融實驗）
        """
        print(f"\n{'=' * 80}")
        print(f"🧪 開始實驗: {experiment_name}")
        print(f"{'=' * 80}\n")
        
        experiment_results = []
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n處理案例 {i}/{len(test_cases)}: {case['id']}")
            
            case_result = await self.process_case(case, experiment_name)
            experiment_results.append(case_result)
            
            # 顯示進度
            accuracy = sum(1 for r in experiment_results if r['is_correct']) / len(experiment_results)
            avg_rounds = sum(r['total_rounds'] for r in experiment_results) / len(experiment_results)
            print(f"   當前準確率: {accuracy:.1%}, 平均輪次: {avg_rounds:.1f}")
        
        # 儲存結果
        self.save_experiment_results(experiment_name, experiment_results)
        
        # 生成統計
        self.generate_statistics(experiment_name, experiment_results)
        
        return experiment_results
    
    async def process_case(self, case: Dict, experiment_name: str) -> Dict:
        """處理單個案例"""
        case_id = case['id']
        rounds_data = case['rounds']
        expected_diagnosis = case.get('expected_pattern', '')
        
        session_id = None
        round_results = []
        
        start_time = time.time()
        
        for round_num, question in enumerate(rounds_data, 1):
            print(f"      Round {round_num}: {question[:50]}...")
            
            if round_num == 1:
                result = await self.engine.diagnose(question)
                session_id = result['session_id']
            else:
                result = await self.engine.diagnose(
                    question,
                    session_id=session_id,
                    continue_spiral=True
                )
            
            # 記錄本輪數據
            round_result = {
                "round": round_num,
                "question": question,
                "diagnosis": result['primary'].get('diagnosis', ''),
                "convergence_metrics": result['convergence_metrics'],
                "stop_decision": result['stop_decision'],
                "gap_questions": result.get('gap_questions', []),
                "pattern_shift": result.get('pattern_shift', {}),
                "review_info": result.get('review_info', {}),
                "processing_time": result['processing_time']
            }
            
            round_results.append(round_result)
            
            # 如果已收斂，停止
            if result['stop_decision']['should_stop']:
                break
        
        total_time = time.time() - start_time
        
        # 最終診斷
        final_diagnosis = round_results[-1]['diagnosis']
        
        # 判斷是否正確
        is_correct = expected_diagnosis in final_diagnosis
        
        case_result = {
            "case_id": case_id,
            "experiment": experiment_name,
            "timestamp": datetime.now().isoformat(),
            "total_rounds": len(round_results),
            "total_time": total_time,
            "final_diagnosis": final_diagnosis,
            "expected_diagnosis": expected_diagnosis,
            "is_correct": is_correct,
            "rounds": round_results,
            # 聚合指標
            "final_ci": round_results[-1]['convergence_metrics']['Final'],
            "avg_processing_time": sum(r['processing_time'] for r in round_results) / len(round_results),
            "gap_questions_count": sum(len(r['gap_questions']) for r in round_results),
            "pattern_shifted": any(r['pattern_shift'].get('shifted', False) for r in round_results),
            "review_revised": any(r['review_info'].get('revised', False) for r in round_results),
        }
        
        print(f"      ✓ 完成 - 診斷: {final_diagnosis}, 正確: {'✅' if is_correct else '❌'}")
        
        return case_result
    
    def save_experiment_results(self, experiment_name: str, results: List[Dict]):
        """儲存實驗結果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 格式（完整數據）
        json_path = self.output_dir / f"{experiment_name}_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 結果已儲存: {json_path}")
        
        # CSV 格式（摘要數據）
        csv_path = self.output_dir / f"{experiment_name}_{timestamp}.csv"
        
        fieldnames = [
            'case_id', 'total_rounds', 'total_time', 'final_diagnosis',
            'expected_diagnosis', 'is_correct', 'final_ci',
            'gap_questions_count', 'pattern_shifted', 'review_revised'
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                row = {k: result[k] for k in fieldnames}
                writer.writerow(row)
        
        print(f"💾 CSV 已儲存: {csv_path}")
    
    def generate_statistics(self, experiment_name: str, results: List[Dict]):
        """生成統計報告"""
        print(f"\n{'=' * 80}")
        print(f"📊 實驗統計: {experiment_name}")
        print(f"{'=' * 80}\n")
        
        total_cases = len(results)
        correct_cases = sum(1 for r in results if r['is_correct'])
        accuracy = correct_cases / total_cases * 100
        
        avg_rounds = sum(r['total_rounds'] for r in results) / total_cases
        avg_time = sum(r['total_time'] for r in results) / total_cases
        avg_ci = sum(r['final_ci'] for r in results) / total_cases
        
        gap_questions_triggered = sum(1 for r in results if r['gap_questions_count'] > 0)
        pattern_shifted_count = sum(1 for r in results if r['pattern_shifted'])
        review_revised_count = sum(1 for r in results if r['review_revised'])
        
        print(f"【準確性】")
        print(f"  案例總數: {total_cases}")
        print(f"  正確案例: {correct_cases}")
        print(f"  準確率: {accuracy:.1f}%")
        
        print(f"\n【收斂性】")
        print(f"  平均輪次: {avg_rounds:.2f}")
        print(f"  平均最終 CI: {avg_ci:.3f}")
        
        print(f"\n【效率】")
        print(f"  平均總時間: {avg_time:.2f}s")
        
        print(f"\n【智能輔助】")
        print(f"  補問觸發: {gap_questions_triggered}/{total_cases} ({gap_questions_triggered/total_cases*100:.1f}%)")
        print(f"  證型轉化: {pattern_shifted_count}/{total_cases} ({pattern_shifted_count/total_cases*100:.1f}%)")
        print(f"  審稿修正: {review_revised_count}/{total_cases} ({review_revised_count/total_cases*100:.1f}%)")
        
        # 儲存統計摘要
        stats = {
            "experiment": experiment_name,
            "total_cases": total_cases,
            "correct_cases": correct_cases,
            "accuracy": accuracy,
            "avg_rounds": avg_rounds,
            "avg_time": avg_time,
            "avg_ci": avg_ci,
            "gap_questions_triggered": gap_questions_triggered,
            "pattern_shifted_count": pattern_shifted_count,
            "review_revised_count": review_revised_count,
        }
        
        stats_path = self.output_dir / f"{experiment_name}_stats.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

# ==================== 測試案例定義 ====================

TEST_CASES_FULL = [
    {
        "id": "case_001",
        "category": "simple",
        "rounds": [
            "失眠多夢，心悸健忘，疲倦乏力",
            "舌尖紅，少苔",
            "口乾，五心煩熱"
        ],
        "expected_pattern": "心腎不交"
    },
    {
        "id": "case_002",
        "category": "simple",
        "rounds": [
            "咳嗽，痰白稀薄，惡寒無汗",
            "鼻塞流清涕",
            "脈浮緊"
        ],
        "expected_pattern": "風寒束肺"
    },
    {
        "id": "case_003",
        "category": "medium",
        "rounds": [
            "腹脹，食慾不振，疲倦乏力",
            "大便溏薄，面色萎黃",
            "舌淡苔白"
        ],
        "expected_pattern": "脾氣虛"
    },
    {
        "id": "case_004",
        "category": "medium",
        "rounds": [
            "頭痛頭暈，急躁易怒",
            "脅痛，口苦",
            "脈弦"
        ],
        "expected_pattern": "肝陽上亢"
    },
    {
        "id": "case_005",
        "category": "medium",
        "rounds": [
            "腰膝痠軟，耳鳴，五心煩熱",
            "盜汗，遺精",
            "舌紅少苔"
        ],
        "expected_pattern": "腎陰虛"
    },
    # 可以繼續添加更多案例...
]

async def main():
    """主程序"""
    collector = ExperimentDataCollector()
    
    # 執行實驗
    # 這裡可以運行不同配置的實驗
    
    print("選擇實驗類型：")
    print("1. Full System（完整系統）")
    print("2. Baseline（基線）")
    print("3. 全部實驗（消融實驗）")
    
    choice = input("請選擇 (1-3): ").strip()
    
    if choice == "1":
        await collector.run_experiment("full_system", TEST_CASES_FULL)
    
    elif choice == "2":
        # Baseline 配置（需要在 main.py 中支持配置切換）
        await collector.run_experiment("baseline", TEST_CASES_FULL)
    
    elif choice == "3":
        # 運行所有實驗組
        experiments = ["baseline", "group_a", "group_b", "group_c", "full_system"]
        for exp in experiments:
            await collector.run_experiment(exp, TEST_CASES_FULL)
            print("\n等待 5 秒後繼續下一個實驗...\n")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())