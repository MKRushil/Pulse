# scbr/core/scorer.py
from typing import List, Tuple, Dict

def _minmax(vals: List[float]) -> List[float]:
    if not vals: return []
    mn, mx = min(vals), max(vals)
    if mx == mn: return [0.0]*len(vals)
    return [(v - mn) / (mx - mn) for v in vals]

def unify_scores(vec_results, bm25_results, w_vec: float, w_bm25: float):
    vec_ids = [x[0] for x in vec_results]
    v_sim = _minmax([1.0 - x[1] for x in vec_results])  # 距離→相似度
    bm_ids = [x[0] for x in bm25_results]
    b_norm = _minmax([x[1] for x in bm25_results])      # 分數歸一化

    id_set = list(dict.fromkeys(vec_ids + bm_ids))
    out = []
    for _id in id_set:
        v = v_sim[vec_ids.index(_id)] if _id in vec_ids else 0.0
        b = b_norm[bm_ids.index(_id)] if _id in bm_ids else 0.0
        u = w_vec*v + w_bm25*b
        if _id in vec_ids:
            meta, text = vec_results[vec_ids.index(_id)][2], vec_results[vec_ids.index(_id)][3]
        else:
            meta, text = bm25_results[bm_ids.index(_id)][2], bm25_results[bm_ids.index(_id)][3]
        out.append((_id, float(v), float(b), float(u), meta, text))
    out.sort(key=lambda x: x[3], reverse=True)
    return out
