import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# ================= 配置區域 =================
INPUT_FILE = "test_results/thesis_final_combined_data.csv"
OUTPUT_DIR = "thesis_charts"
DPI = 300  # 論文印刷標準解析度

# 建立輸出目錄
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 設定全域繪圖風格 (學術論文風格)
sns.set_theme(style="whitegrid", context="paper", font_scale=1.4)
plt.rcParams['font.family'] = 'sans-serif'  # 英文論文通常用 sans-serif (Arial/Helvetica)
plt.rcParams['axes.unicode_minus'] = False  # 解決負號顯示問題

# 定義配色 (Agentic=紅色系/強調, Baseline=藍灰色系/對照)
COLOR_AGENTIC = "#D62728"  # Tab:Red
COLOR_BASELINE = "#1F77B4"  # Tab:Blue
PALETTE = {"Agentic (Experiment)": COLOR_AGENTIC, "Baseline (Control)": COLOR_BASELINE}

def load_data(filepath):
    """讀取並預處理數據"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"找不到檔案: {filepath}，請確認檔案位置。")
    
    df = pd.read_csv(filepath)
    
    # 確保 Round 是整數
    df['Round'] = df['Round'].astype(int)
    
    # 確保 Group 名稱一致 (去除空格等)
    df['Group'] = df['Group'].str.strip()
    
    return df

def plot_accuracy_convergence(df):
    """圖表 1: 螺旋推理準確率收斂曲線"""
    print("正在繪製: 1_Accuracy_Convergence.png ...")
    
    # 計算平均值與標準誤 (SEM) 用於誤差棒
    agg_data = df.groupby(['Group', 'Round'])['Is_Correct_Semantic'].agg(['mean', 'sem']).reset_index()
    agg_data['Accuracy_Pct'] = agg_data['mean'] * 100
    agg_data['Error'] = agg_data['sem'] * 100

    plt.figure(figsize=(10, 6))
    
    # 繪製主折線
    sns.lineplot(
        data=agg_data, x='Round', y='Accuracy_Pct', hue='Group', 
        palette=PALETTE, marker='o', markersize=10, linewidth=3, style='Group', dashes=False
    )
    
    # 添加誤差棒 (Error Bars)
    for name, group in agg_data.groupby('Group'):
        plt.errorbar(
            x=group['Round'], y=group['Accuracy_Pct'], yerr=group['Error'],
            fmt='none', c=PALETTE[name], capsize=5, elinewidth=2
        )

    # 標註具體數值
    for line in range(agg_data.shape[0]):
        row = agg_data.iloc[line]
        # Agentic 標籤在上方，Baseline 在下方，避免重疊
        offset = 1.5 if "Agentic" in row['Group'] else -2.5
        plt.text(
            row['Round'], row['Accuracy_Pct'] + offset, 
            f"{row['Accuracy_Pct']:.1f}%", 
            ha='center', va='center', fontsize=12, fontweight='bold', color=PALETTE[row['Group']]
        )

    plt.title('Accuracy Convergence Across Rounds (Spiral Reasoning)', fontsize=16, pad=20)
    plt.ylabel('Semantic Accuracy (%)', fontsize=14)
    plt.xlabel('Reasoning Round', fontsize=14)
    plt.xticks([1, 2, 3], ['R1: Complaint', 'R2: History', 'R3: Tongue/Pulse'])
    plt.ylim(50, 95)  # 調整 Y 軸範圍讓差異更明顯
    plt.legend(title=None, loc='upper left', frameon=True)
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/1_Accuracy_Convergence.png", dpi=DPI)
    plt.close()

def plot_tool_usage_combo(df):
    """圖表 2: 外部工具動態調用分析 (Combo Chart)"""
    print("正在繪製: 2_Tool_Usage_Dynamics.png ...")
    
    # 只取 Agentic 組
    agentic_df = df[df['Group'].str.contains("Agentic")]
    if agentic_df.empty:
        print("警告: 找不到 Agentic 組數據，跳過圖表 2")
        return

    # 計算統計量
    stats = agentic_df.groupby('Round').agg({
        'L2_Tool_Calls': 'mean',
        'L2_Confidence_Boost': 'mean'
    }).reset_index()

    fig, ax1 = plt.subplots(figsize=(10, 6))

    # 左軸：工具調用次數 (柱狀圖)
    color_bar = '#FF9F4A'  # 柔和的橘色
    bars = ax1.bar(
        stats['Round'], stats['L2_Tool_Calls'], 
        color=color_bar, alpha=0.7, label='Avg Tool Calls', width=0.5
    )
    ax1.set_xlabel('Reasoning Round', fontsize=14)
    ax1.set_ylabel('Avg Tool Calls (Count)', fontsize=14, color='black')
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.set_xticks([1, 2, 3])
    ax1.set_xticklabels(['R1', 'R2', 'R3'])
    ax1.set_ylim(0, 3.0)

    # 在柱狀圖上方標註數值
    for bar in bars:
        height = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width()/2., height + 0.05,
            f'{height:.2f}', ha='center', va='bottom', fontsize=12
        )

    # 右軸：信心增益 (折線圖)
    ax2 = ax1.twinx()
    color_line = '#D62728'  # 深紅色
    ax2.plot(
        stats['Round'], stats['L2_Confidence_Boost'], 
        color=color_line, marker='D', markersize=8, linewidth=3, label='Avg Confidence Boost'
    )
    ax2.set_ylabel('Avg Confidence Boost (0-1)', fontsize=14, color=color_line)
    ax2.tick_params(axis='y', labelcolor=color_line)
    ax2.set_ylim(0, 0.25)

    # 標註折線數值
    for i, txt in enumerate(stats['L2_Confidence_Boost']):
        ax2.text(
            stats['Round'][i], txt + 0.01, 
            f'+{txt:.2f}', ha='center', va='bottom', color=color_line, fontweight='bold'
        )

    # 整合圖例
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper right')

    plt.title('Dynamic Tool Usage & Confidence Impact (Agentic Only)', fontsize=16, pad=20)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/2_Tool_Usage_Dynamics.png", dpi=DPI)
    plt.close()

def plot_efficiency_tradeoff(df):
    """圖表 3: 效能-成本權衡圖 (Scatter with Path)"""
    print("正在繪製: 3_Efficiency_Tradeoff.png ...")
    
    agg = df.groupby(['Group', 'Round']).agg({
        'Latency_Total': 'mean',
        'Is_Correct_Semantic': 'mean'
    }).reset_index()
    agg['Accuracy_Pct'] = agg['Is_Correct_Semantic'] * 100

    plt.figure(figsize=(11, 7))

    # 繪製路徑 (箭頭)
    groups = agg['Group'].unique()
    for grp in groups:
        subset = agg[agg['Group'] == grp].sort_values('Round')
        color = PALETTE[grp]
        
        # 畫線連接 R1->R2->R3
        plt.plot(
            subset['Latency_Total'], subset['Accuracy_Pct'], 
            color=color, alpha=0.5, linestyle='--', linewidth=2
        )
        
        # 畫點
        plt.scatter(
            subset['Latency_Total'], subset['Accuracy_Pct'], 
            color=color, s=200, label=grp, edgecolors='white', linewidth=2, zorder=5
        )

        # 畫箭頭
        for i in range(len(subset) - 1):
            p1 = subset.iloc[i]
            p2 = subset.iloc[i+1]
            plt.arrow(
                p1['Latency_Total'], p1['Accuracy_Pct'],
                (p2['Latency_Total'] - p1['Latency_Total']) * 0.8, # 縮短箭頭避免蓋住點
                (p2['Accuracy_Pct'] - p1['Accuracy_Pct']) * 0.8,
                head_width=0.8, head_length=1.5, fc=color, ec=color, alpha=0.6
            )

        # 標註 R1, R2, R3 (智慧避讓)
        for _, row in subset.iterrows():
            r_label = f"R{int(row['Round'])}"
            # Baseline 標籤放左下，Agentic 放右上，減少重疊
            xytext_offset = (10, 10) if "Agentic" in grp else (-10, -15)
            
            plt.annotate(
                r_label, 
                (row['Latency_Total'], row['Accuracy_Pct']),
                xytext=xytext_offset, textcoords='offset points',
                fontsize=12, fontweight='bold', color=color
            )

    plt.title('Efficiency Frontier: Accuracy vs. Latency Trade-off', fontsize=16, pad=20)
    plt.xlabel('Average Latency (Seconds)', fontsize=14)
    plt.ylabel('Semantic Accuracy (%)', fontsize=14)
    
    # 擴大邊界防止文字被切掉
    plt.xlim(agg['Latency_Total'].min() - 5, agg['Latency_Total'].max() + 5)
    plt.ylim(agg['Accuracy_Pct'].min() - 5, agg['Accuracy_Pct'].max() + 5)
    
    # 只顯示一次圖例
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), loc='lower right')
    
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/3_Efficiency_Tradeoff.png", dpi=DPI)
    plt.close()

def plot_l1_strategy_distribution(df):
    """圖表 4: L1 策略觸發分佈 (堆疊長條圖)"""
    print("正在繪製: 4_L1_Strategy_Distribution.png ...")
    
    # 只看 Agentic
    agentic_df = df[df['Group'].str.contains("Agentic")].copy()
    
    # 填充空值以免報錯 (Baseline沒有策略)
    if 'L1_Strategy' not in agentic_df.columns:
        print("警告: 找不到 L1_Strategy 欄位")
        return

    # 計算各個 Round 的策略分佈
    strategy_counts = agentic_df.groupby(['Round', 'L1_Strategy']).size().unstack(fill_value=0)
    
    # 轉換為百分比
    strategy_pct = strategy_counts.div(strategy_counts.sum(axis=1), axis=0) * 100

    # 顏色映射
    strategy_colors = {
        'keyword_focus_forced': '#2ca02c', # 綠色 (術語強制)
        'balanced': '#ff7f0e',             # 橘色 (平衡)
        'fuzzy_search': '#1f77b4'          # 藍色 (模糊/口語)
    }
    # 確保顏色對應存在
    colors = [strategy_colors.get(col, '#7f7f7f') for col in strategy_pct.columns]

    ax = strategy_pct.plot(
        kind='bar', stacked=True, figsize=(10, 6), color=colors, edgecolor='white', width=0.6
    )

    # 標註百分比
    for c in ax.containers:
        # 只標註 > 5% 的區塊，避免字太小
        labels = [f'{v.get_height():.1f}%' if v.get_height() > 5 else '' for v in c]
        ax.bar_label(c, labels=labels, label_type='center', fontsize=11, color='white', fontweight='bold')

    plt.title('L1 Strategy Distribution by Round (Agentic Gatekeeper)', fontsize=16, pad=20)
    plt.ylabel('Strategy Share (%)', fontsize=14)
    plt.xlabel('Round', fontsize=14)
    plt.xticks(rotation=0)
    plt.legend(title='L1 Strategy', bbox_to_anchor=(1.02, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/4_L1_Strategy_Distribution.png", dpi=DPI)
    plt.close()

def main():
    try:
        df = load_data(INPUT_FILE)
        print(f"數據載入成功，共 {len(df)} 筆記錄。")
        
        plot_accuracy_convergence(df)
        plot_tool_usage_combo(df)
        plot_efficiency_tradeoff(df)
        plot_l1_strategy_distribution(df)
        
        print(f"\n✅ 所有圖表已生成完畢！請查看 '{OUTPUT_DIR}' 資料夾。")
        
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()