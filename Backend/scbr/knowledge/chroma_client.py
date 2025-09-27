# scbr/knowledge/chroma_client.py
from typing import List, Dict, Any, Tuple
from chromadb import HttpClient
from ..llm.client import EmbeddingClient

class ChromaRepo:
    def __init__(self, host: str, port: int, collection: str, embed: EmbeddingClient):
        self.client = HttpClient(host=host, port=port)
        self.collection = self.client.get_or_create_collection(collection)
        self.embed = embed

    def add_docs(self, docs: List[Dict[str, Any]]):
        ids = [d["id"] for d in docs]
        texts = [d["text"] for d in docs]
        metas = [d.get("meta", {}) for d in docs]
        embs = self.embed.embed(texts)
        self.collection.add(ids=ids, documents=texts, metadatas=metas, embeddings=embs)

    def search_vector(self, query: str, k: int = 10) -> List[Tuple[str, float, Dict[str, Any], str]]:
        qv = self.embed.embed([query])[0]
        res = self.collection.query(query_embeddings=[qv], n_results=k, include=["metadatas","documents","distances"])
        out = []
        for i, _id in enumerate(res["ids"][0]):
            dist = float(res["distances"][0][i])  # 0~1 距離，越小越近
            meta = res["metadatas"][0][i]
            doc = res["documents"][0][i]
            out.append((_id, dist, meta, doc))
        return out
