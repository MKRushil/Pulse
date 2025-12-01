# -*- coding: utf-8 -*-
"""
Agentic 檢索決策模組 (AgenticRetrieval)

職責：
1. 接收 L1 Agentic Gate 的檢索策略決策
2. 執行智能檢索（動態 alpha、自動 fallback）
3. 評估檢索結果品質
4. 根據品質自動調整策略

核心創新：
- 動態 alpha 調整（0.2-0.8）
- 多階段 fallback 機制
- 結果品質評估
- 自適應檢索策略
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import logging

# 假設存在這些模組
from ..llm.embedding import EmbedClient
from .search_engine import SearchEngine
from ..config import SCBRConfig

logger = logging.getLogger("AgenticRetrieval")


class AgenticRetrieval:
    """
    智能檢索決策器
    
    基於 L1 Agentic Gate 的決策，執行智能化的檢索流程
    """
    
    def __init__(
        self, 
        search_engine: SearchEngine, 
        embed_client: EmbedClient,
        config: Optional[SCBRConfig] = None
    ):
        """
        初始化 Agentic 檢索器
        
        Args:
            search_engine: 檢索引擎實例
            embed_client: 嵌入客戶端實例
            config: 配置實例
        """
        self.SE = search_engine
        self.embed = embed_client
        self.cfg = config
        
        # 預設配置（若 config 未提供）
        self.quality_threshold = 0.65  # 品質門檻
        self.max_fallback_attempts = 3  # 最大 fallback 嘗試次數
        
        # 從 config 載入 Agentic 配置（如果存在）
        if self.cfg and hasattr(self.cfg, 'agentic_nlu'):
            self.quality_threshold = self.cfg.agentic_nlu.fallback_threshold
            self.max_fallback_attempts = self.cfg.agentic_nlu.max_fallback_attempts
        
        logger.info(
            f"[AgenticRetrieval] 初始化完成 - "
            f"品質門檻: {self.quality_threshold}, "
            f"最大 fallback: {self.max_fallback_attempts}"
        )
    
    async def intelligent_search(
        self,
        index: str,
        text: str,
        l1_strategy: Dict[str, Any],
        limit: int = 3
    ) -> Dict[str, Any]:
        """
        智能檢索主入口 (含強制保底機制)
        
        根據 L1 的策略決策執行檢索，並自動評估品質和執行 fallback。
        若首次檢索結果為空，強制啟動寬鬆模式以確保有回傳值。
        """
        # 提取 L1 策略決策
        decided_alpha = l1_strategy.get("decided_alpha", 0.5)
        strategy_type = l1_strategy.get("strategy_type", "balanced")
        fallback_plan = l1_strategy.get("fallback_plan", "balanced")
        expected_quality = l1_strategy.get("expected_quality", "medium")
        
        logger.info(
            f"[AgenticRetrieval] 開始智能檢索 - "
            f"Alpha: {decided_alpha}, 策略: {strategy_type}, "
            f"預期品質: {expected_quality}"
        )
        
        # 初始化結果
        result = {
            "cases": [],
            "metadata": {
                "initial_alpha": decided_alpha,
                "final_alpha": decided_alpha,
                "attempts": 0,
                "quality_score": 0.0,
                "fallback_triggered": False,
                "fallback_reason": "N/A"
            }
        }
        
        # 第一次嘗試：使用 L1 決定的策略
        cases, quality = await self._execute_search(
            index=index,
            text=text,
            alpha=decided_alpha,
            limit=limit,
            attempt=1
        )
        
        result["metadata"]["attempts"] = 1
        
        # [MODIFIED] 強制保底：如果第一次嘗試結果為空 (0 cases)，立即啟動「寬鬆模式」
        if not cases:
            logger.warning(f"[AgenticRetrieval] 🚨 首次檢索結果為空，啟動強制寬鬆保底模式！")
            
            # 強制使用純 BM25 傾向 (alpha=0.1) + 擴大 Limit * 2
            # 這樣能確保即使向量不匹配，也能透過關鍵字抓到東西
            fallback_limit = limit * 2
            cases, quality = await self._execute_search(
                index=index,
                text=text,
                alpha=0.95, 
                limit=fallback_limit,
                attempt=99 # 特殊標記
            )
            
            result["metadata"]["fallback_triggered"] = True
            result["metadata"]["fallback_reason"] = "Zero results force fallback (寬鬆保底)"
            result["metadata"]["final_alpha"] = 0.1
            result["metadata"]["attempts"] += 1

        # 如果經過保底有結果，但品質仍不達標，且還沒超過重試上限，才執行標準 fallback
        # (注意：如果剛剛已經執行過強制保底，這裡通常不會再進，除非品質極差且還有次數)
        elif quality < self.quality_threshold:
            logger.warning(
                f"[AgenticRetrieval] ⚠️ 檢索品質不足 ({quality:.3f} < {self.quality_threshold})，"
                f"觸發標準 Fallback: {fallback_plan}"
            )
            
            result["metadata"]["fallback_triggered"] = True
            result["metadata"]["fallback_reason"] = f"品質不足: {quality:.3f}"
            
            # 執行標準 fallback 策略
            cases, quality, final_alpha = await self._execute_fallback(
                index=index,
                text=text,
                fallback_plan=fallback_plan,
                initial_quality=quality,
                limit=limit,
                current_attempt=1
            )
            result["metadata"]["final_alpha"] = final_alpha
            result["metadata"]["attempts"] += 1

        # 最終賦值
        result["cases"] = cases[:limit] # 確保不超過 limit
        result["metadata"]["quality_score"] = quality
        
        if quality >= self.quality_threshold:
            logger.info(f"[AgenticRetrieval] ✅ 檢索成功 (品質: {quality:.3f})")
        
        return result
    
    async def _execute_search(
        self,
        index: str,
        text: str,
        alpha: float,
        limit: int,
        attempt: int = 1
    ) -> Tuple[List[Dict], float]:
        """
        執行單次檢索
        
        Args:
            index: 索引名稱
            text: 查詢文本
            alpha: 混合檢索 alpha 值
            limit: 返回數量
            attempt: 嘗試次數（用於日誌）
        
        Returns:
            (cases, quality_score)
        """
        logger.info(
            f"[AgenticRetrieval] 執行檢索 #{attempt} - "
            f"Alpha: {alpha:.2f}"
        )
        
        # 1. 生成向量
        vector = None
        try:
            vector = await self.embed.embed(text)
            logger.info(f"[AgenticRetrieval] 向量生成成功 - 維度: {len(vector)}")
        except Exception as e:
            logger.warning(f"[AgenticRetrieval] 向量生成失敗: {e}, 將使用純 BM25")
            alpha = 1.0  # 純 BM25
        
        # 2. 執行混合檢索
        try:
            # 使用 SearchEngine 的 intelligent_hybrid_search（如果存在）或 hybrid_search
            if hasattr(self.SE, 'intelligent_hybrid_search'):
                cases = await self.SE.intelligent_hybrid_search(
                    index=index,
                    text=text,
                    vector=vector,
                    alpha=alpha,
                    limit=limit,
                    search_fields=["full_text"]  # 使用 full_text 欄位
                )
            else:
                # 使用標準 hybrid_search
                cases = await self.SE.hybrid_search(
                    index=index,
                    text=text,
                    vector=vector,
                    alpha=alpha,
                    limit=limit,
                    search_fields=["full_text"]
                )
        except Exception as e:
            logger.error(f"[AgenticRetrieval] 檢索失敗: {e}", exc_info=True)
            cases = []
        
        # 3. 評估品質
        quality_score = self._evaluate_quality(cases)
        
        logger.info(
            f"[AgenticRetrieval] 檢索完成 - "
            f"找到 {len(cases)} 個案例, 品質: {quality_score:.3f}"
        )
        
        return cases, quality_score
    
    def _evaluate_quality(self, cases: List[Dict]) -> float:
        """
        評估檢索結果品質
        
        評估指標：
        1. 案例數量（是否 >= 預期）
        2. 平均分數（相關度）
        3. 最高分數
        
        Args:
            cases: 檢索結果列表
        
        Returns:
            品質評分（0.0-1.0）
        """
        if not cases:
            return 0.0
        
        # 1. 案例數量評分（0.3 權重）
        count_score = min(len(cases) / 3.0, 1.0)  # 預期至少 3 個案例
        
        # 2. 平均分數評分（0.4 權重）
        scores = []
        for case in cases:
            # 兼容多種分數欄位名稱
            score = (
                case.get("_final_score") or 
                case.get("score") or 
                case.get("_additional", {}).get("score") or 
                0.0
            )
            try:
                scores.append(float(score))
            except (ValueError, TypeError):
                scores.append(0.0)
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # 3. 最高分數評分（0.3 權重）
        max_score = max(scores) if scores else 0.0
        
        # 綜合評分
        quality = (
            count_score * 0.3 +
            avg_score * 0.4 +
            max_score * 0.3
        )
        
        logger.debug(
            f"[AgenticRetrieval] 品質評估 - "
            f"數量: {count_score:.2f}, 平均: {avg_score:.2f}, "
            f"最高: {max_score:.2f} → 總分: {quality:.3f}"
        )
        
        return quality
    
    async def _execute_fallback(
        self,
        index: str,
        text: str,
        fallback_plan: str,
        initial_quality: float,
        limit: int,
        current_attempt: int
    ) -> Tuple[List[Dict], float, float]:
        """
        執行 fallback 策略
        
        Args:
            index: 索引名稱
            text: 查詢文本
            fallback_plan: fallback 計畫類型
            initial_quality: 初始品質
            limit: 返回數量
            current_attempt: 當前嘗試次數
        
        Returns:
            (cases, quality_score, final_alpha)
        """
        # 根據 fallback_plan 決定新的 alpha 值
        fallback_alpha_map = {
            "keyword_focus": 0.2,  # 關鍵字為主
            "vector_focus": 0.8,   # 向量為主
            "balanced": 0.5,       # 均衡
            "expand": 0.5          # 擴展（alpha 不變，但增加 limit）
        }
        
        new_alpha = fallback_alpha_map.get(fallback_plan, 0.5)
        new_limit = limit * 1.5 if fallback_plan == "expand" else limit
        
        logger.info(
            f"[AgenticRetrieval] 執行 Fallback - "
            f"計畫: {fallback_plan}, 新 Alpha: {new_alpha}, "
            f"新 Limit: {int(new_limit)}"
        )
        
        # 執行 fallback 檢索
        cases, quality = await self._execute_search(
            index=index,
            text=text,
            alpha=new_alpha,
            limit=int(new_limit),
            attempt=current_attempt + 1
        )
        
        # 如果品質仍不足且未達最大嘗試次數，嘗試其他策略
        if (quality < self.quality_threshold and 
            current_attempt < self.max_fallback_attempts):
            
            # 嘗試另一個極端
            if fallback_plan == "keyword_focus":
                next_plan = "vector_focus"
            elif fallback_plan == "vector_focus":
                next_plan = "expand"
            else:
                next_plan = "expand"
            
            logger.warning(
                f"[AgenticRetrieval] Fallback 品質仍不足 - "
                f"品質: {quality:.3f}, 嘗試: {next_plan}"
            )
            
            return await self._execute_fallback(
                index=index,
                text=text,
                fallback_plan=next_plan,
                initial_quality=quality,
                limit=limit,
                current_attempt=current_attempt + 1
            )
        
        return cases, quality, new_alpha


# 工具函數

def create_agentic_retrieval(
    search_engine: SearchEngine,
    embed_client: EmbedClient,
    config: Optional[SCBRConfig] = None
) -> AgenticRetrieval:
    """
    創建 AgenticRetrieval 實例的工廠函數
    
    Args:
        search_engine: 檢索引擎
        embed_client: 嵌入客戶端
        config: 配置
    
    Returns:
        AgenticRetrieval 實例
    """
    return AgenticRetrieval(
        search_engine=search_engine,
        embed_client=embed_client,
        config=config
    )