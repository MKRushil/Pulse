# -*- coding: utf-8 -*-
from __future__ import annotations
import chromadb
from scbr.scbr_config import settings

def get_client():
    # Chroma 0.5+ 正確用法：PersistentClient
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)

def ensure_collections():
    """
    確保三個集合一定存在；若不存在就建立。
    避免程式其他地方不小心用了 get_collection() 導致啟動直接掛。
    """
    client = get_client()
    client.get_or_create_collection(settings.CHROMA_COLLECTION_CASE,   metadata={"hnsw:space": "cosine"})
    client.get_or_create_collection(settings.CHROMA_COLLECTION_PULSE,  metadata={"hnsw:space": "cosine"})
    client.get_or_create_collection(settings.CHROMA_COLLECTION_RPCASE, metadata={"hnsw:space": "cosine"})
    return client
