# -*- coding: utf-8 -*-
"""
以使用者問題測 PulsePJ：
1) BM25（優先 bm25_cjk；無則 bm25_text）
2) 向量（nv-embedqa-e5-v5, input_type="query", 1024 維）
3) Hybrid（有向量就融合；無向量退化為純 sparse）
並依 pid 去重輸出。

環境變數（或 Backend/.env）：
  NVIDIA_API_KEY=你的key
  WEAVIATE_URL=http://localhost:8080
  WV_API_KEY=key-admin
"""

import os, requests
from typing import List, Dict, Any

def load_dotenv_if_any():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
            print(f"[INFO] .env loaded from {env_path}")
        except Exception:
            pass
load_dotenv_if_any()

def get_env(name: str, default=""):
    v = os.getenv(name, default)
    return v.strip().strip('"').strip("'") if isinstance(v, str) else v

NVIDIA_API_KEY = "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"
WEAVIATE_URL   = get_env("WEAVIATE_URL", "http://localhost:8080")
WV_API_KEY     = get_env("WV_API_KEY", "key-admin")

try:
    import weaviate
    client = weaviate.Client(url=WEAVIATE_URL, additional_headers={"Authorization": f"Bearer {WV_API_KEY}"})
except Exception as e:
    raise SystemExit("請先安裝 weaviate-client：pip install weaviate-client") from e

def embed_query(text: str) -> List[float]:
    if not NVIDIA_API_KEY:
        raise RuntimeError("未找到 NVIDIA_API_KEY（請設定於 Backend/.env）")
    r = requests.post(
        "https://integrate.api.nvidia.com/v1/embeddings",
        headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
        json={"model":"nvidia/nv-embedqa-e5-v5", "input":[text], "input_type":"query"},
        timeout=60
    )
    if not r.ok:
        print("[ERROR] NVIDIA response:", r.status_code, r.text); r.raise_for_status()
    vec = r.json()["data"][0]["embedding"]
    if len(vec) != 1024:
        raise ValueError(f"Embedding 維度 {len(vec)} != 1024")
    return vec

def dedupe_by_pid(hits: List[Dict[str, Any]]):
    seen, out = set(), []
    for h in hits or []:
        pid = h.get("pid")
        if pid and pid not in seen:
            seen.add(pid); out.append(h)
    return out

def pretty_print(title: str, hits: List[Dict[str, Any]], extras: List[str]):
    hits = dedupe_by_pid(hits)
    print(f"\n=== {title}（Top {len(hits)}）===")
    if not hits: print("(無結果)"); return
    for i, h in enumerate(hits, 1):
        pid = h.get("pid")
        name = h.get("name")
        cat  = h.get("category")
        md   = h.get("main_disease")
        add  = (h.get("_additional") or {})
        extra = " | ".join(f"{k}={add[k]}" for k in extras if k in add)
        print(f"[{i}] pid={pid} | 名稱={name} | 類別={cat} | 主病={md}" + (f" || {extra}" if extra else ""))

def run_all(question: str, k: int = 5, alpha: float = 0.5):
    print(f"\n[QUERY] {question}")

    # 欄位選擇
    props = ["pid","name","category","main_disease"]
    # BM25 欄位（有 bm25_cjk 就用它）
    bm25_props = ["bm25_text"]
    try:
        sch = client.schema.get()
        pset = {p["name"] for c in sch.get("classes", []) if c["class"]=="PulsePJ" for p in c.get("properties", [])}
        if "bm25_cjk" in pset: bm25_props = ["bm25_cjk"]
    except Exception:
        pass

    # 1) BM25
    try:
        r1 = client.query.get("PulsePJ", props)\
            .with_bm25(question, properties=bm25_props)\
            .with_limit(k)\
            .with_additional(["score"])\
            .do()
        h1 = r1.get("data",{}).get("Get",{}).get("PulsePJ",[])
    except Exception as e:
        print("[BM25] 查詢失敗：", e); h1=[]
    pretty_print(f"BM25（props={bm25_props}）", h1, ["score"])

    # 2) 向量
    h2, qv = [], None
    try:
        qv = embed_query(question)
        r2 = client.query.get("PulsePJ", props)\
            .with_near_vector({"vector": qv})\
            .with_limit(k)\
            .with_additional(["distance"])\
            .do()
        h2 = r2.get("data",{}).get("Get",{}).get("PulsePJ",[])
    except Exception as e:
        print("[Vector] 查詢失敗：", e)
    pretty_print("向量（nearVector）", h2, ["distance"])

    # 3) Hybrid
    h3 = []
    try:
        q = client.query.get("PulsePJ", props).with_limit(k).with_additional(["score","distance"])
        if qv: q = q.with_hybrid(question, alpha=alpha, vector=qv)
        else:  q = q.with_hybrid(question, alpha=1.0)
        r3 = q.do()
        h3 = r3.get("data",{}).get("Get",{}).get("PulsePJ",[])
    except Exception as e:
        print("[Hybrid] 查詢失敗：", e)
    pretty_print(f"Hybrid（alpha={alpha}）", h3, ["score","distance"])


if __name__ == "__main__":
    try:
        q = input("請輸入脈象相關問題（Enter 用預設）：").strip()
    except Exception:
        q = ""
    if not q:
        q = "最近常常畏寒肢冷、關節僵硬，可能是哪一類脈象？"
    run_all(q, k=5, alpha=0.5)



