# -*- coding: utf-8 -*-
"""
Backend/s_cbr/core/dynamic_retrieval.py
動態檢索優化器 - 實現動態 α、多欄位加權、RRF 融合
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from dataclasses import dataclass
from ..utils.logger import get_logger

logger = get_logger("DynamicRetrieval")

@dataclass
class RetrievalConfig:
    """檢索配置"""
    # 欄位權重（用於 BM25 和向量加權）
    field_weights: Dict[str, float] = None
    
    # α 動態調整範圍
    alpha_min: float = 0.35
    alpha_max: float = 0.70
    alpha_base: float = 0.3
    alpha_increment: float = 0.05
    
    # Top-k 設定
    initial_k: int = 30
    final_k: int = 10
    
    # RRF 參數
    rrf_k: int = 60
    
    # MMR 參數
    mmr_lambda: float = 0.7
    mmr_threshold: float = 0.85
    
    def __post_init__(self):
        if self.field_weights is None:
            self.field_weights = {
                "symptom_terms": 1.0,
                "pulse_terms": 1.2,
                "tongue_terms": 1.2,
                "zangfu_terms": 0.9,
                "syndrome_terms": 1.1,
                "jieba_tokens": 0.6
            }

class DynamicRetrievalOptimizer:
    """動態檢索優化器"""
    
    def __init__(self, config: RetrievalConfig = None):
        self.config = config or RetrievalConfig()
        logger.info("✅ 動態檢索優化器初始化")
        logger.info(f"   欄位權重: {self.config.field_weights}")
    
    # ==================== A1: 動態 α 計算 ====================
    def calculate_dynamic_alpha(
        self,
        round_num: int,
        symptom_count: int,
        coverage: float = 0.0,
        is_rpcase_empty: bool = False
    ) -> float:
        """
        動態計算 α 值
        
        策略：
        1. 基礎公式：α = clip(0.3 + 0.05*m, 0.35, 0.70)
        2. 輪次調整：第1輪偏 BM25，第2輪起偏向量
        3. 覆蓋率調整：Coverage<0.4 降低 α
        4. RPCase 空集處理：降低 α 重搜
        
        Args:
            round_num: 當前輪次
            symptom_count: 有效症狀數量
            coverage: 當前覆蓋率
            is_rpcase_empty: RPCase 是否為空
            
        Returns:
            動態調整後的 α 值
        """
        # 基礎計算
        m = symptom_count
        base_alpha = np.clip(
            self.config.alpha_base + self.config.alpha_increment * m,
            self.config.alpha_min,
            self.config.alpha_max
        )
        
        # 輪次調整
        if round_num == 1:
            # 第1輪：偏 BM25（0.4±0.05）
            round_alpha = 0.4 + np.random.uniform(-0.05, 0.05)
        elif round_num == 2:
            # 第2輪：偏向量（0.6±0.1）
            round_alpha = 0.6 + np.random.uniform(-0.1, 0.1)
        else:
            # 第3輪起：更偏向量（0.65±0.1）
            round_alpha = 0.65 + np.random.uniform(-0.1, 0.1)
        
        # 加權融合
        alpha = 0.6 * base_alpha + 0.4 * round_alpha
        
        # 覆蓋率調整：Coverage < 0.4 降低 α（回 BM25）
        if coverage < 0.4:
            alpha *= 0.85
            logger.info(f"   ⚠️  Coverage={coverage:.2f} < 0.4，降低 α")
        
        # RPCase 空集調整
        if is_rpcase_empty:
            alpha *= 0.9
            logger.info(f"   ⚠️  RPCase 為空，降低 α")
        
        # 最終限制範圍
        alpha = np.clip(alpha, self.config.alpha_min, self.config.alpha_max)
        
        logger.info(f"🎯 動態 α 計算 [第{round_num}輪]:")
        logger.info(f"   症狀數={m}, 覆蓋率={coverage:.2f}")
        logger.info(f"   基礎α={base_alpha:.3f}, 輪次α={round_alpha:.3f}")
        logger.info(f"   最終α={alpha:.3f}")
        
        return alpha
    
    # ==================== A2: 多欄位加權 ====================
    def get_weighted_search_fields(
        self,
        available_fields: List[str]
    ) -> List[Tuple[str, float]]:
        """
        獲取加權後的搜索欄位
        
        Returns:
            [(field_name, weight), ...]
        """
        weighted_fields = []
        for field in available_fields:
            weight = self.config.field_weights.get(field, 1.0)
            weighted_fields.append((field, weight))
        
        # 按權重降序排列
        weighted_fields.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"📊 加權搜索欄位: {weighted_fields}")
        return weighted_fields
    
    # ==================== A4: RRF 融合 ====================
    def reciprocal_rank_fusion(
        self,
        rankings: List[List[Dict[str, Any]]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        RRF (Reciprocal Rank Fusion) 融合多個排序結果
        
        公式：RRF(d) = Σ 1/(k + rank_i(d))
        
        Args:
            rankings: 多個排序列表 [[doc1, doc2, ...], [doc1, doc3, ...], ...]
            k: RRF 常數，通常為 60
            
        Returns:
            融合後的排序列表
        """
        # 收集所有文檔及其 RRF 分數
        doc_scores = {}
        
        for ranking in rankings:
            for rank, doc in enumerate(ranking, 1):
                doc_id = self._get_doc_id(doc)
                
                # RRF 分數累加
                rrf_score = 1.0 / (k + rank)
                
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        'doc': doc,
                        'rrf_score': 0.0,
                        'appearances': 0
                    }
                
                doc_scores[doc_id]['rrf_score'] += rrf_score
                doc_scores[doc_id]['appearances'] += 1
        
        # 轉換為列表並排序
        fused_results = [
            {
                **item['doc'],
                '_rrf_score': item['rrf_score'],
                '_appearances': item['appearances']
            }
            for item in doc_scores.values()
        ]
        
        fused_results.sort(key=lambda x: x['_rrf_score'], reverse=True)
        
        logger.info(f"🔀 RRF 融合: {len(rankings)} 個排序 → {len(fused_results)} 個結果")
        
        return fused_results
    
    # ==================== A4: MMR 去重 ====================
    def maximal_marginal_relevance(
        self,
        documents: List[Dict[str, Any]],
        lambda_param: float = 0.7,
        similarity_threshold: float = 0.85,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        MMR (Maximal Marginal Relevance) 多樣性重排
        
        平衡相關性和多樣性：
        MMR = λ * Relevance - (1-λ) * max(Similarity)
        
        Args:
            documents: 待重排的文檔列表
            lambda_param: 相關性權重（0.7 = 70% 相關性 + 30% 多樣性）
            similarity_threshold: 相似度閾值，超過則認為重複
            max_results: 最大返回數量
            
        Returns:
            MMR 重排後的文檔列表
        """
        if not documents:
            return []
        
        selected = []
        remaining = documents.copy()
        
        # 選擇第一個（最相關的）
        selected.append(remaining.pop(0))
        
        while remaining and len(selected) < max_results:
            best_score = -float('inf')
            best_idx = -1
            
            for idx, doc in enumerate(remaining):
                # 相關性分數
                relevance = doc.get('_rrf_score', doc.get('_confidence', 0))
                
                # 與已選文檔的最大相似度
                max_similarity = 0.0
                for selected_doc in selected:
                    sim = self._calculate_similarity(doc, selected_doc)
                    max_similarity = max(max_similarity, sim)
                
                # MMR 分數
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx >= 0:
                selected.append(remaining.pop(best_idx))
        
        logger.info(f"🎨 MMR 重排: {len(documents)} → {len(selected)} 個（λ={lambda_param}）")
        
        return selected
    
    # ==================== 輔助方法 ====================
    def _get_doc_id(self, doc: Dict[str, Any]) -> str:
        """獲取文檔唯一 ID"""
        # 嘗試多種可能的 ID 欄位
        for key in ['case_id', 'pid', 'rid', 'id', '_id']:
            if key in doc:
                return str(doc[key])
        
        # Fallback: 使用前幾個欄位的組合
        return hash(frozenset(doc.items()))
    
    def _calculate_similarity(
        self,
        doc1: Dict[str, Any],
        doc2: Dict[str, Any]
    ) -> float:
        """計算兩個文檔的相似度"""
        # 基於症狀的 Jaccard 相似度
        symptoms1 = set(doc1.get('_hits', []))
        symptoms2 = set(doc2.get('_hits', []))
        
        if not symptoms1 or not symptoms2:
            return 0.0
        
        intersection = len(symptoms1 & symptoms2)
        union = len(symptoms1 | symptoms2)
        
        return intersection / union if union > 0 else 0.0
    
    # ==================== A4: 完整檢索流程 ====================
    async def optimized_retrieval(
        self,
        search_engine,
        query: str,
        vector: Optional[List[float]],
        round_num: int,
        symptom_count: int,
        coverage: float = 0.0
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        優化後的完整檢索流程
        
        流程：
        1. 計算動態 α
        2. 多庫並行檢索（取 k=30）
        3. RRF 融合
        4. MMR 去重
        5. 返回 Top-10
        """
        # 1. 計算動態 α
        alpha_case = self.calculate_dynamic_alpha(
            round_num, symptom_count, coverage, False
        )
        alpha_pulse = alpha_case
        alpha_rpcase = alpha_case
        
        # 2. 並行檢索（擴大 Top-k）
        case_hits = await search_engine.hybrid_search(
            index="TCMCase",
            text=query,
            vector=vector,
            alpha=alpha_case,
            limit=self.config.initial_k,
            search_fields=["symptom_terms", "syndrome_terms", "pulse_terms"],
            return_props=["case_id", "diagnosis", "symptom_terms", "syndrome_terms"]
        )
        
        pulse_hits = await search_engine.hybrid_search(
            index="PulsePJ",
            text=query,
            vector=vector,
            alpha=alpha_pulse,
            limit=self.config.initial_k,
            search_fields=["bm25_cjk"],
            return_props=["pid", "name", "symptoms"]
        )
        
        rpcase_hits = await search_engine.hybrid_search(
            index="RPCase",
            text=query,
            vector=vector,
            alpha=alpha_rpcase,
            limit=self.config.initial_k,
            search_fields=["bm25_text"],
            return_props=["rid", "final_diagnosis", "symptom_tags"]
        )
        
        # 檢查 RPCase 是否為空，需要重搜
        if not rpcase_hits and coverage < 0.4:
            logger.info("🔄 RPCase 為空且覆蓋率低，降低 α 重搜")
            alpha_rpcase_retry = alpha_rpcase * 0.8
            rpcase_hits = await search_engine.hybrid_search(
                index="RPCase",
                text=query,
                vector=vector,
                alpha=alpha_rpcase_retry,
                limit=self.config.initial_k,
                search_fields=["bm25_text"],
                return_props=["rid", "final_diagnosis", "symptom_tags"]
            )
        
        # 3. RRF 融合（針對每個庫）
        case_fused = self.reciprocal_rank_fusion([case_hits], self.config.rrf_k)
        pulse_fused = self.reciprocal_rank_fusion([pulse_hits], self.config.rrf_k)
        rpcase_fused = self.reciprocal_rank_fusion([rpcase_hits], self.config.rrf_k)
        
        # 4. MMR 去重
        case_final = self.maximal_marginal_relevance(
            case_fused,
            self.config.mmr_lambda,
            self.config.mmr_threshold,
            self.config.final_k
        )
        pulse_final = self.maximal_marginal_relevance(
            pulse_fused,
            self.config.mmr_lambda,
            self.config.mmr_threshold,
            self.config.final_k
        )
        rpcase_final = self.maximal_marginal_relevance(
            rpcase_fused,
            self.config.mmr_lambda,
            self.config.mmr_threshold,
            self.config.final_k
        )
        
        logger.info(f"✅ 優化檢索完成:")
        logger.info(f"   TCMCase: {len(case_hits)} → {len(case_final)}")
        logger.info(f"   PulsePJ: {len(pulse_hits)} → {len(pulse_final)}")
        logger.info(f"   RPCase: {len(rpcase_hits)} → {len(rpcase_final)}")
        
        return {
            "case": case_final,
            "pulse": pulse_final,
            "rpcase": rpcase_final,
            "alpha_used": {
                "case": alpha_case,
                "pulse": alpha_pulse,
                "rpcase": alpha_rpcase
            }
        }