import React, { useState } from "react";

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

function MultiCheckbox({ options, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map(opt => (
        <label key={opt} className="flex items-center space-x-1">
          <input
            type="checkbox"
            checked={value.includes(opt)}
            onChange={e => {
              if (e.target.checked) onChange([...value, opt]);
              else onChange(value.filter(v => v !== opt));
            }}
          />
          <span>{opt}</span>
        </label>
      ))}
    </div>
  );
}

export default function PulseTableDemo() {
  const [pulse, setPulse] = useState(initialPulse);
  return (
    <div className="p-6">
      <table className="border">
        <thead>
          <tr>
            <th>部位</th>
            <th>脈象</th>
          </tr>
        </thead>
        <tbody>
          {pulsePositions.map(pos => (
            <tr key={pos}>
              <td>{pos}</td>
              <td>
                <MultiCheckbox
                  options={pulseOptionsByPosition[pos]}
                  value={pulse[pos].types}
                  onChange={types => setPulse({ ...pulse, [pos]: { ...pulse[pos], types } })}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <pre className="mt-4 bg-gray-50 p-2">{JSON.stringify(pulse, null, 2)}</pre>
    </div>
  );
}
