# scbr/llm/client.py
from typing import List, Optional
import numpy as np
import httpx

class EmbeddingClient:
    def __init__(self, model_name: str, base_url: str, api_key: Optional[str]):
        self.model_name, self.base_url, self.api_key = model_name, base_url, api_key

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            # 方便本地跑通：無金鑰時給隨機向量
            return [np.random.rand(1024).tolist() for _ in texts]
        headers = {"Authorization": f"Bearer {self.api_key}"}
        # Nvidia Integrate API 標準 body
        body = {"model": self.model_name, "input": texts}
        r = httpx.post(f"{self.base_url}/embeddings", headers=headers, json=body, timeout=60)
        r.raise_for_status()
        data = r.json()
        return [item["embedding"] for item in data["data"]]

class LLMClient:
    def __init__(self, model_name: str, base_url: str, api_key: Optional[str]):
        self.model_name, self.base_url, self.api_key = model_name, base_url, api_key

    def chat(self, system: str, user: str) -> str:
        if not self.api_key:
            # 沒金鑰：直接回傳 placeholder
            return f"[PLACEHOLDER]\n{user[:300]}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {
            "model": self.model_name,
            "messages": [{"role":"system","content":system},{"role":"user","content":user}],
            "temperature": 0.3,
        }
        r = httpx.post(f"{self.base_url}/chat/completions", headers=headers, json=body, timeout=120)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
