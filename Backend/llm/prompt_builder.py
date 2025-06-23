# llm/prompt_builder.py

"""
Prompt 組裝模組：專責產生送給 LLM 的多種 prompt 需求
包含：
1. build_prompt_from_case           —— 標準病歷摘要→診斷（主病/次病/權重）
2. build_spiral_prompt_from_cases   —— 多案例CBR比對推理
3. build_custom_prompt              —— 輸入自訂指令+摘要
4. prompt_template                  —— 主格式外部化，方便之後用 template.txt 管理
"""

def build_prompt_from_case(case: dict, summary: str) -> str:
    """
    根據單一病歷＋摘要產生標準診斷prompt，明確請LLM給主/次病和權重與理由
    """
    return prompt_template.format(summary=summary)

# 主模板（可隨時調整、未來可放外部檔讀入）
prompt_template = '''
你是一位臨床中醫師。根據下列病歷摘要，請執行「辨證論治」：
1. 列出主要病症（主病）、次要病症（次病）。
2. 為每個病症分配 0-1 的權重（愈關鍵愈高，並附在病症後括號內，例：腹痛(0.8)）。
3. 說明你如何從脈象、症狀等推斷主病與次病（分點列出理由）。

【病歷摘要】
{summary}

【請依下列格式回答】
主病：
- XXX（權重）
- ...
次病：
- XXX（權重）
- ...
推理說明：
- ...
'''

def build_spiral_prompt_from_cases(cases: list, query_case: dict) -> str:
    """
    給 LLM 多個病例摘要與查詢病例，請模型做CBR關聯推理
    """
    blocks = []
    for i, c in enumerate(cases):
        # 假設每個 c 都有 'summary' 欄位
        blocks.append(f"【案例{i+1}】\n" + c["summary"])
    # query_case 用 generate_case_summary 產生摘要後填入
    blocks.append(f"【查詢病例】\n" + query_case["summary"])
    prompt = "\n\n".join(blocks) + "\n請根據上述案例推理最相關的主病與診斷理由，並依主病給出權重與分類依據。"
    return prompt


def build_custom_prompt(summary: str, instruction: str) -> str:
    """
    輸入摘要+自訂指令產生自由風格prompt
    """
    return f"{instruction}\n\n【病歷摘要】\n{summary}"
