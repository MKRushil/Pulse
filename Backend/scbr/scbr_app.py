# Backend/scbr/scbr_app.py
from fastapi import APIRouter, HTTPException
from .scbr_config import settings
from scbr.utils.logger import info, error
from scbr.models.schemas import TurnInput, TurnOutput, SaveCaseInput
from scbr.llm.client import EmbeddingClient, LLMClient
from scbr.knowledge.chroma_client import ChromaRepo
from scbr.knowledge.bm25_index import BM25Index
from scbr.knowledge.repositories import HybridRepo
from scbr.core.search_engine import SearchEngine
from scbr.core.dialog_manager import DialogManager
from scbr.core.spiral_engine import SpiralEngine

router = APIRouter()

_engine = None
_dm = None
_case_repo = None
_pulse_repo = None
_rpc_repo = None

def _init_engine_once():
    global _engine, _dm, _case_repo, _pulse_repo, _rpc_repo
    if _engine is not None:
        return _engine

    # Embedding/LLM
    embed = EmbeddingClient(settings.EMBEDDING_MODEL_NAME, settings.EMBEDDING_BASE_URL, settings.EMBEDDING_API_KEY)
    llm   = LLMClient(settings.LLM_MODEL_NAME, settings.LLM_BASE_URL, settings.LLM_API_KEY)

    # === In-process Chroma repos（持久化）===
    persist = settings.CHROMA_PERSIST_DIR
    case_c  = ChromaRepo(persist, settings.CHROMA_COLLECTION_CASE,   embed)
    pulse_c = ChromaRepo(persist, settings.CHROMA_COLLECTION_PULSE,  embed)
    rpc_c   = ChromaRepo(persist, settings.CHROMA_COLLECTION_RPCASE, embed)

    def _bm25(repo: ChromaRepo):
        q = repo.collection.get(include=["metadatas","documents","ids"])
        docs, ids, metas = q["documents"], q["ids"], q["metadatas"]
        return BM25Index(docs, ids, metas)

    _case_repo  = HybridRepo(case_c,  _bm25(case_c))
    _pulse_repo = HybridRepo(pulse_c, _bm25(pulse_c))
    _rpc_repo   = HybridRepo(rpc_c,   _bm25(rpc_c))

    se = SearchEngine(_case_repo, _pulse_repo, _rpc_repo,
                      w_vec=settings.WEIGHT_VECTOR, w_bm25=settings.WEIGHT_BM25)
    _dm = DialogManager(max_turns=settings.MAX_TURNS)
    _engine = SpiralEngine(_dm, se, llm)
    info("scbr_init", ok=True, mode="inprocess", persist=persist)
    return _engine

@router.get("/scbr/health")
def scbr_health():
    try:
        _init_engine_once()
        return {"ok": True, "engine": "ready", "mode": settings.CHROMA_MODE, "persist": settings.CHROMA_PERSIST_DIR}
    except Exception as e:
        return {"ok": False, "error": repr(e)}

@router.post("/query", response_model=TurnOutput)
def scbr_query(payload: TurnInput):
    try:
        engine = _init_engine_once()
        return engine.step(payload.session_id, payload.user_query)
    except Exception as e:
        error("scbr_query_failed", err=str(e))
        raise HTTPException(status_code=503, detail=f"S-CBR init/query error: {e}")

@router.post("/scbr/save")
def scbr_save(payload: SaveCaseInput):
    try:
        _init_engine_once()  # 確保 repo 可用
        # 寫回 RPCase
        doc = {
            "id": f"rp_{payload.session_id}",
            "text": f"{payload.final_problem}\n診斷：{payload.final_diagnosis}\n建議：{payload.final_suggestions}",
            "meta": {"source":"feedback","session_id":payload.session_id}
        }
        # 使用 _rpc_repo 的底層 chroma client
        _rpc_repo.chroma.add_docs([doc])  # 直接寫入向量庫
        _dm.reset(payload.session_id)
        return {"ok": True, "saved": True}
    except Exception as e:
        error("scbr_save_failed", err=str(e))
        raise HTTPException(status_code=500, detail=f"save error: {e}")

@router.post("/scbr/end")
def scbr_end(session_id: str):
    _init_engine_once()
    _dm.reset(session_id)
    return {"ok": True}
