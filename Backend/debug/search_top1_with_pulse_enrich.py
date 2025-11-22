# -*- coding: utf-8 -*-
"""
search_top1_with_pulse_enrich.py
同一個使用者問題：
- 取 Case 的 Hybrid Top-K（預設 5）
- 取 PulsePJ 的 Hybrid Top-K（預設 5）
- 用 PulsePJ 做補強（加權融合）重排 Case，輸出最終 Case Top-1（主體）
- 同時也輸出 PulsePJ Top-1（補充）
- 在主體 Case 的輸出中，帶入 PulsePJ 的補充訊息（名稱/類別/主病/相似度/症狀命中等）

需求：
  pip install weaviate-client requests python-dotenv

環境變數（或 Backend/.env）：
  NVIDIA_API_KEY=你的key
  WEAVIATE_URL=http://localhost:8080
  WV_API_KEY=key-admin
"""

import os, re, requests, math
from typing import List, Dict, Any, Tuple

COSINE_EPS = 0.03

# ---------- dotenv ----------
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

def getenv(name, default=""):
    v = os.getenv(name, default)
    return v.strip().strip('"').strip("'") if isinstance(v, str) else v

NVIDIA_API_KEY = "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"
WEAVIATE_URL   = getenv("WEAVIATE_URL", "http://localhost:8080")
WV_API_KEY     = getenv("WV_API_KEY", "key-admin")

# ---------- Weaviate ----------
try:
    import weaviate
    client = weaviate.Client(url=WEAVIATE_URL, additional_headers={"Authorization": f"Bearer {WV_API_KEY}"})
except Exception as e:
    raise SystemExit("請先安裝 weaviate-client：pip install weaviate-client") from e

# ---------- Embedding ----------
EMBED_URL = "https://integrate.api.nvidia.com/v1/embeddings"
EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"
DIM = 1024

def embed(text: str, input_type: str) -> List[float]:
    if not NVIDIA_API_KEY:
        raise RuntimeError("未設定 NVIDIA_API_KEY（Backend/.env）")
    r = requests.post(
        EMBED_URL,
        headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
        json={"model": EMBED_MODEL, "input": [text], "input_type": input_type},
        timeout=60
    )
    if not r.ok:
        print("[ERROR] NVIDIA response:", r.status_code, r.text); r.raise_for_status()
    vec = r.json()["data"][0]["embedding"]
    if len(vec) != DIM:
        raise ValueError(f"Embedding 維度 {len(vec)} != {DIM}")
    return vec

def cos(a: List[float], b: List[float]) -> float:
    s = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a)) + 1e-9
    nb = math.sqrt(sum(x*x for x in b)) + 1e-9
    return max(0.0, min(1.0, s/(na*nb)))  # clamp 0~1

# ---------- Utils ----------
def to_float(x):
    try:
        return float(x)
    except:
        return None

def pick_sparse_prop(cls_name: str) -> str:
    """優先 bm25_cjk；沒有則 bm25_text"""
    try:
        sch = client.schema.get()
        for c in sch.get("classes", []):
            if c["class"] == cls_name:
                names = {p["name"] for p in c.get("properties", [])}
                return "bm25_cjk" if "bm25_cjk" in names else "bm25_text"
    except Exception:
        pass
    return "bm25_text"

def get_case_candidates(query: str, k: int, qvec: List[float]=None) -> List[Dict[str,Any]]:
    props = ["case_id","chiefComplaint","presentIllness","search_text"]
    sparse_prop = pick_sparse_prop("Case")
    q = client.query.get("Case", props).with_limit(k).with_additional(["score","distance"])
    if qvec is not None:
        q = q.with_hybrid(query, alpha=0.5, vector=qvec, properties=[sparse_prop])
    else:
        q = q.with_hybrid(query, alpha=1.0, properties=[sparse_prop])
    r = q.do()
    return r.get("data",{}).get("Get",{}).get("Case",[]) or []

def get_pulse_candidates(query: str, k: int, qvec: List[float]=None) -> List[Dict[str,Any]]:
    props = ["pid","name","category","main_disease","search_text","symptoms"]
    sparse_prop = pick_sparse_prop("PulsePJ")
    q = client.query.get("PulsePJ", props).with_limit(k).with_additional(["score","distance"])
    if qvec is not None:
        q = q.with_hybrid(query, alpha=0.5, vector=qvec, properties=[sparse_prop])
    else:
        q = q.with_hybrid(query, alpha=1.0, properties=[sparse_prop])
    r = q.do()
    return r.get("data",{}).get("Get",{}).get("PulsePJ",[]) or []

def best_pulse_alignment(case_text: str, pulse_hits: List[Dict[str,Any]]) -> Tuple[Dict[str,Any], float]:
    """回傳與 case_text 最相近的 pulse 物件 + 相似度（cosine of passage embeddings）"""
    if not pulse_hits:
        return None, 0.0
    # 嵌入 Case 與每個 Pulse 的 search_text（passage 模式）
    case_vec = embed(case_text, "passage")
    best = None
    best_cos = -1.0
    for p in pulse_hits:
        p_text = p.get("search_text") or p.get("name") or ""
        p_vec = embed(p_text, "passage")
        c = cos(case_vec, p_vec)
        if c > best_cos:
            best_cos = c
            best = p
    return best, best_cos

def extract_hits(hits: List[Dict[str,Any]], key: str) -> List[Dict[str,Any]]:
    seen, out = set(), []
    for h in hits:
        kid = h.get(key)
        if kid and kid not in seen:
            seen.add(kid); out.append(h)
    return out

def match_symptoms(case_text: str, pulse_symptoms: List[str]) -> List[str]:
    txt = case_text
    matches = []
    for s in pulse_symptoms or []:
        s2 = str(s).strip()
        if not s2: continue
        if s2 in txt:
            matches.append(s2)
    return list(dict.fromkeys(matches))  # 去重保序

# ---------- Pipeline ----------
def run(query: str, k_case: int = 5, k_pulse: int = 5, w_cos: float = 0.3, w_pulse: float = 0.2):
    print(f"\n[QUERY] {query}")
    # 1) 查詢向量（query 模式）；失敗則 None
    qvec = None
    try:
        qvec = embed(query, "query")
    except Exception as e:
        print("[WARN] 查詢向量不可用，改純文本 Hybrid：", e)

    # 2) 取候選
    case_hits  = extract_hits(get_case_candidates(query, k_case, qvec), "case_id")
    pulse_hits = extract_hits(get_pulse_candidates(query, k_pulse, qvec), "pid")

    if not case_hits and not pulse_hits:
        print("(兩邊均無結果)")
        return

    # 3) 對每個 Case 候選，找最契合的 Pulse（cosine + pulse score），計算融合分數
    enriched = []
    for c in case_hits:
        base = to_float((c.get("_additional") or {}).get("score")) or 0.0
        c_text = c.get("search_text") or c.get("chiefComplaint") or c.get("presentIllness") or ""

        best_p, best_cos_val = (None, 0.0)
        if pulse_hits:
            try:
                best_p, best_cos_val = best_pulse_alignment(c_text, pulse_hits)
            except Exception as e:
                print("[WARN] 對 Case 做 Pulse 對齊失敗：", e)
                best_p, best_cos_val = (None, 0.0)

        # ★★★ 新增：若與 Pulse 原始 Top-1 的相似度差不多，就偏向 Top-1 ★★★
        pulse_top1 = pulse_hits[0] if pulse_hits else None
        if pulse_top1:
            top1_text = pulse_top1.get("search_text") or pulse_top1.get("name") or ""
            try:
                # 這裡用 passage 模式做語意對齊
                case_vec_passage = embed(c_text, "passage")
                top1_vec_passage = embed(top1_text, "passage")
                top1_cos = cos(case_vec_passage, top1_vec_passage)
            except Exception:
                top1_cos = 0.0

            # 若 Top-1 與目前 best 的相似度差 <= COSINE_EPS，改採用 Top-1
            if abs(top1_cos - best_cos_val) <= COSINE_EPS:
                best_p, best_cos_val = pulse_top1, top1_cos

        p_score = to_float((best_p.get("_additional") or {}).get("score")) if best_p else 0.0
        final = base + w_cos * best_cos_val + w_pulse * (p_score or 0.0)

        enriched.append({
            "case": c,
            "pulse_best": best_p,
            "cosine": round(best_cos_val, 4),
            "pulse_score": round(p_score or 0.0, 4),
            "base_score": round(base, 4),
            "final_score": round(final, 4),
        })


    # 4) 依融合分數排序，選最終 Case Top-1
    enriched.sort(key=lambda x: x["final_score"], reverse=True)
    best_case = enriched[0] if enriched else None

    # 5) PulsePJ Top-1（原始 Hybrid）
    pulse_top1 = pulse_hits[0] if pulse_hits else None

    # 6) 輸出
    if best_case:
        c = best_case["case"]
        p = best_case["pulse_best"]
        print("\n=== 主體：Case（融合後 Top-1）===")
        print("case_id =", c.get("case_id"))
        print("主訴    =", c.get("chiefComplaint"))
        print("現病史  =", c.get("presentIllness"))
        print("分數    =", {
            "case_hybrid": best_case["base_score"],
            "align_cos": best_case["cosine"],
            "pulse_score": best_case["pulse_score"],
            "final": best_case["final_score"]
        })
        if p:
            # 命中症狀（簡單詞面比對）
            hit_syms = match_symptoms(c.get("search_text") or "", p.get("symptoms") or [])
            print("\n--- 補充（來自 PulsePJ 的加權資訊） ---")
            print("pid     =", p.get("pid"))
            print("名稱    =", p.get("name"))
            print("類別    =", p.get("category"))
            print("主病    =", p.get("main_disease"))
            if hit_syms:
                print("命中症狀 =", "、".join(hit_syms))
    else:
        print("\n(無可用的 Case 候選)")

    if pulse_top1:
        print("\n=== 補充：PulsePJ（原始 Hybrid Top-1）===")
        print("pid     =", pulse_top1.get("pid"))
        print("名稱    =", pulse_top1.get("name"))
        print("類別    =", pulse_top1.get("category"))
        print("主病    =", pulse_top1.get("main_disease"))
        print("score   =", (pulse_top1.get("_additional") or {}).get("score"))
    else:
        print("\n(無可用的 PulsePJ 候選)")

# ---------- main ----------
if __name__ == "__main__":
    try:
        q = input("請輸入病人自己的描述（直接 Enter 用預設）：").strip()
    except Exception:
        q = ""
    if not q:
        q = "最近常常失眠而且多夢，晚上容易驚醒，醫師說我左寸的脈有點遲，白天會心悸口乾，該怎麼辦？"

    # 你可微調補強權重（建議：w_cos 0.2~0.4、w_pulse 0.1~0.3）
    run(q, k_case=5, k_pulse=5, w_cos=0.3, w_pulse=0.2)
