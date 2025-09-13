import { useState } from "react";
import DiagnosisChat from "./DiagnosisChat";
import CaseChat from "./CaseChat";
import TCMExamForm from "./TCMForm";
import BrowseCases from "./BrowseCases";
import ReasoningView from "./ReasoningView";
import {
  MessageCircle,
  User,
  PlusCircle,
  FileText,
  BrainCog
} from "lucide-react";
import ReactMarkdown from "react-markdown";



const menuItems = [
  { name: "診斷對話", icon: <MessageCircle size={22} />, key: "diagnosis" },
  // { name: "個案對話", icon: <User size={22} />, key: "case" },
  { name: "新增病歷", icon: <PlusCircle size={22} />, key: "add" },
  // { name: "瀏覽病歷", icon: <FileText size={22} />, key: "view" },
  // { name: "推理檢視", icon: <BrainCog size={22} />, key: "reasoning" },
];

export default function App() {
  const [selected, setSelected] = useState("diagnosis");
  return (
    <div className="flex h-screen bg-gradient-custom text-blue-900">
      {/* 側邊功能列 */}
      <aside className="w-64 bg-white/90 flex flex-col border-r border-blue-100 shadow-xl">
        <div className="text-2xl font-extrabold text-blue-900 text-center py-6 border-b border-blue-100 tracking-wider">
          中醫輔助系統
        </div>
        <nav className="flex-1">
          <ul>
            {menuItems.map((item) => (
              <li
                key={item.key}
                onClick={() => setSelected(item.key)}
                className={`flex items-center px-8 py-4 cursor-pointer rounded-r-2xl font-bold text-lg transition-all duration-200 select-none
                  ${selected === item.key ? "bg-blue-100 text-blue-700 shadow-inner" : "text-gray-700 hover:bg-blue-50"}`}
              >
                <span className="mr-3">{item.icon}</span>
                {item.name}
              </li>
            ))}
          </ul>
        </nav>
        <div className="px-8 py-4 text-xs text-blue-300 border-t border-blue-100">v1.0</div>
      </aside>
      {/* 右側內容區 */}
      <main className="flex-1 flex flex-col bg-transparent min-h-0">
        {selected === "diagnosis" && <DiagnosisChat />}
        {selected === "case" && <CaseChat />}
        {selected === "add" && <div className="p-4 w-full flex flex-col items-center overflow-y-auto"><TCMExamForm /></div>}
        {selected === "view" && <BrowseCases />}
        {selected === "reasoning" && <ReasoningView />}
      </main>
    </div>
  );
}
