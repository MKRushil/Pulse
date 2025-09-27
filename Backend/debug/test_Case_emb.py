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

    # Schema / count
    schema = client.schema.get()
    classes = {c["class"]: c for c in schema.get("classes", [])}
    assert "Case" in classes, "Case 類別不存在"
    props = {p["name"] for p in classes["Case"]["properties"]}
    has_search = {"search_all","search_all_seg"}.issubset(props)
    print("✅ Case 類別存在")
    print(f"[*] Case 是否有 search_* 欄位：{has_search}")

    agg = client.query.aggregate("Case").with_meta_count().do()
    cnt = agg["data"]["Aggregate"]["Case"][0]["meta"]["count"]
    print(f"✅ Case 目前筆數：{cnt}")

    # 取樣
    res = client.query.get("Case", ["chief_complaint","provisional_dx","summary_text","search_all"]).with_limit(2).with_additional(["id"]).do()
    items = (res.get("data",{}).get("Get",{}).get("Case") or [])
    print("\n--- Case 取樣 ---")
    for i, it in enumerate(items, 1):
        print(f"{i}. id={it['_additional']['id']}\n   主訴={it.get('chief_complaint')}\n   暫診={it.get('provisional_dx')}\n   摘要={it.get('summary_text')}\n")

    # 檢查 search_all 填充率（抽樣 200 筆）
    fill_check = client.query.get("Case", ["search_all"]).with_additional(["id"]).with_limit(200).do()
    sample = (fill_check.get("data",{}).get("Get",{}).get("Case") or [])
    filled = sum(1 for x in sample if (x.get("search_all") or "").strip())
    if has_search:
        print(f"[*] search_all 抽樣填充率：{filled}/{len(sample)}")
        if filled == 0:
            print("⚠️ 抽樣顯示尚未回填 search_all/search_all_seg，BM25/Hybrid 可能查不到；請先回填後再測。")

    # 查詢
    q_text = "肚子痛"
    q_tokens = cut(q_text)
    print(f"[query] 原文='{q_text}'")
    print(f"[seg]   '{q_tokens}'")

    # 4-1) BM25（只有在有 search_* 才能跑）
    if has_search:
        res = (
            client.query.get("Case", ["chief_complaint","provisional_dx","summary_text"])
            .with_hybrid(query=q_tokens, alpha=0.0, properties=["search_all","search_all_seg"])
            .with_additional(["id","score"])
            .with_limit(5)
            .do()
        )
        if "errors" in res:
            print("\n[GraphQL errors] ", res["errors"])
        hits = (res.get("data",{}).get("Get",{}).get("Case") or [])
        print("\n--- BM25 (Case) ---")
        if not hits:
            print("(0 筆)")
        else:
            for h in hits:
                sc = fmt_num(h["_additional"].get("score"))
                print(f"score={sc}  主訴={h.get('chief_complaint')}  暫診={h.get('provisional_dx')}  id={h['_additional']['id']}")
    else:
        print("\n[skip] Case 沒有 search_* 欄位，略過 BM25 測試。")

    # 4-2) Hybrid / nearVector（需 NVIDIA key）
    if NVIDIA_API_KEY:
        q_vec = nv_embed([q_text], input_type="query")[0]

        if has_search:
            res = (
                client.query.get("Case", ["chief_complaint","provisional_dx","summary_text"])
                .with_hybrid(query=q_tokens, vector=q_vec, alpha=0.6, properties=["search_all","search_all_seg"])
                .with_additional(["id","score"])
                .with_limit(5)
                .do()
            )
            if "errors" in res:
                print("\n[GraphQL errors] ", res["errors"])
            hits = (res.get("data",{}).get("Get",{}).get("Case") or [])
            print("\n--- Hybrid (Case) ---")
            if not hits:
                print("(0 筆)")
            else:
                for h in hits:
                    sc = fmt_num(h["_additional"].get("score"))
                    print(f"score={sc}  主訴={h.get('chief_complaint')}  暫診={h.get('provisional_dx')}  id={h['_additional']['id']}")

        res = (
            client.query.get("Case", ["chief_complaint","provisional_dx","summary_text"])
            .with_near_vector({"vector": q_vec})
            .with_additional(["id","distance"])
            .with_limit(5)
            .do()
        )
        if "errors" in res:
            print("\n[GraphQL errors] ", res["errors"])
        hits = (res.get("data",{}).get("Get",{}).get("Case") or [])
        print("\n--- nearVector (Case) ---")
        if not hits:
            print("(0 筆)")
        else:
            for h in hits:
                dist = fmt_num(h["_additional"].get("distance"))
                print(f"dist={dist}  主訴={h.get('chief_complaint')}  暫診={h.get('provisional_dx')}  id={h['_additional']['id']}")
    else:
        print("\n[skip] 未設定 NVIDIA_API_KEY，略過向量查詢測試。")

if __name__ == "__main__":
    main()
