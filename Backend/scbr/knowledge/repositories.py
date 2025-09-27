# scbr/knowledge/repositories.py
from typing import List, Dict, Tuple
from .chroma_client import ChromaRepo
from .bm25_index import BM25Index

class HybridRepo:
    def __init__(self, chroma: ChromaRepo, bm25: BM25Index):
        self.chroma, self.bm25 = chroma, bm25
    def hybrid_search(self, query: str, k=10):
        return self.chroma.search_vector(query, k=k), self.bm25.search(query, k=k)
