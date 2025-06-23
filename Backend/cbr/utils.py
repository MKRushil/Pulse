# cbr/utils.py
"""
共用推理工具模組：
- 排序、聚合、去重
- 支援分支排序、聚合權重、自訂去重策略
- 新增 pulsepj_to_struct()：將脈象知識庫物件 mapping 成統一格式
"""
import json

def sort_cases_by_weight(cases, key="主病", weight_idx=1):
    """
    依據指定 llm_struct 欄位（如主病）權重排序
    cases: list[dict]，每個 case 需含 llm_struct 欄位
    key: 欲排序主體（如"主病"或"次病"）
    weight_idx: 權重欄位索引（預設 1）
    """
    def get_weight(item):
        llm_struct = item.get("llm_struct", {})
        try:
            if isinstance(llm_struct, str):
                llm_struct = json.loads(llm_struct)
            weights = [float(w[weight_idx]) for w in llm_struct.get(key, []) if len(w) > weight_idx]
            return max(weights) if weights else 0
        except Exception:
            return 0
    return sorted(cases, key=get_weight, reverse=True)

def deduplicate_cases(cases):
    """
    依據 case_id 去重
    """
    seen = set()
    unique = []
    for c in cases:
        cid = c.get("case_id")
        if cid not in seen:
            seen.add(cid)
            unique.append(c)
    return unique

def aggregate_cases(*case_lists):
    """
    合併多個查詢結果後去重，並以主病權重排序
    """
    all_cases = []
    for l in case_lists:
        all_cases.extend(l)
    return sort_cases_by_weight(deduplicate_cases(all_cases))

# 新增：脈象知識庫物件 mapping function

def pulsepj_to_struct(pulse_item):
    """
    將 PulsePJ（脈象知識庫物件）mapping 成與病例資料一致格式，方便統一回傳給前端或 LLM
    產出 summary、llm_struct（主病、症狀、知識鏈）等欄位
    """
    summary = f"{pulse_item.get('name','')}：{pulse_item.get('description','')}；主病：{pulse_item.get('main_disease','')}；現代病症：{','.join(pulse_item.get('symptoms',[]))}"
    llm_struct = {
        "主病": [(pulse_item.get("main_disease",""), 1)],
        "症狀": pulse_item.get("symptoms",[]),
        "知識鏈": pulse_item.get("knowledge_chain","")
    }
    return {
        "case_id": pulse_item.get("id", pulse_item.get("neo4j_id", "")),
        "summary": summary,
        "llm_struct": llm_struct,
        **pulse_item   # 保留所有原始欄位，前端若需展開可直接使用
    }
