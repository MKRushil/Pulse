// TCMDiagnosisForm.jsx - 中醫診斷病歷表 v2.0
// 移除方劑與藥物，改為診斷建議

import React, { useState } from "react";

// ==================== 選項數據 ====================
const bodyShapes = ["正常", "瘦弱", "肥胖", "壯實", "虛弱"];
const tongueBodyColors = ["淡紅", "淡白", "紅", "絳紅", "青紫", "瘀點瘀斑"];
const tongueCoatings = ["薄白", "厚白", "薄黃", "厚黃", "膩苔", "腐苔", "少苔", "無苔", "剝苔"];
const tongueShapes = ["正常", "胖大", "瘦薄", "齒痕", "裂紋", "芒刺", "瘀點"];

const pulseTypes = {
  "左寸(心)": ["浮", "沉", "遲", "數", "滑", "澀", "弦", "緊", "細", "洪", "虛", "實", "結", "代"],
  "左關(肝膽)": ["浮", "沉", "遲", "數", "滑", "澀", "弦", "緊", "細", "洪", "虛", "實", "結", "代"],
  "左尺(腎)": ["浮", "沉", "遲", "數", "滑", "澀", "弦", "緊", "細", "洪", "虛", "實", "結", "代"],
  "右寸(肺)": ["浮", "沉", "遲", "數", "滑", "澀", "弦", "緊", "細", "洪", "虛", "實", "結", "代"],
  "右關(脾胃)": ["浮", "沉", "遲", "數", "滑", "澀", "弦", "緊", "細", "洪", "虛", "實", "結", "代"],
  "右尺(命門)": ["浮", "沉", "遲", "數", "滑", "澀", "弦", "緊", "細", "洪", "虛", "實", "結", "代"]
};

const syndromePatterns = [
  "表證", "裡證", "寒證", "熱證", "虛證", "實證",
  "氣虛", "血虛", "陰虛", "陽虛", "氣滯", "血瘀",
  "痰濕", "濕熱", "風寒", "風熱", "肝鬱", "脾虛"
];

const zangfuOptions = [
  "心氣虛", "心血虛", "心陽虛", "心陰虛",
  "肺氣虛", "肺陰虛", "肺熱",
  "脾氣虛", "脾陽虛", "脾虛濕困",
  "肝氣鬱結", "肝血虛", "肝陽上亢", "肝火上炎",
  "腎陽虛", "腎陰虛", "腎氣不固", "腎精不足"
];

// ==================== 組件 ====================
function Section({ title, children, icon }) {
  return (
    <section className="mb-6 bg-white border border-blue-200 rounded-lg shadow-md overflow-hidden">
      <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-200">
        <h2 className="text-xl font-bold text-blue-800 flex items-center gap-2">
          {icon && <span className="text-2xl">{icon}</span>}
          {title}
        </h2>
      </div>
      <div className="p-6">{children}</div>
    </section>
  );
}

function FormField({ label, required, children, hint }) {
  return (
    <div className="mb-4">
      <label className="block font-semibold text-gray-700 mb-2">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
        {hint && <span className="text-sm text-gray-500 ml-2">({hint})</span>}
      </label>
      {children}
    </div>
  );
}

function CheckboxGroup({ options, value = [], onChange, columns = 4 }) {
  return (
    <div className={`grid grid-cols-2 md:grid-cols-${columns} gap-2`}>
      {options.map((opt) => (
        <label key={opt} className="flex items-center space-x-2 bg-gray-50 px-3 py-2 rounded hover:bg-blue-50 cursor-pointer transition-colors">
          <input
            type="checkbox"
            className="w-4 h-4 accent-blue-600"
            checked={value.includes(opt)}
            onChange={(e) => {
              if (e.target.checked) onChange([...value, opt]);
              else onChange(value.filter((v) => v !== opt));
            }}
          />
          <span className="text-sm">{opt}</span>
        </label>
      ))}
    </div>
  );
}

function PulseSection({ value, onChange }) {
  return (
    <div className="space-y-4">
      {Object.entries(pulseTypes).map(([position, types]) => (
        <div key={position} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <div className="font-semibold text-blue-700 mb-3">{position}</div>
          <div className="grid grid-cols-2 md:grid-cols-7 gap-2">
            {types.map((type) => (
              <label key={type} className="flex items-center space-x-2 bg-white px-2 py-1 rounded shadow-sm hover:shadow cursor-pointer transition-shadow">
                <input
                  type="checkbox"
                  className="w-4 h-4 accent-blue-600"
                  checked={value[position]?.includes(type)}
                  onChange={(e) => {
                    const current = value[position] || [];
                    const updated = e.target.checked 
                      ? [...current, type]
                      : current.filter(t => t !== type);
                    onChange({ ...value, [position]: updated });
                  }}
                />
                <span className="text-sm">{type}</span>
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ==================== 主組件 ====================
export default function TCMDiagnosisForm() {
  const [form, setForm] = useState({
    // 基本資料
    basic: {
      name: "",
      gender: "",
      age: "",
      idLast4: "",
      phone: "",
      visitDate: new Date().toISOString().split('T')[0]
    },
    // 主訴與病史
    complaint: {
      chiefComplaint: "",
      presentIllness: "",
      medicalHistory: "",
      familyHistory: ""
    },
    // 望診
    inspection: {
      spirit: "正常",
      bodyShape: [],
      faceColor: "",
      tongueBody: [],
      tongueCoating: [],
      tongueShape: [],
      tongueNote: ""
    },
    // 聞診
    auscultation: {
      voice: "正常",
      breath: "正常",
      cough: false,
      coughNote: ""
    },
    // 問診(十問)
    inquiry: {
      chills: "",
      sweat: "",
      head: "",
      body: "",
      stool: "",
      urine: "",
      appetite: "",
      sleep: "",
      thirst: "",
      gynecology: ""
    },
    // 切診(脈診)
    pulse: {},
    // 辨證論治
    diagnosis: {
      syndromePattern: [],
      zangfuPattern: [],
      diagnosis: "",
      treatment: "",
      suggestion: ""
    }
  });

  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const updateField = (section, field, value) => {
    setForm(prev => ({
      ...prev,
      [section]: { ...prev[section], [field]: value }
    }));
  };

  const validateForm = () => {
    const { basic, complaint } = form;
    if (!basic.name) return "請填寫患者姓名";
    if (!basic.gender) return "請選擇性別";
    if (!basic.age) return "請填寫年齡";
    if (!basic.idLast4 || basic.idLast4.length !== 4) return "請填寫身分證末4碼";
    if (!complaint.chiefComplaint) return "請填寫主訴";
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const error = validateForm();
    if (error) {
      setMessage(`❌ ${error}`);
      setTimeout(() => setMessage(""), 3000);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/case/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });

      if (!response.ok) throw new Error('儲存失敗');
      
      const result = await response.json();
      setMessage(`✅ 病例已成功儲存! ID: ${result.case_id || 'N/A'}`);
      
      // 重置表單
      setTimeout(() => {
        setForm({
          basic: { name: "", gender: "", age: "", idLast4: "", phone: "", visitDate: new Date().toISOString().split('T')[0] },
          complaint: { chiefComplaint: "", presentIllness: "", medicalHistory: "", familyHistory: "" },
          inspection: { spirit: "正常", bodyShape: [], faceColor: "", tongueBody: [], tongueCoating: [], tongueShape: [], tongueNote: "" },
          auscultation: { voice: "正常", breath: "正常", cough: false, coughNote: "" },
          inquiry: { chills: "", sweat: "", head: "", body: "", stool: "", urine: "", appetite: "", sleep: "", thirst: "", gynecology: "" },
          pulse: {},
          diagnosis: { syndromePattern: [], zangfuPattern: [], diagnosis: "", treatment: "", suggestion: "" }
        });
        setMessage("");
      }, 3000);
    } catch (err) {
      setMessage(`❌ 儲存失敗: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-6xl mx-auto bg-gradient-to-br from-blue-50 to-indigo-50 p-6 rounded-xl shadow-2xl my-8">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-blue-900 mb-2">中醫診斷病歷表</h1>
        <p className="text-gray-600">Traditional Chinese Medicine Diagnosis Record</p>
      </div>

      {message && (
        <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 font-semibold ${
          message.startsWith('✅') ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {message}
        </div>
      )}

      {/* 基本資料 */}
      <Section title="基本資料" icon="📋">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FormField label="姓名" required>
            <input
              type="text"
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={form.basic.name}
              onChange={(e) => updateField('basic', 'name', e.target.value)}
              placeholder="請輸入患者姓名"
            />
          </FormField>
          
          <FormField label="性別" required>
            <select
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.basic.gender}
              onChange={(e) => updateField('basic', 'gender', e.target.value)}
            >
              <option value="">請選擇</option>
              <option value="男">男</option>
              <option value="女">女</option>
            </select>
          </FormField>

          <FormField label="年齡" required>
            <input
              type="number"
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.basic.age}
              onChange={(e) => updateField('basic', 'age', e.target.value)}
              placeholder="歲"
            />
          </FormField>

          <FormField label="身分證末4碼" required>
            <input
              type="text"
              maxLength={4}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.basic.idLast4}
              onChange={(e) => updateField('basic', 'idLast4', e.target.value.replace(/[^0-9A-Za-z]/g, '').slice(0, 4))}
              placeholder="後4碼"
            />
          </FormField>

          <FormField label="聯絡電話">
            <input
              type="tel"
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.basic.phone}
              onChange={(e) => updateField('basic', 'phone', e.target.value)}
              placeholder="09XX-XXXXXX"
            />
          </FormField>

          <FormField label="就診日期" required>
            <input
              type="date"
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.basic.visitDate}
              onChange={(e) => updateField('basic', 'visitDate', e.target.value)}
            />
          </FormField>
        </div>
      </Section>

      {/* 主訴與病史 */}
      <Section title="主訴與病史" icon="📝">
        <FormField label="主訴 (Chief Complaint)" required hint="患者主要不適症狀">
          <textarea
            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
            rows={2}
            value={form.complaint.chiefComplaint}
            onChange={(e) => updateField('complaint', 'chiefComplaint', e.target.value)}
            placeholder="例: 咳嗽三天，咽痛，發熱"
          />
        </FormField>

        <FormField label="現病史 (Present Illness)" hint="症狀發展過程">
          <textarea
            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
            rows={3}
            value={form.complaint.presentIllness}
            onChange={(e) => updateField('complaint', 'presentIllness', e.target.value)}
            placeholder="詳述症狀起始時間、發展過程、加重緩解因素等"
          />
        </FormField>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="既往病史">
            <textarea
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              rows={2}
              value={form.complaint.medicalHistory}
              onChange={(e) => updateField('complaint', 'medicalHistory', e.target.value)}
              placeholder="過去疾病史、手術史、過敏史"
            />
          </FormField>

          <FormField label="家族史">
            <textarea
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              rows={2}
              value={form.complaint.familyHistory}
              onChange={(e) => updateField('complaint', 'familyHistory', e.target.value)}
              placeholder="家族遺傳病史"
            />
          </FormField>
        </div>
      </Section>

      {/* 望診 */}
      <Section title="望診 (Inspection)" icon="👁️">
        <div className="space-y-4">
          <FormField label="神態">
            <select
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inspection.spirit}
              onChange={(e) => updateField('inspection', 'spirit', e.target.value)}
            >
              <option>正常</option>
              <option>神疲乏力</option>
              <option>精神萎靡</option>
              <option>煩躁不安</option>
            </select>
          </FormField>

          <FormField label="體型">
            <CheckboxGroup
              options={bodyShapes}
              value={form.inspection.bodyShape}
              onChange={(v) => updateField('inspection', 'bodyShape', v)}
              columns={5}
            />
          </FormField>

          <FormField label="面色">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inspection.faceColor}
              onChange={(e) => updateField('inspection', 'faceColor', e.target.value)}
              placeholder="例: 面色潮紅、面色蒼白、面色晦暗"
            />
          </FormField>

          <div className="border-t pt-4 mt-4">
            <h3 className="font-semibold text-lg text-blue-700 mb-3">舌診</h3>
            
            <FormField label="舌體顏色">
              <CheckboxGroup
                options={tongueBodyColors}
                value={form.inspection.tongueBody}
                onChange={(v) => updateField('inspection', 'tongueBody', v)}
                columns={6}
              />
            </FormField>

            <FormField label="舌苔">
              <CheckboxGroup
                options={tongueCoatings}
                value={form.inspection.tongueCoating}
                onChange={(v) => updateField('inspection', 'tongueCoating', v)}
                columns={6}
              />
            </FormField>

            <FormField label="舌形">
              <CheckboxGroup
                options={tongueShapes}
                value={form.inspection.tongueShape}
                onChange={(v) => updateField('inspection', 'tongueShape', v)}
                columns={6}
              />
            </FormField>

            <FormField label="舌診備註">
              <input
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
                value={form.inspection.tongueNote}
                onChange={(e) => updateField('inspection', 'tongueNote', e.target.value)}
                placeholder="其他舌診發現"
              />
            </FormField>
          </div>
        </div>
      </Section>

      {/* 聞診 */}
      <Section title="聞診 (Auscultation)" icon="👂">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="語聲">
            <select
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.auscultation.voice}
              onChange={(e) => updateField('auscultation', 'voice', e.target.value)}
            >
              <option>正常</option>
              <option>聲音低微</option>
              <option>聲音洪亮</option>
              <option>聲音嘶啞</option>
            </select>
          </FormField>

          <FormField label="呼吸">
            <select
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.auscultation.breath}
              onChange={(e) => updateField('auscultation', 'breath', e.target.value)}
            >
              <option>正常</option>
              <option>氣短</option>
              <option>喘促</option>
              <option>呼吸微弱</option>
            </select>
          </FormField>

          <div className="col-span-2">
            <label className="flex items-center space-x-2 mb-2">
              <input
                type="checkbox"
                className="w-4 h-4 accent-blue-600"
                checked={form.auscultation.cough}
                onChange={(e) => updateField('auscultation', 'cough', e.target.checked)}
              />
              <span className="font-semibold">咳嗽</span>
            </label>
            {form.auscultation.cough && (
              <input
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
                value={form.auscultation.coughNote}
                onChange={(e) => updateField('auscultation', 'coughNote', e.target.value)}
                placeholder="咳嗽特點: 乾咳/痰多/痰色等"
              />
            )}
          </div>
        </div>
      </Section>

      {/* 問診 */}
      <Section title="問診 (Inquiry) - 十問" icon="❓">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="寒熱" hint="惡寒發熱情況">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inquiry.chills}
              onChange={(e) => updateField('inquiry', 'chills', e.target.value)}
              placeholder="例: 惡寒重、發熱輕"
            />
          </FormField>

          <FormField label="汗" hint="出汗情況">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inquiry.sweat}
              onChange={(e) => updateField('inquiry', 'sweat', e.target.value)}
              placeholder="例: 自汗、盜汗、無汗"
            />
          </FormField>

          <FormField label="頭身" hint="頭痛、身痛">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inquiry.head}
              onChange={(e) => updateField('inquiry', 'head', e.target.value)}
              placeholder="例: 頭脹痛、身體酸痛"
            />
          </FormField>

          <FormField label="胸腹" hint="胸悶、腹脹等">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inquiry.body}
              onChange={(e) => updateField('inquiry', 'body', e.target.value)}
              placeholder="例: 胸悶、腹脹、脅痛"
            />
          </FormField>

          <FormField label="二便" hint="大便情況">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inquiry.stool}
              onChange={(e) => updateField('inquiry', 'stool', e.target.value)}
              placeholder="例: 便秘、溏便、次數"
            />
          </FormField>

          <FormField label="小便" hint="小便情況">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inquiry.urine}
              onChange={(e) => updateField('inquiry', 'urine', e.target.value)}
              placeholder="例: 頻尿、色黃、量少"
            />
          </FormField>

          <FormField label="飲食" hint="食慾、口渴">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inquiry.appetite}
              onChange={(e) => updateField('inquiry', 'appetite', e.target.value)}
              placeholder="例: 食慾不振、納差"
            />
          </FormField>

          <FormField label="睡眠">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inquiry.sleep}
              onChange={(e) => updateField('inquiry', 'sleep', e.target.value)}
              placeholder="例: 失眠、多夢、易醒"
            />
          </FormField>

          <FormField label="口渴">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inquiry.thirst}
              onChange={(e) => updateField('inquiry', 'thirst', e.target.value)}
              placeholder="例: 口乾欲飲、不欲飲"
            />
          </FormField>

          <FormField label="婦科" hint="僅女性需填">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.inquiry.gynecology}
              onChange={(e) => updateField('inquiry', 'gynecology', e.target.value)}
              placeholder="例: 月經週期、量色"
              disabled={form.basic.gender !== "女"}
            />
          </FormField>
        </div>
      </Section>

      {/* 脈診 */}
      <Section title="切診 (Pulse Diagnosis) - 脈診" icon="🫀">
        <PulseSection
          value={form.pulse}
          onChange={(v) => setForm(prev => ({ ...prev, pulse: v }))}
        />
      </Section>

      {/* 辨證論治 */}
      <Section title="辨證論治 (Pattern Differentiation & Treatment)" icon="💊">
        <div className="space-y-4">
          <FormField label="證型分類">
            <CheckboxGroup
              options={syndromePatterns}
              value={form.diagnosis.syndromePattern}
              onChange={(v) => updateField('diagnosis', 'syndromePattern', v)}
              columns={6}
            />
          </FormField>

          <FormField label="臟腑辨證">
            <CheckboxGroup
              options={zangfuOptions}
              value={form.diagnosis.zangfuPattern}
              onChange={(v) => updateField('diagnosis', 'zangfuPattern', v)}
              columns={4}
            />
          </FormField>

          <FormField label="診斷" hint="中醫診斷">
            <textarea
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              rows={2}
              value={form.diagnosis.diagnosis}
              onChange={(e) => updateField('diagnosis', 'diagnosis', e.target.value)}
              placeholder="例: 風寒感冒，肺氣不宣"
            />
          </FormField>

          <FormField label="治法">
            <input
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              value={form.diagnosis.treatment}
              onChange={(e) => updateField('diagnosis', 'treatment', e.target.value)}
              placeholder="例: 疏風散寒，宣肺止咳"
            />
          </FormField>

          <FormField label="診斷建議" hint="治療建議、注意事項等">
            <textarea
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
              rows={4}
              value={form.diagnosis.suggestion}
              onChange={(e) => updateField('diagnosis', 'suggestion', e.target.value)}
              placeholder="例: 建議多休息，避免風寒，飲食清淡。可配合針灸治療加強療效。必要時複診調整治療方案。"
            />
          </FormField>
        </div>
      </Section>

      {/* 提交按鈕 */}
      <div className="flex justify-end gap-4 mt-8 pb-4">
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold px-8 py-3 rounded-lg shadow-lg transition-all transform hover:scale-105 disabled:transform-none"
        >
          {loading ? "儲存中..." : "✓ 提交病歷"}
        </button>
        <button
          type="button"
          onClick={() => {
            if (window.confirm('確定要清除所有內容？')) {
              setForm({
                basic: { name: "", gender: "", age: "", idLast4: "", phone: "", visitDate: new Date().toISOString().split('T')[0] },
                complaint: { chiefComplaint: "", presentIllness: "", medicalHistory: "", familyHistory: "" },
                inspection: { spirit: "正常", bodyShape: [], faceColor: "", tongueBody: [], tongueCoating: [], tongueShape: [], tongueNote: "" },
                auscultation: { voice: "正常", breath: "正常", cough: false, coughNote: "" },
                inquiry: { chills: "", sweat: "", head: "", body: "", stool: "", urine: "", appetite: "", sleep: "", thirst: "", gynecology: "" },
                pulse: {},
                diagnosis: { syndromePattern: [], zangfuPattern: [], diagnosis: "", treatment: "", suggestion: "" }
              });
            }
          }}
          className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold px-8 py-3 rounded-lg shadow-lg transition-all"
        >
          ✗ 清除
        </button>
      </div>
    </form>
  );
}