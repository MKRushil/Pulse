# scbr/core/search_engine.py
from .scorer import unify_scores

class SearchEngine:
    def __init__(self, repo_case, repo_pulse, repo_rpcase, w_vec: float, w_bm25: float):
        self.repo_case, self.repo_pulse, self.repo_rpcase = repo_case, repo_pulse, repo_rpcase
        self.w_vec, self.w_bm25 = w_vec, w_bm25

    def search_best(self, query: str, k: int = 8):
        pools = []
        for name, repo in [("Case", self.repo_case), ("PulsePJV", self.repo_pulse), ("RPCase", self.repo_rpcase)]:
            vec, bm = repo.hybrid_search(query, k=k)
            merged = unify_scores(vec, bm, self.w_vec, self.w_bm25)
            for r in merged:
                pools.append((name, *r))  # (class, id, v, b, u, meta, text)
        pools.sort(key=lambda x: x[4], reverse=True)
        best = pools[0] if pools else None
        return best, pools[:k]
