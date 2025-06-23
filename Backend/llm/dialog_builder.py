# llm/dialog_builder.py
"""
對話生成/推理說明組裝工具
- 支援自動生成查詢解釋、步驟摘要回饋
- 已自動兼容 PulsePJ (脈象知識庫) 及 case/PCD 推理結構
"""
def build_dialog_from_reasoning(reasoning_chain):
    """
    根據推理鏈自動生成臨床回饋或患者說明。
    會自動判斷 PulsePJ 及病例主病、知識鏈等。
    """
    lines = []
    for step in reasoning_chain:
        label = step.get("step", "")
        reason = step.get("reason", "")
        hits = step.get("top_hits", [])
        lines.append(f"【{label}】{reason}")
        if hits:
            first = hits[0]
            # 支援病例與脈象知識庫 (PulsePJ) 統一顯示
            llm_struct = first.get("llm_struct", {})
            if "主病" in llm_struct:
                main = llm_struct["主病"]
                if isinstance(main, list) and main and isinstance(main[0], (list, tuple)):
                    lines.append(f"→ 主要建議：{main[0][0]}（權重{main[0][1]}）")
                elif isinstance(main, str):
                    lines.append(f"→ 主要建議：{main}")
            # 輸出知識鏈摘要（若為PulsePJ且有知識鏈）
            knowledge = llm_struct.get("知識鏈")
            if knowledge:
                lines.append(f"知識鏈說明：{knowledge}")
    return "\n".join(lines)
