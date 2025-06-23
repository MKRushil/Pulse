# cbr/tree_builder.py
"""
推理樹（Tree structure）自動生成工具
- 支援單層/多層/多分支推理樹
- 可直接從 reasoning_chain 自動生成
- 每個節點可自訂欄位（如: label, reason, input, top_hits, children, meta）
- 適合後端驗證、前端可互動流程/樹狀圖可視化
"""

def reasoning_chain_to_tree(reasoning_chain):
    """
    將推理鏈 reasoning_chain 轉換為推理樹（單層、主流程樹）
    - 若 reasoning_chain 本身不含 children 分支，會組成一條主路徑
    - 若某步有 branches，可支援巢狀遞迴
    """
    def node_from_step(step):
        # 支援多分支遞迴（進階可自訂）
        children = []
        if "branches" in step and step["branches"]:
            for branch in step["branches"]:
                children.append(node_from_step(branch))
        return {
            "label": step.get("step", ""),
            "reason": step.get("reason", ""),
            "input": step.get("input", ""),
            "top_hits": step.get("top_hits", []),
            "children": children
        }
    # 主結構
    tree = {"label": "推理流程", "children": [node_from_step(step) for step in reasoning_chain]}
    return tree

# --- 使用範例 ---
if __name__ == "__main__":
    # 模擬一份帶有分支的推理鏈
    chain = [
        {
            "step": "case查詢",
            "reason": "主病topN語意查詢",
            "input": "腹痛、失眠",
            "top_hits": [],
            "branches": [
                {
                    "step": "pulsePJ查詢",
                    "reason": "同主病查詢脈象",
                    "input": "腹痛、失眠",
                    "top_hits": []
                }
            ]
        },
        {
            "step": "擴充分支",
            "reason": "多主病多分支查詢",
            "input": "頭痛",
            "top_hits": []
        }
    ]
    t = reasoning_chain_to_tree(chain)
    import json
    print(json.dumps(t, ensure_ascii=False, indent=2))
