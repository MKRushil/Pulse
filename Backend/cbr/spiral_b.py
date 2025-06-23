# cbr/spiral_b.py
"""
方案B查詢：個人化查詢（有身分）
以PCD為主，case/pulsePJ為輔，查詢時嵌入 input_type='query'，推理鏈、推理樹完整記錄。
查詢流程：
1. 以個人資訊對 PCD 向量庫查詢（個案主體）
2. 從 PCD 查到個案主病/主訴，再組新查詢對 case 庫語意搜尋補充
3. 再查 pulsePJ 補充脈象資料
4. 全程記錄推理鏈，回傳主結果與推理步驟
"""
import json
from vector.embedding import generate_embedding
from vector.schema import get_weaviate_client
from cbr.utils import sort_cases_by_weight, aggregate_cases, pulsepj_to_struct
from cbr.reasoning_logger import log_reasoning
from cbr.tree_builder import reasoning_chain_to_tree


def spiral_b_query(pid, query_text, top_n=5, log_id=None):
    reasoning_chain = []
    client = get_weaviate_client()

    # 1. 查 PCD
    pcd_hits = []
    results = client.query.get(
        "PCD",
        ["case_id", "timestamp", "summary", "llm_struct"]
    ).with_where({"path": ["case_id"], "operator": "Equal", "valueString": pid}) \
     .with_limit(top_n).do()
    hits = results.get("data", {}).get("Get", {}).get("PCD", [])
    main_symptoms = []
    for item in hits:
        llm_struct = item.get("llm_struct", "{}")
        try:
            llm_struct_json = json.loads(llm_struct)
            main_symptoms.extend([x[0] for x in llm_struct_json.get("主病", [])])
        except Exception: pass
        pcd_hits.append({**item, "llm_struct": llm_struct})
    pcd_hits = sort_cases_by_weight(pcd_hits, key="主病")
    reasoning_chain.append({
        "step": "PCD查詢",
        "input": pid,
        "top_hits": pcd_hits,
        "reason": "以個案身分查詢完整病歷"
    })

    # 2. case查詢（以主病為query）
    case_hits = []
    if main_symptoms:
        q2 = "、".join(main_symptoms)
        case_vec = generate_embedding(q2)
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
                "input": q2,
                "top_hits": case_hits,
                "reason": "主病關鍵字查詢病例庫"
            })

    # 3. PulsePJ查詢（主病為query，格式統一）
    pulse_hits = []
    if main_symptoms:
        q3 = "、".join(main_symptoms)
        pulse_vec = generate_embedding(q3)
        if pulse_vec is not None:
            results = client.query.get(
                "PulsePJ",
                ["id", "neo4j_id", "name", "description", "main_disease", "symptoms", "knowledge_chain"]
            ).with_near_vector({"vector": pulse_vec.tolist(), "certainty": 0.0}) \
             .with_limit(top_n).do()
            hits = results.get("data", {}).get("Get", {}).get("PulsePJ", [])
            for item in hits:
                pulse_hits.append(pulsepj_to_struct(item))
            reasoning_chain.append({
                "step": "PulsePJ查詢",
                "input": q3,
                "top_hits": pulse_hits,
                "reason": "主病關鍵字查詢脈象庫（知識型資料庫）"
            })

    # 4. 聚合與紀錄
    combined = aggregate_cases(pcd_hits, case_hits, pulse_hits)
    tree = reasoning_chain_to_tree(reasoning_chain)
    if log_id:
        log_reasoning(log_id, reasoning_chain, tree=tree)
    return {
        "results": {"PCD": pcd_hits, "case": case_hits, "PulsePJ": pulse_hits, "all": combined},
        "reasoning_chain": reasoning_chain,
        "tree": tree
    }
