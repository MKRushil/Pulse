import { useState } from "react";
import DiagnosisChat from "./DiagnosisChat";
import TCMExamForm from "./TCMForm";
import {
  MessageCircle,
  PlusCircle
} from "lucide-react";

const menuItems = [
  { name: "診斷對話", icon: <MessageCircle />, key: "diagnosis" },
  { name: "新增病歷", icon: <PlusCircle />, key: "add" }
];

export default function App() {
  const [selected, setSelected] = useState("diagnosis");
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex">
      {/* 側邊功能列 */}
      <aside className="w-80 bg-white border-r border-gray-200 shadow-lg flex flex-col">
        {/* Logo 區域 */}
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">
            中醫智慧輔助系統
          </h1>
          <p className="text-sm text-gray-500">v2.0 - 螺旋推理版</p>
        </div>
        
        {/* 導航選單 */}
        <nav className="flex-1 p-4">
          <div className="space-y-2">
            {menuItems.map((item) => (
              <button
                key={item.key}
                onClick={() => setSelected(item.key)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-left transition-all duration-200 ${
                  selected === item.key
                    ? "bg-blue-100 text-blue-700 border border-blue-200"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-800"
                }`}
              >
                {item.icon}
                <span className="font-medium">{item.name}</span>
              </button>
            ))}
          </div>
        </nav>
        
        {/* 底部說明 */}
        <div className="p-4 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            <p>螺旋推理 S-CBR 系統</p>
            <p>支援持續推理與案例過濾</p>
          </div>
        </div>
      </aside>

      {/* 右側內容區 */}
      <main className="flex-1 overflow-auto">
        {selected === "diagnosis" && <DiagnosisChat />}
        {selected === "add" && <TCMExamForm />}
      </main>
    </div>
  );
}
