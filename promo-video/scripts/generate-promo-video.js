#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'out');
const FRAMES = path.join(OUT, 'frames');
const QA = path.join(OUT, 'qa');
const WIDTH = 1920;
const HEIGHT = 1080;
const FPS = 30;
const TOTAL = 600;

// Shot boundaries (Iteration 2)
const S_BRAND = 0;
const S_GATE = 70;
const S_ROUTE = 126;
const S_INNOV = 186;
const S_SRC = 242;
const S_TITLE = 324;
const S_HUMAN = 384;
const S_PLAT = 454;
const S_OUTRO = 518;
const XFADE = 4;

fs.mkdirSync(FRAMES, { recursive: true });
fs.mkdirSync(QA, { recursive: true });

const C = {
  ink: '#101113',
  ink2: '#22252b',
  paper: '#f6f3ed',
  paper2: '#e9e0d2',
  paper3: '#fffdf8',
  olive: '#2f7d5c',
  red: '#d45546',
  blue: '#406d9f',
  amber: '#c19a5b',
  muted: '#8b8378',
  line: '#d6c7b0',
  white: '#fffdf8',
};

const esc = (s) => String(s).replace(/[&<>"']/g, (m) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;',
}[m]));
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const easeOut = (t) => 1 - Math.pow(1 - clamp(t), 3);
const easeInOut = (t) => {
  t = clamp(t);
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
};
const back = (t) => {
  t = clamp(t);
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
};
const seg = (f, a, b, e = easeOut) => clamp(e((f - a) / (b - a)));
const fade = (f, a, b) => clamp((f - a) / (b - a));
const local = (f, a, b) => clamp((f - a) / (b - a));
const mulberry = (seed) => {
  let t = seed >>> 0;
  return () => {
    t += 0x6D2B79F5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
};

function bg() {
  const dots = [];
  const rand = mulberry(1021);
  for (let i = 0; i < 120; i++) {
    const x = Math.floor(rand() * WIDTH);
    const y = Math.floor(rand() * HEIGHT);
    const op = 0.035 + rand() * 0.05;
    dots.push(`<circle cx="${x}" cy="${y}" r="${0.7 + rand() * 1.8}" fill="${C.paper3}" opacity="${op}"/>`);
  }
  return `
  <rect width="${WIDTH}" height="${HEIGHT}" fill="${C.ink}"/>
  <rect width="${WIDTH}" height="${HEIGHT}" fill="url(#bgGlow)" opacity="0.9"/>
  <path d="M-80 980C220 820 386 906 610 744C842 576 934 302 1276 320C1516 333 1650 458 2000 266V1080H-80V980Z" fill="${C.paper2}" opacity="0.13"/>
  <path d="M-40 870C240 728 438 808 640 664C836 524 1002 374 1294 402C1518 423 1668 510 1960 360" stroke="${C.paper3}" stroke-width="3" opacity="0.10"/>
  ${dots.join('')}`;
}

function defs() {
  return `
  <defs>
    <linearGradient id="bgGlow" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#191b20"/><stop offset="0.55" stop-color="#111317"/><stop offset="1" stop-color="#2b2420"/>
    </linearGradient>
    <linearGradient id="paperGrad" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#fffdf8"/><stop offset="1" stop-color="#e9e0d2"/>
    </linearGradient>
    <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#30343b"/><stop offset="0.5" stop-color="#15171b"/><stop offset="1" stop-color="#4a4137"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="28" stdDeviation="34" flood-color="#000" flood-opacity="0.36"/>
    </filter>
    <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="14" stdDeviation="18" flood-color="#000" flood-opacity="0.24"/>
    </filter>
    <filter id="blur8"><feGaussianBlur stdDeviation="8"/></filter>
  </defs>`;
}

function text(x, y, s, size, fill = C.white, weight = 700, extra = '') {
  return `<text x="${x}" y="${y}" fill="${fill}" font-family="-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',Arial,sans-serif" font-size="${size}" font-weight="${weight}" letter-spacing="0" ${extra}>${esc(s)}</text>`;
}
function serif(x, y, s, size, fill = C.white, weight = 800, extra = '') {
  return `<text x="${x}" y="${y}" fill="${fill}" font-family="Georgia,'Times New Roman','Songti SC','SimSun',serif" font-size="${size}" font-weight="${weight}" letter-spacing="0" ${extra}>${esc(s)}</text>`;
}
function mono(x, y, s, size, fill = C.white, weight = 600, extra = '') {
  return `<text x="${x}" y="${y}" fill="${fill}" font-family="'SFMono-Regular','Menlo','Consolas',monospace" font-size="${size}" font-weight="${weight}" letter-spacing="0" ${extra}>${esc(s)}</text>`;
}
function panel(x, y, w, h, r = 18, fill = 'url(#paperGrad)', stroke = '#e2d7c8', op = 1) {
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" opacity="${op}" filter="url(#softShadow)"/>`;
}
function chip(x, y, label, color, w = 170, op = 1) {
  return `<g opacity="${op}"><rect x="${x}" y="${y}" width="${w}" height="54" rx="27" fill="${color}"/>${text(x + w / 2, y + 36, label, 25, C.white, 700, 'text-anchor="middle"')}</g>`;
}
function fileCard(x, y, name, sub, color, scale = 1, op = 1) {
  return `<g transform="translate(${x} ${y}) scale(${scale})" opacity="${op}">
    <rect width="255" height="148" rx="16" fill="${C.paper3}" stroke="#e1d6c6" filter="url(#softShadow)"/>
    <rect x="0" y="0" width="255" height="38" rx="16" fill="${color}" opacity="0.95"/>
    <rect x="0" y="22" width="255" height="20" fill="${color}" opacity="0.95"/>
    ${mono(18, 73, name, 24, C.ink, 800)}
    ${text(18, 112, sub, 22, C.muted, 600)}
  </g>`;
}

function logoMark(x, y, s = 1, fill = C.paper3) {
  return `<g transform="translate(${x} ${y}) scale(${s})">
    <rect x="-46" y="-46" width="92" height="92" rx="24" fill="${fill === C.paper3 ? C.ink : fill}"/>
    <path d="M0 -28L28 -12V18L0 34L-28 18V-12L0 -28Z" fill="${fill}"/>
    <path d="M0 -18L16 -9V9L0 18L-16 9V-9L0 -18Z" fill="${fill === C.paper3 ? C.ink : C.paper3}"/>
    <path d="M0 -28V34" stroke="${fill === C.paper3 ? C.ink : C.paper3}" stroke-width="7" stroke-linecap="round"/>
  </g>`;
}

function shotBrand(f) {
  const t = f;
  const cross = 1 - fade(t, 26, 38);
  const letters = 'Mr.Li Writer'.split('');
  const letterGroupOp = 1 - seg(t, 22, 28, (x) => x);
  const letterSvg = letters.map((ch, i) => {
    const u = seg(t, 4 + i * 1.7, 18 + i * 1.7);
    const x = 612 + i * 49;
    const sc = lerp(1.45, 1, back(u));
    const op = u;
    return `<text x="${x}" y="510" fill="${C.white}" opacity="${op}" font-family="Georgia,'Times New Roman',serif" font-size="104" font-weight="800" transform="translate(${x} 510) scale(${sc}) translate(${-x} -510)">${esc(ch)}</text>`;
  }).join('');
  const sub = '写作 Skill，让想法变成可信内容';
  const n = Math.floor(seg(t, 20, 36, (x) => x) * sub.length);
  return `
    <g opacity="${cross}">
      <path d="M960 276V392" stroke="${C.amber}" stroke-width="4" stroke-linecap="round" stroke-dasharray="116" stroke-dashoffset="${116 * (1 - seg(t, 0, 10, (x) => x))}"/>
      <path d="M902 334H1018" stroke="${C.amber}" stroke-width="4" stroke-linecap="round" stroke-dasharray="116" stroke-dashoffset="${116 * (1 - seg(t, 8, 18, (x) => x))}"/>
    </g>
    ${logoMark(500, 462, 1.18, C.paper3)}
    <g opacity="${letterGroupOp}">${letterSvg}</g>
    ${serif(1005, 510, 'Mr.Li Writer', 104, C.white, 800, `text-anchor="middle" opacity="${seg(t, 22, 30, (x) => x)}"`)}
    ${text(960, 592, sub.slice(0, n), 44, '#d8cabb', 650, 'text-anchor="middle"')}
    <rect x="${960 + n * 13 - 350}" y="558" width="4" height="45" fill="${C.amber}" opacity="${Math.floor(f / 4) % 2 ? 0.25 : 1}"/>
    ${text(960, 704, '编辑路由 · 确认门禁 · 事实核验 · 平台原生 · 真实交付', 36, '#a9a196', 650, `text-anchor="middle" opacity="${0.92 * seg(t, 30, 40, (x) => x)}"`)}
  `;
}

function shotGate(f) {
  const t = f - S_GATE;
  const rows = [
    ['发布平台', '公众号', C.olive],
    ['内容目标', '普通传播', C.blue],
    ['创作方向', '实用指南', C.amber],
    ['交付样式', '摸鱼绿', C.red],
  ];
  const rowSvg = rows.map((r, i) => {
    const u = seg(t, 6 + i * 5, 20 + i * 5);
    const dx = lerp(46, 0, back(u));
    return `<g opacity="${u}" transform="translate(${dx} 0)">
      <rect x="1120" y="${368 + i * 76}" width="540" height="60" rx="12" fill="#f1eadf" stroke="#e0d5c6"/>
      ${text(1150, 408 + i * 76, r[0], 30, C.ink, 800)}
      ${text(1580, 408 + i * 76, r[1], 28, r[2], 800, 'text-anchor="end"')}
      <circle cx="1618" cy="${398 + i * 76}" r="14" fill="${C.olive}" opacity="${seg(t, 14 + i * 5, 24 + i * 5)}"/>
      ${text(1618, 407 + i * 76, '✓', 19, C.white, 900, `text-anchor="middle" opacity="${seg(t, 14 + i * 5, 24 + i * 5)}"`)}
    </g>`;
  }).join('');
  const stampU = seg(t, 30, 38, back);
  const quoteU = seg(t, 28, 42);
  return `
    ${text(150, 156, '先确认，再动笔', 66, C.white, 900)}
    ${text(154, 218, '一次问清关键项，不用默认值赌你的预期', 34, '#d9d0c4', 650)}
    ${panel(1060, 258, 660, 540, 22, C.paper3)}
    ${text(1120, 330, '标准问题卡', 38, C.ink, 850)}
    ${mono(1120, 706, 'memory firewall · 历史偏好 ≠ 本次确认', 24, C.muted, 700, `opacity="${seg(t, 36, 46)}"`)}
    ${rowSvg}
    <g transform="translate(1660 316) rotate(-10) scale(${stampU})" opacity="${stampU}">
      <rect x="-58" y="-58" width="116" height="116" rx="14" fill="none" stroke="${C.red}" stroke-width="6"/>
      ${text(0, 16, '必问', 42, C.red, 900, 'text-anchor="middle"')}
    </g>
    <g opacity="${seg(t, 22, 30)}">
      ${chip(150, 430, '确认', C.olive, 128, seg(t, 22, 30))}
      ${chip(338, 430, '开写', C.blue, 128, seg(t, 27, 35))}
      ${chip(526, 430, '交付', C.amber, 128, seg(t, 32, 40))}
      <path d="M282 457H332" stroke="#8b8378" stroke-width="4" opacity="${seg(t, 26, 34)}"/>
      <path d="M470 457H520" stroke="#8b8378" stroke-width="4" opacity="${seg(t, 31, 39)}"/>
    </g>
    <g opacity="${quoteU}" transform="translate(0 ${lerp(24, 0, back(quoteU))})">
      ${panel(150, 560, 620, 150, 18, C.paper3)}
      ${text(190, 622, '"写公众号，写成实用指南"', 31, C.ink, 800)}
      ${text(190, 672, '确认来源：用户原话', 25, C.olive, 800)}
    </g>
  `;
}

function shotRouting(f) {
  const t = f - S_ROUTE;
  const labels = ['找答案', '做选择', '避风险', '学方法', '被理解', '看故事'];
  const chips = labels.map((l, i) => {
    const u = seg(t, 5 + i * 4, 18 + i * 4);
    const x = lerp(-220, 188 + (i % 3) * 220, back(u));
    const y = 224 + Math.floor(i / 3) * 86;
    const colors = [C.blue, C.olive, C.red, C.amber, '#6a5acd', '#8b5a2b'];
    return chip(x, y, l, colors[i], 172, u);
  }).join('');
  const rowOp = seg(t, 34, 52);
  const skeleton = [0, 1, 2, 3].map((i) => `
    <rect x="1110" y="${290 + i * 54}" width="${360 + i * 34}" height="12" rx="6" fill="#e4dacf" opacity="${(0.75 - i * 0.08) * (1 - rowOp)}"/>
    <rect x="1110" y="${314 + i * 54}" width="${220 + i * 46}" height="8" rx="4" fill="#d4c7b4" opacity="${(0.38 - i * 0.04) * (1 - rowOp)}"/>
  `).join('');
  return `
    ${panel(1050, 170, 620, 650, 22, C.paper3)}
    ${text(1110, 240, '编辑路由卡', 42, C.ink, 850)}
    <g opacity="${1 - rowOp}">${skeleton}</g>
    ${mono(1110, 306, 'reader_job: avoid_risk', 28, C.olive, 800, `opacity="${rowOp}"`)}
    ${mono(1110, 360, 'evidence_density: high', 28, C.blue, 800, `opacity="${rowOp}"`)}
    ${mono(1110, 414, 'innovation: minimum', 28, C.red, 800, `opacity="${rowOp}"`)}
    ${mono(1110, 468, 'platform: native', 28, C.amber, 800, `opacity="${rowOp}"`)}
    <rect x="1110" y="548" width="${440 * rowOp}" height="8" rx="4" fill="${C.olive}"/>
    <rect x="1110" y="588" width="${370 * rowOp}" height="8" rx="4" fill="${C.blue}"/>
    <rect x="1110" y="628" width="${505 * rowOp}" height="8" rx="4" fill="${C.red}"/>
    ${chips}
    ${text(150, 720, '先判断读者任务，再决定怎么写', 58, C.white, 850)}
    ${text(154, 774, '不是一上来就套文章结构', 32, '#d9d0c4', 650)}
  `;
}

function shotInnovation(f) {
  const t = f - S_INNOV;
  const steps = [
    ['直给型', '能说清就不升维', C.olive],
    ['微创新', '增加一点新信息', C.blue],
    ['视角转换', '换人群或场景', C.amber],
    ['概念创新', '材料足够才启动', C.red],
  ];
  const cards = steps.map((s, i) => {
    const u = seg(t, 2 + i * 6, 18 + i * 6);
    const x = 255 + i * 345;
    const y = lerp(690, 420 - i * 42, back(u));
    const glow = i === 1 ? seg(t, 38, 50) : 0;
    return `<g transform="translate(${x} ${y})" opacity="${u}">
      <rect width="295" height="190" rx="20" fill="${i === 1 ? C.paper3 : '#25282f'}" stroke="${s[2]}" stroke-width="${i === 1 ? 5 : 2}" filter="url(#softShadow)"/>
      <rect x="22" y="24" width="58" height="58" rx="16" fill="${s[2]}"/>
      ${text(51, 64, String(i + 1), 32, C.white, 850, 'text-anchor="middle"')}
      ${text(24, 122, s[0], 38, i === 1 ? C.ink : C.white, 850)}
      ${text(24, 160, s[1], 25, i === 1 ? C.muted : '#cfc7bb', 650)}
      <rect x="-10" y="-10" width="315" height="210" rx="24" fill="${s[2]}" opacity="${glow * 0.16}" filter="url(#blur8)"/>
    </g>`;
  }).join('');
  return `
    ${text(192, 208, '最低必要创新', 74, C.white, 900)}
    ${text(196, 270, '新角度只有在读者收益和材料支撑都增加时才成立', 34, '#d9d0c4', 650)}
    <path d="M230 748C520 650 802 704 1092 560C1288 462 1386 412 1610 398" stroke="${C.amber}" stroke-width="5" opacity="0.54" fill="none"/>
    ${cards}
    <g opacity="${seg(t, 40, 48)}">
      <rect x="1238" y="198" width="300" height="62" rx="31" fill="${C.red}"/>
      ${text(1388, 240, '停止条件', 32, C.white, 850, 'text-anchor="middle"')}
    </g>
  `;
}

function sourceCard(x, y, title, sub, color, u) {
  return `<g transform="translate(${x} ${lerp(y + 90, y, back(u))})" opacity="${u}">
    <rect width="380" height="178" rx="18" fill="${C.paper3}" stroke="#dfd4c5" filter="url(#softShadow)"/>
    <rect x="22" y="24" width="76" height="76" rx="20" fill="${color}"/>
    ${text(60, 75, '✓', 44, C.white, 900, 'text-anchor="middle"')}
    ${text(122, 62, title, 31, C.ink, 850)}
    ${text(122, 108, sub, 24, C.muted, 650)}
    <rect x="122" y="132" width="212" height="8" rx="4" fill="${color}" opacity="0.5"/>
  </g>`;
}

function shotSources(f) {
  const t = f - S_SRC;
  return `
    ${text(150, 156, '真实可靠，不编造', 70, C.white, 900)}
    ${text(154, 216, '种子资料只作起点，硬信息继续核对官方最新来源', 34, '#d9d0c4', 650)}
    ${sourceCard(140, 320, '官方一手来源', '官网 / 公告 / 原始 PDF', C.olive, seg(t, 6, 22))}
    ${sourceCard(560, 320, '最新时点核验', '信息截至 2026-08-29', C.blue, seg(t, 16, 32))}
    ${sourceCard(980, 320, '冲突与降级', '冲突保留，不硬凑结论', C.amber, seg(t, 26, 42))}
    <g opacity="${seg(t, 36, 52)}">
      <rect x="1388" y="320" width="390" height="178" rx="18" fill="#2b1515" stroke="${C.red}" filter="url(#softShadow)"/>
      ${text(1584, 386, 'NO FABRICATION', 34, C.red, 900, 'text-anchor="middle"')}
      ${text(1584, 440, '查不到就降级或标注', 30, C.white, 800, 'text-anchor="middle"')}
    </g>
    <g transform="translate(190 610)">
      <rect width="1540" height="218" rx="22" fill="#0b0d12" stroke="#303744"/>
      ${mono(38, 58, '$ verify sources --risk high', 30, '#9dffcf')}
      ${mono(38, 108, 'A: official notice ... ok', 28, '#c9d3ea', 700, `opacity="${seg(t, 46, 54)}"`)}
      ${mono(38, 154, 'date: information as of 2026-08-29', 28, '#c9d3ea', 700, `opacity="${seg(t, 54, 62)}"`)}
      ${mono(38, 200, 'claim strength: supported / downgrade if stale', 28, '#c9d3ea', 700, `opacity="${seg(t, 62, 70)}"`)}
    </g>
  `;
}

function shotTitleOpening(f) {
  const t = f - S_TITLE;
  const bad = ['随着时代发展', '后台有人问', '你是否也曾', '震惊速看'];
  const layoutShift = 215;
  const badSvg = bad.map((b, i) => {
    const y = 305 + i * 78;
    const u = seg(t, 6 + i * 4, 18 + i * 4);
    return `<g opacity="${u}">
      <rect x="${156 + layoutShift}" y="${y - 42}" width="420" height="58" rx="12" fill="#2a2d34" stroke="#444955"/>
      ${text(182 + layoutShift, y, b, 31, '#cfc7bb', 700)}
      <path d="M${174 + layoutShift} ${y - 14}L${552 + layoutShift} ${y - 14}" stroke="${C.red}" stroke-width="5" opacity="${seg(t, 24 + i * 2, 32 + i * 2)}"/>
    </g>`;
  }).join('');
  const contract = ['目标读者', '此刻相关', '标题承诺', '正文证据'].map((l, i) =>
    chip(1090 + layoutShift, 278 + i * 86, l, [C.olive, C.blue, C.amber, C.red][i], 244, seg(t, 10 + i * 6, 24 + i * 6))
  ).join('');
  return `
    ${text(145, 160, '标题和开头，先做编辑决策', 66, C.white, 900)}
    ${text(150, 218, '点击契约先成立，正文才开始写', 34, '#d9d0c4', 650)}
    ${badSvg}
    ${panel(742 + layoutShift, 292, 300, 360, 20, C.paper3)}
    ${serif(790 + layoutShift, 380, '入口', 82, C.ink, 900)}
    ${text(790 + layoutShift, 458, '直接回答', 34, C.olive, 850)}
    ${text(790 + layoutShift, 512, '具体场景', 34, C.blue, 850)}
    ${text(790 + layoutShift, 566, '判断先行', 34, C.red, 850)}
    <rect x="${783 + layoutShift}" y="592" width="${200 * seg(t, 44, 54)}" height="8" rx="4" fill="${C.amber}"/>
    ${contract}
  `;
}

function shotHumanize(f) {
  const t = f - S_HUMAN;
  const lines = [
    ['删除模板开头', '保留说话位置'],
    ['删掉虚构经历', '只写真实材料'],
    ['合并重复段落', '每段新增东西'],
    ['降低证据腔', '匹配文章体裁'],
  ];
  const rows = lines.map((r, i) => {
    const u = seg(t, i * 4, 10 + i * 4);
    return `<g opacity="${u}">
      <rect x="250" y="${308 + i * 82}" width="620" height="58" rx="12" fill="#2a1d1d" stroke="#613433"/>
      ${text(282, 348 + i * 82, r[0], 30, '#efb0a7', 750)}
      <path d="M272 ${332 + i * 82}L806 ${332 + i * 82}" stroke="${C.red}" stroke-width="4" opacity="${seg(t, 14 + i * 3, 22 + i * 3)}"/>
      <rect x="958" y="${308 + i * 82}" width="620" height="58" rx="12" fill="${C.paper3}" stroke="#dfd4c5"/>
      ${text(990, 348 + i * 82, r[1], 30, C.ink, 800)}
    </g>`;
  }).join('');
  return `
    ${text(160, 156, '去 AI 味不是伪装', 70, C.white, 900)}
    <rect x="162" y="188" width="${330 * seg(t, 2, 12)}" height="7" rx="4" fill="${C.amber}"/>
    ${text(164, 246, '两轮检查后直接改写：材料、位置、取舍、节奏', 34, '#d9d0c4', 650)}
    ${rows}
    <g opacity="${seg(t, 36, 48)}">
      <rect x="710" y="760" width="500" height="78" rx="39" fill="${C.olive}"/>
      ${text(960, 812, 'PASS 1 + PASS 2', 36, C.white, 900, 'text-anchor="middle"')}
    </g>
  `;
}

function shotPlatforms(f) {
  const t = f - S_PLAT;
  const plats = [
    ['公众号', '主题排版四件套', C.olive],
    ['知乎', '回答 / 专栏原文', C.blue],
    ['小红书', '纯文本 / 卡片预览', C.red],
    ['官网/网页', 'SEO / GEO 结构化', C.amber],
    ['个人博客', 'Markdown 长文', '#6a5acd'],
  ];
  const cards = plats.map((p, i) => {
    const u = seg(t, 2 + i * 4, 16 + i * 4);
    const x = lerp(210 + i * 300, 235 + i * 292, u);
    const y = lerp(780, 430 + Math.sin(i) * 42, back(u));
    return fileCard(x, y, p[0], p[1], p[2], 1, u);
  }).join('');
  return `
    ${text(145, 164, '平台不是格式参数', 72, C.white, 900)}
    ${text(150, 224, '交付样式逐平台确认，再写平台原生内容', 34, '#d9d0c4', 650)}
    <path d="M164 706C436 572 666 718 922 572C1174 428 1382 508 1694 352" stroke="${C.paper3}" stroke-width="4" opacity="0.18" fill="none"/>
    ${cards}
    ${text(960, 818, '不把公众号长文缩短后分发到所有平台', 42, C.white, 850, `text-anchor="middle" opacity="${0.96 * seg(t, 40, 50)}"`)}
  `;
}

function shotOutro(f) {
  const t = f - S_OUTRO;
  const items = [
    ['route.card', '路由与确认', C.blue],
    ['sources.log', '最新核验', C.olive],
    ['title.md', '点击契约', C.amber],
    ['article.md', '自然正文', C.red],
    ['gzh.html', '公众号排版', C.olive],
    ['preview.html', '复制预览', C.blue],
    ['validate.py', '交付校验', C.red],
  ];
  const itemSvg = items.map((it, i) => {
    const u = seg(t, 2 + i * 1.5, 12 + i * 1.5);
    const op = Math.max(u, seg(t, 0, 4));
    const angle = (i / items.length) * Math.PI * 2;
    const tx = 960 + Math.cos(angle) * 560 - 128;
    const ty = 510 + Math.sin(angle) * 305 - 74;
    const sx = i % 2 ? -220 : 1960;
    const sy = 120 + i * 110;
    return fileCard(lerp(sx, tx, back(u)), lerp(sy, ty, back(u)), it[0], it[1], it[2], 0.82, op);
  }).join('');
  const word = seg(t, 24, 44);
  return `
    ${itemSvg}
    <g transform="translate(960 505) scale(${lerp(0.86, 1, back(word))})" opacity="${word}">
      <rect x="-340" y="-130" width="680" height="260" rx="30" fill="${C.paper3}" filter="url(#shadow)"/>
      ${logoMark(-240, -6, 0.98, C.paper3)}
      ${serif(-148, -12, 'Mr.Li Writer', 64, C.ink, 900)}
      ${text(15, 70, '从判断、核验、写作到真实交付', 32, C.muted, 800, 'text-anchor="middle"')}
      <rect x="-240" y="96" width="${480 * seg(t, 40, 52)}" height="7" rx="4" fill="${C.amber}"/>
    </g>
    ${text(960, 940, '真实可靠 · 不编造 · 引用最新可核验资料', 43, C.white, 850, `text-anchor="middle" opacity="${seg(t, 40, 52)}"`)}
  `;
}

function scene(f) {
  let body = '';
  if (f < S_GATE) body = shotBrand(f);
  else if (f < S_ROUTE) body = shotGate(f);
  else if (f < S_INNOV) body = shotRouting(f);
  else if (f < S_SRC) body = shotInnovation(f);
  else if (f < S_TITLE) body = shotSources(f);
  else if (f < S_HUMAN) body = shotTitleOpening(f);
  else if (f < S_PLAT) body = shotHumanize(f);
  else if (f < S_OUTRO) body = shotPlatforms(f);
  else if (f < S_OUTRO + XFADE) {
    const k = 1 - (f - S_OUTRO) / XFADE;
    body = `<g opacity="${k}">${shotPlatforms(f)}</g>${shotOutro(f)}`;
  } else body = shotOutro(f);
  const vignette = `<rect width="${WIDTH}" height="${HEIGHT}" fill="none" stroke="#000" stroke-width="80" opacity="0.14"/>`;
  return `<svg width="${WIDTH}" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}" xmlns="http://www.w3.org/2000/svg">
    ${defs()}
    ${bg()}
    ${body}
    ${vignette}
  </svg>`;
}

async function main() {
  const keyFrames = new Set([0, 30, 60, 98, 156, 214, 262, 300, 354, 420, 480, 524, 560, 599]);
  for (let f = 0; f < TOTAL; f++) {
    const svg = scene(f);
    const file = path.join(FRAMES, `frame-${String(f).padStart(4, '0')}.png`);
    await sharp(Buffer.from(svg)).png().toFile(file);
    if (keyFrames.has(f)) {
      await sharp(Buffer.from(svg)).png().toFile(path.join(QA, `f${String(f).padStart(3, '0')}.png`));
    }
    if (f % 30 === 0) process.stdout.write(`frame ${f}/${TOTAL}\n`);
  }
  fs.writeFileSync(path.join(OUT, 'render-info.json'), JSON.stringify({ width: WIDTH, height: HEIGHT, fps: FPS, frames: TOTAL, shots: { brand: S_BRAND, gate: S_GATE, routing: S_ROUTE, innovation: S_INNOV, sources: S_SRC, title: S_TITLE, humanize: S_HUMAN, platforms: S_PLAT, outro: S_OUTRO, xfade: XFADE } }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
