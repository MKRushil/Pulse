# Backend/weaviate_schema_scbr.py
from vector.schema import get_weaviate_client  # 可沿用你的連線工具

def create_scbr_classes():
    client = get_weaviate_client()

    # A. 螺旋會話紀錄（每次提問/每回合決策）
    session = {
        "class": "SCBRSession",
        "vectorizer": "none",
        "properties": [
            {"name": "session_id", "dataType": ["text"]},
            {"name": "query_text", "dataType": ["text"]},
            {"name": "patient_profile_hash", "dataType": ["text"]},
            {"name": "steps", "dataType": ["text"]},   # JSON 序列化每回合結果
            {"name": "status", "dataType": ["text"]},  # active / done
            {"name": "created_at", "dataType": ["date"]},
        ],
    }

    # B. 回饋案例知識庫（只收斂必要欄位，利於後續檢索）
    feedback = {
        "class": "SCBRFeedbackCase",
        "vectorizer": "none",
        "properties": [
            {"name": "session_id", "dataType": ["text"]},
            {"name": "case_id_ref", "dataType": ["text"]},  # 來源 Case/候選ID
            {"name": "query_id", "dataType": ["text"]},
            {"name": "diagnosis", "dataType": ["text"]},    # 主/次病（結構JSON）
            {"name": "formulas", "dataType": ["text"]},     # 方藥/劑量（結構JSON）
            {"name": "decision", "dataType": ["text"]},     # suitable / unsuitable
            {"name": "rationale", "dataType": ["text"]},    # 為何適合/不適合（簡述）
            {"name": "outcome_metrics", "dataType": ["text"]}, # 例如 症狀變化、NRS
            {"name": "evidence_ids", "dataType": ["text"]}, # 關聯的檢索片段ID JSON
            {"name": "created_at", "dataType": ["date"]},
        ],
    }

    for cls in (session, feedback):
        try:
            client.schema.create_class(cls)
        except Exception as e:
            print(f"[Schema] {cls['class']} 可能已存在：{e}")

if __name__ == "__main__":
    create_scbr_classes()
