# scbr/core/spiral_engine.py
from .dialog_manager import DialogManager
from .search_engine import SearchEngine
from ..llm.client import LLMClient
from ..llm.prompts import SYSTEM_DIAG, build_user_prompt
from .metrics import compute_CMS, compute_RCI, update_SALS

class SpiralEngine:
    def __init__(self, dm: DialogManager, se: SearchEngine, llm: LLMClient):
        self.dm, self.se, self.llm = dm, se, llm
        self.sals_state = {}

    def step(self, sid: str, user_query: str):
        self.dm.append_user(sid, user_query)
        problem_accu = self.dm.get_problem_accu(sid)

        best, topk = self.se.search_best(problem_accu, k=8)

        def _snip(x):
            cls, _id, v, b, u, meta, text = x
            return f"[{cls}:{_id}] u={u:.2f}\n{text[:350]}"
        snippets = "\n\n".join(_snip(x) for x in topk[:3])
        pulse_links = "(脈名→常見症狀→候選病證，由 PulsePJV meta 組裝)"
        usr = build_user_prompt(problem_accu, snippets, pulse_links)
        llm_out = self.llm.chat(SYSTEM_DIAG, usr)

        cms = compute_CMS(problem_accu, topk)
        rci = compute_RCI(self.dm.sessions[sid]["turns"], llm_out)
        sals = update_SALS(self.sals_state, sid, cms, rci)

        turn = self.dm.turn_index(sid)+1
        chosen_id = best[1] if best else None
        confidence = float(best[4]) if best else 0.0
        scores = {
            "vector": float(best[2]) if best else 0.0,
            "bm25": float(best[3]) if best else 0.0,
            "unified": confidence,
        }
        return {
            "session_id": sid,
            "turn_index": turn,
            "diagnosis": llm_out,
            "suggestions": "（已含於 diagnosis）",
            "chosen_case_id": chosen_id,
            "confidence": confidence,
            "scores": scores,
            "metrics": {"CMS": cms, "RCI": rci, "SALS": sals},
            "trace": {
                "topk": [dict(cls=x[0], id=x[1], u=x[4]) for x in topk],
                "problem_accu": problem_accu
            }
        }
