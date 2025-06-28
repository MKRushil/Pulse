import { useState, useRef, useEffect } from "react";
import { User, SendHorizontal, Loader2 } from "lucide-react";

export default function CaseChat() {
  // 狀態管理
  const [locked, setLocked] = useState(false); // 是否已鎖定個案
  const [idInput, setIdInput] = useState("");
  const [input, setInput] = useState("");
  const [patient, setPatient] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [idError, setIdError] = useState("");
  const idInputRef = useRef(null);
  const chatInputRef = useRef(null);
  const chatEndRef = useRef(null);

  // 模擬病患查詢資料
  const mockPatients = [
    { id: "A1234", name: "林小明", gender: "男", age: 35, lastVisit: "2025-06-15" },
    { id: "B9876", name: "王美麗", gender: "女", age: 42, lastVisit: "2025-05-29" },
  ];

  // 自動聚焦
  useEffect(() => {
    if (!locked && idInputRef.current) idInputRef.current.focus();
    if (locked && chatInputRef.current) chatInputRef.current.focus();
  }, [locked]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // 查詢個案（只用前4碼）
  const handleSearch = () => {
    if (!/^[A-Z][0-9]{3}$/.test(idInput.trim())) {
      setIdError("格式錯誤，請輸入1碼大寫英+3碼數字");
      return;
    }
    setIdError("");
    const found = mockPatients.find(p => p.id.startsWith(idInput.trim()));
    if (!found) {
      setMessages([{ from: "bot", text: "查無此病人，請確認前4碼。" }]);
      setIdInput("");
      return;
    }
    setPatient(found);
    setLocked(true);
    setMessages([
      { from: "bot", text: `您好，這裡是${found.name}的專屬對話。請輸入您的問題或補充資訊。` },
    ]);
    setIdInput("");
  };

  // 聊天送出
  const handleSend = () => {
    if (!input.trim() || loading || !patient) return;
    setMessages((m) => [...m, { from: "user", text: input }]);
    setLoading(true);
    setInput("");
    setTimeout(() => {
      setMessages((m) => [
        ...m,
        {
          from: "bot",
          text: `【AI回覆】您的補充內容：「${input}」已記錄，若需進一步診斷請詳述症狀。`,
        },
      ]);
      setLoading(false);
    }, 1000);
  };

  // 退出
  const handleExit = () => {
    setLocked(false);
    setPatient(null);
    setMessages([]);
    setInput("");
    setIdInput("");
    setIdError("");
    if (idInputRef.current) idInputRef.current.focus();
  };

  return (
    <div className="flex flex-col flex-1 h-full max-h-full">
      {/* 個案卡＋退出鈕 */}
      {locked && patient && (
        <div className="flex items-center gap-6 bg-blue-100 border border-blue-300 rounded-2xl px-6 py-4 m-8 mb-0 shadow">
          <User size={28} className="text-blue-500" />
          <div className="flex flex-col text-blue-900">
            <div><span className="font-bold">姓名：</span>{patient.name}</div>
            <div><span className="font-bold">身分證：</span>{patient.id}</div>
            <div><span className="font-bold">性別：</span>{patient.gender}　<span className="font-bold">年齡：</span>{patient.age}</div>
            <div><span className="font-bold">最近就診：</span>{patient.lastVisit}</div>
          </div>
          <button onClick={handleExit} className="ml-auto px-4 py-2 bg-blue-200 text-blue-800 rounded-lg hover:bg-blue-300">退出</button>
        </div>
      )}
      {/* 對話區塊 */}
      <div className="flex-1 overflow-y-auto px-8 pb-4">
        <div className="space-y-4">
          {!locked && (
            <div className="text-blue-400 mb-3">請先輸入病人身分證前4碼，才能開始個案對話。</div>
          )}
          {messages.map((msg, i) => (<ChatBubble key={i} msg={msg} />))}
          {loading && locked && (
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
      {/* 下方唯一輸入欄，分段顯示+自動 focus */}
      <form
        className="flex items-center gap-2 p-6 border-t border-blue-100 bg-white/80"
        onSubmit={e => { e.preventDefault(); locked ? handleSend() : handleSearch(); }}
      >
        {!locked ? (
          <>
            <input
              type="text"
              ref={idInputRef}
              value={idInput}
              onChange={e => setIdInput(e.target.value.toUpperCase())}
              maxLength={4}
              className={`flex-1 rounded-xl bg-blue-50 px-4 py-3 outline-none text-lg text-blue-900 placeholder:text-blue-400 border ${idError ? 'border-red-400' : 'border-blue-200'}`}
              placeholder="請輸入病人身分證前4碼（大寫英數）..."
              autoFocus
            />
            <button type="submit" className="bg-blue-600 hover:bg-blue-700 transition p-3 rounded-xl text-white">搜尋</button>
          </>
        ) : (
          <>
            <input
              ref={chatInputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              className="flex-1 rounded-xl bg-blue-50 px-4 py-3 outline-none text-lg text-blue-900 placeholder:text-blue-400 border border-blue-200"
              placeholder="請輸入您的問題或補充資訊..."
              autoFocus
            />
            <button type="submit" className="bg-blue-600 hover:bg-blue-700 transition p-3 rounded-xl text-white" disabled={loading || !patient}>
              <SendHorizontal size={20} />
            </button>
          </>
        )}
      </form>
      {!locked && idError && (
        <div className="text-red-500 text-sm px-8 pb-2">{idError}</div>
      )}
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
        {msg.text}
      </div>
    </div>
  );
}
