# -*- coding: utf-8 -*-
"""
test_dual_hybrid_top1.py
以單一使用者問題，分別對 Weaviate 的 Case 與 PulsePJ 類別做 Hybrid 搜尋，各自列出 Top-1。

需求：
  pip install weaviate-client requests python-dotenv

環境變數（或 Backend/.env）：
  NVIDIA_API_KEY=你的key
  WEAVIATE_URL=http://localhost:8080
  WV_API_KEY=key-admin
"""

import os
import requests
from typing import List, Dict, Any

# --- 讀 .env（若存在） ---
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
    v = os.getenv(name, default)
    return v.strip().strip('"').strip("'") if isinstance(v, str) else v

NVIDIA_API_KEY = "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"
WEAVIATE_URL   = get_env("WEAVIATE_URL", "http://localhost:8080")
WV_API_KEY     = get_env("WV_API_KEY", "key-admin")

# --- 連接 Weaviate ---
try:
    import weaviate
    client = weaviate.Client(
        url=WEAVIATE_URL,
        additional_headers={"Authorization": f"Bearer {WV_API_KEY}"}
    )
except Exception as e:
    raise SystemExit("請先安裝 weaviate-client：pip install weaviate-client") from e

# --- 嵌入（查詢向量，1024 維）---
def embed_query(text: str) -> List[float]:
    if not NVIDIA_API_KEY:
        raise RuntimeError("未找到 NVIDIA_API_KEY，將改用純文本 Hybrid。")
    r = requests.post(
        "https://integrate.api.nvidia.com/v1/embeddings",
        headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
        json={"model":"nvidia/nv-embedqa-e5-v5","input":[text],"input_type":"query"},
        timeout=60
    )
    if not r.ok:
        print("[ERROR] NVIDIA response:", r.status_code, r.text)
        r.raise_for_status()
    vec = r.json()["data"][0]["embedding"]
    if len(vec) != 1024:
        raise ValueError(f"Embedding 維度 {len(vec)} != 1024")
    return vec

# --- 輔助 ---
def props_exist(cls: str, names: List[str]) -> Dict[str, bool]:
    try:
        sch = client.schema.get()
        for c in sch.get("classes", []):
            if c["class"] == cls:
                pset = {p["name"] for p in c.get("properties", [])}
                return {n: (n in pset) for n in names}
    except Exception:
        pass
    return {n: False for n in names}

def print_case(hit: Dict[str, Any], title: str):
    if not hit:
        print(f"\n=== {title}（Top-1）===\n(無結果)")
        return
    add = hit.get("_additional") or {}
    print(f"\n=== {title}（Top-1）===")
    print(f"case_id={hit.get('case_id')}")
    print(f"主訴   ={hit.get('chiefComplaint')}")
    print(f"現病史 ={hit.get('presentIllness')}")
    if "score" in add or "distance" in add:
        print("附加   =", {k: add[k] for k in ["score","distance"] if k in add})

def print_pulse(hit: Dict[str, Any], title: str):
    if not hit:
        print(f"\n=== {title}（Top-1）===\n(無結果)")
        return
    add = hit.get("_additional") or {}
    print(f"\n=== {title}（Top-1）===")
    print(f"pid    ={hit.get('pid')}")
    print(f"名稱   ={hit.get('name')}")
    print(f"類別   ={hit.get('category')}")
    print(f"主病   ={hit.get('main_disease')}")
    if "score" in add or "distance" in add:
        print("附加   =", {k: add[k] for k in ["score","distance"] if k in add})

# --- 核心：對某類別做 Hybrid Top-1 ---
def hybrid_top1_case(query: str, alpha: float = 0.5):
    # 取查詢向量（若無 API key 則 None）
    qv = None
    try:
        qv = embed_query(query)
    except Exception as e:
        print("[Case] 向量不可用，改用純文本 Hybrid。原因：", e)

    # 優先使用 bm25_cjk
    use_cjk = props_exist("Case", ["bm25_cjk"]).get("bm25_cjk", False)

    q = client.query.get("Case", ["case_id","chiefComplaint","presentIllness"])\
        .with_limit(1)\
        .with_additional(["score","distance"])

    # 指定 sparse 欄位（只有 with_hybrid 的文本會用到；weaviate-client 內部取決於版本，若不支援 props 指定也不會報錯）
    if qv:
        q = q.with_hybrid(query, alpha=alpha, vector=qv, properties=["bm25_cjk"] if use_cjk else ["bm25_text"])
    else:
        q = q.with_hybrid(query, alpha=1.0, properties=["bm25_cjk"] if use_cjk else ["bm25_text"])

    resp = q.do()
    hits = resp.get("data",{}).get("Get",{}).get("Case",[])
    return hits[0] if hits else None

def hybrid_top1_pulse(query: str, alpha: float = 0.5):
    qv = None
    try:
        qv = embed_query(query)
    except Exception as e:
        print("[PulsePJ] 向量不可用，改用純文本 Hybrid。原因：", e)

    use_cjk = props_exist("PulsePJ", ["bm25_cjk"]).get("bm25_cjk", False)

    q = client.query.get("PulsePJ", ["pid","name","category","main_disease"])\
        .with_limit(1)\
        .with_additional(["score","distance"])

    if qv:
        q = q.with_hybrid(query, alpha=alpha, vector=qv, properties=["bm25_cjk"] if use_cjk else ["bm25_text"])
    else:
        q = q.with_hybrid(query, alpha=1.0, properties=["bm25_cjk"] if use_cjk else ["bm25_text"])

    resp = q.do()
    hits = resp.get("data",{}).get("Get",{}).get("PulsePJ",[])
    return hits[0] if hits else None

# --- 入口 ---
if __name__ == "__main__":
    try:
        q = input("請輸入病人自己的描述（直接 Enter 用預設）：").strip()
    except Exception:
        q = ""
    if not q:
        q = "最近常常失眠而且多夢，晚上容易驚醒，醫師說我左寸的脈有點遲，白天會心悸口乾，該怎麼辦？"

    # 你可依資料特性微調 alpha（0.4~0.7常見）
    alpha = 0.5

    case_hit = hybrid_top1_case(q, alpha=alpha)
    print_case(case_hit, f"Case Hybrid（alpha={alpha}）")

    pulse_hit = hybrid_top1_pulse(q, alpha=alpha)
    print_pulse(pulse_hit, f"PulsePJ Hybrid（alpha={alpha}）")
