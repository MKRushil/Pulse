# -*- coding: utf-8 -*-
"""
TCM Case Schema Definition
中醫病例資料模型與 Weaviate Collection Schema
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import weaviate
from weaviate.classes.config import Configure, Property, DataType, VectorDistances


# ============================================
# Pydantic Models for API Validation
# ============================================

class BasicInfo(BaseModel):
    """基本資料"""
    name: str
    gender: str
    age: str
    idLast4: str = Field(..., min_length=4, max_length=4)
    phone: Optional[str] = ""
    visitDate: str


class ComplaintInfo(BaseModel):
    """主訴與病史"""
    chiefComplaint: str
    presentIllness: Optional[str] = ""
    medicalHistory: Optional[str] = ""
    familyHistory: Optional[str] = ""


class InspectionInfo(BaseModel):
    """望診"""
    spirit: str = "正常"
    bodyShape: List[str] = []
    faceColor: Optional[str] = ""
    tongueBody: List[str] = []
    tongueCoating: List[str] = []
    tongueShape: List[str] = []
    tongueNote: Optional[str] = ""


class AuscultationInfo(BaseModel):
    """聞診"""
    voice: str = "正常"
    breath: str = "正常"
    cough: bool = False
    coughNote: Optional[str] = ""


class InquiryInfo(BaseModel):
    """問診"""
    chills: Optional[str] = ""
    sweat: Optional[str] = ""
    head: Optional[str] = ""
    body: Optional[str] = ""
    stool: Optional[str] = ""
    urine: Optional[str] = ""
    appetite: Optional[str] = ""
    sleep: Optional[str] = ""
    thirst: Optional[str] = ""
    gynecology: Optional[str] = ""


class DiagnosisInfo(BaseModel):
    """辨證論治"""
    syndromePattern: List[str] = []
    zangfuPattern: List[str] = []
    diagnosis: Optional[str] = ""
    treatment: Optional[str] = ""
    suggestion: Optional[str] = ""  # 診斷建議 (取代方劑與藥物)


class TCMCaseInput(BaseModel):
    """前端提交的病例資料"""
    basic: BasicInfo
    complaint: ComplaintInfo
    inspection: InspectionInfo
    auscultation: AuscultationInfo
    inquiry: InquiryInfo
    pulse: Dict[str, List[str]] = {}  # 脈診 {部位: [脈象列表]}
    diagnosis: DiagnosisInfo


# ============================================
# Weaviate Collection Schema
# ============================================

def create_tcm_case_collection(client: weaviate.WeaviateClient, collection_name: str = "TCMCase"):
    """
    創建 TCM Case Collection
    
    設計理念:
    1. 混合搜索: 向量相似度 + BM25 關鍵詞
    2. Jieba 分詞結果存儲為多個字段以支援精確搜索
    3. 結構化資料保留原始 JSON 以便完整檢索
    """
    
    # 檢查是否已存在
    if client.collections.exists(collection_name):
        print(f"✅ Collection '{collection_name}' 已存在")
        return client.collections.get(collection_name)
    
    # 創建 Collection
    collection = client.collections.create(
        name=collection_name,
        description="中醫病例資料庫 - 支援混合搜索與結構化查詢",
        
        # 向量化配置 - 使用 text2vec-transformers 或外部向量
        vectorizer_config=None,  # 我們會使用外部 NVIDIA Embedding API
        
        properties=[
            # ==================== 基本資訊 ====================
            Property(
                name="case_id",
                data_type=DataType.TEXT,
                description="病例唯一ID",
                skip_vectorization=True,
                index_searchable=True
            ),
            Property(
                name="patient_id",
                data_type=DataType.TEXT,
                description="患者匿名ID (基於身分證末4碼生成)",
                skip_vectorization=True,
                index_searchable=True
            ),
            Property(
                name="visit_date",
                data_type=DataType.DATE,
                description="就診日期",
                skip_vectorization=True
            ),
            Property(
                name="age",
                data_type=DataType.INT,
                description="年齡",
                skip_vectorization=True
            ),
            Property(
                name="gender",
                data_type=DataType.TEXT,
                description="性別",
                skip_vectorization=True,
                index_searchable=True
            ),
            
            # ==================== 向量搜索欄位 ====================
            Property(
                name="full_text",
                data_type=DataType.TEXT,
                description="完整病歷文本 (用於向量化)",
                skip_vectorization=False,  # 此欄位會被向量化
                index_searchable=True
            ),
            
            # ==================== Jieba 分詞結果 (BM25 搜索) ====================
            Property(
                name="jieba_tokens",
                data_type=DataType.TEXT_ARRAY,
                description="Jieba 分詞結果 (所有詞彙)",
                skip_vectorization=True,
                index_searchable=True
            ),
            Property(
                name="syndrome_terms",
                data_type=DataType.TEXT_ARRAY,
                description="證型術語 (如: 風寒感冒、氣虛)",
                skip_vectorization=True,
                index_searchable=True
            ),
            Property(
                name="zangfu_terms",
                data_type=DataType.TEXT_ARRAY,
                description="臟腑術語 (如: 肝鬱、脾虛)",
                skip_vectorization=True,
                index_searchable=True
            ),
            Property(
                name="symptom_terms",
                data_type=DataType.TEXT_ARRAY,
                description="症狀術語",
                skip_vectorization=True,
                index_searchable=True
            ),
            Property(
                name="pulse_terms",
                data_type=DataType.TEXT_ARRAY,
                description="脈象術語",
                skip_vectorization=True,
                index_searchable=True
            ),
            Property(
                name="tongue_terms",
                data_type=DataType.TEXT_ARRAY,
                description="舌象術語",
                skip_vectorization=True,
                index_searchable=True
            ),
            Property(
                name="treatment_terms",
                data_type=DataType.TEXT_ARRAY,
                description="治法術語",
                skip_vectorization=True,
                index_searchable=True
            ),
            
            # ==================== 結構化欄位 (精確查詢) ====================
            Property(
                name="chief_complaint",
                data_type=DataType.TEXT,
                description="主訴",
                skip_vectorization=True,
                index_searchable=True
            ),
            Property(
                name="diagnosis",
                data_type=DataType.TEXT,
                description="診斷",
                skip_vectorization=True,
                index_searchable=True
            ),
            Property(
                name="treatment_principle",
                data_type=DataType.TEXT,
                description="治法",
                skip_vectorization=True,
                index_searchable=True
            ),
            Property(
                name="suggestion",
                data_type=DataType.TEXT,
                description="診斷建議",
                skip_vectorization=True,
                index_searchable=True
            ),
            
            # ==================== 原始 JSON 資料 ====================
            Property(
                name="raw_data",
                data_type=DataType.TEXT,
                description="原始病例 JSON (完整保留)",
                skip_vectorization=True,
                index_searchable=False
            ),
            
            # ==================== 元數據 ====================
            Property(
                name="created_at",
                data_type=DataType.DATE,
                description="建立時間",
                skip_vectorization=True
            ),
            Property(
                name="updated_at",
                data_type=DataType.DATE,
                description="更新時間",
                skip_vectorization=True
            ),
        ],
        
        # 向量索引配置
        vector_index_config=Configure.VectorIndex.hnsw(
            distance_metric=VectorDistances.COSINE,  # ← 使用 enum
            ef_construction=128,
            ef=64
        ),
        
        # 倒排索引配置 (支援 BM25)
        inverted_index_config=Configure.inverted_index(
            bm25_b=0.75,
            bm25_k1=1.2,
            index_null_state=True,
            index_property_length=True,
            index_timestamps=True
        )
    )
    
    print(f"✅ Collection '{collection_name}' 創建成功")
    return collection


# ============================================
# Case Data Object for Weaviate
# ============================================

class TCMCaseData:
    """準備上傳到 Weaviate 的病例資料"""
    
    @staticmethod
    def prepare_for_upload(
        case_input: TCMCaseInput,
        case_id: str,
        jieba_analysis: Dict[str, Any],
        embedding_vector: List[float]
    ) -> Dict[str, Any]:
        """
        將前端資料轉換為 Weaviate 資料對象
        
        Args:
            case_input: 前端提交的病例
            case_id: 病例ID
            jieba_analysis: Jieba 分詞分析結果
            embedding_vector: 1024維向量
        
        Returns:
            Weaviate 資料對象
        """
        import json
        from datetime import datetime
        
        # 生成患者匿名 ID
        patient_id = f"P_{case_input.basic.idLast4}_{case_input.basic.age}_{case_input.basic.gender}"
        
        # 構建完整文本 (用於向量化)
        full_text = TCMCaseData._build_full_text(case_input)
        
        # 提取年齡數字
        try:
            age_int = int(case_input.basic.age)
        except:
            age_int = 0
        
        # 準備資料對象
        data_obj = {
            "case_id": case_id,
            "patient_id": patient_id,
            "visit_date": datetime.fromisoformat(case_input.basic.visitDate).isoformat(),
            "age": age_int,
            "gender": case_input.basic.gender,
            
            "full_text": full_text,
            
            # Jieba 分詞結果
            "jieba_tokens": jieba_analysis.get("all_tokens", []),
            "syndrome_terms": jieba_analysis.get("syndrome", []),
            "zangfu_terms": jieba_analysis.get("zangfu", []),
            "symptom_terms": jieba_analysis.get("symptom", []),
            "pulse_terms": jieba_analysis.get("pulse", []),
            "tongue_terms": jieba_analysis.get("tongue", []),
            "herb_terms": jieba_analysis.get("herb", []),
            "formula_terms": jieba_analysis.get("formula", []),
            
            # 結構化欄位
            "chief_complaint": case_input.complaint.chiefComplaint,
            "diagnosis": case_input.diagnosis.diagnosis or "",
            "treatment_principle": case_input.diagnosis.treatment or "",
            "suggestion": case_input.diagnosis.suggestion or "",
            
            # 原始資料
            "raw_data": json.dumps(case_input.dict(), ensure_ascii=False),
            
            # 元數據
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        return data_obj, embedding_vector
    
    @staticmethod
    def _build_full_text(case: TCMCaseInput) -> str:
        """構建完整文本用於向量化"""
        parts = []
        
        # 基本資訊
        parts.append(f"性別{case.basic.gender} 年齡{case.basic.age}歲")
        
        # 主訴與病史
        parts.append(f"主訴: {case.complaint.chiefComplaint}")
        if case.complaint.presentIllness:
            parts.append(f"現病史: {case.complaint.presentIllness}")
        
        # 望診
        if case.inspection.bodyShape:
            parts.append(f"體型: {' '.join(case.inspection.bodyShape)}")
        if case.inspection.faceColor:
            parts.append(f"面色: {case.inspection.faceColor}")
        if case.inspection.tongueBody:
            parts.append(f"舌體: {' '.join(case.inspection.tongueBody)}")
        if case.inspection.tongueCoating:
            parts.append(f"舌苔: {' '.join(case.inspection.tongueCoating)}")
        
        # 聞診
        if case.auscultation.cough:
            parts.append(f"咳嗽: {case.auscultation.coughNote}")
        
        # 問診
        for key, val in case.inquiry.dict().items():
            if val:
                parts.append(f"{key}: {val}")
        
        # 脈診
        pulse_desc = []
        for pos, types in case.pulse.items():
            if types:
                pulse_desc.append(f"{pos} {' '.join(types)}")
        if pulse_desc:
            parts.append(f"脈象: {'; '.join(pulse_desc)}")
        
        # 辨證
        if case.diagnosis.syndromePattern:
            parts.append(f"證型: {' '.join(case.diagnosis.syndromePattern)}")
        if case.diagnosis.zangfuPattern:
            parts.append(f"臟腑: {' '.join(case.diagnosis.zangfuPattern)}")
        if case.diagnosis.diagnosis:
            parts.append(f"診斷: {case.diagnosis.diagnosis}")
        if case.diagnosis.treatment:
            parts.append(f"治法: {case.diagnosis.treatment}")
        if case.diagnosis.suggestion:
            parts.append(f"建議: {case.diagnosis.suggestion}")
        
        return " ".join(parts)