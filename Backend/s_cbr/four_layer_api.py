# -*- coding: utf-8 -*-
"""
四層 SCBR API 封裝（不更動既有 diagnose 流程的情況下，提供新入口）。
依設計文件：L1→L2→L3→L4 必須逐步呼叫，禁止並行。
資料來源：僅 TCMCase.json；禁止 YAML/Knowledge/RPCase。
"""

from typing import Dict, Any, Optional
from .llm.client import LLMClient
from .config import SCBRConfig
from .core.four_layer_pipeline import FourLayerSCBR


async def run_scbr_four_layers(question: str, llm_client: Optional[LLMClient] = None, config: Optional[SCBRConfig] = None, history_summary: str = "") -> Dict[str, Any]:
    if not llm_client:
        raise RuntimeError("四層 SCBR 需要 LLMClient，請先啟用 LLM")
    pipe = FourLayerSCBR(llm_client, config=config)
    return await pipe.run_once(question, history_summary=history_summary)
