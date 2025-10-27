# Backend/test_benchmark.py
"""
性能與準確性基準測試
"""

import asyncio
import time
import statistics
from typing import List, Dict
from pathlib import Path
import json

from s_cbr.main import SCBREngine

class BenchmarkTester:
    """基準測試器"""
    
    def __init__(self):
        self.engine = SCBREngine()
        self.results = {
            "performance": [],
            "convergence": [],
            "accuracy": []
        }
    
    # ==================== 測試案例庫 ====================
    TEST_CASES = [
        {
            "id": "case_001",
            "rounds": [
                "失眠多夢，心悸健忘",
                "舌尖紅，少苔",
                "口乾，五心煩熱"
            ],
            "expected_pattern": "心腎不交",
            "expected_rounds": 2
        },
        {
            "id": "case_002",
            "rounds": [
                "咳嗽，痰白稀薄",
                "惡寒，無汗",
                "脈浮緊"
            ],
            "expected_pattern": "風寒束肺",
            "expected_rounds": 2
        },
        {
            "id": "case_003",
            "rounds": [
                "腹脹，食慾不振",
                "大便溏薄",
                "疲倦乏力，面色萎黃"
            ],
            "expected_pattern": "脾虛",
            "expected_rounds": 2
        },
        {
            "id": "case_004",
            "rounds": [
                "頭痛頭暈",
                "急躁易怒",
                "脅痛，口苦，脈弦"
            ],
            "expected_pattern": "肝陽上亢",
            "expected_rounds": 2
        },
        {
            "id": "case_005",
            "rounds": [
                "腰膝痠軟，耳鳴",
                "五心煩熱，盜汗",
                "舌紅少苔"
            ],
            "expected_pattern": "腎陰虛",
            "expected_rounds": 2
        },
    ]
    
    async def run_all_benchmarks(self):
        """執行所有基準測試"""
        print("\n" + "=" * 80)
        print("📊 S-CBR 性能基準測試")
        print("=" * 80 + "\n")
        
        # 1. 性能測試
        await self.test_performance()
        
        # 2. 收斂性測試
        await self.test_convergence()
        
        # 3. 準確性測試
        await self.test_accuracy()
        
        # 4. 生成報告
        self.generate_report()
    
    async def test_performance(self):
        """性能測試：響應時間、吞吐量"""
        print("\n" + "─" * 80)
        print("⏱️  性能測試")
        print("─" * 80)
        
        response_times = []
        
        for i in range(10):
            start = time.time()
            await self.engine.diagnose(f"測試症狀 {i}: 失眠心悸")
            elapsed = time.time() - start
            response_times.append(elapsed)
            print(f"   第 {i+1} 次: {elapsed:.2f}s")
        
        avg_time = statistics.mean(response_times)
        std_time = statistics.stdev(response_times)
        
        print(f"\n   平均響應時間: {avg_time:.2f}s")
        print(f"   標準差: {std_time:.2f}s")
        print(f"   最快: {min(response_times):.2f}s")
        print(f"   最慢: {max(response_times):.2f}s")
        
        self.results["performance"] = {
            "avg_time": avg_time,
            "std_time": std_time,
            "min_time": min(response_times),
            "max_time": max(response_times),
            "samples": len(response_times)
        }
        
        # 評估
        if avg_time < 5.0:
            print(f"   ✅ 性能評級: 優秀 (< 5s)")
        elif avg_time < 10.0:
            print(f"   ✅ 性能評級: 良好 (< 10s)")
        else:
            print(f"   ⚠️  性能評級: 需優化 (> 10s)")
    
    async def test_convergence(self):
        """收斂性測試：收斂速度、穩定性"""
        print("\n" + "─" * 80)
        print("📈 收斂性測試")
        print("─" * 80)
        
        convergence_data = []
        
        for case in self.TEST_CASES[:3]:  # 測試前3個案例
            print(f"\n   測試案例: {case['id']}")
            
            session_id = None
            round_cis = []
            
            for round_num, question in enumerate(case['rounds'], 1):
                if round_num == 1:
                    result = await self.engine.diagnose(question)
                    session_id = result['session_id']
                else:
                    result = await self.engine.diagnose(
                        question,
                        session_id=session_id,
                        continue_spiral=True
                    )
                
                ci = result['convergence_metrics']['Final']
                round_cis.append(ci)
                print(f"      Round {round_num}: CI = {ci:.3f}")
            
            # 計算收斂速度
            if len(round_cis) >= 2:
                convergence_speed = round_cis[-1] - round_cis[0]
                print(f"      收斂速度: {convergence_speed:+.3f}")
                
                convergence_data.append({
                    "case_id": case['id'],
                    "rounds": len(round_cis),
                    "final_ci": round_cis[-1],
                    "speed": convergence_speed,
                    "trajectory": round_cis
                })
        
        # 統計
        avg_final_ci = statistics.mean([c['final_ci'] for c in convergence_data])
        avg_speed = statistics.mean([c['speed'] for c in convergence_data])
        
        print(f"\n   平均最終 CI: {avg_final_ci:.3f}")
        print(f"   平均收斂速度: {avg_speed:+.3f}")
        
        self.results["convergence"] = {
            "avg_final_ci": avg_final_ci,
            "avg_speed": avg_speed,
            "cases": convergence_data
        }
        
        # 評估
        if avg_final_ci >= 0.85:
            print(f"   ✅ 收斂評級: 優秀 (≥ 0.85)")
        elif avg_final_ci >= 0.75:
            print(f"   ✅ 收斂評級: 良好 (≥ 0.75)")
        else:
            print(f"   ⚠️  收斂評級: 需優化 (< 0.75)")
    
    async def test_accuracy(self):
        """準確性測試：診斷準確率"""
        print("\n" + "─" * 80)
        print("🎯 準確性測試")
        print("─" * 80)
        
        correct = 0
        total = len(self.TEST_CASES)
        
        for case in self.TEST_CASES:
            print(f"\n   測試案例: {case['id']}")
            print(f"   預期診斷: {case['expected_pattern']}")
            
            session_id = None
            
            for round_num, question in enumerate(case['rounds'], 1):
                if round_num == 1:
                    result = await self.engine.diagnose(question)
                    session_id = result['session_id']
                else:
                    result = await self.engine.diagnose(
                        question,
                        session_id=session_id,
                        continue_spiral=True
                    )
            
            # 最終診斷
            final_diagnosis = result['primary'].get('diagnosis', '')
            print(f"   實際診斷: {final_diagnosis}")
            
            # 判斷是否正確（包含預期證型）
            if case['expected_pattern'] in final_diagnosis:
                print(f"   ✅ 正確")
                correct += 1
            else:
                print(f"   ❌ 不符")
        
        accuracy = correct / total * 100
        
        print(f"\n   準確率: {accuracy:.1f}% ({correct}/{total})")
        
        self.results["accuracy"] = {
            "correct": correct,
            "total": total,
            "accuracy": accuracy
        }
        
        # 評估
        if accuracy >= 80:
            print(f"   ✅ 準確性評級: 優秀 (≥ 80%)")
        elif accuracy >= 70:
            print(f"   ✅ 準確性評級: 良好 (≥ 70%)")
        else:
            print(f"   ⚠️  準確性評級: 需優化 (< 70%)")
    
    def generate_report(self):
        """生成測試報告"""
        print("\n" + "=" * 80)
        print("📋 基準測試報告")
        print("=" * 80)
        
        # 性能
        perf = self.results["performance"]
        print(f"\n【性能指標】")
        print(f"  平均響應時間: {perf['avg_time']:.2f}s")
        print(f"  標準差: {perf['std_time']:.2f}s")
        
        # 收斂性
        conv = self.results["convergence"]
        print(f"\n【收斂性指標】")
        print(f"  平均最終 CI: {conv['avg_final_ci']:.3f}")
        print(f"  平均收斂速度: {conv['avg_speed']:+.3f}")
        
        # 準確性
        acc = self.results["accuracy"]
        print(f"\n【準確性指標】")
        print(f"  診斷準確率: {acc['accuracy']:.1f}%")
        print(f"  正確/總數: {acc['correct']}/{acc['total']}")
        
        # 總評
        print(f"\n【總體評估】")
        
        scores = []
        if perf['avg_time'] < 5.0:
            scores.append(("性能", 90))
        elif perf['avg_time'] < 10.0:
            scores.append(("性能", 75))
        else:
            scores.append(("性能", 60))
        
        if conv['avg_final_ci'] >= 0.85:
            scores.append(("收斂性", 90))
        elif conv['avg_final_ci'] >= 0.75:
            scores.append(("收斂性", 75))
        else:
            scores.append(("收斂性", 60))
        
        if acc['accuracy'] >= 80:
            scores.append(("準確性", 90))
        elif acc['accuracy'] >= 70:
            scores.append(("準確性", 75))
        else:
            scores.append(("準確性", 60))
        
        overall = sum(s[1] for s in scores) / len(scores)
        
        for name, score in scores:
            print(f"  {name}: {score}/100")
        
        print(f"\n  綜合評分: {overall:.1f}/100")
        
        if overall >= 85:
            print(f"  🏆 評級: 優秀 - 可進入研究階段")
        elif overall >= 75:
            print(f"  ✅ 評級: 良好 - 建議優化後進入研究")
        else:
            print(f"  ⚠️  評級: 需改進 - 建議先優化系統")
        
        # 儲存報告
        report_path = Path("benchmark_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n  報告已儲存: {report_path}")

async def main():
    """主測試入口"""
    tester = BenchmarkTester()
    await tester.run_all_benchmarks()

if __name__ == "__main__":
    asyncio.run(main())