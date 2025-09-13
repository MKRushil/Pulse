# cbr/spiral.py
"""
單一路由查詢（匿名查詢），對 Case 與 PulsePJ 語意查詢，
查詢時嵌入 input_type='query'，聚合推理鏈，支援可視化。
加入 logging，便於追蹤查詢與推理流程
查詢流程：
1. 使用者輸入症狀、摘要或主訴
2. 先對 case 向量庫做語意查詢（topN），記錄推理鏈
3. 再對 pulsePJ 脈象向量庫查詢（補充脈象關聯），記錄推理鏈
4. 回傳主要查詢結果與推理鏈（可視化用）
"""
import json
import logging
from vector.embedding import generate_embedding
from vector.schema import get_weaviate_client
from cbr.utils import sort_cases_by_weight, aggregate_cases, pulsepj_to_struct
from cbr.reasoning_logger import log_reasoning
from cbr.tree_builder import reasoning_chain_to_tree
from llm.prompt_builder import build_integrated_prompt
from llm.llm_executor import run_llm_diagnosis

logging.basicConfig(level=logging.INFO)

def spiral_query(query_text, top_n=5, log_id=None):
    reasoning_chain = []
    client = get_weaviate_client()

    # 1. 查 case
    case_vec = generate_embedding(query_text)
    # 兼容 list/numpy.ndarray 兩種回傳型別
    def _to_list(v):
        try:
            return v.tolist()  # numpy
        except Exception:
            return list(v) if isinstance(v, (list, tuple)) else v
    case_hits = []
    if case_vec is not None:
        results = client.query.get(
            "Case",
            ["case_id", "timestamp", "summary", "llm_struct"]
        ).with_near_vector({"vector": _to_list(case_vec), "certainty": 0.0}) \
         .with_limit(top_n).do()
        hits = results.get("data", {}).get("Get", {}).get("Case", [])
        logging.info("Case查詢 hits 數量: %d", len(hits))
        for item in hits:
            llm_struct = item.get("llm_struct", "{}")
            try: llm_struct = json.loads(llm_struct)
            except Exception as e:
                logging.warning("Case llm_struct解析錯誤: %s", str(e))
            case_hits.append({**item, "llm_struct": llm_struct})
        case_hits = sort_cases_by_weight(case_hits, key="主病")
        reasoning_chain.append({
            "step": "Case查詢",
            "input": query_text,
            "top_hits": case_hits,
            "reason": "症狀語意查詢病例庫"
        })

    # 2. 查 PulsePJ，mapping 統一格式
    pulse_hits = []
    if case_vec is not None:
        results = client.query.get(
            "PulsePJ",
            ["name", "description", "main_disease", "neo4j_id"]
        ).with_near_vector({"vector": _to_list(case_vec), "certainty": 0.0}) \
         .with_limit(top_n).do()
        hits = results.get("data", {}).get("Get", {}).get("PulsePJ", [])
        logging.info("PulsePJ查詢 hits 數量: %d", len(hits))
        for item in hits:
            pulse_hits.append(pulsepj_to_struct(item))
        reasoning_chain.append({
            "step": "PulsePJ查詢",
            "input": query_text,
            "top_hits": pulse_hits,
            "reason": "症狀語意查詢脈象庫（知識型資料庫）"
        })

    # 3. 聚合與紀錄
    combined = aggregate_cases(case_hits, pulse_hits)
    tree = reasoning_chain_to_tree(reasoning_chain)
    if log_id:
        log_reasoning(log_id, reasoning_chain, tree=tree)
    prompt = build_integrated_prompt(query_text, case_hits, pulse_hits)
    llm_output, llm_struct = run_llm_diagnosis(prompt)
    logging.info("spiral 查詢完成，Case:%d, PulsePJ:%d, 聚合: %d", len(case_hits), len(pulse_hits), len(combined))
    return {
        "results": {"case": case_hits, "PulsePJ": pulse_hits, "all": combined},
        "reasoning_chain": reasoning_chain,
        "tree": tree,
        "dialog": llm_output,      # 給前端AI整合推理結果
        "llm_struct": llm_struct   # 給前端結構化可視化推理用
    }


def run(question: str, patient_ctx: dict | None = None):
    """
    與 Backend/main.py 對接的入口函式。
    目前忽略 patient_ctx，直接以問題文字執行語意檢索與推理整合。
    """
    return spiral_query(question, top_n=5)

