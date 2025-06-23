# cbr/spiral_a.py
"""
方案A查詢：無身分查詢（匿名查詢），對Case和pulsePJ語意查詢，
查詢時嵌入 input_type='query'，聚合推理鏈，支援可視化。
查詢流程：
1. 使用者輸入症狀、摘要或主訴
2. 先對 case 向量庫做語意查詢（topN），記錄推理鏈
3. 再對 pulsePJ 脈象向量庫查詢（補充脈象關聯），記錄推理鏈
4. 回傳主要查詢結果與推理鏈（可視化用）
"""
import json
from vector.embedding import generate_embedding
from vector.schema import get_weaviate_client
from cbr.utils import sort_cases_by_weight, aggregate_cases, pulsepj_to_struct
from cbr.reasoning_logger import log_reasoning
from cbr.tree_builder import reasoning_chain_to_tree


def spiral_a_query(query_text, top_n=5, log_id=None):
    reasoning_chain = []
    client = get_weaviate_client()

    # 1. 查 case
    case_vec = generate_embedding(query_text)
    case_hits = []
    if case_vec is not None:
        results = client.query.get(
            "Case",
            ["case_id", "timestamp", "summary", "llm_struct"]
        ).with_near_vector({"vector": case_vec.tolist(), "certainty": 0.0}) \
         .with_limit(top_n).do()
        hits = results.get("data", {}).get("Get", {}).get("Case", [])
        for item in hits:
            llm_struct = item.get("llm_struct", "{}")
            try: llm_struct = json.loads(llm_struct)
            except: pass
            case_hits.append({**item, "llm_struct": llm_struct})
        case_hits = sort_cases_by_weight(case_hits, key="主病")
        reasoning_chain.append({
            "step": "case查詢",
            "input": query_text,
            "top_hits": case_hits,
            "reason": "症狀語意查詢病例庫"
        })

    # 2. 查 pulsePJ，mapping 統一格式
    pulse_hits = []
    if case_vec is not None:
        results = client.query.get(
            "PulsePJ",
            ["id", "neo4j_id", "name", "description", "main_disease", "symptoms", "knowledge_chain"]
        ).with_near_vector({"vector": case_vec.tolist(), "certainty": 0.0}) \
         .with_limit(top_n).do()
        hits = results.get("data", {}).get("Get", {}).get("pulsePJ", [])
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
    return {
        "results": {"case": case_hits, "PulsePJ": pulse_hits, "all": combined},
        "reasoning_chain": reasoning_chain,
        "tree": tree
    }
