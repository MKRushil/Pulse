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
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (continueSpiral = false) => {
    if ((!input.trim() && !continueSpiral) || loading) return;

    console.log("觸發 send", { input, continueSpiral, sessionId, currentRound });

    // 如果不是繼續推理，添加用戶訊息
    if (!continueSpiral && input.trim()) {
      setMessages((m) => [...m, { from: "user", text: input }]);
    } else if (continueSpiral) {
      setMessages((m) => [...m, { 
        from: "user", 
        text: `🔄 繼續第 ${currentRound + 1} 輪螺旋推理`, 
        type: "continue" 
      }]);
    }

    setLoading(true);
    const question = continueSpiral ? `繼續推理上一個問題` : input;
    if (!continueSpiral) setInput("");

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
          llmStruct: data.llm_struct
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
      setTimeout(resetSession, 2000);

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

  const resetSession = async () => {
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
    <div className="h-full flex flex-col bg-gradient-to-b from-blue-50 to-green-50">
      {/* 標題列與狀態 */}
      <header className="bg-white border-b border-gray-200 p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-800">🌀 螺旋推理診斷</h2>
            <p className="text-sm text-gray-600">智慧中醫輔助診斷系統 v2.0</p>
          </div>
          
          {/* 狀態指示器 */}
          {sessionId && (
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-gray-600">第 {currentRound} 輪</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-gray-600">已用案例：{usedCasesCount}</span>
              </div>
              <button
                onClick={resetSession}
                className="flex items-center space-x-1 px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                title="重置會話"
              >
                <X size={14} />
                <span>重置</span>
              </button>
            </div>
          )}
        </div>
      </header>

      {/* 對話區域 */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.from === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-4xl px-4 py-3 rounded-lg shadow-sm ${
              msg.from === "user" 
                ? "bg-blue-500 text-white" 
                : msg.type === "error"
                ? "bg-red-50 border border-red-200 text-gray-800"
                : msg.type === "success"
                ? "bg-green-50 border border-green-200 text-gray-800"
                : msg.type === "system" 
                ? "bg-yellow-50 border border-yellow-200 text-gray-800"
                : "bg-white border border-gray-200 text-gray-800"
            }`}>
              <div className="prose max-w-none text-sm">
                <ReactMarkdown>{msg.text}</ReactMarkdown>
              </div>
              
              {/* 診斷結果的操作按鈕區 */}
              {msg.type === "diagnosis" && (
                <div className="mt-4 pt-3 border-t border-gray-200 flex items-center justify-between">
                  <div className="text-xs text-gray-500 space-y-1">
                    <div>推理輪次：{msg.round} | 處理時間：{msg.sessionInfo?.processing_time_ms}ms</div>
                    <div>案例使用：{usedCasesCount}/10 | 會話：{sessionId?.split('_').pop()}</div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {/* 儲存案例按鈕 */}
                    <button
                      onClick={saveCase}
                      disabled={savingCase || loading}
                      className="flex items-center space-x-1 px-3 py-1 bg-green-100 hover:bg-green-200 text-green-700 rounded-lg transition-colors text-sm disabled:opacity-50"
                      title="儲存此診斷結果為新案例"
                    >
                      {savingCase ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                      <span>儲存案例</span>
                    </button>
                    
                    {/* 繼續推理按鈕 */}
                    {msg.continueAvailable && (
                      <button
                        onClick={() => send(true)}
                        disabled={loading}
                        className="flex items-center space-x-1 px-3 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg transition-colors text-sm"
                        title="繼續螺旋推理"
                      >
                        <RotateCcw size={14} />
                        <span>繼續推理</span>
                      </button>
                    )}
                  </div>
                </div>
              )}
              
              {/* 推理結束指示 */}
              {msg.type === "diagnosis" && !msg.continueAvailable && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-xs text-green-600">
                      <CheckCircle2 size={14} />
                      <span>螺旋推理完成</span>
                    </div>
                    <button
                      onClick={saveCase}
                      disabled={savingCase}
                      className="flex items-center space-x-1 px-3 py-1 bg-green-100 hover:bg-green-200 text-green-700 rounded-lg transition-colors text-sm"
                    >
                      {savingCase ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                      <span>儲存案例</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* 載入指示器 */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 px-4 py-3 rounded-lg shadow-sm">
              <div className="flex items-center space-x-2">
                <Loader2 size={16} className="animate-spin text-blue-500" />
                <span className="text-sm text-gray-600">
                  {continueAvailable ? `正在進行第 ${currentRound + 1} 輪推理...` : "正在分析症狀..."}
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* 輸入區域 */}
      <footer className="bg-white border-t border-gray-200 p-4">
        <div className="flex space-x-2">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                sessionId 
                  ? "描述新的症狀或條件..." 
                  : "請詳細描述您的症狀（如：主訴、現病史、望聞問切等）..."
              }
              className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={2}
              disabled={loading}
            />
          </div>
          
          <div className="flex flex-col space-y-2">
            <button
              onClick={() => send(false)}
              disabled={!input.trim() || loading}
              className="px-4 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center"
              title="發送新問題"
            >
              <SendHorizontal size={20} />
            </button>
            
            {continueAvailable && !loading && (
              <button
                onClick={() => send(true)}
                disabled={loading}
                className="px-4 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center"
                title="繼續螺旋推理"
              >
                <RotateCcw size={20} />
              </button>
            )}
          </div>
        </div>
        
        <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
          <span>按 Enter 發送，Shift+Enter 換行</span>
          {sessionId && (
            <span>會話ID: {sessionId.split('_').pop()} | 輪次: {currentRound}/{usedCasesCount < 10 ? '10' : '已滿'}</span>
          )}
        </div>
      </footer>
    </div>
  );
}
