# -*- coding: utf-8 -*-
"""
用法範例：
  (cd Backend)  # 確保從 Backend 資料夾執行，PYTHONPATH 可見 scbr 套件
  uvicorn main:app --reload   # 可先跑後端（非必須）
  # 匯入資料
  python -m scbr.data_ingest --case_dir ./data --pulse_file ../Embedding/PulsePJ_vector.json
"""
import os
import json
import argparse
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings

# 讀設定（Pydantic v2 + pydantic-settings）
from scbr.scbr_config import settings
# 使用我們的內建 Embedding client（若沒 API Key 會產生隨機向量，方便測通）
from scbr.llm.client import EmbeddingClient

# in-process Chroma（duckdb+parquet）持久化在 settings.CHROMA_PERSIST_DIR
_client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory=settings.CHROMA_PERSIST_DIR
))

# 取用/建立 collections
_case_col  = _client.get_or_create_collection(settings.CHROMA_COLLECTION_CASE, metadata={"hnsw:space": "cosine"})
_pulse_col = _client.get_or_create_collection(settings.CHROMA_COLLECTION_PULSE, metadata={"hnsw:space": "cosine"})
# RPCase 可在需要時再加入
# _rpc_col   = _client.get_or_create_collection(settings.CHROMA_COLLECTION_RPCASE, metadata={"hnsw:space": "cosine"})

# 我們的嵌入客戶端（可呼叫 NVIDIA Integrate；沒 API Key 時回隨機向量）
_embed = EmbeddingClient(
    model_name=settings.EMBEDDING_MODEL_NAME,
    base_url=settings.EMBEDDING_BASE_URL,
    api_key=settings.EMBEDDING_API_KEY
)

def _ensure_list(x):
    return x if isinstance(x, list) else [x]

def _embed_texts(texts: List[str]) -> List[List[float]]:
    return _embed.embed(texts)

def import_cases(case_dir: str) -> int:
    """
    將 case_dir 內的 *.json 病例匯入到 Case collection。
    預期 JSON 內有 inquiry.basic/inquiry 等欄位，若沒有就以檔名為 id。
    """
    count = 0
    if not os.path.isdir(case_dir):
        print(f"[WARN] Case 目錄不存在：{case_dir}")
        return 0

    for filename in os.listdir(case_dir):
        if not filename.lower().endswith(".json"):
            continue
        file_path = os.path.join(case_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[SKIP] 讀檔失敗 {file_path}: {e}")
            continue

        # 這裡依你提供的案例格式做合理提取；不存在就給空字串
        case_id = (
            data.get("basic", {}).get("id")
            or data.get("case_id")
            or os.path.splitext(filename)[0]
        )
        chief_complaint = (
            data.get("inquiry", {}).get("chiefComplaint")
            or data.get("chief_complaint", "")
        )
        present_illness = (
            data.get("inquiry", {}).get("presentIllness")
            or data.get("present_illness", "")
        )
        tentative_diagnosis = (
            data.get("inquiry", {}).get("tentativeDiagnosis")
            or data.get("diagnosis", "")
        )

        # 組 summary 作為文件內容（同時利於 BM25）
        summary_text = f"主訴: {chief_complaint}; 現病史: {present_illness}; 暫診: {tentative_diagnosis}"
        emb = _embed_texts([summary_text])[0]

        _case_col.add(
            ids=[str(case_id)],
            documents=[summary_text],
            metadatas=[{
                "summary_text": summary_text,
                "diagnosis": tentative_diagnosis,
                "source": "CaseImport"
            }],
            embeddings=[emb]
        )
        count += 1
        print(f"[OK] 匯入 Case：{case_id}")

    return count

def import_pulse(pulse_file: str) -> int:
    """
    匯入 PulsePJV 資料：
    - 若檔案內已有 'vector'/'embedding' 欄位→直接用
    - 否則用我們的 EmbeddingClient 計算
    支援 JSON (清單) 或 JSONL（每行一筆）
    """
    if not os.path.isfile(pulse_file):
        print(f"[WARN] Pulse 檔案不存在：{pulse_file}")
        return 0

    items: List[Dict[str, Any]] = []
    with open(pulse_file, "r", encoding="utf-8") as f:
        raw = f.read().strip()
        try:
            obj = json.loads(raw)
            if isinstance(obj, list):
                items = obj
            elif isinstance(obj, dict):
                items = [obj]
        except Exception:
            # 當作 JSONL
            items = [json.loads(line) for line in raw.splitlines() if line.strip()]

    n = 0
    for entry in items:
        pid = entry.get("id") or entry.get("name") or f"pulse_{n}"
        desc = entry.get("description") or entry.get("text") or ""
        vector = (
            entry.get("vector")
            or entry.get("embedding")
            or None
        )
        if vector is None:
            vector = _embed_texts([desc])[0]

        _pulse_col.add(
            ids=[str(pid)],
            documents=[desc],
            metadatas=[{
                "description": desc,
                "source": "PulseImport"
            }],
            embeddings=[vector]
        )
        n += 1
        if n % 100 == 0:
            print(f"[進度] 已匯入 {n} 筆 PulsePJV")

    print(f"[OK] 匯入 PulsePJV：{n} 筆")
    return n

def main():
    parser = argparse.ArgumentParser(description="匯入 Case 與 PulsePJV 到 Chroma（in-process）")
    parser.add_argument("--case_dir", default=os.path.join(".", "data"),
                        help="病例 JSON 目錄（預設：./data）")
    parser.add_argument("--pulse_file", default=os.path.join("..", "Embedding", "PulsePJ_vector.json"),
                        help="PulsePJV JSON/JSONL 檔案路徑（預設：../Embedding/PulsePJ_vector.json）")
    args = parser.parse_args()

    print(f"[INFO] Chroma persist dir: {settings.CHROMA_PERSIST_DIR}")
    print(f"[INFO] Case collection: {settings.CHROMA_COLLECTION_CASE}")
    print(f"[INFO] Pulse collection: {settings.CHROMA_COLLECTION_PULSE}")

    c = import_cases(args.case_dir)
    p = import_pulse(args.pulse_file)
    print(f"[DONE] 匯入完成：Case={c}, PulsePJV={p}")

if __name__ == "__main__":
    main()
