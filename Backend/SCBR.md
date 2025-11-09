# SCBR Architecture

This document describes the Four‑Layer SCBR flow, its components, and runtime behavior for both the Web API and E2E validation paths.

## System Overview (Mermaid)

```mermaid
graph TD
  subgraph Client
    FE[Web UI (Vite/React)]
  end

  subgraph FastAPI Backend
    API[/POST /api/scbr/v2/diagnose/] --> ENG[SCBREngine<br/>Backend/s_cbr/main.py]
    ENG --> SEC[Security Layer<br/>input_sanitizer / rate_limiter / output_validator]
    ENG --> FL[FourLayerSCBR<br/>core/four_layer_pipeline.py]
    FL --> L1[L1 Gate<br/>l1_gate_prompt.txt]
    L1 --> RET[Retrieval<br/>core/search_engine.py]
    FL --> L2[L2 Case-Anchored<br/>l2_case_anchored_diagnosis_prompt.txt]
    FL --> L3[L3 Safety Review<br/>l3_safety_review_prompt.txt]
    FL --> L4[L4 Presentation<br/>l4_presentation_prompt.txt]
    subgraph LLM
      LC[LLMClient<br/>llm/client.py]
      LAPI[(LLM API)]
      LC --> LAPI
    end
  end

  FE --> API
  FL --- LC
  RET --> WV[(Weaviate: TCMCase)]
  subgraph Optional
    EMB[Embeddings<br/>llm/embedding.py] --> RET
  end

  subgraph E2E
    E2E[run_four_layer_e2e.py] --> FLA[run_scbr_four_layers()<br/>four_layer_api.py] --> FL
  end
```

## Four‑Layer Pipeline (Mermaid)

```mermaid
flowchart TD
  Q[Input: question + history_summary + disable_case_slimming] --> L1[L1 Gate (LLM)]
  L1 -->|keyword_plan, next_action| RET[Retrieval]
  RET -->|hybrid_search| LOGRAW[[Log: [Retrieval RAW] samples (no full_text)]]
  RET --> F1{Filter non-dict hits?}
  F1 -->|Yes| NOTE_ND[[debug_note += "Retrieval returned non-dict hits; filtered to dict only."]]
  F1 --> DIC[dict_hits]
  DIC --> E0{dict_hits empty?}
  E0 -->|Yes| EARLY{{Return {l1, l2: None, l3: None, l4: None}<br/>debug_note += "Retrieval empty from vector store."}}
  E0 -->|No| UDOM[Compute user_domain]
  UDOM --> PLAN[Build plan_terms from keyword_plan]
  PLAN --> INJ{plan_terms non-empty AND no hit overlaps?}
  INJ -->|Yes| VIRT[[Inject virtual case built from user query & plan_terms<br/>debug_note += "No same-domain cases found; virtual case injected from user query."]]
  INJ --> ORDER
  VIRT --> ORDER[Weak domain ordering + backfill to 3]
  ORDER --> TOP3[raw_top3 = selected[:3]]
  TOP3 --> SLIM{USE_RETRIEVAL_SLIMMING && !disable_case_slimming?}
  SLIM -->|Yes| MAKE_SLIM[Build retrieved_cases_slim + domain_match]
  SLIM -->|No| SKIP_SLIM[Skip slimming]
  MAKE_SLIM --> HET
  SKIP_SLIM --> HET[Check heterogeneous fields]
  HET -->|Missing keys| NOTE_H[[debug_note += "Retrieved cases had heterogeneous fields; passed through as raw to L2/L3."]]
  HET --> LOGFIN[[Log: [Retrieval AFTER ASSEMBLY] used]]
  LOGFIN --> L2[L2 Case-Anchored (LLM)]
  L2 --> OK{L2 status == "ok"?}
  OK -->|No| L2F[[Fallback L2: status="fallback_from_pipeline",<br/>input.retrieved_cases=raw_top3,<br/>selected_case=raw_top3[0]<br/>debug_note += "L2 returned non-ok; pipeline filled fallback L2 for E2E."]]
  OK -->|Yes| PASSL2[Use L2 result]
  L2F --> L3[L3 Safety Review (LLM)]
  PASSL2 --> L3[L3 Safety Review (LLM)]
  L3 --> L4[L4 Presentation (LLM)]
  L4 --> OUT[[Output: {layer, l1, l2, l3, l4, debug_note}]]
```

## Directory Map
- Backend API: `Backend/main.py` (FastAPI), `Backend/s_cbr/api.py` (routes)
- Engine: `Backend/s_cbr/main.py` (SCBREngine), `Backend/s_cbr/four_layer_api.py` (E2E entry)
- Pipeline: `Backend/s_cbr/core/four_layer_pipeline.py`
- Retrieval: `Backend/s_cbr/core/search_engine.py`
- LLM: `Backend/s_cbr/llm/client.py`, `Backend/s_cbr/llm/embedding.py`
- Security: `Backend/s_cbr/security/*` (input_sanitizer, output_validator, rate_limiter, pii_masker)
- Prompts: `Backend/s_cbr/prompts/l1_gate_prompt.txt`, `l2_case_anchored_diagnosis_prompt.txt`, `l3_safety_review_prompt.txt`, `l4_presentation_prompt.txt`
- Knowledge: `Backend/s_cbr/knowledge/tcm_config.py` + YAML dictionaries
- Utils: `Backend/s_cbr/utils/logger.py`, `Backend/s_cbr/utils/error_handler.py`
- E2E: `Backend/s_cbr/debug/run_four_layer_e2e.py`
- Config: `Backend/s_cbr/config.py`

## Request Flow
- Router: `POST /api/scbr/v2/diagnose` → `s_cbr/api.py` validates and structures history; calls `run_spiral_cbr(...)`.
- Engine: `s_cbr/main.py` runs security checks, then delegates to the four‑layer pipeline.
- Pipeline: `core/four_layer_pipeline.py` executes L1→L2→L3→L4 and aggregates output with `debug_note`.
- Legacy: `POST /api/query` maps to the four‑layer flow for compatibility.

## Four‑Layer Behavior
- L1 Gate: Produces `keyword_plan` and action; logs LLM raw vs. filtered output for observability.
- Retrieval:
  - Hybrid when vector available; otherwise BM25‑only.
  - Field selection and fallback logging (`bm25_cjk` → `bm25_text` → `full_text` → `jieba_tokens` → `chief_complaint`; also tries alternates).
  - Non‑dict hits filtered with note: “Retrieval returned non‑dict hits; filtered to dict only.”
  - No dict hits returns `{l1, l2: None, l3: None, l4: None}` with note: “Retrieval empty from vector store.”
- Virtual Case Injection:
  - Build `plan_terms` from L1 (`symptom_terms ∪ tongue_pulse_terms ∪ zangfu_terms`).
  - If `plan_terms` non‑empty AND all hits have no term overlap: inject a virtual case at head; keep up to 2 original hits; note: “No same‑domain cases found; virtual case injected from user query.”
- Domain Ordering:
  - Weak ordering (digestive/gyne/general) with backfill to ensure 3 results.
  - If no same‑domain cases: note “Domain relax applied: using original top3 because no same‑domain cases were found.”
- Slimming:
  - Raw top3 always sent to L2 and L3; slimming optional via `USE_RETRIEVAL_SLIMMING` and `disable_case_slimming`.
  - If heterogeneous fields: note “Retrieved cases had heterogeneous fields; passed through as raw to L2/L3.”
- L2 Fallback:
  - If L2 missing or not ok, synthesize minimal L2 to proceed: `status="fallback_from_pipeline"`, `input.retrieved_cases=raw_top3`, `selected_case=raw_top3[0]`; note added.

## Observability
- Retrieval logging: “[Retrieval RAW]” (samples without `full_text`) and “[Retrieval AFTER ASSEMBLY]” (final used hits).
- Debug notes: surfaced in final output for Web/E2E:
  - Filtered non‑dict hits; empty retrieval; domain relax; virtual case injection; raw passthrough; post‑retrieval fallback; L2 fallback.
- E2E console: prints domain relax, raw passthrough, post‑retrieval fallback, and filtered non‑dict hit markers.

## Config & Environment
- Config: `s_cbr/config.py` (Weaviate, LLM, Search, Security, FeatureFlags).
- LLM input size: `config.llm.max_input_chars` (default 12000; configurable).
- Env vars: `WEAVIATE_URL`, `WEAVIATE_API_KEY`, `LLM_API_URL`, `LLM_API_KEY`, `LLM_MODEL`.

## Entrypoints
- Web: `Backend/main.py` mounts `s_cbr/api.py` at `/api/scbr/v2`.
- Programmatic (E2E): `s_cbr/four_layer_api.py::run_scbr_four_layers(...)`.
- E2E Runner: `python -m Backend.s_cbr.debug.run_four_layer_e2e`.

## Run & Verify
- Backend: `uvicorn Backend.main:app --reload`
- E2E: `python -m Backend.s_cbr.debug.run_four_layer_e2e`
- Check logs: verify retrieval logs and debug notes to confirm fallback behavior.

