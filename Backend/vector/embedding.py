# vector/embedding.py
"""
模組說明：
- 負責將文字資料送到 NVIDIA embedding API，取得語意向量
- 由 config.py 控制 api_key, base_url, model_name
- 支援 input_type ('passage' 用於資料建庫，'query' 用於查詢)
- 回傳 numpy array，可直接用於 Weaviate
"""
from openai import OpenAI
import numpy as np
import logging
from config import EMBEDDING_API_KEY, EMBEDDING_BASE_URL, EMBEDDING_MODEL_NAME

# 初始化 NVIDIA OpenAI 兼容 client
client = OpenAI(
    api_key=EMBEDDING_API_KEY,
    base_url=EMBEDDING_BASE_URL
)

def generate_embedding(text: str, input_type: str = "passage"):
    """
    產生文字語意向量
    :param text: 要嵌入的內容（str）
    :param input_type: 'passage'（資料建庫）或 'query'（查詢）
    :return: numpy array (float32)
    """
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL_NAME,
            input=[text],
            extra_body={"input_type": input_type}
        )
        emb = response.data[0].embedding
        return np.array(emb, dtype=np.float32)
    except Exception as e:
        logging.error("產生嵌入向量失敗: %s, text: %s", str(e), text)
        print(f"[Embedding] 產生嵌入失敗: {e}")
        return None
