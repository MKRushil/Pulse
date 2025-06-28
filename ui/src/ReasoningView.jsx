export default function ReasoningView() {
  // 推理檢視預留區塊（可串模型結果、圖表等）
  return (
    <div className="flex flex-col flex-1 items-center p-8 overflow-y-auto">
      <div className="text-2xl font-bold mb-4 text-blue-800">推理檢視</div>
      <div className="bg-white border border-blue-100 rounded-2xl shadow-lg p-6 max-w-2xl w-full text-blue-900">
        <div className="text-blue-400 mb-2">（此處可串 API 顯示推理結果、病例關聯圖、主病次病分布等）</div>
        <div className="font-bold mb-2">推理結果示意：</div>
        <ul className="list-disc pl-6 mt-2">
          <li>主病：「肝鬱」相關病例共 23 筆</li>
          <li>常見引發次病：「頭痛」、「胸悶」、「失眠」</li>
        </ul>
      </div>
    </div>
  );
}
