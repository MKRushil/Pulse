# scbr/core/metrics.py
import numpy as np

def compute_CMS(problem_accu: str, topk):
    if not topk: return 0.0
    u = np.array([x[4] for x in topk[:5]])
    return float(0.6*u.max() + 0.4*u.mean())

def compute_RCI(turns, current_answer: str):
    prev = ""
    for t in reversed(turns):
        if t["role"]=="assistant":
            prev = t["content"]; break
    if not prev: return 0.5
    tok = lambda s: set(s.lower().split())
    inter = len(tok(prev) & tok(current_answer))
    uni = len(tok(prev) | tok(current_answer)) or 1
    return float(inter/uni)

def update_SALS(state, sid: str, cms: float, rci: float):
    prev = state.get(sid, 0.0)
    now = prev + 0.1 + 0.2*cms + 0.2*rci
    state[sid] = max(0.0, min(1.0, now))
    return float(state[sid])
