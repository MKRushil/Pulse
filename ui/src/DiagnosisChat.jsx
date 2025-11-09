import { useState, useRef, useEffect } from "react";
import { SendHorizontal, Loader2, RotateCcw, CheckCircle2, Save, X, Plus, ShieldAlert } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { analyzeInput, analyzeOutput } from "./security/llmSafety.js";

export default function DiagnosisChat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    { 
      from: "bot", 
      text: "🌀 **S-CBR 螺旋推理診斷系統 v2.0**\n\n您好！我是中醫智慧輔助診斷系統。請描述您的症狀，我將通過螺旋推理為您提供診斷建議。\n\n💡 **使用說明**：\n- 每輪推理後，您可以補充條件繼續深入推理\n- 系統會自動累積問題進行收斂\n- 滿意結果後可儲存為新案例",
      type: "system"
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [currentRound, setCurrentRound] = useState(0);
  const [continueAvailable, setContinueAvailable] = useState(false);
  const [usedCasesCount, setUsedCasesCount] = useState(0);
  const [savingCase, setSavingCase] = useState(false);
  const [currentDiagnosis, setCurrentDiagnosis] = useState(null);
  const [hasStarted, setHasStarted] = useState(false); // 新增：是否已開始對話
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (isSupplementary = false) => {
    if (!input.trim() || loading) return;

    // Client-side OWASP checks before sending
    const analysis = analyzeInput(input.trim());
    if (analysis.blocked) {
      setMessages((m) => [
        ...m,
        {
          from: "bot",
          type: "error",
          text: `❌ **拒絕回答**\n\n為保護安全，您的輸入被拒絕。\n\n原因：\n- ${analysis.reasons.join("\n- ")}\n\n請僅輸入與中醫症狀有關的描述，避免提供個資/指令/程式碼。`
        }
      ]);
      return;
    }

    const safeText = analysis.maskedText || input.trim();
    const question = isSupplementary && sessionId
      ? `補充條件：${safeText}`  // 補充條件格式
      : safeText;

    // 添加用戶消息
    setMessages((m) => [...m, { 
      from: "user", 
      text: isSupplementary ? `📝 補充條件：${input}` : input,
      type: isSupplementary ? "supplement" : "normal"
    }]);

    setLoading(true);
    setInput("");
    
    // 設置已開始對話
    if (!hasStarted) {
      setHasStarted(true);
    }

    try {
      const requestBody = {
        question,
        session_id: sessionId,
        continue: isSupplementary && sessionId ? true : false,  // 補充時設為true
        patient_ctx: {}
      };

      console.log("發送請求", requestBody);

      const res = await fetch("/api/scbr/v2/diagnose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          session_id: sessionId,
          continue_spiral: Boolean(isSupplementary && sessionId),
          patient_ctx: {}
        })
      });

      if (!res.ok) {
        let errBody = null;
        try { errBody = await res.json(); } catch (_) {}
        const detail = errBody?.detail || errBody;
        const apiErr = (typeof detail === "string" ? detail : (detail?.message || detail?.error));
        const status = res.status;

        const friendly = apiErr || (
          status === 403 ? "本次輸入已被系統安全規則拒絕，請僅描述中醫症狀。" :
          status === 429 ? "請求過於頻繁，請稍後再試。" :
          `伺服器錯誤 (${status})`
        );

        setMessages((m) => [
          ...m,
          { from: "bot", type: "error", text: `❌ **拒絕回答**\n\n${friendly}` }
        ]);
        setLoading(false);
        return;
      }

      const data = await res.json();
      console.log('API回傳', data);

      // Even if 200, backend may signal error in body
      if (data?.error) {
        const friendly = data?.message || data?.error || "本次輸入被拒絕，請僅描述中醫症狀。";
        setMessages((m) => [
          ...m,
          { from: "bot", type: "error", text: `❌ **拒絕回答**\n\n${friendly}` }
        ]);
        setLoading(false);
        return;
      }

      // 更新狀態
      setSessionId(data.session_id);
      setCurrentRound(data.round || 1);
      setContinueAvailable(data.continue_available !== false); // 預設為true除非明確false
      setUsedCasesCount(data.used_cases_count || currentRound);
      setCurrentDiagnosis(data);

      // 構建回應訊息
      const rawResponse = data.final_text || data.text || data.answer || "[系統] 未取得回應";
      const out = analyzeOutput(rawResponse);
      const responseText = out.sanitizedText;
      
      setMessages((m) => [
        ...m,
        { 
          from: "bot", 
          text: responseText,
          type: "diagnosis",
          round: data.round || currentRound,
          continueAvailable: data.continue_available !== false,
          converged: data.converged,
          convergenceMetrics: data.convergence_metrics
        }
      ]);

      if (out.warnings?.length) {
        setMessages((m) => [
          ...m,
          {
            from: "bot",
            type: "warning",
            text: `⚠️ **安全提示**\n\n${out.warnings.map((w) => `- ${w}`).join("\n")}`
          }
        ]);
      }

    } catch (err) {
      console.error("fetch 錯誤", err);
      setMessages((m) => [
        ...m,
        { 
          from: "bot", 
          text: `❌ **系統錯誤**\n\n${err?.message || "無法取得診斷結果"}`,
          type: "error"
        }
      ]);
    }

    setLoading(false);
  };

  const saveCase = async () => {
    if (!currentDiagnosis || !sessionId) return;
    
    setSavingCase(true);
    try {
      const saveBody = {
        session_id: sessionId,
        diagnosis: currentDiagnosis,
        conversation_history: messages
      };

      const res = await fetch("/api/case/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(saveBody)
      });

      if (!res.ok) throw new Error(`儲存失敗: ${res.status}`);

      setMessages((m) => [
        ...m,
        { 
          from: "bot", 
          text: `✅ **案例已儲存**\n\n診斷結果已成功儲存為回饋案例。`,
          type: "success"
        }
      ]);

      setTimeout(endReasoning, 2000);

    } catch (err) {
      console.error("儲存案例錯誤", err);
      setMessages((m) => [
        ...m,
        { 
          from: "bot", 
          text: `❌ **儲存失敗**\n\n${err?.message}`,
          type: "error"
        }
      ]);
    }
    setSavingCase(false);
  };

  const endReasoning = () => {
    // 重置所有狀態
    setSessionId(null);
    setCurrentRound(0);
    setContinueAvailable(false);
    setUsedCasesCount(0);
    setCurrentDiagnosis(null);
    setHasStarted(false);
    setMessages([
      { 
        from: "bot", 
        text: "🔄 **會話已重置**\n\n請重新描述您的症狀，開始新的螺旋推理診斷。",
        type: "system"
      }
    ]);
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(hasStarted);
    }
  };

  return (
    <div className="flex flex-col flex-1 h-full max-h-full">
      {/* 頂部操作欄 */}
      <div className="flex justify-between items-center px-8 py-4 border-b border-gray-200">
        <h1 className="text-2xl font-bold tracking-wider">螺旋推理診斷</h1>
        
        {sessionId && (
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              第 {currentRound} 輪推理
            </span>
            <button
              onClick={endReasoning}
              className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 
                       text-white rounded-lg transition-colors"
            >
              <X size={18} />
              結束推理
            </button>
          </div>
        )}
      </div>

      {/* 對話區域 */}
      <div className="flex-1 overflow-y-auto px-8 pb-4">
        <div className="space-y-4">
          {messages.map((msg, i) => (
            <div key={i}>
              <ChatBubble msg={msg} />
              
              {/* 診斷結果的操作按鈕區 */}
              {msg.type === "diagnosis" && (
                <div className="mt-4 space-y-2">
                  {/* 推理資訊 */}
                  <div className="text-xs text-blue-600 font-medium">
                    第 {msg.round} 輪推理 | 會話ID: {sessionId?.slice(-8)}
                  </div>
                  
                  {/* 收斂度指標 */}
                  {msg.convergenceMetrics && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                      <div className="text-sm">
                        <span className="font-semibold">收斂度：</span>
                        <span className="ml-2">
                          {(() => {
                            const m = msg.convergenceMetrics || {};
                            const val = typeof m.Final === 'number' ? m.Final : (typeof m.overall_convergence === 'number' ? m.overall_convergence : 0);
                            return `${(val * 100).toFixed(1)}%`;
                          })()}
                        </span>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                          <div 
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ 
                              width: (() => {
                                const m = msg.convergenceMetrics || {};
                                const val = typeof m.Final === 'number' ? m.Final : (typeof m.overall_convergence === 'number' ? m.overall_convergence : 0);
                                return `${val * 100}%`;
                              })()
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* 操作按鈕 */}
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={saveCase}
                      disabled={savingCase}
                      className="flex items-center gap-1 px-3 py-1 bg-green-500 hover:bg-green-600 
                                text-white text-sm rounded transition-colors disabled:opacity-50"
                    >
                      {savingCase ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                      儲存案例
                    </button>
                  </div>
                  
                  {/* 收斂完成提示 - 只在明確收斂時顯示 */}
                  {msg.converged === true && (
                    <div className="flex items-center justify-center mt-4 p-3 bg-green-50 
                                  border border-green-200 rounded-lg">
                      <div className="flex items-center gap-2 text-green-700">
                        <CheckCircle2 size={18} />
                        <span className="font-medium">已達收斂標準</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {/* 載入指示器 */}
          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 px-6 py-4 rounded-2xl shadow border 
                            bg-blue-100 text-blue-500 animate-pulse">
                <Loader2 className="animate-spin" size={22} />
                <span>正在進行第 {currentRound + 1} 輪推理...</span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>
      </div>

      {/* 輸入區域 */}
      <div className="flex items-center gap-2 p-6 border-t border-blue-100">
        <input 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          className="flex-1 rounded-xl bg-blue-50 px-4 py-3 outline-none text-lg"
          placeholder={hasStarted ? "補充症狀或條件..." : "請描述您的症狀..."}
        />
        
        <button
          onClick={() => send(hasStarted)}
          className={`${
            hasStarted 
              ? "bg-green-500 hover:bg-green-600" 
              : "bg-blue-600 hover:bg-blue-700"
          } text-white p-3 rounded-xl transition-colors flex items-center gap-2`}
          disabled={loading || !input.trim()}
          type="button"
        >
          {hasStarted ? (
            <>
              <Plus size={20} />
              <span className="text-sm font-medium">補充</span>
            </>
          ) : (
            <SendHorizontal size={20} />
          )}
        </button>
      </div>
    </div>
  );
}

function ChatBubble({ msg }) {
  return (
    <div className={`flex ${msg.from === "user" ? "justify-end" : "justify-start"}`}>
      <div className={`relative max-w-[75%] px-6 py-4 rounded-2xl shadow-md border text-base leading-relaxed ${
        msg.from === "user" 
          ? "bg-gradient-to-br from-blue-400 to-blue-600 border-blue-400 text-white" 
          : "bg-gradient-to-br from-blue-100 to-blue-200 border-blue-200 text-blue-900"
      }`}>
        {msg.from === "bot" ? (
          <div>
            {msg.type === "warning" && (
              <div className="flex items-center gap-2 mb-2 text-amber-700">
                <ShieldAlert size={16} />
                <span className="text-sm font-medium">安全檢查</span>
              </div>
            )}
            <ReactMarkdown>{msg.text}</ReactMarkdown>
          </div>
        ) : (
          msg.text
        )}
      </div>
    </div>
  );
}
