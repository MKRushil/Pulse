import { useState, useRef, useEffect } from "react";
import { SendHorizontal, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";


export default function DiagnosisChat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    { from: "bot", text: "您好，請描述您的症狀或想詢問的健康問題。" },
  ]);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async () => {
    if (!input.trim() || loading) return;
    console.log("觸發 send", input); // debug
    setMessages((m) => [...m, { from: "user", text: input }]);
    setLoading(true);
    const question = input;
    setInput("");
    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });
      if (!res.ok) throw new Error("伺服器錯誤");
      const data = await res.json();
      console.log('API回傳', data);
      setMessages((m) => [
        ...m,
        {
          from: "bot",
          text: data.dialog || data.answer || "[系統] 未取得回應，請稍候再試。",
        },
      ]);
    } catch (err) {
      console.error("fetch 錯誤", err);
      setMessages((m) => [
        ...m,
        { from: "bot", text: `[系統錯誤] ${err?.message || "無法取得診斷結果，請確認網路或稍後再試。"}` },
      ]);
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col flex-1 h-full max-h-full">
      <div className="text-2xl font-bold px-8 pt-8 pb-4 tracking-wider">診斷對話</div>
      <div className="flex-1 overflow-y-auto px-8 pb-4">
        <div className="space-y-4">
          {messages.map((msg, i) => (
            <ChatBubble key={i} msg={msg} />
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 px-6 py-4 rounded-[1.5rem] shadow border bg-blue-100 text-blue-500 animate-pulse">
                <Loader2 className="animate-spin" size={22} />
                <span>思考中…</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
      </div>
      <div className="flex items-center gap-2 p-6 border-t border-blue-100 bg-white/80">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") send(); }}
          className="flex-1 rounded-xl bg-blue-50 px-4 py-3 outline-none text-lg text-blue-900 placeholder:text-blue-400 border border-blue-200"
          placeholder="請輸入您的症狀描述或提問..."
        />
        <button
          onClick={send}
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
      <div
        className={`relative max-w-[75%] px-6 py-4 rounded-[1.5rem] shadow-md border text-base leading-relaxed
        ${msg.from === "user"
          ? "bg-gradient-to-br from-blue-400 to-blue-600 border-blue-400 text-white"
          : "bg-gradient-to-br from-blue-100 to-blue-200 border-blue-200 text-blue-900"}
        after:absolute after:bottom-0 after:w-0 after:h-0 after:border-solid
        ${msg.from === "user"
          ? "after:right-[-10px] after:border-l-[14px] after:border-l-blue-600 after:border-t-[14px] after:border-t-transparent"
          : "after:left-[-10px] after:border-r-[14px] after:border-r-blue-100 after:border-t-[14px] after:border-t-transparent"}
        `}
      >
        {msg.from === "bot"
          ? <ReactMarkdown>{msg.text}</ReactMarkdown>
          : msg.text
        }
      </div>
    </div>
  );
}

