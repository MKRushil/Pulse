# Backend/test_system_complete.py
"""
S-CBR 完整系統測試腳本
測試所有核心功能與新增模組
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent))

from s_cbr.main import SCBREngine
from s_cbr.utils.logger import get_logger

logger = get_logger("SystemTest")

class SystemTester:
    """系統測試器"""
    
    def __init__(self):
        self.engine = None
        self.test_results = []
        
    async def run_all_tests(self):
        """執行所有測試"""
        print("\n" + "=" * 80)
        print("🧪 S-CBR 完整系統測試")
        print("=" * 80 + "\n")
        
        tests = [
            ("初始化測試", self.test_initialization),
            ("單輪推理測試", self.test_single_round),
            ("多輪推理測試", self.test_multi_round),
            ("收斂度計算測試", self.test_convergence),
            ("終止條件測試", self.test_stop_criteria),
            ("補問生成測試", self.test_gap_asker),
            ("證型轉化測試", self.test_pattern_shift),
            ("自我審稿測試", self.test_self_review),
            ("會話管理測試", self.test_session_management),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                print(f"\n{'─' * 80}")
                print(f"📋 {test_name}")
                print(f"{'─' * 80}")
                
                result = await test_func()
                
                if result:
                    print(f"✅ {test_name} - 通過")
                    passed += 1
                else:
                    print(f"❌ {test_name} - 失敗")
                    failed += 1
                    
                self.test_results.append({
                    "name": test_name,
                    "passed": result,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                print(f"❌ {test_name} - 異常: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
        
        # 輸出總結
        print("\n" + "=" * 80)
        print("📊 測試總結")
        print("=" * 80)
        print(f"✅ 通過: {passed}/{len(tests)}")
        print(f"❌ 失敗: {failed}/{len(tests)}")
        print(f"通過率: {passed/len(tests)*100:.1f}%")
        
        if failed == 0:
            print("\n🎉 所有測試通過！系統運行正常。")
        else:
            print(f"\n⚠️  有 {failed} 個測試失敗，請檢查錯誤信息。")
        
        return failed == 0
    
    async def test_initialization(self):
        """測試系統初始化"""
        try:
            self.engine = SCBREngine()
            
            # 檢查核心組件
            checks = {
                "spiral": self.engine.spiral,
                "dialog": self.engine.dialog,
                "convergence": self.engine.convergence,
                "llm": self.engine.llm,
                "stop_criteria": self.engine.stop_criteria,
                "gap_asker": self.engine.gap_asker,
                "pattern_shifter": self.engine.pattern_shifter,
                "self_reviewer": self.engine.self_reviewer,
            }
            
            for name, component in checks.items():
                status = "✅" if component is not None else "❌"
                print(f"   {status} {name}: {'已載入' if component else '未載入'}")
            
            all_loaded = all(c is not None for c in checks.values())
            return all_loaded
            
        except Exception as e:
            print(f"   ❌ 初始化失敗: {e}")
            return False
    
    async def test_single_round(self):
        """測試單輪推理"""
        try:
            question = "患者失眠多夢，心悸健忘，疲倦乏力"
            
            result = await self.engine.diagnose(question)
            
            # 檢查必要欄位
            required_fields = [
                "session_id", "round", "primary", "convergence_metrics",
                "stop_decision", "gap_questions", "pattern_shift", "review_info"
            ]
            
            for field in required_fields:
                if field not in result:
                    print(f"   ❌ 缺少欄位: {field}")
                    return False
            
            print(f"   ✅ Session ID: {result['session_id']}")
            print(f"   ✅ 診斷: {result['primary'].get('diagnosis', 'N/A')}")
            print(f"   ✅ 收斂度: {result['convergence_metrics']['Final']:.3f}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 單輪推理失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_multi_round(self):
        """測試多輪推理"""
        try:
            # 第1輪
            r1 = await self.engine.diagnose("失眠多夢，心悸健忘")
            session_id = r1['session_id']
            
            print(f"   ✅ 第1輪完成 - 診斷: {r1['primary'].get('diagnosis', 'N/A')}")
            
            # 第2輪
            r2 = await self.engine.diagnose(
                "舌尖紅，少苔，口乾",
                session_id=session_id,
                continue_spiral=True
            )
            
            print(f"   ✅ 第2輪完成 - 診斷: {r2['primary'].get('diagnosis', 'N/A')}")
            print(f"   ✅ 輪次累積: Round {r2['round']}")
            
            # 驗證輪次
            if r2['round'] != 2:
                print(f"   ❌ 輪次錯誤: 預期2，實際{r2['round']}")
                return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ 多輪推理失敗: {e}")
            return False
    
    async def test_convergence(self):
        """測試收斂度計算"""
        try:
            result = await self.engine.diagnose("失眠心悸，疲倦乏力")
            
            metrics = result['convergence_metrics']
            
            # 檢查所有指標
            required_metrics = ['RCI', 'CMS', 'CSC', 'CAS', 'Final']
            
            for metric in required_metrics:
                if metric not in metrics:
                    print(f"   ❌ 缺少指標: {metric}")
                    return False
                
                value = metrics[metric]
                if not (0 <= value <= 1):
                    print(f"   ❌ {metric} 超出範圍: {value}")
                    return False
                
                print(f"   ✅ {metric}: {value:.3f}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 收斂度計算失敗: {e}")
            return False
    
    async def test_stop_criteria(self):
        """測試終止條件"""
        try:
            result = await self.engine.diagnose("失眠多夢")
            
            stop_decision = result.get('stop_decision', {})
            
            required_fields = [
                'should_stop', 'can_save', 'treatment_effective',
                'stop_reason', 'recommendations'
            ]
            
            for field in required_fields:
                if field not in stop_decision:
                    print(f"   ❌ 缺少欄位: {field}")
                    return False
            
            print(f"   ✅ 終止判斷: {stop_decision['should_stop']}")
            print(f"   ✅ 可儲存: {stop_decision['can_save']}")
            print(f"   ✅ 建議: {len(stop_decision['recommendations'])} 條")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 終止條件測試失敗: {e}")
            return False
    
    async def test_gap_asker(self):
        """測試補問生成"""
        try:
            # 第1輪（症狀不足）
            result = await self.engine.diagnose("失眠")
            
            gap_questions = result.get('gap_questions', [])
            
            print(f"   ✅ 生成補問: {len(gap_questions)} 個")
            
            if gap_questions:
                for i, q in enumerate(gap_questions, 1):
                    print(f"      {i}. {q}")
            else:
                print(f"   ⚠️  未生成補問（可能症狀已足夠）")
            
            # 補問應該是列表
            if not isinstance(gap_questions, list):
                print(f"   ❌ gap_questions 類型錯誤")
                return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ 補問測試失敗: {e}")
            return False
    
    async def test_pattern_shift(self):
        """測試證型轉化"""
        try:
            # 第1輪
            r1 = await self.engine.diagnose("失眠多夢，心悸健忘")
            session_id = r1['session_id']
            
            # 第2輪（加入陰虛症狀）
            r2 = await self.engine.diagnose(
                "舌尖紅，少苔，口乾，五心煩熱",
                session_id=session_id,
                continue_spiral=True
            )
            
            pattern_shift = r2.get('pattern_shift', {})
            
            print(f"   ✅ 證型轉化檢查完成")
            print(f"   - 是否轉化: {pattern_shift.get('shifted', False)}")
            
            if pattern_shift.get('shifted'):
                print(f"   - 原證型: {pattern_shift.get('original_pattern', 'N/A')}")
                print(f"   - 新證型: {pattern_shift.get('new_pattern', 'N/A')}")
                print(f"   - 原因: {pattern_shift.get('reason', 'N/A')}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 證型轉化測試失敗: {e}")
            return False
    
    async def test_self_review(self):
        """測試自我審稿"""
        try:
            # 第1輪
            r1 = await self.engine.diagnose("失眠心悸")
            session_id = r1['session_id']
            
            # 第2輪
            r2 = await self.engine.diagnose(
                "口乾口苦",
                session_id=session_id,
                continue_spiral=True
            )
            
            review_info = r2.get('review_info', {})
            
            print(f"   ✅ 審稿檢查完成")
            print(f"   - 通過: {review_info.get('passed', True)}")
            print(f"   - 問題: {len(review_info.get('issues', []))} 個")
            print(f"   - 已修正: {review_info.get('revised', False)}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 自我審稿測試失敗: {e}")
            return False
    
    async def test_session_management(self):
        """測試會話管理"""
        try:
            # 創建新會話
            r1 = await self.engine.diagnose("測試症狀")
            session_id = r1['session_id']
            
            # 重置會話
            self.engine.reset_session(session_id)
            
            print(f"   ✅ 會話創建: {session_id}")
            print(f"   ✅ 會話重置成功")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 會話管理測試失敗: {e}")
            return False

async def main():
    """主測試入口"""
    tester = SystemTester()
    success = await tester.run_all_tests()
    
    # 返回退出碼
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())