# Backend/scbr/knowledge/chroma_client.py
from typing import List, Dict, Any, Tuple
import chromadb
from chromadb.config import Settings
from ..llm.client import EmbeddingClient

class ChromaRepo:
    """
    In-process Chroma（duckdb+parquet）客戶端，支援持久化。
    """
    def __init__(self, persist_dir: str, collection: str, embed: EmbeddingClient):
        # 建立 in-process client（持久化目錄）
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_dir
        ))
        self.collection = self.client.get_or_create_collection(collection)
        self.embed = embed

    def add_docs(self, docs: List[Dict[str, Any]]):
        """
        docs: [{"id": str, "text": str, "meta": dict}, ...]
        """
        if not docs:
            return
        ids = [d["id"] for d in docs]
        texts = [d["text"] for d in docs]
        metas = [d.get("meta", {}) for d in docs]
        embs = self.embed.embed(texts)
        self.collection.add(ids=ids, documents=texts, metadatas=metas, embeddings=embs)
        # in-process 模式下，新增/刪除後會自動寫入 persist_directory

    def search_vector(self, query: str, k: int = 10) -> List[Tuple[str, float, Dict[str, Any], str]]:
        qv = self.embed.embed([query])[0]
        res = self.collection.query(
            query_embeddings=[qv],
            n_results=k,
            include=["metadatas","documents","distances"]
        )
        out = []
        ids = res.get("ids", [[]])[0]
        if not ids:
            return out
        for i, _id in enumerate(ids):
            dist = float(res["distances"][0][i])  # 0~1，越小越近
            meta = res["metadatas"][0][i]
            doc = res["documents"][0][i]
            out.append((_id, dist, meta, doc))
        return out
