import { useState, useRef, useEffect } from "react";
import { SendHorizontal, Loader2, RotateCcw, CheckCircle2, Save, X } from "lucide-react";
import ReactMarkdown from "react-markdown";

export default function DiagnosisChat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    { 
      from: "bot", 
      text: "🌀 **S-CBR 螺旋推理診斷系統 v2.0**\n\n您好！我是中醫智慧輔助診斷系統。請描述您的症狀，我將通過螺旋推理為您提供診斷建議。\n\n💡 **使用說明**：\n- 每輪推理後，您可以選擇繼續深入推理\n- 系統會自動過濾已使用的案例\n- 滿意結果後可儲存為新案例",
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
  const [conversationContext, setConversationContext] = useState(null);
  const [isFollowUp, setIsFollowUp] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (continueSpiral = false, isFollowUpQuestion = false) => {
    if ((!input.trim() && !continueSpiral) || loading) return;

    console.log("觸發 send", { input, continueSpiral, sessionId, currentRound });

    let question;
    if (continueSpiral) {
      setMessages((m) => [...m, { 
        from: "user", 
        text: `🔄 繼續第 ${currentRound + 1} 輪螺旋推理`, 
        type: "continue" 
      }]);
      question = `繼續推理上一個問題`;
    } else if (isFollowUpQuestion && conversationContext) {
      // 🔧 將新輸入作為補充條件
      question = `${conversationContext.originalQuery}。補充條件：${input}`;
      setMessages((m) => [...m, { from: "user", text: `📝 補充條件：${input}` }]);
      setIsFollowUp(true);
    } else {
      // 全新問題
      setMessages((m) => [...m, { from: "user", text: input }]);
      question = input;
      setConversationContext({
        originalQuery: input,
        timestamp: new Date().toISOString()
      });
      setIsFollowUp(false);
    }

    setLoading(true);
    if (!continueSpiral && !isFollowUpQuestion) setInput("");

    try {
      const requestBody = {
        question,
        session_id: sessionId,
        continue: continueSpiral,
        patient_ctx: {}
      };

      console.log("發送請求", requestBody);

      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody)
      });

      if (!res.ok) {
        const errorData = await res.text();
        throw new Error(`伺服器錯誤 (${res.status}): ${errorData}`);
      }

      const data = await res.json();
      console.log('API回傳', data);

      // 更新狀態
      setSessionId(data.session_id);
      setCurrentRound(data.round || 0);
      setContinueAvailable(data.continue_available || false);
      setUsedCasesCount(data.session_info?.used_cases_count || 0);
      setCurrentDiagnosis(data.llm_struct || {});

      // 構建回應訊息
      const responseText = data.dialog || data.answer || "[系統] 未取得回應，請稍候再試。";
      
      setMessages((m) => [
        ...m,
        { 
          from: "bot", 
          text: responseText,
          type: "diagnosis",
          round: data.round,
          continueAvailable: data.continue_available,
          sessionInfo: data.session_info,
          llmStruct: data.llm_struct,
          evaluationMetrics: data.evaluation_metrics  // 🔧 新增評估指標
        }
      ]);

    } catch (err) {
      console.error("fetch 錯誤", err);
      setMessages((m) => [
        ...m,
        { 
          from: "bot", 
          text: `❌ **系統錯誤**\n\n${err?.message || "無法取得診斷結果，請確認網路或稍後再試。"}`,
          type: "error"
        }
      ]);
    }

    setLoading(false);
  };

  const addCondition = () => {
    if (conversationContext && input.trim()) {
      send(false, true); // 作為補充條件發送
    }
  };

  const saveCase = async () => {
    if (!currentDiagnosis || !sessionId) return;
    
    setSavingCase(true);
    try {
      const saveBody = {
        session_id: sessionId,
        diagnosis: currentDiagnosis,
        conversation_history: messages,
        save_as_rpcase: true
      };

      const res = await fetch("/api/case/save-feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(saveBody)
      });

      if (!res.ok) throw new Error(`儲存失敗: ${res.status}`);

      const result = await res.json();
      console.log("案例儲存成功", result);

      setMessages((m) => [
        ...m,
        { 
          from: "bot", 
          text: `✅ **案例已儲存**\n\n診斷結果已成功儲存為回饋案例，將協助未來類似問題的推理。\n\n案例ID: ${result.case_id || '自動生成'}`,
          type: "success"
        }
      ]);

      // 儲存後重置會話
      setTimeout(endReasoning, 2000);

    } catch (err) {
      console.error("儲存案例錯誤", err);
      setMessages((m) => [
        ...m,
        { 
          from: "bot", 
          text: `❌ **儲存失敗**\n\n${err?.message || "無法儲存案例，請稍後再試。"}`,
          type: "error"
        }
      ]);
    }
    setSavingCase(false);
  };

  // 🔧 一鍵結束推理
  const endReasoning = async () => {
    try {
      if (sessionId) {
        await fetch("/api/spiral-reset", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId })
        });
      }
      
      // 重置所有狀態
      setSessionId(null);
      setCurrentRound(0);
      setContinueAvailable(false);
      setUsedCasesCount(0);
      setCurrentDiagnosis(null);
      setConversationContext(null);
      setIsFollowUp(false);
      setMessages([
        { 
          from: "bot", 
          text: "🔄 **會話已重置**\n\n請重新描述您的症狀，開始新的螺旋推理診斷。",
          type: "system"
        }
      ]);
      
      console.log("會話已重置");
    } catch (err) {
      console.error("重置會話失敗", err);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(false);
    }
  };

  return (
    <div className="flex flex-col flex-1 h-full max-h-full">
      {/* 🔧 添加頂部操作欄 */}
      <div className="flex justify-between items-center px-8 py-4 border-b border-gray-200">
        <h1 className="text-2xl font-bold tracking-wider">螺旋推理診斷</h1>
        
        {sessionId && (
          <button
            onClick={endReasoning}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 
                       text-white rounded-lg transition-colors"
          >
            <X size={18} />
            結束推理
          </button>
        )}
      </div>

      {/* 對話區域 */}
      <div className="flex-1 overflow-y-auto px-8 pb-4">
        <div className="space-y-4">
          {messages.map((msg, i) => (
            <div key={i}>
              <ChatBubble key={i} msg={msg} />
              
              {/* 診斷結果的操作按鈕區 */}
              {msg.type === "diagnosis" && (
                <div className="mt-4 space-y-2">
                  <div className="text-xs text-blue-600 font-medium">
                    推理輪次：{msg.round} | 處理時間：{msg.sessionInfo?.processing_time_ms}ms
                    <br />
                    案例使用：{usedCasesCount}/10 | 會話：{sessionId?.split('_').pop()}
                  </div>
                  
                  {/* 🔧 顯示評估指標 */}
                  {msg.evaluationMetrics && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                      <h4 className="font-semibold text-blue-800 mb-3">📊 評估指標</h4>
                      <div className="space-y-3">
                        {Object.entries(msg.evaluationMetrics).map(([key, metric]) => (
                          <div key={key} className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="font-medium text-blue-700">
                                {metric.abbreviation} ({metric.name})
                              </div>
                              <div className="text-sm text-blue-600">
                                {metric.description}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="font-bold text-lg text-blue-800">
                                {metric.score}/{metric.max_score}
                              </div>
                              <div className="w-20 bg-gray-200 rounded-full h-2 mt-1">
                                <div 
                                  className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                                  style={{ width: `${(metric.score / metric.max_score) * 100}%` }}
                                ></div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="flex gap-2 mt-3">
                    {/* 儲存案例按鈕 */}
                    <button
                      onClick={saveCase}
                      disabled={savingCase}
                      className="flex items-center gap-1 px-3 py-1 bg-green-500 hover:bg-green-600 
                                text-white text-sm rounded transition-colors disabled:opacity-50"
                    >
                      {savingCase ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                      儲存案例
                    </button>
                    
                    {/* 繼續推理按鈕 */}
                    {msg.continueAvailable && (
                      <button
                        onClick={() => send(true)}
                        disabled={loading}
                        className="flex items-center gap-1 px-3 py-1 bg-blue-500 hover:bg-blue-600 
                                  text-white text-sm rounded transition-colors disabled:opacity-50"
                      >
                        <RotateCcw size={14} />
                        繼續推理
                      </button>
                    )}
                  </div>
                </div>
              )}
              
              {/* 推理結束指示 */}
              {msg.type === "diagnosis" && !msg.continueAvailable && (
                <div className="flex items-center justify-center mt-4 p-3 bg-green-50 
                              border border-green-200 rounded-lg">
                  <div className="flex items-center gap-2 text-green-700">
                    <CheckCircle2 size={18} />
                    <span className="font-medium">螺旋推理完成</span>
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* 載入指示器 */}
          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 px-6 py-4 rounded-1.5rem shadow border 
                            bg-blue-100 text-blue-500 animate-pulse">
                <Loader2 className="animate-spin" size={22} />
                <span>
                  {continueAvailable ? `正在進行第 ${currentRound + 1} 輪推理...` : "正在分析症狀..."}
                </span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>
      </div>

      {/* 🔧 修改輸入區域，添加補充條件按鈕 */}
      <div className="flex items-center gap-2 p-6 border-t border-blue-100">
        <input 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          className="flex-1 rounded-xl bg-blue-50 px-4 py-3 outline-none text-lg"
          placeholder={
            conversationContext 
              ? "添加補充條件..." 
              : "請描述您的症狀..."
          }
        />
        
        {/* 補充條件按鈕 */}
        {conversationContext && (
          <button
            onClick={addCondition}
            className="bg-green-500 hover:bg-green-600 text-white p-3 rounded-xl 
                       transition-colors flex items-center gap-2"
            disabled={loading || !input.trim()}
          >
            <span>補充</span>
          </button>
        )}
        
        {/* 原有發送按鈕 */}
        <button
          onClick={() => send(false)}
          className="bg-blue-600 hover:bg-blue-700 transition p-3 rounded-xl"
          disabled={loading}
          type="button"
        >
          <SendHorizontal size={20} />
        </button>
      </div>
    </div>
  );
}

function ChatBubble({ msg }) {
  return (
    <div className={`flex ${msg.from === "user" ? "justify-end" : "justify-start"}`}>
      <div className={`relative max-w-75% px-6 py-4 rounded-1.5rem shadow-md border text-base leading-relaxed ${
        msg.from === "user" 
          ? "bg-gradient-to-br from-blue-400 to-blue-600 border-blue-400 text-white" 
          : "bg-gradient-to-br from-blue-100 to-blue-200 border-blue-200 text-blue-900"
      } after:absolute after:bottom-0 after:w-0 after:h-0 after:border-solid ${
        msg.from === "user"
          ? "after:right--10px after:border-l-14px after:border-l-blue-600 after:border-t-14px after:border-t-transparent"
          : "after:left--10px after:border-r-14px after:border-r-blue-100 after:border-t-14px after:border-t-transparent"
      }`}>
        {msg.from === "bot" ? (
          <ReactMarkdown>{msg.text}</ReactMarkdown>
        ) : (
          msg.text
        )}
      </div>
    </div>
  );
}
