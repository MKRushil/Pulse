// Simple client-side OWASP LLM Top 10 safety checks
// Categories covered heuristically: LLM01..LLM10

const re = {
  // LLM01 Prompt Injection and role-play / override
  injection: [
    /ignore\s+(previous|above|all)\s+instructions?/i,
    /disregard\s+(above|previous)/i,
    /不要?理會(上面|之前)/i,
    /忽略(之前|上面|所有|全部)(的)?(指令|規則|要求)/i,
    /forget\s+(everything|all)/i,
    /忘記(所有|全部|一切)/i,
    /(you\s+are\s+now|now\s+you\s+are)/i,
    /(你|您)現在(是|變成|成為)/i,
    /(pretend|act\s+as)\s+/i,
    /(假裝|扮演|角色扮演)/i,
    /(show|display|reveal|output)\s+(your|the)\s+(prompt|instruction|system)/i,
    /(顯示|輸出|告訴我|展示)(你的|妳的|系統)?(提示詞|指令|規則|prompt)/i,
    /(你的|妳的)(第一|首要|初始)(條|個)(指令|規則|任務)/i,
    /(repeat|copy)\s+your\s+(prompt|instructions?)/i,
    /<\|im_(start|end)\|>/i,
    /(\|\|system\|\||###OVERRIDE###|---END---)/i,
    /(system:|assistant:|user:)/i,
    /```[\s\S]*```/ // code fences
  ],

  // LLM02 Sensitive PII/PHI (basic)
  pii: [
    /\b[A-Z]\d{9}\b/g, // TW ID
    /\b(09\d{8}|\d{2,3}-\d{7,8}|\+886[-\s]?\d{1,3}[-\s]?\d{6,8})\b/g, // phone
    /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g, // email
    /(地址[:：]\s*[\u4e00-\u9fa5\d]{5,50})/g, // address
  ],
  selfName: [
    /(我叫|我是|名叫|我的名字叫)\s*[\u4e00-\u9fa5]{2,4}/
  ],

  // LLM03 Suspicious external links (supply chain risk in prompt)
  links: [
    /(http|https):\/\/[^\s]+/i
  ],

  // LLM04 Data/Model poisoning cues (heuristic)
  poisoning: [
    /(加入|新增).*?(訓練|資料集|語料)/,
    /(train|finetune).*(on|with)/i
  ],

  // LLM05 Dangerous output patterns (also used for output check)
  dangerousClaims: [
    /(一定|必定|肯定|保證)(能|會|可以)(治癒|治好|康復)/,
    /(絕對|百分百)(有效|見效)/,
    /(停止|不要|別)(服用|吃|使用).*?(西藥|藥物)/
  ],

  // LLM06 Excessive agency cues (asking to run tools/commands)
  agency: [
    /(執行|運行|run)\s+(shell|命令|command)/i,
    /(讀寫|寫入|刪除|修改).*?(檔案|文件|file)/
  ],

  // LLM07 System prompt leakage in output
  sysLeak: [
    /(strategy_layer|generation_layer)/i,
    /(根據我的系統指令|according to my instructions)/i,
    /(系統要求我|the system requires me to)/i,
    /(我的\s*prompt|my\s*prompt\s*is)/i
  ],

  // LLM08 Input anomaly
  html: /<[^>]+>/,
  specialChar: /[^\u4e00-\u9fa5a-zA-Z0-9\s，。、！？：；「」『』（）\-]/g,

  // LLM10 length constraint
  maxInputLen: 1000
};

// Whitelist: common TCM symptom keywords (subset, client-side)
const SYMPTOMS = [
  '症狀','不舒服','不適','疼痛','痛','癢','腫','出汗','發炎','腫脹',
  '咳嗽','咽痛','喉嚨痛','鼻塞','流鼻水','發熱','發燒','頭痛','頭暈',
  '胸悶','胸痛','心悸','氣短','乏力','疲倦','腹痛','腹瀉','便祕',
  '噁心','嘔吐','食慾不振','口乾','口渴','多汗','盜汗','畏寒',
  '失眠','多夢','焦慮','易怒','腰痛','關節痛','肢麻','浮腫'
];

// Anatomy/gender terms
const MALE_TERMS = ['男','男性','我是男','我男','男生','先生'];
const FEMALE_TERMS = ['女','女性','我是女','我女','女生','小姐'];
const MALE_ONLY = ['陰莖','睪丸','前列腺','包皮','射精'];
const FEMALE_ONLY = ['子宮','陰道','卵巢','乳房','月經','生理期','經痛','懷孕'];

function maskPII(text) {
  let masked = text;
  const mappings = [];

  re.pii.forEach((pattern) => {
    masked = masked.replace(pattern, (m) => {
      mappings.push({ type: 'PII', original: m });
      if (/@/.test(m)) return '***信箱***';
      if (/^\+?\d|\d{2,3}-/.test(m)) return '***電話***';
      if (/^[A-Z]\d{9}$/.test(m)) return '***身份證***';
      if (/地址[:：]/.test(m)) return '地址: ***地址***';
      return '***已脫敏***';
    });
  });

  return { masked, mappings };
}

export function analyzeInput(text) {
  const reasons = [];
  const categories = [];
  let blocked = false;
  let severity = 'warn';

  if (!text || !text.trim()) {
    return { blocked: true, severity: 'error', reasons: ['輸入為空'], categories: ['LLM10'], maskedText: '' };
  }

  // LLM10: length
  if (text.length > re.maxInputLen) {
    blocked = true; severity = 'error';
    reasons.push(`輸入過長(${text.length} > ${re.maxInputLen})`);
    categories.push('LLM10');
  }

  // LLM08: HTML/script
  if (re.html.test(text)) {
    blocked = true; severity = 'error';
    reasons.push('檢測到HTML/Script標籤');
    categories.push('LLM08');
  }

  // LLM01: injection
  if (re.injection.some((p) => p.test(text))) {
    blocked = true; severity = 'error';
    reasons.push('疑似提示詞注入/角色扮演/指令覆蓋');
    categories.push('LLM01');
  }

  // Code-like (heuristic)
  const codeLike = /(for\s+\w+\s+in\s+range\(|def\s+[a-zA-Z_]+\(|class\s+[A-Z]|import\s+\w+|console\.log\(|SELECT\s+\*\s+FROM|\{\s*\}|;\s*$|function\s+[a-zA-Z_]+\(|\b(var|let|const)\s+\w+|=>\s*\{|#include\s*<|public\s+static\s+void\s+main|<script|<div|<\?php|curl\s+|pip\s+install|npm\s+install)/i;
  if (codeLike.test(text)) {
    blocked = true; severity = 'error';
    reasons.push('輸入包含程式碼/指令樣式內容');
    categories.push('LLM01');
  }

  // LLM02: PII + self name disclosure
  const { masked, mappings } = maskPII(text);
  if (re.selfName.some((p) => p.test(text))) {
    blocked = true; severity = 'error';
    reasons.push('偵測到姓名等個資（請勿提供個資）');
    categories.push('LLM02');
  }
  if (mappings.length > 0 && !blocked) {
    // Not block, but warn
    reasons.push(`已脫敏 ${mappings.length} 項敏感資訊`);
    categories.push('LLM02');
  }

  // LLM03: links in prompt
  if (re.links.some((p) => p.test(text))) {
    reasons.push('輸入包含外部連結，請小心供應鏈風險');
    categories.push('LLM03');
  }

  // LLM04: poisoning cues
  if (re.poisoning.some((p) => p.test(text))) {
    reasons.push('輸入包含資料/模型訓練相關語句（可能不符合用途）');
    categories.push('LLM04');
  }

  // LLM08: special char ratio
  const specials = text.match(re.specialChar) || [];
  const ratio = specials.length / (text.length + 1);
  if (ratio > 0.3) {
    reasons.push(`特殊字符比例偏高(${(ratio * 100).toFixed(0)}%)`);
    categories.push('LLM08');
  }

  // Symptom whitelist: require at least one keyword
  const symptomFocused = SYMPTOMS.some((k) => text.includes(k));
  if (!symptomFocused) {
    blocked = true; severity = 'error';
    reasons.push('非症狀導向輸入，請描述身體不適或症狀');
    categories.push('scope');
  }

  // Anatomy/gender inconsistency
  const hasMale = MALE_TERMS.some((k) => text.includes(k));
  const hasFemale = FEMALE_TERMS.some((k) => text.includes(k));
  const hasMaleAnat = MALE_ONLY.some((k) => text.includes(k));
  const hasFemaleAnat = FEMALE_ONLY.some((k) => text.includes(k));
  if ((hasMale && hasFemaleAnat) || (hasFemale && hasMaleAnat) || (hasMaleAnat && hasFemaleAnat)) {
    blocked = true; severity = 'error';
    reasons.push('性別與生理/解剖描述不相符，請確認');
    categories.push('scope');
  }

  return { blocked, severity, reasons, categories, maskedText: masked };
}

export function analyzeOutput(text) {
  const warnings = [];
  let safe = true;

  // LLM07: system leakage
  if (re.sysLeak.some((p) => p.test(text))) {
    safe = false;
    warnings.push('輸出包含系統提示詞片段，已標記');
  }

  // LLM05: dangerous medical claims
  if (re.dangerousClaims.some((p) => p.test(text))) {
    safe = false;
    warnings.push('輸出包含可能不當的醫療建議語句');
  }

  // Sanitize basic: strip script tags if any got through (defense-in-depth)
  const sanitized = text.replace(/<script.*?>[\s\S]*?<\/script>/gi, '[移除腳本]');

  return { safe, warnings, sanitizedText: sanitized };
}
