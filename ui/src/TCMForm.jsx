// 修改版 TCMForm.jsx
// 1. 已刪除「症狀（可複選）、其它症狀補充」部分
// 2. 新增「暫定診斷結果」欄位（可填寫）

import React, { useState } from "react";

const bodyShapes = ["正常", "瘦", "胖"];
const faceColors = [
  "面色潤澤", "面色晃白", "面色淡白", "面色蒼白", "面色偏紅", "面色萎黃", "面色黧黑", "面垢滯或油亮",
  "鼻色淡黃", "鼻有油津", "鼻色暗滯", "唇紅微乾", "唇色淡紅", "唇色暗紫", "毛髮不華", "精神萎靡"
];
const eyeOptions = [
  "正常", "目睛赤", "目睛黃", "白珠青紫", "眼筋紅黃", "目胞腫", "結膜粉紅", "結膜淡白", "眼眶暗黑上", "眼眶暗黑下", "紅筋浮起或瘀點"
];
const skinOptions = [
  "無特殊", "蒼赤", "偏白", "偏黃", "暗滯", "斑", "疹", "肌膚甲錯", "皮膚乾"
];
const sleepOptions = [
  "睡得安穩", "難入眠", "眠淺", "多夢", "睡一半醒後不易入睡", "睡眠時腳抽筋", "睡眠呼吸中止", "夢遊"
];
const spiritOptions = [
  "正常", "提不起勁", "情緒亢奮", "煩躁不安", "壓力大"
];

const pulseOptionsByPosition = {
  "左寸": ["浮", "中", "沉", "數", "弦", "軟", "滑", "澀", "有力", "無力"],
  "左關": ["浮", "中", "沉", "數", "遲", "弦", "軟", "滑", "澀", "有力", "無力"],
  "左尺": ["浮", "中", "沉", "數", "遲", "弦", "軟", "滑", "澀", "有力", "無力"],
  "右寸": ["浮", "中", "沉", "數", "遲", "弦", "軟", "滑", "澀", "有力", "無力"],
  "右關": ["浮", "中", "沉", "數", "遲", "弦", "軟", "滑", "澀", "有力", "無力"],
  "右尺": ["浮", "中", "沉", "數", "遲", "弦", "軟", "滑", "澀", "有力", "無力"]
};
const pulsePositions = Object.keys(pulseOptionsByPosition);
const initialPulse = {};
for (const pos of pulsePositions) {
  initialPulse[pos] = { types: [], note: "" };
}

function Section({ title, children }) {
  return (
    <section className="mb-6 bg-gray-50 border border-gray-200 rounded-2xl shadow-sm">
      <div className="px-6 py-3 border-b bg-gradient-to-r from-blue-100 via-white to-blue-100 rounded-t-2xl">
        <h2 className="text-xl font-bold text-blue-700 tracking-wide">{title}</h2>
      </div>
      <div className="p-6">{children}</div>
    </section>
  );
}

function MultiCheckbox({ options, label, value = [], onChange }) {
  return (
    <div className="mb-3">
      {label && <div className="font-semibold mb-2 text-blue-700">{label}</div>}
      <div className="flex flex-wrap gap-3">
        {options.map((opt) => (
          <label key={opt} className="flex items-center space-x-2 bg-gray-100 px-2 py-1 rounded-xl shadow-sm cursor-pointer">
            <input
              type="checkbox"
              className="accent-blue-600 scale-125"
              checked={value.includes(opt)}
              onChange={(e) => {
                if (e.target.checked) onChange([...value, opt]);
                else onChange(value.filter((v) => v !== opt));
              }}
            />
            <span className="text-base">{opt}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function PulseTable({ value, onChange }) {
  return (
    <div className="p-6">
      <table className="border min-w-full">
        <thead>
          <tr>
            <th>部位</th>
            <th>脈象</th>
            <th>備註</th>
          </tr>
        </thead>
        <tbody>
          {pulsePositions.map(pos => (
            <tr key={pos}>
              <td className="text-blue-900 font-semibold text-center">{pos}</td>
              <td>
                <MultiCheckbox
                  options={pulseOptionsByPosition[pos]}
                  value={value[pos].types}
                  onChange={types => onChange({ ...value, [pos]: { ...value[pos], types } })}
                />
              </td>
              <td>
                <input
                  className="border rounded p-1 w-28"
                  value={value[pos].note}
                  onChange={e => onChange({ ...value, [pos]: { ...value[pos], note: e.target.value } })}
                  placeholder="備註"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function TCMExamForm() {
  const [form, setForm] = useState({
    basic: {
      name: "",
      gender: "",
      age: "",
      id: "",
      phone: "",
      address: ""
    },
    inspection: {
      bodyShape: [],
      faceColor: [],
      faceOther: "",
      eye: [],
      skin: [],
    },
    inquiry: {
      sleep: [],
      spirit: [],
      chiefComplaint: "",   // 主訴
      presentIllness: "",  // 現病史
      // 已移除 symptoms 與 otherSymptom
      tentativeDiagnosis: "" // 新增暫定診斷結果
    }
  });
  const [pulse, setPulse] = useState(initialPulse);
  const [error, setError] = useState("");
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  const handleChange = (section, field, value) => {
    setForm({
      ...form,
      [section]: {
        ...form[section],
        [field]: value
      }
    });
  };
  const handleIdChange = e => {
    const v = e.target.value.replace(/[^0-9a-zA-Z]/g, '').slice(-4);
    handleChange('basic', 'id', v);
  };
  function validateForm() {
    if (!form.basic.name) return "請填寫姓名";
    if (!form.basic.gender) return "請選擇性別";
    if (!form.basic.age) return "請填寫年齡";
    if (!form.basic.id || form.basic.id.length !== 4) return "請填寫正確身分證末4碼";
    return "";
  }
  async function handleSubmit(e) {
    e.preventDefault();
    const err = validateForm();
    if (err) return setError(err);
    setError("");
    setSending(true);
    setMessage("");
    const data = { ...form, pulse };
    try {
      const res = await fetch('/api/case/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!res.ok) throw new Error('儲存失敗');
      setMessage('✅ 病例已成功儲存！');
      setForm({
        basic: { name: "", gender: "", age: "", id: "", phone: "", address: "" },
        inspection: { bodyShape: [], faceColor: [], faceOther: "", eye: [], skin: [] },
        inquiry: { sleep: [], spirit: [], chiefComplaint: "", presentIllness: "", tentativeDiagnosis: "" },
      });
      setPulse(initialPulse);
    } catch (err) {
      setMessage('❌ 儲存失敗，請重試');
    }
    setSending(false);
  }
  function handleClear() {
    setError("");
    setForm({
      basic: { name: "", gender: "", age: "", id: "", phone: "", address: "" },
      inspection: { bodyShape: [], faceColor: [], faceOther: "", eye: [], skin: [] },
      inquiry: { sleep: [], spirit: [], chiefComplaint: "", presentIllness: "", tentativeDiagnosis: "" },
    });
    setPulse(initialPulse);
  }
  return (
    <form
      className="max-w-3xl mx-auto bg-gradient-to-br from-blue-50 via-white to-blue-100 rounded-3xl shadow-2xl p-4 mt-8 space-y-6 border border-blue-100"
      onSubmit={handleSubmit}
    >
      <div className="text-3xl font-extrabold mb-4 text-blue-900 tracking-wide text-center pt-2 pb-3 border-b-2 border-blue-100">中醫病患病歷</div>
      {error && (
        <div className="bg-red-100 text-red-700 px-4 py-2 rounded mb-2 text-center font-semibold">{error}</div>
      )}
      {message && (
        <div className={`fixed top-8 left-1/2 -translate-x-1/2 px-6 py-3 rounded-2xl shadow-lg z-50 font-bold ${message.startsWith('✅') ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-700'}`}>{message}</div>
      )}
      <Section title="基本資料">
        <div className="grid grid-cols-2 gap-4">
          <input placeholder="姓名（必填）" className="border rounded p-2" value={form.basic.name} onChange={e => handleChange('basic', 'name', e.target.value)} />
          <select className="border rounded p-2" value={form.basic.gender} onChange={e => handleChange('basic', 'gender', e.target.value)}>
            <option value="">性別（必填）</option>
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
          <input placeholder="年齡（必填）" className="border rounded p-2" value={form.basic.age} onChange={e => handleChange('basic', 'age', e.target.value)} />
          <input
            placeholder="身分編號4碼（必填）"
            maxLength={4}
            className="border rounded p-2"
            value={form.basic.id}
            onChange={handleIdChange}
          />
          <input placeholder="電話" className="border rounded p-2" value={form.basic.phone} onChange={e => handleChange('basic', 'phone', e.target.value)} />
          <input placeholder="地址" className="col-span-2 border rounded p-2" value={form.basic.address} onChange={e => handleChange('basic', 'address', e.target.value)} />
        </div>
      </Section>
      <Section title="望診">
        <MultiCheckbox options={bodyShapes} label="體型" value={form.inspection.bodyShape} onChange={v => handleChange('inspection', 'bodyShape', v)} />
        <div className="flex items-center gap-2 mb-2">
          <MultiCheckbox options={faceColors} label="頭面部" value={form.inspection.faceColor} onChange={v => handleChange('inspection', 'faceColor', v)} />
          <input className="border rounded p-1 w-32 bg-blue-50" placeholder="其它說明" value={form.inspection.faceOther} onChange={e => handleChange('inspection', 'faceOther', e.target.value)} />
        </div>
        <MultiCheckbox options={eyeOptions} label="目部" value={form.inspection.eye} onChange={v => handleChange('inspection', 'eye', v)} />
        <MultiCheckbox options={skinOptions} label="皮膚" value={form.inspection.skin} onChange={v => handleChange('inspection', 'skin', v)} />
      </Section>
      <Section title="問診">
        <MultiCheckbox options={sleepOptions} label="睡眠" value={form.inquiry.sleep} onChange={v => handleChange('inquiry', 'sleep', v)} />
        <MultiCheckbox options={spiritOptions} label="精神" value={form.inquiry.spirit} onChange={v => handleChange('inquiry', 'spirit', v)} />
        <div className="mb-4 flex flex-col gap-4">
          <div>
            <label className="font-semibold text-blue-700 mb-2 block">主訴</label>
            <input
              className="border rounded p-1 w-full bg-blue-50"
              placeholder="請輸入主訴（如：咳嗽三天，咽癢）"
              value={form.inquiry.chiefComplaint}
              onChange={e => handleChange('inquiry', 'chiefComplaint', e.target.value)}
              required
            />
          </div>
          <div>
            <label className="font-semibold text-blue-700 mb-2 block">現病史</label>
            <textarea
              className="border rounded p-1 w-full bg-blue-50"
              placeholder="請輸入現病史或相關症狀發展（可多行）"
              value={form.inquiry.presentIllness}
              onChange={e => handleChange('inquiry', 'presentIllness', e.target.value)}
              rows={2}
            />
          </div>
          <div>
            <label className="font-semibold text-blue-700 mb-2 block">暫定診斷結果</label>
            <input
              className="border rounded p-1 w-full bg-blue-50"
              placeholder="請輸入暫定診斷結果（如：風熱感冒、脾虛）"
              value={form.inquiry.tentativeDiagnosis}
              onChange={e => handleChange('inquiry', 'tentativeDiagnosis', e.target.value)}
            />
          </div>
        </div>
      </Section>
      <Section title="脈診">
        <PulseTable value={pulse} onChange={setPulse} />
      </Section>
      <div className="flex justify-end gap-6 mt-10 pb-2">
        <button type="submit" className="bg-blue-600 hover:bg-blue-700 transition-colors text-white rounded-2xl px-10 py-3 text-lg shadow-xl font-bold" disabled={sending}>送出</button>
        <button type="button" className="bg-gray-200 hover:bg-gray-300 transition-colors rounded-2xl px-10 py-3 text-lg font-bold" onClick={handleClear}>清除</button>
      </div>
    </form>
  );
}
