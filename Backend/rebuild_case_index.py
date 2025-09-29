# -*- coding: utf-8 -*-
"""
rebuild_case_index.py
重建 Case 向量庫（1024 維，支援 BM25/Hybrid）
- 讀 Backend/data/*.json
- 產生 bm25_text/search_text，並同步寫入 bm25_cjk（中文 BM25）
- NVIDIA nv-embedqa-e5-v5（input_type=passage，1024 維）
- Weaviate: vectorizer="none", distance="cosine"
- tokenization 預設 "gse_ch"；若不支援自動退回 "trigram"

環境變數（或 Backend/.env）：
  NVIDIA_API_KEY=xxxx
  WEAVIATE_URL=http://localhost:8080
  WV_API_KEY=key-admin
  DATA_DIR=C:\work\系統-中醫\Pulse-project\Backend\data
"""

import os, json, glob, hashlib, datetime, requests, traceback
from typing import Dict, Any

DEFAULT_DATA_DIR = r"C:\work\系統-中醫\Pulse-project\Backend\data"
DEFAULT_WEAVIATE_URL = "http://localhost:8080"
DEFAULT_WV_API_KEY = "key-admin"

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

DATA_DIR = os.environ.get("DATA_DIR", DEFAULT_DATA_DIR)
WEAVIATE_URL = os.environ.get("WEAVIATE_URL", DEFAULT_WEAVIATE_URL)
WV_API_KEY = os.environ.get("WV_API_KEY", DEFAULT_WV_API_KEY)
NVIDIA_API_KEY = "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"

try:
    import weaviate
    from weaviate.util import generate_uuid5
except Exception as e:
    raise RuntimeError("請先安裝 weaviate-client：pip install weaviate-client") from e


def flatten_case_text(d: Dict[str, Any]) -> Dict[str, Any]:
    basic = d.get("basic", {}) or {}
    age_raw = str(basic.get("age", "")).strip()
    age = int(age_raw) if age_raw.isdigit() else None
    gender = str(basic.get("gender", "")).strip()

    iq = d.get("inquiry", {}) or {}
    chief = str(iq.get("chiefComplaint", "")).strip()
    present = str(iq.get("presentIllness", "")).strip()

    insp = d.get("inspection", {}) or {}
    insp_parts = []
    if isinstance(insp, dict):
        for k, v in insp.items():
            if isinstance(v, list):
                v2 = "/".join([str(x) for x in v if str(x).strip()])
                if v2: insp_parts.append(f"{k}:{v2}")
            else:
                vs = str(v).strip()
                if vs: insp_parts.append(f"{k}:{vs}")
    elif isinstance(insp, list):
        insp_parts = [str(x).strip() for x in insp if str(x).strip()]
    inspection_text = " | ".join(insp_parts)

    pulse = d.get("pulse", {}) or {}
    pulse_parts = []
    if isinstance(pulse, dict):
        for pos, obj in pulse.items():
            t = obj.get("types", [])
            t_str = "/".join([str(x) for x in t if str(x).strip()]) if isinstance(t, list) else ""
            note = str(obj.get("note", "")).strip()
            seg = f"{pos}:{t_str}" if t_str else f"{pos}"
            if note: seg += f"/{note}"
            pulse_parts.append(seg)
    pulse_text = " | ".join(pulse_parts)

    merged = "；".join([x for x in [chief, present, inspection_text, pulse_text] if x]).strip("；")

    return {
        "age": age,
        "gender": gender,
        "chiefComplaint": chief,
        "presentIllness": present,
        "inspection_text": inspection_text,
        "pulse_text": pulse_text,
        "bm25_text": merged,
        "search_text": merged,
    }


def embed_text(text: str, input_type: str = "passage") -> list:
    if not NVIDIA_API_KEY:
        raise RuntimeError("未設定 NVIDIA_API_KEY，請用環境變數或 Backend/.env。")
    headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": EMBEDDING_MODEL, "input": [text], "input_type": input_type}
    url = f"{EMBEDDING_BASE_URL}/embeddings"
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    if not r.ok:
        try: print("[ERROR] NVIDIA response:", r.status_code, r.text)
        except Exception: pass
        r.raise_for_status()
    vec = r.json()["data"][0]["embedding"]
    if not isinstance(vec, list): raise ValueError("NVIDIA 回傳 embedding 格式非 list")
    if len(vec) != TARGET_DIM:
        raise ValueError(f"Embedding 維度 {len(vec)} != {TARGET_DIM}，請確認模型/參數。")
    return vec


def ensure_case_class(client: "weaviate.Client"):
    """建立/補 schema；bm25_cjk 優先 gse_ch，不行則 trigram。"""
    schema = client.schema.get()
    classes = {c["class"]: c for c in schema.get("classes", [])}

    # 嘗試新增屬性（帶 fallback）
    def _ensure_bm25_cjk_property():
        cur = client.schema.get()
        cdict = {c["class"]: c for c in cur.get("classes", [])}
        props = {p["name"] for p in cdict.get("Case", {}).get("properties", [])}
        if "bm25_cjk" in props: 
            return  # 已存在

        def _try_add(tokenization: str):
            client.schema.property.create("Case", {
                "name": "bm25_cjk",
                "dataType": ["text"],
                "indexSearchable": True,
                "tokenization": tokenization,
            })

        # 先試 gse_ch，不行再 trigram
        try:
            _try_add("gse_ch")
            print("[INFO] Added property Case.bm25_cjk (tokenization=gse_ch)")
        except Exception as e1:
            print(f"[WARN] gse_ch 不支援，改用 trigram；原因：{e1}")
            _try_add("trigram")
            print("[INFO] Added property Case.bm25_cjk (tokenization=trigram)")

    # 若 Class 尚未建立：創建（同樣帶 fallback）
    if "Case" not in classes:
        # 預設 schema 用 gse_ch，失敗就用 trigram
        base_schema = {
            "class": "Case",
            "description": "TCM cases for S-CBR",
            "vectorizer": "none",
            "vectorIndexConfig": {"distance": "cosine"},
            "properties": [
                {"name":"case_id","dataType":["text"],"indexSearchable":True},
                {"name":"age","dataType":["int"]},
                {"name":"gender","dataType":["text"],"indexSearchable":True},
                {"name":"chiefComplaint","dataType":["text"],"indexSearchable":True},
                {"name":"presentIllness","dataType":["text"],"indexSearchable":True},
                {"name":"inspection_text","dataType":["text"],"indexSearchable":True},
                {"name":"pulse_text","dataType":["text"],"indexSearchable":True},
                {"name":"bm25_text","dataType":["text"],"indexSearchable":True},
                {"name":"bm25_cjk","dataType":["text"],"indexSearchable":True,"tokenization":"gse_ch"},
                {"name":"search_text","dataType":["text"],"indexSearchable":True},
                {"name":"created_at","dataType":["date"]},
                {"name":"raw_json","dataType":["text"],"indexSearchable":False},
            ]
        }
        try:
            client.schema.create_class(base_schema)
            print("[INFO] Created class: Case (bm25_cjk=gse_ch)")
        except Exception as e1:
            print(f"[WARN] 建立 Case 失敗（gse_ch），改用 trigram；原因：{e1}")
            # 改 tokenization 後重試
            for p in base_schema["properties"]:
                if p["name"] == "bm25_cjk":
                    p["tokenization"] = "trigram"
            client.schema.create_class(base_schema)
            print("[INFO] Created class: Case (bm25_cjk=trigram)")
        return

    # Class 已存在：確保 bm25_cjk 屬性存在（帶 fallback）
    _ensure_bm25_cjk_property()
    print("[INFO] Class Case exists")


def derive_case_id(d: Dict[str, Any], file_path: str) -> str:
    cid = str(d.get("basic", {}).get("id", "")).strip()
    return cid if cid else hashlib.sha256(file_path.encode("utf-8", errors="ignore")).hexdigest()[:12]


def main():
    if not os.path.isdir(DATA_DIR): raise FileNotFoundError(f"DATA_DIR 不存在：{DATA_DIR}")
    if not WEAVIATE_URL: raise RuntimeError("WEAVIATE_URL 未設定")
    if not WV_API_KEY: raise RuntimeError("WV_API_KEY 未設定")
    if not NVIDIA_API_KEY: raise RuntimeError("NVIDIA_API_KEY 未設定")

    client = weaviate.Client(url=WEAVIATE_URL, additional_headers={"Authorization": f"Bearer {WV_API_KEY}"})
    ensure_case_class(client)

    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    if not files:
        print(f"[WARN] 資料夾無 JSON：{DATA_DIR}")
        return

    imported = failed = 0
    with client.batch as batch:
        batch.batch_size = 64
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    d = json.load(f)

                cid = derive_case_id(d, fp)
                flat = flatten_case_text(d)
                base_text = flat["search_text"] or flat["chiefComplaint"] or flat["presentIllness"] or "（無敘述）"

                vec = embed_text(base_text, input_type="passage")

                obj = {
                    "case_id": cid,
                    "age": flat["age"],
                    "gender": flat["gender"],
                    "chiefComplaint": flat["chiefComplaint"],
                    "presentIllness": flat["presentIllness"],
                    "inspection_text": flat["inspection_text"],
                    "pulse_text": flat["pulse_text"],
                    "bm25_text": flat["bm25_text"],
                    "bm25_cjk": flat["bm25_text"],  # 同步寫入中文 BM25 欄位
                    "search_text": flat["search_text"],
                    "created_at": datetime.datetime.utcnow().isoformat() + "Z",
                    "raw_json": json.dumps(d, ensure_ascii=False),
                }
                # 穩定 UUID（若要以 case_id 為唯一鍵，改成 generate_uuid5({"case_id": cid})）
                uuid = generate_uuid5(obj)

                batch.add_data_object(data_object=obj, class_name="Case", uuid=uuid, vector=vec)
                imported += 1
            except Exception as e:
                failed += 1
                traceback.print_exc()
                print(f"[ERROR] 檔案處理失敗：{fp}\n  -> {e}")

    print(f"[DONE] Imported: {imported}, Failed: {failed}, From dir: {DATA_DIR}")


if __name__ == "__main__":
    main()
