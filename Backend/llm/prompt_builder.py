# llm/prompt_builder.py
"""
中醫輔助診斷 Prompt 組裝模組
---
支援：
- 單步驟（summary + 三步驟診斷）
- 兩步驟 Chain-of-Thought（條列摘要 → 臨床推理/權重/說明）
- 可加自定進階欄位/多模式切換
所有內容皆繁體中文設計。
"""

def build_prompt_single_step(summary: str):
    """
    傳統單步 prompt，summary + 三步驟診斷（摘要→主次病→推理說明）
    """
    return f"""
請根據以下病歷內容，依照臨床標準流程，分三步驟處理，**回覆全部使用繁體中文**：

{summary}

---
**步驟一：語意摘要**
請以醫案專業語言簡要摘要此病例症狀與發展過程。

**步驟二：主病/次病與權重萃取**
請根據摘要，列出主病（可能為1項或多項，請使用標準中醫證型/現代病名），次病（如有）。
每項請用以下格式：
- 主病：{{病名1}}（權重0.8），{{病名2}}（權重0.5）
- 次病：{{病名1}}（權重0.3）

**步驟三：推理說明**
請說明權重分配與主次病判斷依據，務必引用現病史內容佐證推論。

---
**規範：**  
1. 所有內容皆用繁體中文，勿產生簡體。  
2. 權重請用0~1小數點（如0.7），主病權重應大於次病。  
3. 回覆格式務必依照上述步驟區分。
"""

def build_prompt_stage1(summary: str):
    """
    Chain Step 1：請 LLM 條列組裝完整病例摘要（不做診斷）
    """
    return f"""
請根據以下原始病例資料，彙整所有內容（主訴、現病史、望診、問診、脈診等），
以專業醫案格式條列與摘要，所有內容請用繁體中文。

【原始資料】
{summary}

---
請條列整理：
- 性別、年齡、姓名
- 主訴
- 現病史
- 望診（體型、臉色、眼部、皮膚…）
- 問診（睡眠、精神、症狀、其它）
- 脈診（六部脈/脈象）

請勿診斷，僅做摘要。
"""

def build_prompt_stage2(abstract: str):
    """
    Chain Step 2：請 LLM 執行主病/次病/權重推理，結構化回答
    """
    return f"""
請根據以下病例摘要內容，執行臨床推理，判斷主病、次病及權重，並以繁體中文說明推理過程。

【病例摘要】
{abstract}

---
請分三步驟作答：
1. 主病與次病條列如下（每行一項）：
- 風濕痺阻（權重0.8）
- 血虛痺阻（權重0.2）
（主病請列在前面，次病列在後，如無可略）
2. 詳細解釋主病/次病與權重分配依據，必須引用摘要內容
3. 結論與臨床建議

**回覆格式請務必與本步驟說明一致，內容全為繁體中文。**
"""

def build_integrated_prompt(query_text: str, case_hits: list, pulse_hits: list):
    """
    高級：組合「用戶問題」+ 案例摘要 + 脈象知識，輸出 AI 推理整合 prompt
    """
    # 案例
    case_block = ""
    if case_hits:
        case_block = "【相似病例摘要】\n" + "\n".join([
            f"- {c.get('summary','')}" for c in case_hits[:3]
        ])
    # 脈象
    pulse_block = ""
    if pulse_hits:
        pulse_block = "【相關脈象知識】\n" + "\n".join([
            f"- {p.get('name','')}：{p.get('description','')}；主病：{p.get('main_disease','')}" for p in pulse_hits[:3]
        ])
    prompt = f"""
請根據下列資訊，依中醫臨床推理習慣，進行專業繁體中文診斷說明：

【使用者問題】
{query_text}

{case_block}

{pulse_block}

---
請結合臨床證據與脈象知識，結構化回答
- 可能證型
- 鑑別思路
- 推薦治療建議
"""
    return prompt

# # ↓↓↓ 若你原本還有其他組裝 prompt 的 function，也可以保留 ↓↓↓

# def build_prompt_from_case(case: dict):
#     """
#     舊版：將病例原始欄位組合成摘要
#     """
#     basic = case.get('basic', {})
#     inspection = case.get('inspection', {})
#     inquiry = case.get('inquiry', {})
#     pulse = case.get('pulse', {})
#     # ...根據原有欄位拼裝...
#     summary = f"""姓名：{basic.get('name','')}，性別：{basic.get('gender','')}，年齡：{basic.get('age','')}
# 主訴：{inquiry.get('mainSymptom','')}
# 現病史：{inquiry.get('otherSymptom','')}
# 望診：{inspection}
# 問診：{inquiry}
# 脈診：{pulse}
# """
#     return summary

# 你可以再加更多自定義模板 function，請勿隨意刪除老 function，以利日後擴展與維護！

