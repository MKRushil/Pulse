# -*- coding: utf-8 -*-
"""
防禦數據分析工具（用於論文研究）

功能：
1. 讀取 logs/defense_events.jsonl 日誌檔案
2. 生成 OWASP 風險分佈圖表（PNG）
3. 匯出 Excel 完整數據（含多個工作表）
4. 生成 LaTeX 表格（用於論文）
5. 統計分析（時間分佈、防禦層效能等）

使用方式：
    python -m s_cbr.research.defense_analytics

輸出檔案：
    logs/owasp_distribution.png      # OWASP 分佈圖
    logs/defense_analysis.xlsx        # Excel 完整數據
    終端輸出 LaTeX 表格代碼
"""

import json
from pathlib import Path
from typing import Dict, List
from collections import Counter
from datetime import datetime


class DefenseAnalytics:
    """防禦數據分析器"""
    
    def __init__(self, log_file: str = "logs/defense_events.jsonl"):
        """
        初始化分析器
        
        Args:
            log_file: JSONL 日誌檔案路徑
        """
        self.log_file = Path(log_file)
        self.events = self._load_events()
    
    def _load_events(self) -> List[Dict]:
        """
        載入所有防禦事件
        
        Returns:
            事件列表
        """
        events = []
        if self.log_file.exists():
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        events.append(json.loads(line))
                    except:
                        pass
        return events
    
    def get_owasp_distribution(self) -> Dict:
        """
        獲取 OWASP 風險分佈
        
        Returns:
            包含計數和百分比的字典
        """
        owasp_counts = Counter([e["owasp_risk"] for e in self.events])
        total = len(self.events)
        
        return {
            "counts": dict(owasp_counts),
            "percentages": {k: v/total*100 for k, v in owasp_counts.items()} if total > 0 else {}
        }
    
    def get_defense_layer_stats(self) -> Dict:
        """
        獲取各防禦層統計
        
        Returns:
            防禦層計數字典
        """
        layer_counts = Counter([e["defense_layer"] for e in self.events])
        return dict(layer_counts)
    
    def get_attack_type_distribution(self) -> Dict:
        """
        獲取攻擊類型分佈
        
        Returns:
            攻擊類型計數字典
        """
        attack_counts = Counter([e["attack_type"] for e in self.events])
        return dict(attack_counts)
    
    def get_hourly_distribution(self) -> Dict:
        """
        獲取攻擊時間分佈（小時級）
        
        Returns:
            24小時的計數字典
        """
        hours = []
        for e in self.events:
            try:
                dt = datetime.fromisoformat(e["timestamp"])
                hours.append(dt.hour)
            except:
                pass
        
        hour_counts = Counter(hours)
        return {h: hour_counts.get(h, 0) for h in range(24)}
    
    def get_defense_action_distribution(self) -> Dict:
        """
        獲取防禦動作分佈
        
        Returns:
            防禦動作計數字典（block/sanitize/reject）
        """
        action_counts = Counter([e["defense_action"] for e in self.events])
        return dict(action_counts)
    
    def plot_owasp_distribution(self, save_path: str = "logs/owasp_distribution.png"):
        """
        繪製 OWASP 風險分佈圖（用於論文）
        
        Args:
            save_path: 圖片保存路徑
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Microsoft JhengHei', 'SimHei']
            matplotlib.rcParams['axes.unicode_minus'] = False
        except ImportError:
            print("❌ 需要安裝 matplotlib: pip install matplotlib")
            return
        
        dist = self.get_owasp_distribution()
        
        if not dist["counts"]:
            print("⚠️ 沒有數據可繪製")
            return
        
        plt.figure(figsize=(14, 7))
        
        # 排序（按計數降序）
        sorted_items = sorted(dist["counts"].items(), key=lambda x: x[1], reverse=True)
        labels = [item[0].replace("_", "\n") for item in sorted_items]
        values = [item[1] for item in sorted_items]
        
        plt.bar(labels, values, color='steelblue', alpha=0.8)
        plt.xlabel("OWASP LLM Risk", fontsize=12)
        plt.ylabel("攔截次數", fontsize=12)
        plt.title("SCBR 系統防禦 OWASP LLM Top 10 分佈", fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # 在柱子上顯示數值
        for i, v in enumerate(values):
            plt.text(i, v + 0.5, str(v), ha='center', va='bottom')
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ 圖表已保存：{save_path}")
        plt.close()
    
    def generate_latex_table(self) -> str:
        """
        生成 LaTeX 表格（用於論文）
        
        Returns:
            LaTeX 表格代碼
        """
        dist = self.get_owasp_distribution()
        layer_stats = self.get_defense_layer_stats()
        
        latex = """
\\begin{table}[h]
\\centering
\\caption{SCBR 系統 OWASP LLM Top 10 防禦統計}
\\label{tab:owasp_defense}
\\begin{tabular}{lcc}
\\hline
\\textbf{OWASP Risk} & \\textbf{攔截次數} & \\textbf{百分比} \\\\
\\hline
"""
        
        # 排序（按計數降序）
        sorted_items = sorted(dist["counts"].items(), key=lambda x: x[1], reverse=True)
        
        for risk, count in sorted_items:
            pct = dist["percentages"][risk]
            # LaTeX 轉義
            risk_display = risk.replace("_", "\\_")
            latex += f"{risk_display} & {count} & {pct:.2f}\\% \\\\\n"
        
        latex += """\\hline
\\end{tabular}
\\end{table}
"""
        
        # 防禦層統計表
        latex += """

\\begin{table}[h]
\\centering
\\caption{各防禦層攔截統計}
\\label{tab:defense_layer}
\\begin{tabular}{lc}
\\hline
\\textbf{防禦層} & \\textbf{攔截次數} \\\\
\\hline
"""
        
        for layer, count in sorted(layer_stats.items(), key=lambda x: x[1], reverse=True):
            layer_display = layer.replace("_", "\\_")
            latex += f"{layer_display} & {count} \\\\\n"
        
        latex += """\\hline
\\end{tabular}
\\end{table}
"""
        
        return latex
    
    def export_to_excel(self, save_path: str = "logs/defense_analysis.xlsx"):
        """
        匯出完整數據到 Excel（用於論文）
        
        Args:
            save_path: Excel 檔案保存路徑
        """
        try:
            import pandas as pd
        except ImportError:
            print("❌ 需要安裝 pandas 和 openpyxl: pip install pandas openpyxl")
            return
        
        if not self.events:
            print("⚠️ 沒有數據可匯出")
            return
        
        # 創建 Excel 寫入器
        with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
            # 工作表 1: 原始數據
            df_raw = pd.DataFrame(self.events)
            df_raw.to_excel(writer, sheet_name="原始數據", index=False)
            
            # 工作表 2: OWASP 分佈
            owasp_dist = self.get_owasp_distribution()
            df_owasp = pd.DataFrame([
                {
                    "OWASP Risk": k,
                    "Count": v,
                    "Percentage": f"{owasp_dist['percentages'][k]:.2f}%"
                }
                for k, v in sorted(owasp_dist["counts"].items(), key=lambda x: x[1], reverse=True)
            ])
            df_owasp.to_excel(writer, sheet_name="OWASP分佈", index=False)
            
            # 工作表 3: 防禦層分佈
            layer_stats = self.get_defense_layer_stats()
            df_layer = pd.DataFrame([
                {"Defense Layer": k, "Count": v}
                for k, v in sorted(layer_stats.items(), key=lambda x: x[1], reverse=True)
            ])
            df_layer.to_excel(writer, sheet_name="防禦層分佈", index=False)
            
            # 工作表 4: 攻擊類型分佈
            attack_dist = self.get_attack_type_distribution()
            df_attack = pd.DataFrame([
                {"Attack Type": k, "Count": v}
                for k, v in sorted(attack_dist.items(), key=lambda x: x[1], reverse=True)
            ])
            df_attack.to_excel(writer, sheet_name="攻擊類型分佈", index=False)
            
            # 工作表 5: 時間分佈
            hourly_dist = self.get_hourly_distribution()
            df_hourly = pd.DataFrame([
                {"Hour": f"{h:02d}:00", "Count": count}
                for h, count in sorted(hourly_dist.items())
            ])
            df_hourly.to_excel(writer, sheet_name="時間分佈", index=False)
            
            # 工作表 6: 防禦動作分佈
            action_dist = self.get_defense_action_distribution()
            df_action = pd.DataFrame([
                {"Defense Action": k, "Count": v}
                for k, v in sorted(action_dist.items(), key=lambda x: x[1], reverse=True)
            ])
            df_action.to_excel(writer, sheet_name="防禦動作分佈", index=False)
        
        print(f"✅ Excel 已保存：{save_path}")
    
    def print_summary(self):
        """打印摘要統計"""
        print("=" * 60)
        print("SCBR 防禦數據分析摘要")
        print("=" * 60)
        
        total = len(self.events)
        print(f"\n📊 總防禦事件數：{total}")
        
        if total == 0:
            print("\n⚠️ 沒有防禦事件記錄")
            return
        
        # OWASP 分佈
        print("\n🛡️ OWASP 風險分佈（Top 5）：")
        owasp_dist = self.get_owasp_distribution()
        sorted_owasp = sorted(owasp_dist["counts"].items(), key=lambda x: x[1], reverse=True)[:5]
        for risk, count in sorted_owasp:
            pct = owasp_dist["percentages"][risk]
            print(f"  {risk}: {count} 次 ({pct:.2f}%)")
        
        # 防禦層分佈
        print("\n🔒 防禦層統計：")
        layer_stats = self.get_defense_layer_stats()
        for layer, count in sorted(layer_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {layer}: {count} 次")
        
        # 防禦動作分佈
        print("\n⚔️ 防禦動作分佈：")
        action_dist = self.get_defense_action_distribution()
        for action, count in sorted(action_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"  {action}: {count} 次")
        
        # 時間分佈（尖峰時段）
        print("\n⏰ 攻擊尖峰時段（Top 3）：")
        hourly_dist = self.get_hourly_distribution()
        sorted_hours = sorted(hourly_dist.items(), key=lambda x: x[1], reverse=True)[:3]
        for hour, count in sorted_hours:
            if count > 0:
                print(f"  {hour:02d}:00 - {hour:02d}:59: {count} 次")
        
        print("\n" + "=" * 60)


# ==================== 命令行入口 ====================

def main():
    """命令行主函數"""
    print("=" * 60)
    print("SCBR 防禦數據分析工具")
    print("用於論文研究的數據可視化")
    print("=" * 60)
    
    # 創建分析器
    analytics = DefenseAnalytics()
    
    # 打印摘要
    analytics.print_summary()
    
    # 生成圖表
    print("\n📈 正在生成圖表...")
    analytics.plot_owasp_distribution()
    
    # 生成 LaTeX 表格
    print("\n📄 正在生成 LaTeX 表格...")
    latex_code = analytics.generate_latex_table()
    print("\nLaTeX 代碼（可直接用於論文）：")
    print(latex_code)
    
    # 匯出 Excel
    print("\n📊 正在匯出 Excel...")
    analytics.export_to_excel()
    
    print("\n" + "=" * 60)
    print("✅ 分析完成！")
    print("\n生成的檔案：")
    print("  • logs/owasp_distribution.png      # OWASP 分佈圖")
    print("  • logs/defense_analysis.xlsx        # Excel 完整數據")
    print("\n使用這些檔案撰寫論文的實驗章節。")
    print("=" * 60)


if __name__ == "__main__":
    main()