# Backend/scbr/knowledge/bm25_index.py

import math
from collections import Counter, defaultdict
from typing import List, Dict, Tuple

class BM25Index:
    """
    簡易版 BM25 (in-memory)
    建立時需要整份 corpus 的文件、ids 與 meta
    之後可用 search(query) 進行檢索
    """

    def __init__(self, docs: List[str], ids: List[str], metas: List[Dict]):
        self.docs, self.ids, self.metas = docs, ids, metas
        self.N = len(docs)
        self.avgdl = sum(len(d.split()) for d in docs) / max(self.N, 1)

        # 計算 document frequency (df)
        self.df = defaultdict(int)
        for d in docs:
            for t in set(d.split()):
                self.df[t] += 1

    def _score(self, q_tokens: List[str], d_tokens: List[str], k1=1.5, b=0.75):
        """
        計算單一文件與 query 的 BM25 分數
        """
        freq = Counter(d_tokens)
        dl = len(d_tokens)
        score = 0.0
        for t in q_tokens:
            if t not in self.df:
                continue
            # idf
            idf = math.log((self.N - self.df[t] + 0.5) / (self.df[t] + 0.5) + 1)
            # bm25
            score += idf * (freq[t] * (k1 + 1)) / (
                freq[t] + k1 * (1 - b + b * dl / self.avgdl)
            )
        return score

    def search(self, query: str, k: int = 10) -> List[Tuple[str, float, Dict, str]]:
        """
        輸入 query 字串，回傳前 k 筆結果
        回傳格式: (id, bm25_score, meta, doc_text)
        """
        q_tokens = query.split()
        scored = []
        for i, d in enumerate(self.docs):
            s = self._score(q_tokens, d.split())
            if s > 0:
                scored.append((self.ids[i], float(s), self.metas[i], d))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
