# scbr/scbr_app.py
from fastapi import APIRouter, HTTPException
from .scbr_config import settings
from .utils.logger import info, error
from .models.schemas import TurnInput, TurnOutput, SaveCaseInput
from .llm.client import EmbeddingClient, LLMClient
from .knowledge.chroma_client import ChromaRepo
from .knowledge.bm25_index import BM25Index
from .knowledge.repositories import HybridRepo
from .core.search_engine import SearchEngine
from .core.dialog_manager import DialogManager
from .core.spiral_engine import SpiralEngine

router = APIRouter()

# --- 單例初始化 ---
_embed = EmbeddingClient(
    model_name=settings.EMBEDDING_MODEL_NAME,
    base_url=settings.EMBEDDING_BASE_URL,
    api_key=settings.EMBEDDING_API_KEY,
)
_llm = LLMClient(
    model_name=settings.LLM_MODEL_NAME,
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
)

_case_c = ChromaRepo(settings.CHROMA_HOST, settings.CHROMA_PORT, settings.CHROMA_COLLECTION_CASE, _embed)
_pulse_c= ChromaRepo(settings.CHROMA_HOST, settings.CHROMA_PORT, settings.CHROMA_COLLECTION_PULSE, _embed)
_rpc_c  = ChromaRepo(settings.CHROMA_HOST, settings.CHROMA_PORT, settings.CHROMA_COLLECTION_RPCASE, _embed)

def _load_for_bm25(repo: ChromaRepo):
    q = repo.collection.get(include=["metadatas","documents","ids"])
    return q["documents"], q["ids"], q["metadatas"]

_case_bm25 = BM25Index(*_load_for_bm25(_case_c))
_pulse_bm25= BM25Index(*_load_for_bm25(_pulse_c))
_rpc_bm25  = BM25Index(*_load_for_bm25(_rpc_c))

_repo_case   = HybridRepo(_case_c, _case_bm25)
_repo_pulse  = HybridRepo(_pulse_c, _pulse_bm25)
_repo_rpcase = HybridRepo(_rpc_c, _rpc_bm25)

_se = SearchEngine(_repo_case, _repo_pulse, _repo_rpcase, w_vec=settings.WEIGHT_VECTOR, w_bm25=settings.WEIGHT_BM25)
_dm = DialogManager(max_turns=settings.MAX_TURNS)
_engine = SpiralEngine(_dm, _se, _llm)

@router.get("/scbr/health")
def scbr_health():
    return {"ok": True, "collections": {
        "case": settings.CHROMA_COLLECTION_CASE,
        "pulse": settings.CHROMA_COLLECTION_PULSE,
        "rpcase": settings.CHROMA_COLLECTION_RPCASE
    }}

@router.post("/query", response_model=TurnOutput)
def scbr_query(payload: TurnInput):
    try:
        return _engine.step(payload.session_id, payload.user_query)
    except Exception as e:
        error("scbr_query_failed", err=str(e))
        raise HTTPException(status_code=500, detail="S-CBR engine error")

@router.post("/scbr/save")
def scbr_save(payload: SaveCaseInput):
    try:
        if not payload.satisfied:
            _dm.reset(payload.session_id)
            return {"ok": True, "saved": False}
        doc = {
            "id": f"rp_{payload.session_id}",
            "text": f"{payload.final_problem}\n診斷：{payload.final_diagnosis}\n建議：{payload.final_suggestions}",
            "meta": {"source":"feedback","session_id":payload.session_id}
        }
        _rpc_c.add_docs([doc])
        _dm.reset(payload.session_id)
        return {"ok": True, "saved": True}
    except Exception as e:
        error("scbr_save_failed", err=str(e))
        raise HTTPException(status_code=500, detail="save error")

@router.post("/scbr/end")
def scbr_end(session_id: str):
    _dm.reset(session_id)
    return {"ok": True}
