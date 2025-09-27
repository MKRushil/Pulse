# scbr/llm/prompts.py
SYSTEM_DIAG = "你是嚴謹的中醫輔助診斷助手，請結合脈診知識與候選案例輸出：1) 診斷結果 2) 建議。"

def build_user_prompt(problem_accu: str, top_case_snippets: str, pulse_links: str) -> str:
    return f"""問題彙整：
{problem_accu}

候選案例摘要：
{top_case_snippets}

脈診知識連結：
{pulse_links}

請先給【診斷結果】，再給【建議】（作息/飲食/中藥方向），條列清楚。"""
