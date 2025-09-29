# -*- coding: utf-8 -*-
"""
重建 PulsePJ 向量庫（1024 維，支援中文 BM25 + Hybrid）
- 讀取 Embedding/PulsePJ_vector.json
- 生成 bm25_text / bm25_cjk（中文 tokenization）/ search_text
- NVIDIA nv-embedqa-e5-v5（input_type=passage, 1024 維）
- Weaviate: vectorizer="none", distance="cosine"
- tokenization 優先 "gse_ch"；不支援時自動回退 "trigram"
- UUID 以資料的 "id" 穩定產生，避免重複

環境變數（建議放 Backend/.env）：
  NVIDIA_API_KEY=你的key
  WEAVIATE_URL=http://localhost:8080
  WV_API_KEY=key-admin
  PULSE_JSON=C:\work\系統-中醫\Pulse-project\Embedding\PulsePJ_vector.json
"""

import os, json, requests, datetime, traceback
from typing import Dict, Any, List

EMBEDDING_BASE_URL = "https://integrate.api.nvidia.com/v1"
EMBEDDING_MODEL = "nvidia/nv-embedqa-e5-v5"
TARGET_DIM = 1024

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

PULSE_JSON   = os.getenv("PULSE_JSON", r"C:\work\系統-中醫\Pulse-project\Embedding\PulsePJ_vector.json")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WV_API_KEY   = os.getenv("WV_API_KEY", "key-admin")
NVIDIA_API_KEY = "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"

try:
    import weaviate
    from weaviate.util import generate_uuid5
except Exception as e:
    raise RuntimeError("請先安裝 weaviate-client：pip install weaviate-client") from e


# --- 文本彙總：給 BM25/向量 ---
def build_text_fields(x: Dict[str, Any]) -> Dict[str, str]:
    """
    將脈象資料彙總為：
      - bm25_text：一般文字（英文字首也可用）
      - bm25_cjk：中文 BM25 欄（入庫時同內容寫入）
      - search_text：向量/Hybrid 用
    """
    name = str(x.get("name", "")).strip()
    desc = str(x.get("description", "")).strip()
    cat  = str(x.get("category", "")).strip()
    md   = str(x.get("main_disease", "")).strip()
    chain= str(x.get("knowledge_chain", "")).strip()
    syms = x.get("symptoms", []) or []
    syms_txt = "、".join([str(s).strip() for s in syms if str(s).strip()])

    merged = "；".join([t for t in [name, desc, cat, md, syms_txt, chain] if t]).strip("；")
    if not merged:
        merged = name or desc or chain or "(無內容)"

    return {
        "bm25_text": merged,
        "bm25_cjk":  merged,
        "search_text": merged,
    }


def embed_passage(text: str) -> List[float]:
    if not NVIDIA_API_KEY:
        raise RuntimeError("未設定 NVIDIA_API_KEY，請用環境變數或 Backend/.env。")
    r = requests.post(
        f"{EMBEDDING_BASE_URL}/embeddings",
        headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
        json={"model": EMBEDDING_MODEL, "input": [text], "input_type": "passage"},
        timeout=60
    )
    if not r.ok:
        print("[ERROR] NVIDIA response:", r.status_code, r.text)
        r.raise_for_status()
    vec = r.json()["data"][0]["embedding"]
    if len(vec) != TARGET_DIM:
        raise ValueError(f"Embedding 維度 {len(vec)} != {TARGET_DIM}")
    return vec


def ensure_pulse_class(client: "weaviate.Client"):
    """建立/補 schema；PulsePJ 類，bm25_cjk tokenization gse_ch → trigram 回退"""
    schema = client.schema.get()
    classes = {c["class"]: c for c in schema.get("classes", [])}

    def _ensure_bm25_cjk_property():
        cur = client.schema.get()
        props = {p["name"] for c in cur.get("classes", []) if c["class"] == "PulsePJ" for p in c.get("properties", [])}
        if "bm25_cjk" in props:
            return
        def _try_add(tok: str):
            client.schema.property.create("PulsePJ", {
                "name": "bm25_cjk", "dataType": ["text"], "indexSearchable": True, "tokenization": tok
            })
        try:
            _try_add("gse_ch")
            print("[INFO] Added PulsePJ.bm25_cjk (gse_ch)")
        except Exception as e1:
            print(f"[WARN] gse_ch 不支援，改用 trigram；原因：{e1}")
            _try_add("trigram")
            print("[INFO] Added PulsePJ.bm25_cjk (trigram)")

    if "PulsePJ" not in classes:
        base = {
            "class": "PulsePJ",
            "description": "Pulse knowledge base for S-CBR",
            "vectorizer": "none",
            "vectorIndexConfig": {"distance": "cosine"},
            "properties": [
                {"name":"pid", "dataType":["text"], "indexSearchable":True},     # 原始 id（如 P1）
                {"name":"type","dataType":["text"], "indexSearchable":True},
                {"name":"name","dataType":["text"], "indexSearchable":True},
                {"name":"description","dataType":["text"], "indexSearchable":True},
                {"name":"category","dataType":["text"], "indexSearchable":True},
                {"name":"main_disease","dataType":["text"], "indexSearchable":True},
                {"name":"symptoms","dataType":["text[]"], "indexSearchable":True},
                {"name":"knowledge_chain","dataType":["text"], "indexSearchable":True},
                {"name":"bm25_text","dataType":["text"], "indexSearchable":True},
                {"name":"bm25_cjk","dataType":["text"], "indexSearchable":True, "tokenization":"gse_ch"},
                {"name":"search_text","dataType":["text"], "indexSearchable":True},
                {"name":"created_at","dataType":["date"]},
                {"name":"raw_json","dataType":["text"], "indexSearchable":False},
            ]
        }
        try:
            client.schema.create_class(base)
            print("[INFO] Created class: PulsePJ (bm25_cjk=gse_ch)")
        except Exception as e1:
            print(f"[WARN] 建立 PulsePJ 失敗（gse_ch），改 trigram；原因：{e1}")
            for p in base["properties"]:
                if p["name"] == "bm25_cjk":
                    p["tokenization"] = "trigram"
            client.schema.create_class(base)
            print("[INFO] Created class: PulsePJ (bm25_cjk=trigram)")
        return

    _ensure_bm25_cjk_property()
    print("[INFO] Class PulsePJ exists")


def main():
    if not os.path.isfile(PULSE_JSON):
        raise FileNotFoundError(f"找不到檔案：{PULSE_JSON}")
    if not WEAVIATE_URL:
        raise RuntimeError("WEAVIATE_URL 未設定")
    if not WV_API_KEY:
        raise RuntimeError("WV_API_KEY 未設定")
    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY 未設定")

    client = weaviate.Client(
        url=WEAVIATE_URL,
        additional_headers={"Authorization": f"Bearer {WV_API_KEY}"}
    )
    ensure_pulse_class(client)

    with open(PULSE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON 根節點應為陣列")

    imported = failed = 0
    with client.batch as batch:
        batch.batch_size = 64
        for x in data:
            try:
                pid = str(x.get("id", "")).strip() or str(x.get("neo4j_id", "")).strip()
                if not pid:
                    raise ValueError("資料缺少 id/neo4j_id")

                texts = build_text_fields(x)
                base_text = texts["search_text"]

                vec = embed_passage(base_text)

                obj = {
                    "pid": pid,
                    "type": x.get("type"),
                    "name": x.get("name"),
                    "description": x.get("description"),
                    "category": x.get("category"),
                    "main_disease": x.get("main_disease"),
                    "symptoms": x.get("symptoms") or [],
                    "knowledge_chain": x.get("knowledge_chain"),
                    "bm25_text": texts["bm25_text"],
                    "bm25_cjk": texts["bm25_cjk"],
                    "search_text": texts["search_text"],
                    "created_at": datetime.datetime.utcnow().isoformat() + "Z",
                    "raw_json": json.dumps(x, ensure_ascii=False),
                }

                # 穩定 UUID：以 pid 為 key（避免重複）
                uuid = generate_uuid5({"pid": pid})

                batch.add_data_object(
                    data_object=obj,
                    class_name="PulsePJ",
                    uuid=uuid,
                    vector=vec
                )
                imported += 1
            except Exception as e:
                failed += 1
                traceback.print_exc()
                print(f"[ERROR] 失敗 pid={x.get('id')} -> {e}")

    print(f"[DONE] Imported: {imported}, Failed: {failed}, From file: {PULSE_JSON}")


if __name__ == "__main__":
    main()
