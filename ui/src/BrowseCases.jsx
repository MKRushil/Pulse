export default function BrowseCases() {
  // 病例查詢展示預留，僅示意（可串 API）
  return (
    <div className="flex flex-col flex-1 items-center p-8 overflow-y-auto">
      <div className="text-2xl font-bold mb-4 text-blue-800">瀏覽病歷</div>
      <div className="bg-white border border-blue-100 rounded-2xl shadow-lg p-6 max-w-2xl w-full text-blue-900">
        <div className="text-blue-400 mb-2">（此處可串 API 顯示病歷列表與搜尋功能）</div>
        <div className="font-bold">案例列表示意：</div>
        <ul className="list-disc pl-6 mt-2">
          <li>林小明　35歲　最後就診：2025-06-15</li>
          <li>王美麗　42歲　最後就診：2025-05-29</li>
        </ul>
      </div>
    </div>
  );
}
