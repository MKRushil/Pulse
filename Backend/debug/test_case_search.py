# -*- coding: utf-8 -*-
"""
test_case_search.py
以單一使用者問題，同時測 Case 類的：
1) BM25（優先 bm25_cjk；若無則 bm25_text）
2) 向量（nv-embedqa-e5-v5, input_type="query", 1024 維）
3) Hybrid（有向量就融合；無向量退化為純 sparse）
並在輸出前依 case_id 去重。

環境變數（或 Backend/.env）：
  NVIDIA_API_KEY=xxxx
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

def get_env(name: str, default: str = "") -> str:
    val = os.getenv(name, default)
    if isinstance(val, str): val = val.strip().strip('"').strip("'")
    return val

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
        raise RuntimeError(
            "未找到 NVIDIA_API_KEY（請在 Backend/.env 或系統環境變數設定）。\n"
            "例如 Backend/.env：\nNVIDIA_API_KEY=你的key"
        )
    r = requests.post(
        "https://integrate.api.nvidia.com/v1/embeddings",
        headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
        json={"model": "nvidia/nv-embedqa-e5-v5", "input": [text], "input_type": "query"},
        timeout=60
    )
    if not r.ok:
        print("[ERROR] NVIDIA response:", r.status_code, r.text)
        r.raise_for_status()
    vec = r.json()["data"][0]["embedding"]
    if len(vec) != 1024:
        raise ValueError(f"Embedding 維度 {len(vec)} != 1024，請確認模型/參數")
    return vec

def safe_len(x) -> int:
    try: return len(x)
    except Exception: return 0

def dedupe_by_case_id(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for h in hits or []:
        cid = h.get("case_id")
        if cid and cid not in seen:
            seen.add(cid); out.append(h)
    return out

def pretty_print(title: str, hits: List[Dict[str, Any]], extras: List[str]):
    hits = dedupe_by_case_id(hits)
    n = safe_len(hits)
    print(f"\n=== {title}（Top {n}）===")
    if not hits:
        print("(無結果)"); return
    for i, h in enumerate(hits, 1):
        cid  = h.get("case_id")
        chief= h.get("chiefComplaint")
        pres = h.get("presentIllness")
        add  = (h.get("_additional") or {})
        extra = " | ".join(f"{k}={add[k]}" for k in extras if k in add)
        print(f"[{i}] case_id={cid} | 主訴={chief} | 現病史={pres}" + (f" || {extra}" if extra else ""))

def run_all(question: str, k: int = 5, alpha: float = 0.5):
    print(f"\n[QUERY] 使用者問題：{question}")

    # --- 檢查要用哪個欄位做 BM25（bm25_cjk > bm25_text）
    bm25_props = ["bm25_text"]
    try:
        sch = client.schema.get()
        props = {p["name"] for c in sch.get("classes", []) if c["class"] == "Case" for p in c.get("properties", [])}
        if "bm25_cjk" in props: bm25_props = ["bm25_cjk"]
    except Exception:
        pass

    # --- BM25
    try:
        resp_bm25 = client.query.get("Case", ["case_id", "chiefComplaint", "presentIllness"])\
            .with_bm25(question, properties=bm25_props)\
            .with_limit(k)\
            .with_additional(["score"])\
            .do()
        hits_bm25 = resp_bm25.get("data", {}).get("Get", {}).get("Case", [])
    except Exception as e:
        print("[BM25] 查詢失敗：", e); hits_bm25 = []
    pretty_print(f"BM25（props={bm25_props}）", hits_bm25, extras=["score"])

    # --- 向量
    hits_vec, qv = [], None
    try:
        qv = embed_query(question)
        resp_vec = client.query.get("Case", ["case_id", "chiefComplaint", "presentIllness"])\
            .with_near_vector({"vector": qv})\
            .with_limit(k)\
            .with_additional(["distance"])\
            .do()
        hits_vec = resp_vec.get("data", {}).get("Get", {}).get("Case", [])
    except Exception as e:
        print("[Vector] 查詢失敗：", e)
    pretty_print("向量（nearVector）", hits_vec, extras=["distance"])

    # --- Hybrid（有向量就融合；沒有就純 sparse）
    hits_hy = []
    try:
        q = client.query.get("Case", ["case_id", "chiefComplaint", "presentIllness"])\
            .with_limit(k)\
            .with_additional(["score", "distance"])
        if qv: q = q.with_hybrid(question, alpha=alpha, vector=qv)
        else:  q = q.with_hybrid(question, alpha=1.0)
        resp_hy = q.do()
        hits_hy = resp_hy.get("data", {}).get("Get", {}).get("Case", [])
    except Exception as e:
        print("[Hybrid] 查詢失敗：", e)
    pretty_print(f"Hybrid（alpha={alpha}）", hits_hy, extras=["score","distance"])


if __name__ == "__main__":
    try:
        q = input("請輸入病人自己的描述（直接按 Enter 使用預設）：").strip()
    except Exception:
        q = ""
    if not q:
        q = "最近常常失眠而且多夢，晚上容易驚醒，醫師說我左寸的脈有點遲，白天會心悸口乾，該怎麼辦？"
    run_all(q, k=5, alpha=0.5)
