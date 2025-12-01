# -*- coding: utf-8 -*-
"""
統一的 LLM 客戶端 - 安全增強版本

主要安全功能：
- LLM01: 防止提示詞注入
- LLM02: 輸出內容過濾
- LLM07: 系統提示詞保護
- LLM10: Token 限制與超時控制
"""

import aiohttp,asyncio
import json
import re
import hashlib
from typing import List, Dict, Optional, Any
from ..config import SCBRConfig
from ..utils.logger import get_logger

logger = get_logger("LLMClient")

class LLMClient:
    """
    統一的 LLM 客戶端 - 安全增強版本
    
    安全機制：
    1. 輸入隔離：用戶輸入與系統提示詞嚴格分離
    2. 輸出過濾：檢測並移除敏感系統資訊洩露
    3. Token 限制：防止資源耗盡攻擊
    4. 超時控制：防止長時間掛起
    5. 錯誤隔離：不洩露技術細節給用戶
    """
    
    def __init__(self, config: SCBRConfig):
        """
        初始化 LLM 客戶端
        
        Args:
            config: S-CBR 配置對象
        """
        self.config = config
        self.url = self._build_url(config.llm.api_url)
        self.headers = {
            "Authorization": f"Bearer {config.llm.api_key}",
            "Content-Type": "application/json"
        }
        self.model = config.llm.model
        
        # ✅ 安全限制
        self.max_tokens = min(config.llm.max_tokens, 4000)  # 硬性上限 2000
        self.timeout = min(config.llm.timeout, 60)  # 最多 60 秒
        self.max_retries = 2  # 最多重試 2 次

        # ✅ 可配置的輸入長度上限（依 19.md）
        # 若 config.llm 具備 max_input_chars 即使用之；否則預設 12000
        self.max_input_chars = getattr(config.llm, "max_input_chars", 12000)
        
        # ✅ 敏感資訊檢測模式
        self._setup_sensitive_patterns()
        
        logger.info(f"✅ LLM客戶端初始化: model={self.model}, max_tokens={self.max_tokens}, timeout={self.timeout}s")

        # 最近一次原始/過濾後輸出（供四層 L1 追蹤用）
        self._last_raw_output: Optional[str] = None
        self._last_filtered_output: Optional[str] = None
        self._last_is_l1: bool = False
        
    def _setup_sensitive_patterns(self):
        """
        設置敏感資訊檢測模式
        用於輸出過濾，防止洩露系統資訊
        """
        self.sensitive_patterns = [
            # API 相關
            r'(?i)(api[_\s-]?key|bearer[_\s]+token|authorization[_\s]*:)',
            r'sk-[a-zA-Z0-9]{48}',  # OpenAI API key pattern
            
            # 系統提示詞相關
            r'(?i)(system[_\s]*(prompt|instruction|message|role))',
            r'(?i)(你是|you are).{0,50}(系統|system|assistant)',
            r'(?i)根據我的(指令|instructions|prompts)',
            
            # 內部路徑/配置
            r'/(?:home|root|etc|var|usr)/[a-zA-Z0-9/_-]+',
            r'(?i)config\.(yaml|json|py|ini)',
            
            # 技術細節
            r'(?i)(weaviate|embedding|vector\s+database)',
            r'(?i)(model\s*=|temperature\s*=|top_p\s*=)',
            
            # 策略層/生成層洩露
            r'strategy_layer|generation_layer',
            r'(?i)llm_rules\.yaml'
        ]
        
        # 編譯正則表達式以提高效能
        self.compiled_patterns = [
            re.compile(pattern) for pattern in self.sensitive_patterns
        ]
        
    def _build_url(self, base_url: str) -> str:
        """
        構建完整 API URL
        
        Args:
            base_url: 基礎 URL
            
        Returns:
            完整的 API endpoint URL
        """
        base = base_url.rstrip("/")
        
        # 如果已經是完整的 completions endpoint，直接返回
        if base.endswith("/chat/completions"):
            return base
        
        # 針對 NVIDIA API 的特殊處理
        if "nvidia" in base:
            if "/v1" in base:
                return f"{base}/chat/completions"
            return f"{base}/v1/chat/completions"
        
        # 預設：添加 /chat/completions
        return f"{base}/chat/completions"
    
    def _sanitize_system_prompt(self, system_prompt: str) -> str:
        """
        淨化系統提示詞，移除可能的注入內容
        
        Args:
            system_prompt: 原始系統提示詞
            
        Returns:
            淨化後的系統提示詞
        """
        # 移除可能的提示詞注入標記
        injection_markers = [
            "```",
            "<|im_start|>",
            "<|im_end|>",
            "---END---",
            "###OVERRIDE###"
        ]
        
        sanitized = system_prompt
        for marker in injection_markers:
            sanitized = sanitized.replace(marker, "")
        
        return sanitized.strip()
    
    def _sanitize_user_input(self, user_prompt: str) -> str:
        """
        淨化用戶輸入，防止提示詞注入
        
        Args:
            user_prompt: 用戶輸入
            
        Returns:
            淨化後的用戶輸入
        """
        # 檢測並移除常見的注入模式
        dangerous_patterns = [
            r'(?i)ignore\s+(previous|above|prior)\s+(instructions?|commands?)',
            r'(?i)disregard\s+(the\s+)?(above|previous)',
            r'(?i)forget\s+(everything|all|previous)',
            r'(?i)你現在是|you\s+are\s+now',
            r'(?i)system\s*:|assistant\s*:',
            r'(?i)show\s+me\s+your\s+(prompt|instructions?)',
            r'(?i)reveal\s+your\s+(prompt|instructions?)',
        ]
        
        sanitized = user_prompt
        for pattern in dangerous_patterns:
            if re.search(pattern, sanitized):
                logger.warning(f"⚠️ 檢測到可疑注入模式: {pattern}")
                # 移除匹配的內容
                sanitized = re.sub(pattern, "[已移除]", sanitized)
        
        return sanitized.strip()
    
    def _filter_sensitive_output(self, output: str) -> str:
        """
        過濾輸出中的敏感資訊
        
        Args:
            output: LLM 原始輸出
            
        Returns:
            過濾後的安全輸出
        """
        filtered = output
        violations_found = []
        
        # 檢查所有敏感模式
        for pattern in self.compiled_patterns:
            matches = pattern.findall(filtered)
            if matches:
                violations_found.extend(matches)
                # 用安全占位符替換
                filtered = pattern.sub("[系統資訊已隱藏]", filtered)
        
        # 如果發現敏感資訊，記錄日誌
        if violations_found:
            logger.warning(f"⚠️ 輸出過濾：檢測到 {len(violations_found)} 處敏感資訊")
            logger.debug(f"   敏感模式: {violations_found[:3]}")  # 只記錄前3個
        
        return filtered
    
    def _truncate_if_too_long(self, text: str, max_chars: int = 30000) -> str:
        """
        如果文本過長，進行截斷
        
        Args:
            text: 輸入文本
            max_chars: 最大字符數
            
        Returns:
            截斷後的文本
        """
        if len(text) <= max_chars:
            return text
        
        logger.warning(f"⚠️ 輸入過長，從 {len(text)} 截斷至 {max_chars} 字符")
        return text[:max_chars] + "...[內容過長已截斷]"
    
    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        執行聊天完成 - 安全增強版本
        
        安全流程：
        1. 淨化系統提示詞
        2. 淨化用戶輸入（防注入）
        3. 長度檢查與截斷
        4. 調用 LLM API
        5. 輸出過濾（移除敏感資訊）
        6. 錯誤隔離（不洩露技術細節）
        
        Args:
            system_prompt: 系統提示詞（策略層或生成層）
            user_prompt: 用戶輸入
            temperature: 溫度參數
            
        Returns:
            LLM 響應內容（已過濾敏感資訊）
        """
        
        # ==================== STEP 1: 輸入淨化 ====================
        clean_system = self._sanitize_system_prompt(system_prompt)
        clean_user = self._sanitize_user_input(user_prompt)
        
        # ==================== STEP 2: 長度檢查 ====================
        # 依設定值截斷輸入（不再硬碼 3000）
        clean_user = self._truncate_if_too_long(clean_user, max_chars=self.max_input_chars)
        
        # ==================== STEP 3: 構建請求 ====================
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": clean_system},
                {"role": "user", "content": clean_user}
            ],
            "max_tokens": self.max_tokens,
            "temperature": temperature if temperature is not None else self.config.llm.temperature
        }
        
        logger.debug(f"📤 發送 LLM 請求: model={self.model}, tokens≤{self.max_tokens}")
        
        # ==================== STEP 4: 調用 API（含重試） ====================
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.url,
                        headers=self.headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        
                        # 檢查 HTTP 狀態碼
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"❌ LLM API 錯誤 {response.status}: {error_text[:200]}")
                            
                            # 如果是速率限制，不重試
                            if response.status == 429:
                                return self._get_fallback_response(error_type="rate_limited")
                            
                            # 其他錯誤，記錄並重試
                            last_error = f"HTTP {response.status}"
                            continue
                        
                        # 解析響應
                        data = await response.json()
                        
                        if "choices" in data and data["choices"]:
                            raw_content = data["choices"][0]["message"]["content"]
                            
                            # ==================== STEP 5: 輸出過濾 ====================
                            filtered_content = self._filter_sensitive_output(raw_content)

                            # 記錄最近一次輸出（供 L1 追蹤比較）
                            try:
                                self._last_raw_output = raw_content
                                self._last_filtered_output = filtered_content
                                # 嘗試判定是否為 L1 請求（user_prompt JSON 內含 layer=L1_GATE）
                                self._last_is_l1 = '"layer": "L1_GATE"' in clean_user or '"layer":"L1_GATE"' in clean_user
                            except Exception:
                                pass
                            
                            logger.debug(f"📥 LLM 響應成功 (過濾後: {len(filtered_content)} 字符)")
                            return filtered_content
                        else:
                            logger.error(f"❌ LLM 響應格式錯誤: {data}")
                            last_error = "Invalid response format"
                            continue
                        
            except asyncio.TimeoutError:
                logger.error(f"⏱️ LLM 請求超時 (嘗試 {attempt + 1}/{self.max_retries + 1})")
                last_error = "Timeout"
                continue
                
            except aiohttp.ClientError as e:
                logger.error(f"🌐 LLM 網路錯誤: {e}")
                last_error = str(e)
                continue
                
            except Exception as e:
                logger.error(f"❌ LLM 處理錯誤: {e}")
                import traceback
                traceback.print_exc()
                last_error = str(e)
                break  # 未知錯誤不重試
        
        # ==================== STEP 6: 所有重試失敗，返回備用響應 ====================
        logger.error(f"❌ LLM 調用失敗（已重試 {self.max_retries} 次）: {last_error}")
        return self._get_fallback_response(error_type="general_failure")
    
    def _get_fallback_response(self, error_type: str = "general_failure") -> str:
        """
        獲取備用響應（當 LLM 調用失敗時）
        
        注意：不洩露技術細節，僅返回對用戶有意義的訊息
        
        Args:
            error_type: 錯誤類型
            
        Returns:
            安全的備用響應
        """
        fallback_map = {
            "rate_limited": (
                "診斷結果：系統當前負載較高，請稍候再試。\n"
                "建議：請在幾分鐘後重新提交診斷請求。"
            ),
            "timeout": (
                "診斷結果：診斷處理超時，建議簡化症狀描述後重試。\n"
                "建議：請描述最主要的1-3個症狀。"
            ),
            "general_failure": (
                "診斷結果：證型待定。\n"
                "建議：調整作息，保持情緒穩定，清淡飲食。\n"
                "如症狀持續或加重，請及時就醫。"
            )
        }
        
        return fallback_map.get(error_type, fallback_map["general_failure"])
    
    async def batch_complete(
        self,
        prompts: List[Dict[str, str]],
        temperature: Optional[float] = None
    ) -> List[str]:
        """
        批量完成請求（用於並行處理多個推理任務）
        
        Args:
            prompts: 提示詞列表，每個元素為 {"system": ..., "user": ...}
            temperature: 溫度參數
            
        Returns:
            響應列表
        """
        import asyncio
        
        tasks = [
            self.chat_complete(
                system_prompt=p["system"],
                user_prompt=p["user"],
                temperature=temperature
            )
            for p in prompts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 將異常轉換為備用響應
        processed_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ 批量請求 {idx} 失敗: {result}")
                processed_results.append(self._get_fallback_response())
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_token_count_estimate(self, text: str) -> int:
        """
        估算文本的 Token 數量
        簡單估算：1 token ≈ 1.5 個中文字符
        
        Args:
            text: 輸入文本
            
        Returns:
            估算的 token 數量
        """
        # 粗略估算：中文字符 / 1.5
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        english_chars = len(text) - chinese_chars
        
        # 中文 1.5 char/token，英文 4 char/token
        estimated_tokens = int(chinese_chars / 1.5 + english_chars / 4)
        
        return estimated_tokens
    
    def is_within_token_limit(self, system_prompt: str, user_prompt: str) -> bool:
        """
        檢查輸入是否在 token 限制內
        
        Args:
            system_prompt: 系統提示詞
            user_prompt: 用戶輸入
            
        Returns:
            是否在限制內
        """
        total_input_tokens = (
            self.get_token_count_estimate(system_prompt) +
            self.get_token_count_estimate(user_prompt)
        )
        
        # 預留 max_tokens 用於輸出
        max_input_tokens = 4096 - self.max_tokens  # 假設 context window = 4096
        
        if total_input_tokens > max_input_tokens:
            logger.warning(
                f"⚠️ Token 限制警告: "
                f"輸入 {total_input_tokens} tokens > 限制 {max_input_tokens} tokens"
            )
            return False
        
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康檢查
        
        Returns:
            健康狀態資訊
        """
        return {
            "status": "healthy",
            "model": self.model,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "url": self.url[:50] + "..."  # 只顯示前50字符
        }

    # ==================== 四層管線相容層 ====================
    async def complete_json(self, system_prompt: str, user_prompt: Any, temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        四層 SCBR 專用相容方法：讀取系統提示詞與 payload，呼叫聊天完成，並嘗試將輸出解析為 JSON。
        """
        # 允許 dict/str 作為輸入
        if isinstance(user_prompt, (dict, list)):
            user_text = json.dumps(user_prompt, ensure_ascii=False)
        else:
            user_text = str(user_prompt)

        # 傳遞 temperature 參數
        text = await self.chat_complete(system_prompt=system_prompt, user_prompt=user_text, temperature=temperature)

        # 嘗試直接解析
        try:
            return json.loads(text)
        except Exception:
            pass

        # [增強版] JSON 提取邏輯：基於堆疊尋找最外層的 {} 或 []
        import re
        
        def _extract_outermost_json(text: str) -> str:
            stack = 0
            start = -1
            
            # 尋找第一個 { 或 [
            match = re.search(r'[\[\{]', text)
            if not match:
                return text
            
            start = match.start()
            opener = match.group()
            closer = '}' if opener == '{' else ']'
            
            # 從 start 開始掃描，尋找對應的結束符號
            # 注意：這裡忽略了字串內部的括號，對於簡單修復通常足夠
            # 若要更嚴謹需實作完整的狀態機，但這裡我們求快求穩
            for i, char in enumerate(text[start:], start):
                if char == opener:
                    stack += 1
                elif char == closer:
                    stack -= 1
                    if stack == 0:
                        return text[start:i+1]
            
            # 如果沒找到閉合的，返回從開始到最後的內容，交給後續修復
            return text[start:]

        seg = _extract_outermost_json(text)
        
        # 清理 Markdown code block
        seg = seg.strip()
        seg = re.sub(r"^```\s*json\s*", "", seg, flags=re.IGNORECASE)
        seg = re.sub(r"^```\s*", "", seg)
        seg = re.sub(r"\s*```\s*$", "", seg)
        seg = seg.strip()

        try:
            return json.loads(seg)
        except Exception:
            # 進入修復流程
            original_seg = seg

            # 1) 砍掉行尾 // 註解
            def _strip_line_comments(snippet: str) -> str:
                lines = []
                for line in snippet.splitlines():
                    if "//" in line:
                        line = line.split("//", 1)[0]
                    lines.append(line)
                return "\n".join(lines)

            # 2) 補引號（過濾器破壞的 key）
            def _quote_filtered_keys(snippet: str) -> str:
                fixed_lines = []
                for line in snippet.splitlines():
                    if ":" in line and "[系統資訊已隱藏]" in line:
                        prefix, rest = line.split(":", 1)
                        key = prefix.strip()
                        if not (key.startswith('"') and key.endswith('"')):
                            leading_ws = prefix[: len(prefix) - len(prefix.lstrip())]
                            qkey = '"' + key.replace('"', '\\"') + '"'
                            line = f"{leading_ws}{qkey}:{rest}"
                    fixed_lines.append(line)
                return "\n".join(fixed_lines)

            seg = _strip_line_comments(seg)
            
            # 值為 {...} / ... 的佔位改為合法字串
            placeholder = '"__omitted__"'
            seg = re.sub(r"(:\s*)\{\.\.\.\}(\s*[,}\]])", r"\1" + placeholder + r"\2", seg)
            seg = re.sub(r"(:\s*)\.\.\.(\s*[,}\]])", r"\1" + placeholder + r"\2", seg)
            
            seg = _quote_filtered_keys(seg)

            # 移除尾逗號
            seg = re.sub(r",\s*(\})", r"\1", seg)
            seg = re.sub(r",\s*(\])", r"\1", seg)

            # [增強版] 括號平衡修正 & 尾部垃圾清理
            def _balance_brackets(snippet: str) -> str:
                # 1. 簡單的堆疊平衡補全
                stack = []
                for ch in snippet:
                    if ch in '{[':
                        stack.append('}' if ch == '{' else ']')
                    elif ch in '}]':
                        if stack:
                            if stack[-1] == ch:
                                stack.pop()
                            # 如果不匹配，可能是多餘的閉合括號，這裡暫不處理
                if stack:
                    snippet += "".join(reversed(stack))
                return snippet

            seg = _balance_brackets(seg)

            # 最終嘗試
            try:
                return json.loads(seg)
            except json.JSONDecodeError as e:
                # [MODIFIED] 針對 "Unterminated string" 的增強型截斷修復
                # 判斷是否為字串未閉合 (截斷) 或 預期值錯誤
                if "Unterminated string" in str(e) or "Expecting value" in str(e):
                    logger.warning("⚠️ 檢測到 JSON 字串未閉合 (可能是 Token 截斷)，啟動截斷修復模式...")
                    
                    # 策略：因為截斷通常發生在最後一個欄位的 value 寫到一半
                    # 我們嘗試找到最後一個 "key": value 結構的結束點，或者直接砍到最後一個逗號前
                    
                    cleaned_seg = seg.strip()
                    
                    # 如果結尾不是閉合符號 (} 或 ])，大概率是被截斷了
                    if not cleaned_seg.endswith(('}', ']')):
                        # 尋找最後一個逗號 (假設它是分隔欄位的)
                        last_comma_index = cleaned_seg.rfind(',')
                        
                        if last_comma_index != -1:
                            # ✂️ 砍掉最後一個逗號之後的所有內容 (即捨棄最後一個被截斷的欄位)
                            truncated_seg = cleaned_seg[:last_comma_index]
                            
                            # 🔧 重新平衡括號 (利用上文定義的 _balance_brackets 補上缺少的 } 或 ])
                            fixed_seg = _balance_brackets(truncated_seg)
                            
                            logger.info(f"🔧 截斷修復：捨棄尾部並重組 -> ...{fixed_seg[-50:]}")
                            try:
                                return json.loads(fixed_seg)
                            except Exception as e2:
                                logger.warning(f"❌ 截斷修復失敗 (捨棄策略): {e2}")
                        
                        # 備用策略：如果找不到逗號（可能只有一個欄位就爆了），嘗試直接補引號
                        else:
                            # 嘗試補全引號和括號
                            try_fix = cleaned_seg + '"}' 
                            try_fix = _balance_brackets(try_fix)
                            try:
                                return json.loads(try_fix)
                            except:
                                pass

                # 如果還是失敗，記錄日誌並拋出
                try:
                    logger.error("❌ LLM JSON 解析失敗（修復前片段）：\n%s", original_seg)
                    # logger.error("❌ LLM JSON 解析失敗（修復後片段）：\n%s", seg) # 註解掉以免 Log 太長
                except Exception:
                    pass
                raise # 拋出異常讓上層處理
