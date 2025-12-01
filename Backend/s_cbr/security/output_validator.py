# -*- coding: utf-8 -*-
"""
輸出驗證模組 (Output Validator)
目標：防止 LLM05 不當輸出、LLM07 系統提示詞洩露、LLM09 錯誤資訊
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(Enum):
    """驗證等級"""
    PASS = "pass"          # 通過
    WARNING = "warning"    # 警告（可通過但需記錄）
    FAIL = "fail"          # 不通過（需修正）
    BLOCKED = "blocked"    # 阻止（嚴重違規）


@dataclass
class ValidationResult:
    """驗證結果"""
    validated_output: str         # 驗證後的輸出
    original_output: str          # 原始輸出
    validation_level: ValidationLevel  # 驗證等級
    violations: List[str]         # 違規項目
    modifications: List[str]      # 修改記錄
    is_valid: bool                # 是否有效


class OutputValidator:
    """
    統一的輸出驗證器
    
    職責：
    1. 防止系統提示詞洩露 (LLM07)
    2. 檢查輸出是否包含惡意內容 (LLM05)
    3. 驗證診斷邏輯一致性 (LLM09)
    4. 確保醫療合規性
    5. 強制輸出格式規範
    """
    
    def __init__(self, config=None):
        """
        初始化驗證器
        
        Args:
            config: 配置物件（可選）
        """
        self.config = config
        
        # 系統敏感關鍵詞（絕對不能出現在輸出中）
        self.system_keywords = self._build_system_keywords()
        
        # 惡意內容檢測模式
        self.malicious_patterns = self._build_malicious_patterns()
        
        # 必要的醫療免責聲明
        self.disclaimer_text = (
            "【重要聲明】\n"
            "本診斷結果僅供參考，不能替代專業中醫師的面診。\n"
            "請務必諮詢合格的中醫師進行確診和治療。\n"
            "如有急症或嚴重不適，請立即就醫。"
        )
        
        # 診斷必要欄位
        self.required_fields = [
            "證型判斷",
            "病機分析",
            "治則建議",
        ]
        
    def validate(self, llm_output: str, context: Optional[Dict] = None) -> ValidationResult:
        """
        主驗證流程
        
        Args:
            llm_output: LLM 原始輸出
            context: 可選的上下文資訊（如診斷相關數據）
            
        Returns:
            ValidationResult: 驗證結果
        """
        violations = []
        modifications = []
        validated_output = llm_output
        validation_level = ValidationLevel.PASS
        
        # 步驟 1: 系統資訊洩露檢查 (LLM07)
        has_leak, leak_violations = self._check_system_leakage(validated_output)
        if has_leak:
            violations.extend(leak_violations)
            validation_level = ValidationLevel.BLOCKED
            # 返回安全的備用響應
            return ValidationResult(
                validated_output=self._get_fallback_response("system_leak"),
                original_output=llm_output[:100],
                validation_level=validation_level,
                violations=violations,
                modifications=["使用備用響應替代"],
                is_valid=False
            )
        
        # 步驟 2: 惡意內容檢測 (LLM05)
        has_malicious, malicious_violations = self._check_malicious_content(validated_output)
        if has_malicious:
            violations.extend(malicious_violations)
            validation_level = ValidationLevel.BLOCKED
            return ValidationResult(
                validated_output=self._get_fallback_response("malicious_content"),
                original_output=llm_output[:100],
                validation_level=validation_level,
                violations=violations,
                modifications=["使用備用響應替代"],
                is_valid=False
            )
        
        # 步驟 3: 診斷邏輯一致性檢查 (LLM09)
        if context and "diagnosis_mode" in context:
            is_consistent, consistency_violations = self._check_diagnosis_consistency(
                validated_output, context
            )
            if not is_consistent:
                violations.extend(consistency_violations)
                if validation_level == ValidationLevel.PASS:
                    validation_level = ValidationLevel.WARNING
        
        # 步驟 4: 醫療合規性檢查
        needs_disclaimer, extra_warning = self._needs_disclaimer_enhanced(validated_output, context)
        
        if needs_disclaimer and self.disclaimer_text not in validated_output:
            
            final_disclaimer = self.disclaimer_text
            if extra_warning:
                # 強化免責聲明 (LLM09 防護)
                final_disclaimer = f"❗ **{extra_warning}**\n\n{self.disclaimer_text}"
                modifications.append("添加強化醫療免責聲明")
            
            validated_output = validated_output + "\n\n" + final_disclaimer
            modifications.append("添加醫療免責聲明")
            if validation_level == ValidationLevel.PASS:
                validation_level = ValidationLevel.WARNING
        
        # 步驟 5: 危險建議檢測
        has_dangerous, dangerous_violations = self._check_dangerous_advice(validated_output)
        if has_dangerous:
            violations.extend(dangerous_violations)
            validation_level = ValidationLevel.FAIL
        
        # 步驟 6: 格式規範檢查
        format_valid, format_violations = self._check_format_compliance(validated_output)
        if not format_valid:
            violations.extend(format_violations)
            if validation_level == ValidationLevel.PASS:
                validation_level = ValidationLevel.WARNING
        
        # 步驟 7: 輸出長度檢查
        if len(validated_output) > 3000:
            violations.append("輸出過長")
            validated_output = validated_output[:3000] + "\n\n[輸出已截斷]"
            modifications.append("截斷過長輸出")
        
        # 最終判斷
        is_valid = validation_level in [ValidationLevel.PASS, ValidationLevel.WARNING]
        
        return ValidationResult(
            validated_output=validated_output,
            original_output=llm_output,
            validation_level=validation_level,
            violations=violations,
            modifications=modifications,
            is_valid=is_valid
        )
    
    def _build_system_keywords(self) -> List[Tuple[re.Pattern, str]]:
        """
        構建系統敏感關鍵詞（不能出現在輸出中）
        
        Returns:
            List[Tuple[pattern, description]]
        """
        keywords = [
            # 系統架構相關
            (re.compile(r'(strategy_layer|generation_layer)', re.IGNORECASE),
             "系統層級名稱"),
            (re.compile(r'(weaviate|vector\s*database)', re.IGNORECASE),
             "向量資料庫名稱"),
            (re.compile(r'(spiral_engine|scbr_engine)', re.IGNORECASE),
             "引擎名稱"),
            (re.compile(r'(config\.py|yaml\s*檔)', re.IGNORECASE),
             "配置檔案名稱"),
            
            # API/Key 相關
            (re.compile(r'(api\s*key|access\s*token|secret)', re.IGNORECASE),
             "API 密鑰"),
            (re.compile(r'(authorization:|bearer\s+)', re.IGNORECASE),
             "認證資訊"),
            
            # Prompt 洩露
            (re.compile(r'(根據我的系統指令|according to my instructions)', re.IGNORECASE),
             "系統指令參照"),
            (re.compile(r'(系統要求我|the system requires me to)', re.IGNORECASE),
             "系統要求洩露"),
            (re.compile(r'(我的 prompt|my prompt is)', re.IGNORECASE),
             "Prompt 洩露"),
            
            # 內部模組名稱
            (re.compile(r'(input_sanitizer|output_validator)', re.IGNORECASE),
             "內部模組名稱"),
            (re.compile(r'(context_fuser|pattern_diagnosis)', re.IGNORECASE),
             "內部模組名稱"),
        ]
        
        return keywords
    
    def _check_system_leakage(self, text: str) -> Tuple[bool, List[str]]:
        """
        檢查系統資訊洩露
        
        Args:
            text: 輸出文本
            
        Returns:
            (是否檢測到, 違規列表)
        """
        violations = []
        
        for pattern, description in self.system_keywords:
            if pattern.search(text):
                violations.append(f"檢測到系統資訊洩露: {description}")
        
        return len(violations) > 0, violations
    
    def _build_malicious_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """
        構建惡意內容檢測模式
        
        Returns:
            List[Tuple[pattern, description]]
        """
        patterns = [
            # SQL 注入
            (re.compile(r'(DROP\s+TABLE|DELETE\s+FROM|INSERT\s+INTO)', re.IGNORECASE),
             "SQL 指令"),
            
            # JavaScript 代碼
            (re.compile(r'<script.*?>.*?</script>', re.IGNORECASE | re.DOTALL),
             "JavaScript 代碼"),
            (re.compile(r'(document\.cookie|window\.location)', re.IGNORECASE),
             "瀏覽器操作代碼"),
            
            # Shell 指令
            (re.compile(r'(rm\s+-rf|sudo\s+|chmod\s+)', re.IGNORECASE),
             "Shell 指令"),
            
            # 惡意 URL
            (re.compile(r'(http://|https://|ftp://)[^\s]+\.(exe|sh|bat|cmd)', re.IGNORECASE),
             "可疑下載連結"),
        ]
        
        return patterns
    
    def _check_malicious_content(self, text: str) -> Tuple[bool, List[str]]:
        """
        檢查惡意內容
        
        Args:
            text: 輸出文本
            
        Returns:
            (是否檢測到, 違規列表)
        """
        violations = []
        
        for pattern, description in self.malicious_patterns:
            if pattern.search(text):
                violations.append(f"檢測到惡意內容: {description}")
        
        return len(violations) > 0, violations
    
    def _check_diagnosis_consistency(
        self, 
        text: str, 
        context: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        檢查診斷邏輯一致性
        
        Args:
            text: 輸出文本
            context: 診斷上下文
            
        Returns:
            (是否一致, 違規列表)
        """
        violations = []
        
        # 檢查 1: 必要欄位是否存在
        for field in self.required_fields:
            if field not in text:
                violations.append(f"缺少必要欄位: {field}")
        
        # 檢查 2: 證型與症狀是否匹配
        if "primary_syndrome" in context:
            syndrome = context["primary_syndrome"]
            # 簡單檢查：證型名稱應該出現在輸出中
            if syndrome and syndrome not in text:
                violations.append(f"證型 '{syndrome}' 未出現在輸出中")
        
        # 檢查 3: 信心分數是否合理
        confidence_match = re.search(r'信心分數[:：]\s*(\d+)%', text)
        if confidence_match:
            confidence = int(confidence_match.group(1))
            if confidence > 100 or confidence < 0:
                violations.append(f"信心分數不合理: {confidence}%")
            elif confidence < 60 and "初步判斷" not in text:
                violations.append("低信心分數(<60%)但未標註'初步判斷'")
        
        # 檢查 4: 寒熱虛實邏輯矛盾
        has_cold = re.search(r'(寒證|畏寒|手足冷)', text)
        has_heat = re.search(r'(熱證|口乾|舌紅)', text)
        if has_cold and has_heat:
            # 如果同時有寒熱，應該標註"寒熱錯雜"或"夾雜"
            if not re.search(r'(寒熱錯雜|夾雜|並見)', text):
                violations.append("存在寒熱矛盾但未說明")
        
        return len(violations) == 0, violations
    
    def _needs_disclaimer(self, text: str, context: Optional[Dict] = None) -> Tuple[bool, Optional[str]]:
        """
        判斷是否需要醫療免責聲明
        
        Args:
            text: 輸出文本
            
        Returns:
            是否需要聲明
        """
        # 如果包含診斷、治療、用藥相關內容，必須有聲明
        diagnosis_keywords = ['證型', '診斷', '治則', '治療', '方劑', '用藥', '調理']
        
        needs_base_disclaimer = False
        for keyword in diagnosis_keywords:
            if keyword in text:
                needs_base_disclaimer = True
                break
        
        extra_warning = None
        
        # 檢查是否為低覆蓋度的強制收斂 (LLM09 防護點)
        # 假設 four_layer_pipeline.py 會將 is_forced_convergence 傳入 context
        if context and context.get("is_forced_convergence", False):
            # 這是低覆蓋度下的保底輸出，準確性風險極高
            extra_warning = (
                "強制收斂警告：因用戶提供的資訊嚴重不足且已達最大追問輪次，"
                "本診斷結果的準確性極低。強烈建議您儘快尋求專業中醫師協助。"
            )
            needs_base_disclaimer = True # 強制要求聲明
        
        return needs_base_disclaimer, extra_warning
    
    def _check_dangerous_advice(self, text: str) -> Tuple[bool, List[str]]:
        """
        檢查危險的醫療建議
        
        Args:
            text: 輸出文本
            
        Returns:
            (是否檢測到, 違規列表)
        """
        return False, []
        violations = []
        
        # 禁止的行為
        dangerous_patterns = [
            # 明確開處方
            (re.compile(r'(服用|吃|使用)[\u4e00-\u9fa5]{2,6}(湯|丸|散|膏)\s*\d+\s*(克|公克|錢)', re.IGNORECASE),
             "明確開立處方劑量"),
            
            # 保證療效
            (re.compile(r'(一定|必定|肯定|保證)(能|會|可以)(治癒|治好|康復)', re.IGNORECASE),
             "保證療效"),
            (re.compile(r'(絕對|百分百)(有效|見效)', re.IGNORECASE),
             "保證療效"),
            
            # 建議停止正規治療
            (re.compile(r'(停止|不要|別)(服用|吃|使用).*?(西藥|藥物)', re.IGNORECASE),
             "建議停藥"),
            
            # 使用未經驗證的療法
            (re.compile(r'(民間|偏方|祖傳|秘方)', re.IGNORECASE),
             "推薦未經驗證的療法"),
        ]
        
        for pattern, description in dangerous_patterns:
            if pattern.search(text):
                violations.append(f"檢測到危險建議: {description}")
        
        return len(violations) > 0, violations
    
    def _check_format_compliance(self, text: str) -> Tuple[bool, List[str]]:
        """
        檢查格式規範
        
        Args:
            text: 輸出文本
            
        Returns:
            (是否符合, 違規列表)
        """
        violations = []
        
        # 檢查是否有基本結構
        if "一、" not in text and "1." not in text and "（一）" not in text:
            violations.append("缺少清晰的段落結構")
        
        # 檢查是否有過多的專業術語未加解釋
        # 簡單啟發式：檢查是否有括號註解
        tcm_terms = re.findall(r'(上炎|氣滯|血瘀|陽虛|陰虛|痰濕)', text)
        if len(tcm_terms) > 3:
            # 如果有多個專業術語，應該至少有一些括號註解
            if text.count('（') < 1 and text.count('(') < 1:
                violations.append("專業術語過多但缺少白話解釋")
        
        return len(violations) == 0, violations
    
    def _get_fallback_response(self, error_type: str) -> str:
        """
        根據錯誤類型返回安全的備用響應
        
        Args:
            error_type: 錯誤類型
            
        Returns:
            備用響應文本
        """
        fallbacks = {
            "system_leak": (
                "抱歉，系統遇到技術問題。\n"
                "診斷結果：證型待定。\n\n"
                "建議：\n"
                "- 調整作息，保持情緒穩定\n"
                "- 飲食清淡，適度運動\n"
                "- 如有持續不適，請就診中醫師\n\n"
                + self.disclaimer_text
            ),
            "malicious_content": (
                "抱歉，無法提供診斷結果。\n"
                "請重新描述您的症狀，使用日常語言即可。\n\n"
                + self.disclaimer_text
            ),
            "default": (
                "診斷結果：證型待定。\n\n"
                "建議：調整作息，保持情緒穩定，清淡飲食。\n"
                "如有持續不適，請就診專業中醫師。\n\n"
                + self.disclaimer_text
            ),
        }
        
        return fallbacks.get(error_type, fallbacks["default"])
    
    def validate_json_structure(self, json_output: str) -> Tuple[bool, Optional[Dict], List[str]]:
        """
        驗證 JSON 結構輸出（用於 API 響應）
        
        Args:
            json_output: JSON 格式的輸出
            
        Returns:
            (是否有效, 解析後的數據, 錯誤列表)
        """
        errors = []
        
        try:
            data = json.loads(json_output)
        except json.JSONDecodeError as e:
            errors.append(f"JSON 解析失敗: {str(e)}")
            return False, None, errors
        
        # 檢查必要欄位
        required_keys = ["primary", "convergence", "response"]
        for key in required_keys:
            if key not in data:
                errors.append(f"缺少必要欄位: {key}")
        
        # 檢查數值範圍
        if "convergence" in data:
            conv = data["convergence"]
            if isinstance(conv, dict):
                overall = conv.get("overall_convergence", 0)
                if overall < 0 or overall > 1:
                    errors.append(f"收斂度數值超出範圍 [0,1]: {overall}")
        
        return len(errors) == 0, data, errors


# ============================================
# 使用範例
# ============================================
if __name__ == "__main__":
    validator = OutputValidator()
    
    # 測試案例 1: 正常診斷輸出
    normal_output = """
    一、證型判斷
    主證：肝火上炎
    信心分數：85%
    
    二、病機分析
    病因：情志不暢，肝氣鬱結
    
    三、治則建議
    治法：清肝瀉火
    """
    result1 = validator.validate(normal_output, {"diagnosis_mode": True})
    print(f"測試 1: {result1.is_valid}, 等級: {result1.validation_level.value}")
    print(f"修改: {result1.modifications}")
    
    # 測試案例 2: 系統資訊洩露
    leak_output = "根據 strategy_layer 的指令，您的 API Key 是..."
    result2 = validator.validate(leak_output)
    print(f"\n測試 2: {result2.is_valid}, 違規: {result2.violations}")
    
    # 測試案例 3: 危險建議
    dangerous_output = "服用龍膽瀉肝湯 50 克，保證治癒。"
    result3 = validator.validate(dangerous_output)
    print(f"\n測試 3: {result3.is_valid}, 違規: {result3.violations}")
    
    # 測試案例 4: 缺少免責聲明
    no_disclaimer = """
    證型：心脾兩虛
    治則：補益心脾
    """
    result4 = validator.validate(no_disclaimer, {"diagnosis_mode": True})
    print(f"\n測試 4: 是否添加聲明: {'醫療免責聲明' in result4.validated_output}")