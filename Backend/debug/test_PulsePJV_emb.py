# -*- coding: utf-8 -*-
import os, logging, requests
from typing import List
import jieba, weaviate

# === 設定 ===
try:
    import config
    WEAVIATE_URL       = getattr(config, "WEAVIATE_URL", "http://localhost:8080")
    WV_API_KEY         = getattr(config, "WV_API_KEY", "key-admin")
    EMBEDDING_BASE_URL = getattr(config, "EMBEDDING_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NVIDIA_API_KEY     = getattr(config, "NVIDIA_API_KEY", "")
    EMBEDDING_MODEL    = getattr(config, "EMBEDDING_NV_MODEL_NAME", "nvidia/nv-embedqa-e5-v5")
except Exception:
    WEAVIATE_URL       = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    WV_API_KEY         = os.getenv("WV_API_KEY", "key-admin")
    EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NVIDIA_API_KEY     = os.getenv("NVIDIA_API_KEY", "")
    EMBEDDING_MODEL    = os.getenv("EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5")

USERDICT_PATH = r"C:\work\系統-中醫\Pulse-project\Backend\prompt\tcm_userdict_jieba_v2.txt"

# === 初始化 jieba ===
logging.getLogger("jieba").setLevel(logging.ERROR)
if os.path.exists(USERDICT_PATH):
    with open(USERDICT_PATH, "r", encoding="utf-8") as f:
        jieba.load_userdict(f)

def cut(s: str) -> str:
    return " ".join(jieba.cut((s or "").strip(), HMM=False))

def nv_embed(texts: List[str], input_type="query") -> List[List[float]]:
    if not NVIDIA_API_KEY:
        return []
    headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
    r = requests.post(
        f"{EMBEDDING_BASE_URL}/embeddings",
        headers=headers,
        json={"model": EMBEDDING_MODEL, "input": texts, "input_type": input_type},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()["data"]
    return [d["embedding"] for d in data]

def fmt_num(x):
    try:
        return f"{float(x):.4f}"
    except Exception:
        return str(x)

def main():
    print(f"[init] WEAVIATE_URL={WEAVIATE_URL}")
    client = weaviate.Client(url=WEAVIATE_URL, additional_headers={"Authorization": f"Bearer {WV_API_KEY}"})

    # Schema 與 count
    schema = client.schema.get()
    classes = {c["class"]: c for c in schema.get("classes", [])}
    assert "PulsePJV" in classes, "PulsePJV 類別不存在"
    prop_names = {p["name"] for p in classes["PulsePJV"]["properties"]}
    need = {"search_all", "search_all_seg", "reference_links_arr"}
    assert need.issubset(prop_names), f"PulsePJV 欄位缺失：{need - prop_names}"

    agg = client.query.aggregate("PulsePJV").with_meta_count().do()
    cnt = agg["data"]["Aggregate"]["PulsePJV"][0]["meta"]["count"]
    print(f"✅ PulsePJV 類別存在")
    print(f"✅ PulsePJV 欄位齊全（包含 {need}）")
    print(f"✅ PulsePJV 目前筆數：{cnt}")

    # 取樣
    res = client.query.get("PulsePJV", ["name","category","main_disease","reference_links_arr","search_all"]).with_limit(2).with_additional(["id"]).do()
    items = (res.get("data",{}).get("Get",{}).get("PulsePJV") or [])
    print("\n--- PulsePJV 取樣 ---")
    for i, it in enumerate(items, 1):
        print(f"{i}. id={it['_additional']['id']}\n   name={it.get('name')}\n   category={it.get('category')}\n   main={it.get('main_disease')}\n   links={it.get('reference_links_arr')}\n")

    # 查詢
    q_text = "失眠 多夢 胸悶"
    q_tokens = cut(q_text)
    print(f"[query] 原文='{q_text}'")
    print(f"[seg]   '{q_tokens}'")

    # BM25（alpha=0）
    res = (
        client.query.get("PulsePJV", ["name","category","main_disease"])
        .with_hybrid(query=q_tokens, alpha=0.0, properties=["search_all","search_all_seg"])
        .with_additional(["id","score"])
        .with_limit(5)
        .do()
    )
    if "errors" in res:
        print("\n[GraphQL errors] ", res["errors"])
    hits = (res.get("data",{}).get("Get",{}).get("PulsePJV") or [])
    print("\n--- BM25 (PulsePJV) ---")
    if not hits:
        print("(0 筆)")
    else:
        for h in hits:
            sc = fmt_num(h["_additional"].get("score"))
            print(f"score={sc}  name={h.get('name')}  main={h.get('main_disease')}  id={h['_additional']['id']}")

    # 有 NVIDIA key → Hybrid/nearVector
    if NVIDIA_API_KEY:
        q_vec = nv_embed([q_text], input_type="query")[0]

        res = (
            client.query.get("PulsePJV", ["name","category","main_disease"])
            .with_hybrid(query=q_tokens, vector=q_vec, alpha=0.6, properties=["search_all","search_all_seg"])
            .with_additional(["id","score"])
            .with_limit(5)
            .do()
        )
        if "errors" in res:
            print("\n[GraphQL errors] ", res["errors"])
        hits = (res.get("data",{}).get("Get",{}).get("PulsePJV") or [])
        print("\n--- Hybrid (PulsePJV) ---")
        if not hits:
            print("(0 筆)")
        else:
            for h in hits:
                sc = fmt_num(h["_additional"].get("score"))
                print(f"score={sc}  name={h.get('name')}  main={h.get('main_disease')}  id={h['_additional']['id']}")

        res = (
            client.query.get("PulsePJV", ["name","category","main_disease"])
            .with_near_vector({"vector": q_vec})
            .with_additional(["id","distance"])
            .with_limit(5)
            .do()
        )
        if "errors" in res:
            print("\n[GraphQL errors] ", res["errors"])
        hits = (res.get("data",{}).get("Get",{}).get("PulsePJV") or [])
        print("\n--- nearVector (PulsePJV) ---")
        if not hits:
            print("(0 筆)")
        else:
            for h in hits:
                dist = fmt_num(h["_additional"].get("distance"))
                print(f"dist={dist}  name={h.get('name')}  main={h.get('main_disease')}  id={h['_additional']['id']}")
    else:
        print("\n[skip] 未設定 NVIDIA_API_KEY，略過向量查詢測試。")

if __name__ == "__main__":
    main()
