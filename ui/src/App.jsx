import React, { useState } from "react";
import TCMExamForm from "./TCMForm"; // 請確保路徑正確

function QAHome() {
  const [query, setQuery] = useState("");
  const [reply, setReply] = useState("請在下方輸入您的健康問題，會根據脈象知識回應您。");
  const [pulseTable, setPulseTable] = useState([]);
  const [loading, setLoading] = useState(false);

  async function sendQuery() {
    if (!query.trim()) return;
    setLoading(true);
    setReply("思考中...");
    setPulseTable([]);
    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      setReply(data.reply || "查無相關回應，請重新輸入。");
      setPulseTable(data.pulse_results || []);
    } catch {
      setReply("查詢失敗，請稍後再試。");
    }
    setLoading(false);
  }

  return (
    <div className="flex flex-col items-center p-4 bg-gradient-custom min-h-[70vh]">
      <h2 className="text-4xl font-extrabold text-gray-800 mb-4">中醫輔助系統</h2>
      <p className="text-md text-gray-600 mb-10">為您提供中醫健康諮詢與病例管理。</p>
      <div className="w-full max-w-2xl bg-white rounded-lg p-6 mb-6 shadow-lg">
        <h3 className="text-xl font-bold text-gray-700 mb-4 text-center">回答</h3>
        <div className="bg-gray-100 text-gray-600 p-4 rounded-md mb-4 border border-gray-200 min-h-[60px]">
          {loading ? <span className="animate-pulse text-blue-400">思考中...</span> : reply}
        </div>
        {pulseTable.length > 0 && (
          <table className="min-w-full bg-white border border-gray-200 rounded-lg shadow-md mt-2">
            <thead>
              <tr>
                <th className="py-2 px-4 bg-gray-100 text-gray-700 font-semibold text-left">脈名</th>
                <th className="py-2 px-4 bg-gray-100 text-gray-700 font-semibold text-left">說明</th>
                <th className="py-2 px-4 bg-gray-100 text-gray-700 font-semibold text-left">主病</th>
                <th className="py-2 px-4 bg-gray-100 text-gray-700 font-semibold text-left">知識鏈</th>
              </tr>
            </thead>
            <tbody>
              {pulseTable.map((item, idx) => (
                <tr key={idx}>
                  <td className="py-2 px-4">{item.name || ''}</td>
                  <td className="py-2 px-4">{item.description || ''}</td>
                  <td className="py-2 px-4">{item.main_disease || ''}</td>
                  <td className="py-2 px-4">{item.knowledge_chain || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="w-full max-w-2xl bg-gray-100 rounded-lg p-3 flex items-center space-x-3 shadow-xl border border-gray-200">
        <button onClick={() => setQuery("")}
          className="text-gray-500 hover:text-gray-700 p-2 rounded-full hover:bg-gray-200" title="清除輸入">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
        </button>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") sendQuery(); }}
          placeholder="請輸入您的健康問題或中醫查詢..."
          className="flex-grow p-2 bg-transparent text-gray-800 placeholder-gray-500 focus:outline-none"
        />
        <button onClick={sendQuery}
          className="text-gray-500 hover:text-gray-700 p-2 rounded-full hover:bg-gray-200" title="送出">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a7 7 0 017-7V7a7 7 0 01-7 7z"/></svg>
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState('home');
  return (
    <div className="min-h-screen bg-[#FCFAF1]">
      {/* 導覽列 */}
      <header className="h-16 bg-gray-100 flex items-center justify-between px-4 shadow-md">
        <h1 className="text-xl font-bold text-gray-700 md:text-2xl">中醫系統平台</h1>
        <div className="flex items-center space-x-4">
          <button onClick={() => setPage('home')}
            className={`py-2 px-4 rounded-md font-semibold transition ${page === 'home' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-800'}`}>首頁</button>
          <button onClick={() => setPage('case')}
            className={`py-2 px-4 rounded-md font-semibold transition ${page === 'case' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-800'}`}>病例表</button>
        </div>
      </header>
      <main>
        {page === 'home' ? <QAHome /> : <TCMExamForm />}
      </main>
    </div>
  );
}
