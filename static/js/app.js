/* 微积分计算器 Web 版前端逻辑。后端为 Python（Flask + sympy）。
   特性：积木编辑器置顶、MathLive 虚拟键盘（页面底部）、公式浮层预览、
   输入行内“公式输入 / 加入缓存”按钮、桌面端一致的表达式输入格式、
   手机端竖屏适配（侧栏抽屉 / 键盘全宽）。
*/

// ============================ 全局状态 ============================
let STATE = { fs: [], vs: [], eqs: [], rels: [], pjs: {}, ljs: {}, cache: [] };
let LANG = localStorage.getItem("lang") || "zh";
let THEME = localStorage.getItem("theme") || "light";
let lastFocusedInput = null;
let currentTab = "home";
let suppressKBOpen = false;

// ============================ 小工具 ============================
const $ = (id) => document.getElementById(String(id).replace(/^#/, ""));

function apiPost(path, data) {
  return fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data || {}),
  }).then((r) => r.json());
}
function apiGet(path) {
  return fetch(path).then((r) => r.json());
}

function toast(msg) {
  const t = $("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove("show"), 1800);
}

function typeset(node) {
  if (node && window.MathJax && MathJax.typesetPromise) {
    try { MathJax.typesetPromise([node]); } catch (e) {}
  }
}

function showResult(boxId, data) {
  const box = $(boxId);
  if (!box) return;
  if (data.ok) {
    box.className = "result";
    box.innerHTML = "$$" + data.latex + "$$";
    typeset(box);
  } else {
    box.className = "result error";
    box.textContent = t("error") + ": " + data.error;
  }
}
function showImage(boxId, url) {
  const box = $(boxId);
  if (!box) return;
  box.className = "img-result";
  box.innerHTML = '<img src="' + url + '" alt="plot">';
}

function refreshState() {
  return apiGet("/api/state").then((d) => {
    if (d.ok) STATE = d;
  }).catch(() => {});
}

// ============================ 公式输入格式（与桌面端一致） ============================
// 输入框接受 原生 Sympy 表达式 或 '$'+LaTeX 代码。预览浮层使用 MathJax 渲染，
// 仅接受 LaTeX，因此需把原生 SymPy 表达式经后端转换成 LaTeX。
// 这里维护一个转换缓存，避免对相同表达式反复请求。
const _latexCache = new Map();
function exprToLatex(v) {
  return new Promise((resolve) => {
    const s = (v || "").trim();
    if (!s) { resolve(""); return; }
    if (s.startsWith("$")) { resolve(s.slice(1).trim()); return; }  // 已是 LaTeX，直接返回
    const cached = _latexCache.get(s);
    if (cached !== undefined) { resolve(cached); return; }
    apiPost("/api/expr2latex", { expr: s }).then((r) => {
      if (r && r.ok) { _latexCache.set(s, r.latex); resolve(r.latex); }
      else { _latexCache.set(s, ""); resolve(""); }   // 解析失败：缓存空结果避免重复请求
    }).catch(() => { _latexCache.set(s, ""); resolve(""); });
  });
}

// ============================ 公式浮层预览 ============================
// 鼠标悬停于输入框上方、且输入框未被选中时，在其正上方实时浮现公式预览框。
function positionPreviewPop(inp, pop) {
  const r = inp.getBoundingClientRect();
  const w = Math.min(pop.offsetWidth || 300, window.innerWidth - 12);
  const left = Math.max(6, Math.min(r.left, window.innerWidth - w - 6));
  pop.style.left = left + "px";
  pop.style.width = Math.max(180, Math.min(r.width, 380)) + "px";
  // 始终浮于输入框上方（留 12px 间距），按实际高度定位，避免遮挡文本框内容
  let top = r.top - pop.offsetHeight - 12;
  if (top < 8) top = r.bottom + 12;  // 上方空间不足时改放下方
  pop.style.top = top + "px";
}
function updatePreviewPop(id) {
  const inp = $(id);
  if (!inp) return;
  const pop = $("#preview-pop");
  if (!pop) return;
  // 文本框被选中（聚焦）时不显示预览，避免遮挡编辑
  if (document.activeElement === inp) { pop.hidden = true; return; }
  const body = $("#preview-pop-body");
  const raw = (inp.value || "").trim();
  pop.hidden = false;
  positionPreviewPop(inp, pop);
  if (!raw) {
    body.innerHTML = '<span class="ph">' + t("previewPlaceholder") + "</span>";
    return;
  }
  // 原生 SymPy 表达式需经后端转成 LaTeX 才能被 MathJax 渲染
  exprToLatex(raw).then((latex) => {
    if (document.activeElement === inp) { pop.hidden = true; return; }  // 异步返回时已聚焦则不再显示
    if (!latex) { body.textContent = raw; return; }  // 无法转换时退化显示原始文本
    body.innerHTML = "$$" + latex + "$$";
    if (window.MathJax && MathJax.typesetPromise) {
      MathJax.typesetPromise([body]).then(() => {
        if (document.activeElement !== inp) positionPreviewPop(inp, pop);  // 渲染后高度变化，重新定位
      }).catch(() => {});
    }
  });
}
function hidePreviewPop() {
  const pop = $("#preview-pop");
  if (pop) pop.hidden = true;
}
function attachPreview(id) {
  const inp = $(id);
  if (!inp || inp.dataset.preview) return;
  inp.dataset.preview = "1";
  inp.addEventListener("focus", () => {
    lastFocusedInput = id;
    // 选中/聚焦输入框时不显示预览（避免遮挡编辑）
    hidePreviewPop();
    // 聚焦公式输入框时，页面底部弹出 MathLive 虚拟键盘（与桌面版一致）
    if (suppressKBOpen) { suppressKBOpen = false; }
    else openMathKB(null);
  });
  // 仅当鼠标悬停且输入框未被选中时显示预览
  inp.addEventListener("input", () => {
    if (document.activeElement !== inp) updatePreviewPop(id);
  });
  inp.addEventListener("mouseenter", () => {
    if (document.activeElement !== inp) updatePreviewPop(id);
  });
  inp.addEventListener("mouseleave", () => hidePreviewPop());
  inp.addEventListener("blur", () => setTimeout(hidePreviewPop, 150));
}

// ============================ MathLive 虚拟键盘 ============================
let _kbRetries = 0;
function showMathKb() {
  // MathLive 0.110（UMD）：键盘由 window.mathVirtualKeyboard.show() 控制，
  // 必须先让 math-field 聚焦建立连接，再显示键盘。
  // 实测：过早调用 show()（<400ms）无效（custom element / MathLive 内部初始化未完成），
  // 真实环境（含 MathJax 大文件加载）甚至需 >700ms。这里采用"延迟 + 自动重试直到可见"。
  try {
    const kb = $("#mathkb");
    if (kb) kb.hidden = false;
    if (window.mathVirtualKeyboard) window.mathVirtualKeyboard.show();
    // 若键盘仍未可见，自动重试（最长约 2 秒）
    const k = document.querySelector(".ML__keyboard");
    if ((!k || !k.classList.contains("is-visible")) && _kbRetries < 6) {
      _kbRetries++;
      setTimeout(showMathKb, 300);
    }
  } catch (e) {}
}
function openMathKB(btn) {
  const kb = $("#mathkb");
  if (!kb) return;
  if (btn && btn.getAttribute("data-target")) {
    lastFocusedInput = btn.getAttribute("data-target");
    // 移动端不聚焦文本输入框，避免系统键盘覆盖 MathLive 键盘
    // 仅保存目标输入框ID，后续插入时使用
    updatePreviewPop(lastFocusedInput);
  }
  kb.hidden = false;                      // 先让容器可见（math-field 需要布局）
  const mf = $("#mf");
  if (mf) {
    // policy=auto：聚焦 math-field 后 MathLive 自动弹出虚拟键盘
    try { mf.mathVirtualKeyboardPolicy = "auto"; } catch (e) {}
    if (mf.focus) mf.focus();
  }
  const title = $("#mathkb-title");
  if (title) title.textContent = (lastFocusedInput ? "#" + lastFocusedInput + " · " : "") + t("mathInput");
  const out = $("#mathkbLatex");
  if (out && mf) out.textContent = mf.value || t("empty");
  // 延迟触发：等待 custom element upgrade 与 MathLive 内部连接完成后再显示，
  // 内置自动重试直到键盘可见（过早调用 show() 会抑制自动弹出）。
  _kbRetries = 0;
  setTimeout(showMathKb, 400);
}
function closeMathKB() {
  _kbRetries = 99;  // 停止自动重试，避免键盘被重新打开
  try { if (window.mathVirtualKeyboard) window.mathVirtualKeyboard.hide(); } catch (e) {}
  const kb = $("#mathkb");
  if (kb) kb.hidden = true;
  // 收起后重新聚焦最后使用的输入框，方便用户直接输入
  // 使用 suppressKBOpen 防止 refocus 时再次自动弹出 MathLive
  if (lastFocusedInput) {
    const t = $(lastFocusedInput);
    if (t) {
      suppressKBOpen = true;
      t.focus();
    }
  }
}
function clearMathKB() {
  const mf = $("#mf");
  if (mf) mf.value = "";
  const out = $("#mathkbLatex");
  if (out) out.textContent = t("empty");
}
function insertMath() {
  const mf = $("#mf");
  if (!mf) return;
  const latex = mf.value.trim();
  if (!latex) { toast(t("mathEmpty")); return; }
  apiPost("/api/latex2expr", { latex }).then((r) => {
    if (!r.ok) { toast(r.error); return; }
    const tgt = $(lastFocusedInput);
    if (tgt) {
      tgt.value = r.text;           // 原生 SymPy 表达式（与桌面端一致）
      tgt.dispatchEvent(new Event("input"));
      suppressKBOpen = true;        // 防止插入后再次自动弹出键盘
      tgt.focus();                  // 插入后聚焦输入框：按规则保持预览隐藏，避免遮挡编辑
    }
    clearMathKB();
    closeMathKB();
    toast(t("inserted"));
  });
}
function localizeKB() {
  const title = $("#mathkb-title");
  if (title) title.textContent = t("mathInput");
  const c = $("#mathkbClear"), i = $("#mathkbInsert"), x = $("#mathkbClose");
  if (c) c.textContent = t("clear");
  if (i) i.textContent = t("hkInsert");
  if (x) x.textContent = t("hkClose");
  const mf = $("#mf");
  if (mf) {
    mf.placeholder = t("mathFieldPh");
  }
  try {
    if (window.MathfieldElement) MathfieldElement.locale = LANG === "en" ? "en" : "zh-CN";
  } catch (e) {}
}

// 同步积木编辑器（iframe）的主题：调用其内部 applyBlocklyTheme 原地切换，无需重载。
function syncBlocklyTheme() {
  const f = $("#blocklyFrame");
  if (f && f.contentWindow && f.contentWindow.applyBlocklyTheme) {
    f.contentWindow.applyBlocklyTheme(THEME);
  }
}
// 同步积木编辑器（iframe）的语言：语言需重载 iframe 才能生效（Blockly Msg 在加载时注入）。
function syncBlocklyLang() {
  const f = $("#blocklyFrame");
  if (!f) return;
  const base = (f.getAttribute("src") || "/blockly").split("?")[0];
  const target = base + "?lang=" + (LANG === "en" ? "en" : "zh") + "&theme=" + THEME;
  if (f.getAttribute("src") !== target) f.src = target;
}

// ============================ 表单构造 ============================
function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;")
    .replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
// 缓存下拉框：列出缓存内容，选中即插入到对应输入框（显示在“加入缓存”右侧）
function cacheSelect(id) {
  let opts = '<option value="">' + t("cachePick") + "</option>";
  (STATE.cache || []).forEach((c, i) => {
    opts += '<option value="' + i + '">' + escapeHtml(c[1] || c[0] || "") + "</option>";
  });
  return '<select class="cache-select" data-target="' + id + '" onchange="insertCacheSel(this)" title="' + t("cachePick") + '">' + opts + "</select>";
}
function insertCacheSel(sel) {
  const idx = sel.value;
  sel.value = "";
  if (idx === "") return;
  const tgt = $(sel.getAttribute("data-target"));
  const c = STATE.cache && STATE.cache[parseInt(idx, 10)];
  if (!tgt || !c) return;
  tgt.value = c[1] || c[0] || "";
  tgt.dispatchEvent(new Event("input"));
  tgt.focus();
  updatePreviewPop(tgt.id);
  toast(t("insert"));
}
function formulaField(id, label, placeholder, opts) {
  opts = opts || {};
  const actions = [];
  if (opts.math !== false) {
    actions.push('<button type="button" class="ghost small mf-btn" data-target="' + id +
      '" onclick="openMathKB(this)" title="' + t("mathInput") + '">ƒ</button>');
  }
  if (opts.cache !== false) {
    actions.push('<button type="button" class="ghost small" data-target="' + id +
      '" onclick="addCacheData(this)" title="' + t("addCache") + '">' + t("addCache") + "</button>");
    actions.push(cacheSelect(id));
  }
  const actionsHtml = actions.length
    ? '<div class="inline-actions">' + actions.join("") + "</div>" : "";
  const cls = opts.main ? "field main" : "field";
  const val = opts.value !== undefined && opts.value !== ""
    ? ' value="' + opts.value + '"' : "";
  return (
    '<div class="' + cls + '"><label>' + label + "</label>" +
    '<div class="field-inner">' +
    '<input type="text" id="' + id + '" class="formula-input" placeholder="' + (placeholder || "") + '"' + val + ' autocomplete="off">' +
    actionsHtml +
    "</div></div>"
  );
}
// 页面头部操作区：打开缓存区快捷入口
function pageHead(title, sub) {
  return '<div class="page-head"><div><h1>' + title + "</h1>" +
    (sub ? "<p>" + sub + "</p>" : "") + "</div>" +
    '<div class="head-actions">' +
    '<button type="button" class="ghost" onclick="goTab(\'huancun\')">🗄 ' + t("cacheTab") + "</button>" +
    "</div></div>";
}
function selectField(id, label, options, selected) {
  let html = '<div class="field"><label>' + label + "</label><select id=\"" + id + "\">";
  options.forEach((o) => {
    const v = typeof o === "string" ? o : o.v;
    const tx = typeof o === "string" ? o : o.t;
    html += '<option value="' + v + '"' + (v === selected ? " selected" : "") + ">" + tx + "</option>";
  });
  html += "</select></div>";
  return html;
}
function numField(id, label, placeholder, value) {
  return (
    '<div class="field"><label>' + label + "</label>" +
    '<input type="number" id="' + id + '" placeholder="' + (placeholder || "") + '" value="' + (value || "") + '" step="any"></div>'
  );
}
function textField(id, label, placeholder, value) {
  return (
    '<div class="field"><label>' + label + "</label>" +
    '<input type="text" id="' + id + '" placeholder="' + (placeholder || "") + '" value="' + (value || "") + '" autocomplete="off"></div>'
  );
}
function checkboxField(id, label, checked) {
  return (
    '<div class="field" style="flex:0 0 auto"><label>' + label + "</label>" +
    '<input type="checkbox" id="' + id + '"' + (checked ? " checked" : "") + ' style="width:auto;height:18px;"></div>'
  );
}
function computeBtn(label) {
  return '<button class="primary" id="btnCalc">' + (label || t("calc")) + "</button>";
}

function populateSelect(id, items, emptyLabel) {
  const sel = $(id);
  if (!sel) return;
  sel.innerHTML = "";
  if (emptyLabel) {
    const o = document.createElement("option");
    o.value = ""; o.textContent = emptyLabel;
    sel.appendChild(o);
  }
  items.forEach((it) => {
    const o = document.createElement("option");
    const v = typeof it === "string" ? it : it.v;
    o.value = v; o.textContent = typeof it === "string" ? it : it.t;
    sel.appendChild(o);
  });
}

function card(title, inner) {
  return '<div class="card"><h3>' + title + "</h3>" + inner + "</div>";
}
// 示例快捷填入：点击示例按钮即可将其填入对应输入框
function exampleChips(id, examples) {
  if (!examples || !examples.length) return "";
  return '<div class="ex-chips"><span class="ex-chips-label">' + t("示例：") + "</span>" +
    examples.map((e) =>
      '<button type="button" class="ex-chip" data-target="' + id +
      '" data-val="' + escapeHtml(e) + '" onclick="fillExample(this)">' +
      escapeHtml(e) + "</button>"
    ).join("") + "</div>";
}
function fillExample(btn) {
  const tgt = $(btn.getAttribute("data-target"));
  if (!tgt) return;
  tgt.value = btn.getAttribute("data-val");
  tgt.dispatchEvent(new Event("input"));
  tgt.focus();
  updatePreviewPop(tgt.id);
}
// 可折叠的“输入提示”卡片：内容源自 src/help.html 的输入标准（LaTeX / 数学符号 / 函数 / 分母有理化）
function funcInputHint() {
  return card(t("输入提示"),
    '<details class="hint-box">' +
    '<summary>' + t("hintSummary") + '</summary>' +
    '<div class="hint-body">' +
    "<p>" + t("hintP1") + "</p>" +
    "<p>" + t("hintP2") + "</p>" +
    "<p>" + t("hintP3") + "</p>" +
    "<p>" + t("hintP4") + "</p>" +
    '<p class="hint-foot">' + t("hintFoot") +
    '<a href="https://limingkang12345.github.io/CalculusCalculator/" target="_blank" rel="noopener">' + t("onlineDocs") + "</a>。</p>" +
    "</div></details>"
  );
}
// 已保存函数列表的 HTML（可独立刷新，避免重渲染整页覆盖输入框）
function funcListHtml() {
  let h = "";
  STATE.fs.forEach((n) => {
    h += '<div class="list-row"><span>' + n + "</span>" +
      '<div class="actions"><button class="ghost danger" data-kind="func" data-name="' + n + '" onclick="delFromData(this)">' + t("delete") + "</button></div></div>";
  });
  if (!STATE.fs.length) h = '<p class="hint">' + t("noData") + "</p>";
  return h;
}
// 函数输入准则：直接输入函数名（作为符号） vs 输入 函数(自变量值)（函数调用）
function funcUsageHint() {
  return card(t("函数输入准则"),
    '<div class="hint-body" style="border-radius:10px">' +
    "<p>" + t("hintFuncP1") + "</p>" +
    "<p>" + t("hintFuncP2") + "</p>" +
    '<p class="hint-foot">' + t("hintFuncFoot") + "</p>" +
    "</div>"
  );
}
// 仅刷新“已保存函数”列表，保留定义函数输入框的内容
function refreshFuncList() {
  const el = $("fsList");
  if (el) el.innerHTML = funcListHtml();
}

// ============================ 选项常量 ============================
const SIMPLIFY_METHODS = [
  t("通用化简"), t("展开"), t("因式分解"), t("主元"), t("通分"), t("分离"),
  t("三角变换"), t("三角展开"), t("指数合并"), t("指数展开"),
  t("对数展开"), t("对数合并"), t("换元"),
];
const CALC_ENGINES = [t("Python内置引擎"), t("Mpmath高精度引擎"), t("SymPy符号引擎"), t("LaTeX代码生成引擎")];
const INEQ_OPS = [">", "≥", "<", "≤", "≠"];
const TRIANGLE_CONDS = [t("A 角"), t("B 角"), t("C 角"), t("a 边"), t("b 边"), t("c 边")];

const PLANE_DEF_METHODS = [
  t("点 (坐标 x,y)"), t("直线 (两点)"), t("圆 (圆心,半径)"), t("圆 (三点)"),
  t("三角形 (三点)"), t("多边形 (多点)"), t("圆 (直径两端)"), t("圆 (圆心过点)"),
  t("中垂线 (线段)"), t("平行线 (过点)"), t("垂线 (过点)"), t("角平分线 (两直线)"),
  t("角平分线 (三角形内角)"), t("中线 (三角形)"), t("高线 (三角形)"),
  t("中位线 (三角形)"), t("内切圆 (三角形)"), t("旁切圆 (三角形)"), t("线段 (两点)"),
];
const PLANE_CALC_METHODS = [
  t("两点间距离"), t("中点"), t("三点共线判断"), t("平移"), t("旋转"), t("对称"),
  t("直线方程"), t("直线斜率"), t("两直线交点"), t("点到直线距离"),
  t("两直线夹角"), t("平行判断"), t("垂直判断"), t("圆心"), t("圆半径"),
  t("圆面积"), t("圆周长"), t("两圆交点"), t("圆的切线"), t("三角形面积"),
  t("三角形周长"), t("三角形外心"), t("外接圆半径"), t("三角形内心"),
  t("内切圆半径"), t("三角形重心"), t("三角形垂心"), t("直角三角形判断"),
  t("等腰三角形判断"), t("等边三角形判断"), t("多边形面积"), t("多边形周长"),
];
const SOLID_DEF_METHODS = [
  t("点 (坐标 x,y,z)"), t("直线 (两点)"), t("平行平面 (过一点)"),
  t("垂直平面 (过一点,垂直直线)"), t("平行直线 (过一点)"), t("垂线 (过一点,垂足)"),
  t("垂线 (过一点,垂直平面)"), t("平面 (过直线和一点)"),
  t("平面 (过两相交直线)"), t("垂足 (点到平面)"), t("垂足 (点到直线)"), t("线段 (两点)"),
];
const SOLID_CALC_METHODS = [
  t("两点间距离"), t("中点"), t("点到平面距离"), t("点到直线距离"),
  t("点在平面上的投影"), t("点在直线上的投影"), t("四点共面判断"),
  t("直线方向向量"), t("两直线交点"), t("两直线夹角"),
  t("两直线平行判断"), t("两直线垂直判断"), t("直线在平面上的投影"),
  t("平面方程"), t("平面法向量"), t("两平面夹角"), t("两平面交线"),
  t("两平面平行判断"), t("两平面垂直判断"), t("直线与平面交点"),
  t("四面体体积"), t("直线与平面的夹角"),
];
const FUNC_ATTRS = [
  t("表达式 & 定义域"), t("值域"), t("递增区间"), t("递减区间"),
  t("奇偶性"), t("周期性"), t("最大值"), t("最小值"),
];
const VEC_OPS = [
  { v: "add", t: t("向量加法") }, { v: "sub", t: t("向量减法") },
  { v: "scalar", t: t("数乘") }, { v: "dot", t: t("数量积(点乘)") },
  { v: "cross", t: t("向量积(叉乘)") }, { v: "length", t: t("模(长度)") },
  { v: "angle", t: t("夹角") }, { v: "projection", t: t("投影") },
  { v: "unit", t: t("单位向量") },
];
const VEC_ATTRS = [t("向量表达式"), t("模"), t("方向角"), t("单位向量")];

// ============================ 各功能页 ============================
// 积木编辑器置于最上方
const TABS = [
  // -------- 积木编辑器（置顶） --------
  {
    id: "blockly", zh: "积木编辑器", en: "Blocks", icon: "🧩", group: "top",
    html() {
      return (
        '<iframe id="blocklyFrame" src="/blockly?lang=' + (LANG === "en" ? "en" : "zh") +
        '&theme=' + THEME + '" title="' + t("积木编辑器") +
        '" loading="lazy"></iframe>'
      );
    },
    init() {
      // iframe 内为完整 Blockly 编辑器，无需在此额外初始化。
    },
  },

  // -------- 首页 --------
  {
    id: "home", zh: "首页", en: "Home", icon: "⌂", group: "misc",
    html() {
      return (
        '<div class="home-hero"><h1>' + t("appTitle") + "</h1><p>" +
        t("homeDesc") + "</p>" +
        '<div class="home-stats">' +
        '<span class="home-stat">' + t("homeStat1") + '</span>' +
        '<span class="home-stat">' + t("homeStat2") + '</span>' +
        '<span class="home-stat">' + t("homeStat3") + '</span>' +
        '<span class="home-stat">' + t("homeStat4") + '</span>' +
        "</div>" +
        '<div class="home-links">' +
        '<a href="https://github.com/limingkang12345/CalculusCalculator" target="_blank" rel="noopener">GitHub</a>' +
        '<a href="https://limingkang12345.github.io/CalculusCalculator/" target="_blank" rel="noopener">' + t("onlineDocs") + "</a>" +
        '<a href="https://pypi.org/project/CalculusCalculator/" target="_blank" rel="noopener">PyPI</a>' +
        "</div></div>" +
        card(t("featureOverview"), '<div class="feature-grid">' +
          ["featDerivative", "featIntegral", "featFuncAttr", "featTransform",
           "featEquation", "featInequality", "featDE", "featTriangle",
           "featVector", "featPlot", "feat2D", "feat3D", "featBlockly", "featCache", "featArchive"].map(function (k) {
            return '<div class="feature-chip"><b>✓</b>' + t(k) + "</div>";
          }).join("") +
          "</div>") +
        card(t("usageTips"), "<ul>" +
          "<li>" + t("homeTip1") + "</li>" +
          "<li>" + t("homeTip2") + "</li>" +
          "<li>" + t("homeTip3") + "</li>" +
          "<li>" + t("homeTip4") + "</li></ul>")
      );
    },
  },

  // -------- 函数定义 --------
  {
    id: "dingyi", zh: "函数定义", en: "Define Function", icon: "ƒ", group: "calc",
    html() {
      return (
        pageHead(t("函数定义")) +
        card(t("定义函数"), '<div class="row">' +
          formulaField("f_expr", t("expr"), "x**2+1", { value: "x**2", main: true }) +
          textField("f_name", t("name"), "f", "f") +
          textField("f_var", t("var"), "x", "x") +
          textField("f_domain", t("domain"), "Reals", "Reals") +
          "</div>" +
          '<p class="field-hint">' + t("dingyiFieldHint") + "</p>" +
          exampleChips("f_expr", ["x**2", "sin(x)", "$\\frac{x}{2}", "sqrt(x)+1"]) +
          '<div style="margin-top:12px"><button class="primary" onclick="saveFunc()">' + t("save") + "</button></div>"
        ) +
        card(t("savedFuncs"), '<div id="fsList">' + funcListHtml() + "</div>") +
        funcUsageHint() +
        card(t("函数属性"), '<div class="row">' +
          formulaField("fa_expr", t("expr"), "x**2", { value: "x**2", main: true }) +
          textField("fa_var", t("var"), "x", "x") +
          textField("fa_domain", t("domain"), "Reals", "Reals") +
          selectField("fa_attr", t("属性"), FUNC_ATTRS.map((x, i) => ({ v: i, t: x }))) +
          "</div>" +
          exampleChips("fa_expr", ["x**2", "sin(x)", "$\\frac{x}{2}"]) +
          '<div style="margin-top:12px">' + computeBtn() +
          '</div><div class="result" id="fa_res"></div>'
        ) +
        funcInputHint()
      );
    },
    init() {
      attachPreview("f_expr"); attachPreview("fa_expr");
      $("btnCalc").onclick = () => {
        const d = {
          expr: $("fa_expr").value, var: $("fa_var").value || "x",
          domain: $("fa_domain").value, attr: parseInt($("fa_attr").value),
        };
        apiPost("/api/funcattr", d).then((r) => showResult("fa_res", r));
      };
    },
  },

  // -------- 求导 --------
  {
    id: "qiudao", zh: "求导", en: "Derivative", icon: "∂", group: "calc",
    html() {
      return (
        pageHead(t("求导")) +
        card("", '<div class="row">' +
          formulaField("d_expr", t("expr"), "sin(x)", { value: "sin(x)", main: true }) +
          textField("d_var", t("var"), "x", "x") +
          numField("d_order", t("阶数"), "1", "1") +
          formulaField("d_point", t("在某点(可空)"), "0", { cache: false }) +
          checkboxField("d_yin", t("隐函数求导"), false) +
          textField("d_yinvar", t("隐函数变量"), "t", "t") +
          "</div>" + exampleChips("d_expr", ["sin(x)", "x**2", "exp(x)", "log(x)"]) +
          '<div style=margin-top:12px>' + computeBtn() + "</div>" +
          '<div class="result" id="d_res"></div>'
        ) +
        funcInputHint()
      );
    },
    init() {
      attachPreview("d_expr"); attachPreview("d_point");
      $("btnCalc").onclick = () => {
        const d = {
          expr: $("d_expr").value, var: $("d_var").value || "x",
          order: $("d_order").value || "1",
          point: $("d_point").value, yinhanshu: $("d_yin").checked,
          yinvar: $("d_yinvar").value,
        };
        apiPost("/api/derivative", d).then((r) => showResult("d_res", r));
      };
    },
  },

  // -------- 积分 --------
  {
    id: "jifen", zh: "积分", en: "Integral", icon: "∫", group: "calc",
    html() {
      return (
        pageHead(t("积分")) +
        card("", '<div class="row">' +
          formulaField("i_expr", t("expr"), "x**2", { value: "x**2", main: true }) +
          textField("i_var", t("var"), "x", "x") +
          checkboxField("i_def", t("定积分"), false) +
          formulaField("i_a", t("下限"), "0", { cache: false }) +
          formulaField("i_b", t("上限"), "1", { cache: false }) +
          "</div>" + exampleChips("i_expr", ["x**2", "sin(x)", "1/x", "exp(x)"]) +
          '<div style=margin-top:12px>' + computeBtn() + "</div>" +
          '<div class="result" id="i_res"></div>'
        ) +
        funcInputHint()
      );
    },
    init() {
      attachPreview("i_expr"); attachPreview("i_a"); attachPreview("i_b");
      $("btnCalc").onclick = () => {
        const definite = $("i_def").checked;
        const d = {
          expr: $("i_expr").value, var: $("i_var").value || "x",
          a: definite ? $("i_a").value : "", b: definite ? $("i_b").value : "",
        };
        apiPost("/api/integral", d).then((r) => showResult("i_res", r));
      };
    },
  },

  // -------- 变形 --------
  {
    id: "bianxing", zh: "函数变形", en: "Transform", icon: "⇄", group: "calc",
    html() {
      const m = SIMPLIFY_METHODS.map((x, i) => ({ v: i, t: x }));
      return (
        pageHead(t("函数变形")) +
        card("", '<div class="row">' +
          formulaField("b_expr", t("expr"), "(x+1)**2", { value: "(x+1)**2", main: true }) +
          selectField("b_method", t("options"), m) +
          formulaField("b_zhuyuan", t("主元(可空)"), "x", { cache: false }) +
          formulaField("b_huanyuan", t("换元-新元(可空)"), "t", { cache: false }) +
          formulaField("b_huayuanshi", t("换元-原式(可空)"), "x", { cache: false }) +
          "</div>" + exampleChips("b_expr", ["(x+1)**2", "x**2-1", "sin(x)**2+cos(x)**2"]) +
          '<div style=margin-top:12px>' + computeBtn() + "</div>" +
          '<div class="result" id="b_res"></div>'
        ) +
        funcInputHint()
      );
    },
    init() {
      attachPreview("b_expr"); attachPreview("b_zhuyuan"); attachPreview("b_huanyuan"); attachPreview("b_huayuanshi");
      $("btnCalc").onclick = () => {
        const d = {
          expr: $("b_expr").value, method: $("b_method").value,
          zhuyuan: $("b_zhuyuan").value, huanyuan: $("b_huanyuan").value,
          huayuanshi: $("b_huayuanshi").value,
        };
        apiPost("/api/simplify", d).then((r) => showResult("b_res", r));
      };
    },
  },

  // -------- 方程 --------
  {
    id: "fangcheng", zh: "方程", en: "Equation", icon: "=", group: "calc",
    html() {
      return (
        pageHead(t("方程")) +
        card("", '<div class="row">' +
          formulaField("e_lhs", t("左边"), "x**2-1", { value: "x**2-1", main: true }) +
          formulaField("e_rhs", t("右边"), "0", { value: "0" }) +
          textField("e_var", t("var"), "x", "x") +
          selectField("e_domain", t("domain"), [{ v: "Reals", t: "Reals" }, { v: "Complexes", t: "Complexes" }], "Reals") +
          checkboxField("e_de", t("微分方程"), false) +
          "</div>" +
          exampleChips("e_lhs", ["x**2-1", "x**2-4", "sin(x)-1"]) +
          '<p class="field-hint">' + t("eqFieldHint") + "</p>" +
          '<div style=margin-top:12px>' + computeBtn() + "</div>" +
          '<div class="result" id="e_res"></div>'
        ) +
        funcInputHint()
      );
    },
    init() {
      attachPreview("e_lhs"); attachPreview("e_rhs");
      $("btnCalc").onclick = () => {
        const d = {
          lhs: $("e_lhs").value, rhs: $("e_rhs").value,
          var: $("e_var").value || "x", domain: $("e_domain").value,
          de: $("e_de").checked,
        };
        apiPost("/api/equation", d).then((r) => showResult("e_res", r));
      };
    },
  },

  // -------- 方程组 --------
  {
    id: "fangchengzu", zh: "方程组", en: "Equations", icon: "≡", group: "calc",
    html() {
      return (
        '<div class="page-head"><h1>' + t("方程组") + "</h1></div>" +
        card(t("方程列表"), '<div id="sysEqs"></div><button class="ghost" onclick="addSysEq()">+ ' + t("add") + "</button>") +
        card("", '<div class="row">' +
          textField("sys_vars", t("主元(逗号分隔)"), "x,y") +
          "</div><div style=margin-top:12px>" + computeBtn() + "</div>" +
          '<div class="result" id="sys_res"></div>'
        )
      );
    },
    init() {
      loadSysEqs();
      $("btnCalc").onclick = () => {
        const eqs = [];
        document.querySelectorAll("#sysEqs .eq-row").forEach((row) => {
          eqs.push([row.querySelector(".lhs").value, row.querySelector(".rhs").value]);
        });
        const vars = $("sys_vars").value.split(",").map((s) => s.trim()).filter(Boolean);
        apiPost("/api/system", { eqs, vars }).then((r) => showResult("sys_res", r));
      };
    },
  },

  // -------- 不等式 --------
  {
    id: "budengshi", zh: "不等式", en: "Inequality", icon: "≠", group: "calc",
    html() {
      const ops = INEQ_OPS.map((o) => ({ v: o, t: o }));
      return (
        pageHead(t("不等式")) +
        card("", '<div class="row">' +
          formulaField("n_lhs", t("左边"), "x**2-1", { value: "x**2-1", main: true }) +
          selectField("n_op", t("关系"), ops, "≥") +
          formulaField("n_rhs", t("右边"), "0", { value: "0" }) +
          textField("n_var", t("var"), "x") +
          selectField("n_domain", t("domain"), [{ v: "Reals", t: "Reals" }, { v: "Complexes", t: "Complexes" }], "Reals") +
          "</div>" +
          exampleChips("n_lhs", ["x**2-1", "x**2-4", "sin(x)"]) +
          '<div style=margin-top:12px>' + computeBtn() + "</div>" +
          '<div class="result" id="n_res"></div>'
        ) +
        funcInputHint()
      );
    },
    init() {
      attachPreview("n_lhs"); attachPreview("n_rhs");
      $("btnCalc").onclick = () => {
        const d = {
          lhs: $("n_lhs").value, rhs: $("n_rhs").value,
          op: $("n_op").value, var: $("n_var").value || "x", domain: $("n_domain").value,
        };
        apiPost("/api/inequality", d).then((r) => showResult("n_res", r));
      };
    },
  },

  // -------- 不等式组 --------
  {
    id: "budengshizu", zh: "不等式组", en: "Inequalities", icon: "⋚", group: "calc",
    html() {
      let rels = "";
      STATE.rels.forEach((k) => {
        rels += '<div class="list-row"><span>' + k + "</span>" +
          '<div class="actions"><button class="ghost danger" data-kind="rel" data-name="' + encodeURIComponent(k) + '" onclick="delFromData(this)">' + t("delete") + "</button></div></div>";
      });
      if (!STATE.rels.length) rels = '<p class="hint">' + t("noData") + "</p>";
      return (
        pageHead(t("不等式组")) +
        card(t("添加不等式"), '<div class="row">' +
          formulaField("nz_lhs", t("左边"), "x", { value: "x", main: true }) +
          selectField("nz_op", t("关系"), INEQ_OPS.map((o) => ({ v: o, t: o })), "≥") +
          formulaField("nz_rhs", t("右边"), "0", { value: "0" }) +
          "</div><div style=margin-top:12px><button class=\"primary\" onclick=\"saveRel()\">" + t("save") + "</button></div>"
        ) +
        card(t("已添加不等式"), '<div id="relList">' + rels + "</div>") +
        card(t("求解"), '<div class="row">' + textField("nz_var", t("var"), "x") + "</div>" +
          '<div style=margin-top:12px>' + computeBtn(t("求解不等式组")) + "</div>" +
          '<div class="result" id="nz_res"></div>'
        )
      );
    },
    init() {
      attachPreview("nz_lhs"); attachPreview("nz_rhs");
      $("btnCalc").onclick = () => {
        apiPost("/api/inequality_system", { var: $("nz_var").value || "x" })
          .then((r) => showResult("nz_res", r));
      };
    },
  },

  // -------- 函数计算 --------
  {
    id: "jisuan", zh: "函数计算", en: "Calculate", icon: "∑", group: "calc",
    html() {
      const eng = CALC_ENGINES.map((x, i) => ({ v: i, t: x }));
      return (
        pageHead(t("函数计算")) +
        card("", '<div class="row">' +
          formulaField("c_expr", t("expr"), "sqrt(2)+pi", { value: "sqrt(2)+pi", main: true }) +
          selectField("c_engine", t("options"), eng) +
          numField("c_prec", t("精度(小数位)"), "16", "16") +
          "</div>" +
          exampleChips("c_expr", ["sqrt(2)+pi", "2**10", "log(8,2)", "$\\frac{1}{3}"]) +
          '<div style=margin-top:12px>' + computeBtn() + "</div>" +
          '<div class="result" id="c_res"></div>'
        ) +
        funcInputHint()
      );
    },
    init() {
      attachPreview("c_expr");
      $("c_engine").addEventListener("change", () => {
        $("c_prec").parentElement.style.display = $("c_engine").value === "1" ? "" : "none";
      });
      $("c_prec").parentElement.style.display = "none";
      $("btnCalc").onclick = () => {
        const d = {
          expr: $("c_expr").value, engine: $("c_engine").value,
          precision: $("c_prec").value || "16",
        };
        apiPost("/api/calculate", d).then((r) => showResult("c_res", r));
      };
    },
  },

  // -------- 解三角形 --------
  {
    id: "jiesanjiaoxing", zh: "解三角形", en: "Triangle", icon: "△", group: "calc",
    html() {
      const defVals = ["30", "60", "5"];
      let rows = "";
      for (let i = 0; i < 3; i++) {
        rows +=
          '<div class="row" style="margin-bottom:10px">' +
          selectField("t_type" + i, t("已知项"), TRIANGLE_CONDS.map((x, j) => ({ v: j + 1, t: x }))) +
          formulaField("t_val" + i, t("expr"), "30", { cache: false, value: defVals[i] }) +
          "</div>";
      }
      return (
        pageHead(t("解三角形")) +
        card("", rows + '<div style=margin-top:12px>' + computeBtn() + "</div>" +
          '<div class="result" id="t_res"></div>'
        )
      );
    },
    init() {
      for (let i = 0; i < 3; i++) attachPreview("t_val" + i);
      $("btnCalc").onclick = () => {
        const conds = [];
        for (let i = 0; i < 3; i++) {
          conds.push({ type: $("t_type" + i).value, value: $("t_val" + i).value });
        }
        apiPost("/api/triangle", { conds }).then((r) => showResult("t_res", r));
      };
    },
  },

  // -------- 向量 --------
  {
    id: "dingyixiangliang", zh: "向量", en: "Vector", icon: "➙", group: "calc",
    html() {
      let vs = "";
      STATE.vs.forEach((n) => {
        vs += '<div class="list-row"><span>' + n + "</span>" +
          '<div class="actions"><button class="ghost danger" data-kind="vector" data-name="' + n + '" onclick="delFromData(this)">' + t("delete") + "</button></div></div>";
      });
      if (!STATE.vs.length) vs = '<p class="hint">' + t("noData") + "</p>";
      const ops = VEC_OPS;
      return (
        pageHead(t("向量")) +
        card(t("定义向量"), '<div class="row">' +
          textField("v_name", t("name"), "a", "a") +
          formulaField("v_x", t("x 分量"), "1", { value: "1" }) +
          formulaField("v_y", t("y 分量"), "2", { value: "2" }) +
          "</div><div style=margin-top:12px><button class=\"primary\" onclick=\"saveVec()\">" + t("save") + "</button></div>"
        ) +
        card(t("savedVecs"), '<div id="vsList">' + vs + "</div>") +
        card(t("向量运算"), '<div class="row">' +
          selectField("v_op", t("options"), ops) +
          selectField("v_v1", t("向量1"), STATE.vs.map((n) => ({ v: n, t: n })), "") +
          selectField("v_v2", t("向量2"), STATE.vs.map((n) => ({ v: n, t: n })), "") +
          formulaField("v_scalar", t("数乘系数"), "2", { cache: false }) +
          "</div><div style=margin-top:12px>" + computeBtn() + "</div>" +
          '<div class="result" id="v_res"></div>'
        ) +
        card(t("向量属性"), '<div class="row">' +
          selectField("va_name", t("name"), STATE.vs.map((n) => ({ v: n, t: n })), "") +
          selectField("va_attr", t("options"), VEC_ATTRS.map((x, i) => ({ v: i, t: x }))) +
          "</div><div style=margin-top:12px><button class=\"primary\" id=\"btnAttr\">" + t("查询") + "</button></div>" +
          '<div class="result" id="va_res"></div>'
        )
      );
    },
    init() {
      attachPreview("v_x"); attachPreview("v_y"); attachPreview("v_scalar");
      $("btnCalc").onclick = () => {
        const op = $("v_op").value;
        const d = { op, v1: $("v_v1").value, v2: $("v_v2").value, scalar: $("v_scalar").value };
        apiPost("/api/vector_compute", d).then((r) => showResult("v_res", r));
      };
      $("btnAttr").onclick = () => {
        apiPost("/api/vector_attr", { name: $("va_name").value, attr: $("va_attr").value })
          .then((r) => showResult("va_res", r));
      };
    },
  },

  // -------- 函数绘图 --------
  {
    id: "huitu_hanshu", zh: "函数绘图", en: "Plot", icon: "📈", group: "geo",
    html() {
      return (
        pageHead(t("函数绘图")) +
        card(t("函数列表"), '<div id="plotItems"></div><button class="ghost" onclick="addPlotItem()">+ ' + t("add") + "</button>") +
        card(t("options"), '<div class="row">' +
          checkboxField("p_axis", t("显示坐标轴"), true) +
          checkboxField("p_grid", t("显示网格"), true) +
          formulaField("p_xlim", t("x 范围(可空,逗号)"), "-10,10", { cache: false, value: "-10,10" }) +
          formulaField("p_ylim", t("y 范围(可空,逗号)"), "", { cache: false }) +
          "</div><div style=margin-top:12px>" + computeBtn(t("绘图")) + "</div>" +
          '<div id="p_img"></div>'
        )
      );
    },
    init() {
      addPlotItem();
      attachPreview("p_xlim"); attachPreview("p_ylim");
      $("btnCalc").onclick = () => {
        const items = [];
        document.querySelectorAll("#plotItems .plot-row").forEach((row) => {
          items.push({
            expr: row.querySelector(".pe").value, var: row.querySelector(".pv").value || "x",
            a: row.querySelector(".pa").value, b: row.querySelector(".pb").value,
            color: row.querySelector(".pc").value,
          });
        });
        const xlim = $("p_xlim").value ? $("p_xlim").value.split(",").map((s) => s.trim()) : null;
        const ylim = $("p_ylim").value ? $("p_ylim").value.split(",").map((s) => s.trim()) : null;
        apiPost("/api/plot/func", {
          items, opts: { show_axis: $("p_axis").checked, show_grid: $("p_grid").checked, xlim, ylim },
        }).then((r) => { if (r.ok) showImage("p_img", r.image); else showResult("p_img", r); });
      };
    },
  },

  // -------- 平面几何定义 --------
  {
    id: "dingyi_pj", zh: "平面几何定义", en: "Define 2D", icon: "▱", group: "geo",
    html() {
      let objs = "";
      Object.keys(STATE.pjs).forEach((n) => {
        objs += '<div class="list-row"><span>' + STATE.pjs[n] + " " + n + "</span>" +
          '<div class="actions"><button class="ghost danger" data-kind="pjs" data-name="' + n + '" onclick="delFromData(this)">' + t("delete") + "</button></div></div>";
      });
      if (!Object.keys(STATE.pjs).length) objs = '<p class="hint">' + t("noData") + "</p>";
      const m = PLANE_DEF_METHODS.map((x, i) => ({ v: i + 1, t: x }));
      return (
        pageHead(t("平面几何定义")) +
        card(t("定义对象"), '<div class="row">' +
          textField("pj_name", t("name"), "A", "A") +
          selectField("pj_method", t("options"), m) +
          textField("pj_params", t("params"), "0,0") +
          "</div><p class='hint'>" + t("paramsHint") + "</p>" +
          '<div style=margin-top:12px><button class="primary" onclick="savePjs()">' + t("save") + "</button></div>"
        ) +
        card(t("savedObjs"), '<div id="pjsList">' + objs + "</div>")
      );
    },
  },

  // -------- 平面几何计算 --------
  {
    id: "pjjisuan", zh: "平面几何计算", en: "Compute 2D", icon: "◿", group: "geo",
    html() {
      const m = PLANE_CALC_METHODS.map((x, i) => ({ v: i + 1, t: x }));
      return (
        pageHead(t("平面几何计算")) +
        card("", '<div class="row">' +
          selectField("pj_calc_method", t("options"), m) +
          textField("pj_calc_params", t("params"), "A,B") +
          "</div><p class='hint'>" + t("paramsHint") + "</p>" +
          '<div style=margin-top:12px>' + computeBtn() + "</div>" +
          '<div class="result" id="pjc_res"></div>'
        )
      );
    },
    init() {
      $("btnCalc").onclick = () => {
        apiPost("/api/geometry", {
          kind: "plane", method: $("pj_calc_method").value, params: $("pj_calc_params").value,
        }).then((r) => showResult("pjc_res", r));
      };
    },
  },

  // -------- 立体几何定义 --------
  {
    id: "dingyi_lj", zh: "立体几何定义", en: "Define 3D", icon: "◳", group: "geo",
    html() {
      let objs = "";
      Object.keys(STATE.ljs).forEach((n) => {
        objs += '<div class="list-row"><span>' + STATE.ljs[n] + " " + n + "</span>" +
          '<div class="actions"><button class="ghost danger" data-kind="ljs" data-name="' + n + '" onclick="delFromData(this)">' + t("delete") + "</button></div></div>";
      });
      if (!Object.keys(STATE.ljs).length) objs = '<p class="hint">' + t("noData") + "</p>";
      const m = SOLID_DEF_METHODS.map((x, i) => ({ v: i + 1, t: x }));
      return (
        pageHead(t("立体几何定义")) +
        card(t("定义对象"), '<div class="row">' +
          textField("lj_name", t("name"), "A", "A") +
          selectField("lj_method", t("options"), m) +
          textField("lj_params", t("params"), "0,0,0") +
          "</div><p class='hint'>" + t("paramsHint") + "</p>" +
          '<div style=margin-top:12px><button class="primary" onclick="saveLjs()">' + t("save") + "</button></div>"
        ) +
        card(t("savedObjs"), '<div id="ljsList">' + objs + "</div>")
      );
    },
  },

  // -------- 立体几何计算 --------
  {
    id: "ljjisuan", zh: "立体几何计算", en: "Compute 3D", icon: "❒", group: "geo",
    html() {
      const m = SOLID_CALC_METHODS.map((x, i) => ({ v: i + 1, t: x }));
      return (
        pageHead(t("立体几何计算")) +
        card("", '<div class="row">' +
          selectField("lj_calc_method", t("options"), m) +
          textField("lj_calc_params", t("params"), "A,B") +
          "</div><p class='hint'>" + t("paramsHint") + "</p>" +
          '<div style=margin-top:12px>' + computeBtn() + "</div>" +
          '<div class="result" id="ljc_res"></div>'
        )
      );
    },
    init() {
      $("btnCalc").onclick = () => {
        apiPost("/api/geometry", {
          kind: "solid", method: $("lj_calc_method").value, params: $("lj_calc_params").value,
        }).then((r) => showResult("ljc_res", r));
      };
    },
  },

  // -------- 平面几何绘图 --------
  {
    id: "huitu_pingmianjihe", zh: "平面几何绘图", en: "Plot 2D", icon: "✏", group: "geo",
    html() {
      let boxes = "";
      Object.keys(STATE.pjs).forEach((n) => {
        boxes += '<label><input type="checkbox" value="' + n + '" checked> ' + STATE.pjs[n] + " " + n + "</label>";
      });
      if (!Object.keys(STATE.pjs).length) boxes = '<p class="hint">' + t("noData") + "</p>";
      return (
        pageHead(t("平面几何绘图")) +
        card(t("selectObjects"), '<div class="checkbox-list" id="pj_boxes">' + boxes + "</div>") +
        '<div style=margin-top:12px>' + computeBtn(t("绘图")) + "</div>" +
        '<div id="pj_img"></div>'
      );
    },
    init() {
      $("btnCalc").onclick = () => {
        const names = Array.from(document.querySelectorAll("#pj_boxes input:checked")).map((c) => c.value);
        apiPost("/api/plot/pjs", { names, theme: THEME }).then((r) => {
          if (r.ok) showImage("pj_img", r.image); else showResult("pj_img", r);
        });
      };
    },
  },

  // -------- 立体几何绘图 --------
  {
    id: "huitu_litijihe", zh: "立体几何绘图", en: "Plot 3D", icon: "🧊", group: "geo",
    html() {
      let boxes = "";
      Object.keys(STATE.ljs).forEach((n) => {
        boxes += '<label><input type="checkbox" value="' + n + '" checked> ' + STATE.ljs[n] + " " + n + "</label>";
      });
      if (!Object.keys(STATE.ljs).length) boxes = '<p class="hint">' + t("noData") + "</p>";
      return (
        pageHead(t("立体几何绘图")) +
        card(t("selectObjects"), '<div class="checkbox-list" id="lj_boxes">' + boxes + "</div>") +
        '<div style=margin-top:12px>' + computeBtn(t("绘图")) + "</div>" +
        '<div id="lj_img"></div>'
      );
    },
    init() {
      $("btnCalc").onclick = () => {
        const names = Array.from(document.querySelectorAll("#lj_boxes input:checked")).map((c) => c.value);
        apiPost("/api/plot/ljs", { names, theme: THEME }).then((r) => {
          if (r.ok) showImage("lj_img", r.image); else showResult("lj_img", r);
        });
      };
    },
  },

  // -------- 缓存区 --------
  {
    id: "huancun", zh: "缓存区", en: "Cache", icon: "🗄", group: "misc",
    html() {
      let rows = "";
      STATE.cache.forEach((c, idx) => {
        rows += '<div class="list-row"><div class="preview">$' + (c[0] || c[1]) + "$</div>" +
          '<div class="actions">' +
          '<button class="ghost" onclick="copyCache(' + idx + ')">' + t("copy") + "</button>" +
          '<button class="ghost" onclick="insertCache(' + idx + ')">' + t("insert") + "</button>" +
          "</div></div>";
      });
      if (!STATE.cache.length) rows = '<p class="hint">' + t("noData") + "</p>";
      return (
        '<div class="page-head"><h1>' + t("缓存区") + "</h1><p>" +
        t("cacheDesc") + "</p></div>" +
        card("", '<div id="cacheList">' + rows + "</div>" +
          '<div style=margin-top:12px><button class="ghost danger" onclick="clearCache()">' + t("clearCache") + "</button></div>")
      );
    },
    init() {
      const list = $("#cacheList");
      if (list) typeset(list);
    },
  },

  // -------- 设置 --------
  {
    id: "shezhi", zh: "设置", en: "Settings", icon: "⚙", group: "misc",
    html() {
      return (
        '<div class="page-head"><h1>' + t("设置") + "</h1></div>" +
        card(t("uiGroup"), '<div class="row">' +
          selectField("s_theme", t("theme"), [{ v: "light", t: t("light") }, { v: "dark", t: t("dark") }], THEME) +
          selectField("s_lang", t("language"), [{ v: "zh", t: "中文" }, { v: "en", t: "English" }], LANG) +
          "</div><p class='hint'>" + t("webVersion") + "</p>") +
        card(t("存档 / 加载（.cca / JSON）"), '<div class="row">' +
          '<button class="primary" onclick="saveArchive()">' + t("exportArchive") + "</button> " +
          '<button class="ghost" onclick="$(\'loadFile\').click()">' + t("importArchive") + "</button>" +
          '<input type="file" id="loadFile" accept=".json,.cca,application/json" style="display:none" onchange="loadArchive(this)">' +
          "</div><p class='hint'>" + t("archiveHint") + "</p>") +
        card(t("相关链接"), '<div class="home-links" style="justify-content:flex-start">' +
          '<a href="https://github.com/limingkang12345/CalculusCalculator" target="_blank" rel="noopener">GitHub</a>' +
          '<a href="https://limingkang12345.github.io/CalculusCalculator/" target="_blank" rel="noopener">' + t("onlineDocs") + "</a>" +
          '<a href="https://pypi.org/project/CalculusCalculator/" target="_blank" rel="noopener">PyPI</a>' +
          "</div>")
      );
    },
    init() {
      $("s_theme").onchange = () => { THEME = $("s_theme").value; applyTheme(); localStorage.setItem("theme", THEME); syncBlocklyTheme(); };
      $("s_lang").onchange = () => { LANG = $("s_lang").value; localStorage.setItem("lang", LANG); renderNav(); loadTab(currentTab); localizeKB(); syncBlocklyLang(); };
    },
  },

  // -------- 帮助 --------
  {
    id: "help", zh: "帮助", en: "Help", icon: "?", group: "misc",
    html() {
      return (
        '<div class="page-head"><h1>' + t("help") + "</h1></div>" +
        card(t("输入说明"), "<ul>" +
          "<li>" + t("helpLi1") + "</li>" +
          "<li>" + t("helpLi2") + "</li>" +
          "<li>" + t("helpLi3") + "</li>" +
          "<li>" + t("helpLi4") + "</li>" +
          "<li>" + t("helpLi5") + "</li>" +
          "<li>" + t("helpLi6") + "</li></ul>") +
        card(t("数据"), "<p>" + t("dataDesc") + "</p>") +
        card(t("相关链接"), '<div class="home-links" style="justify-content:flex-start">' +
          '<a href="https://github.com/limingkang12345/CalculusCalculator" target="_blank" rel="noopener">GitHub</a>' +
          '<a href="https://limingkang12345.github.io/CalculusCalculator/" target="_blank" rel="noopener">' + t("onlineDocs") + "</a>" +
          '<a href="https://pypi.org/project/CalculusCalculator/" target="_blank" rel="noopener">PyPI</a>' +
          "</div>")
      );
    },
  },
];

// ============================ 全局动作 ============================
function blk(s) {
  const e = $("blkExpr");
  if (!e) return;
  e.value += s; e.dispatchEvent(new Event("input")); e.focus();
}
function blkData(btn) { blk(btn.getAttribute("data-ch")); }
function blkClear() {
  const e = $("blkExpr");
  if (!e) return;
  e.value = ""; e.dispatchEvent(new Event("input"));
}
function blkCalc() {
  const e = $("blkExpr");
  if (!e) return;
  const expr = e.value.trim();
  if (!expr) return;
  const op = $("blkOp").value;
  let p;
  if (op === "diff") p = apiPost("/api/derivative", { expr, var: "x", order: "1" });
  else if (op === "integ") p = apiPost("/api/integral", { expr, var: "x" });
  else if (op === "simplify") p = apiPost("/api/simplify", { expr, method: "0" });
  else if (op === "factor") p = apiPost("/api/simplify", { expr, method: "2" });
  else if (op === "solve") p = apiPost("/api/equation", { lhs: expr, rhs: "0", var: "x", domain: "Reals" });
  else p = apiPost("/api/calculate", { expr, engine: "2" });
  p.then((r) => showResult("blkRes", r));
}

function saveFunc() {
  const d = { name: $("f_name").value, expr: $("f_expr").value, domain: $("f_domain").value, var: $("f_var").value };
  apiPost("/api/func", d).then((r) => {
    toast(r.ok ? t("success") : r.error);
    if (r.ok) refreshState().then(refreshFuncList);  // 仅刷新函数列表，保留定义函数输入框内容
  });
}
function saveVec() {
  const d = { name: $("v_name").value, x: $("v_x").value, y: $("v_y").value };
  apiPost("/api/vector", d).then((r) => { toast(r.ok ? t("success") : r.error); if (r.ok) refreshState().then(() => loadTab("dingyixiangliang")); });
}
function saveRel() {
  const d = { lhs: $("nz_lhs").value, rhs: $("nz_rhs").value, op: $("nz_op").value };
  apiPost("/api/rel", d).then((r) => { toast(r.ok ? t("success") : r.error); if (r.ok) refreshState().then(() => loadTab("budengshizu")); });
}
function savePjs() {
  const d = { name: $("pj_name").value, method: $("pj_method").value, params: $("pj_params").value };
  apiPost("/api/pjs", d).then((r) => { toast(r.ok ? t("success") : r.error); if (r.ok) refreshState().then(() => loadTab("dingyi_pj")); });
}
function saveLjs() {
  const d = { name: $("lj_name").value, method: $("lj_method").value, params: $("lj_params").value };
  apiPost("/api/ljs", d).then((r) => { toast(r.ok ? t("success") : r.error); if (r.ok) refreshState().then(() => loadTab("dingyi_lj")); });
}
function delItem(kind, name) {
  name = decodeURIComponent(name);
  let path = "";
  if (kind === "func") path = "/api/func/";
  else if (kind === "vector") path = "/api/vector/";
  else if (kind === "rel") path = "/api/rel/";
  else if (kind === "pjs") path = "/api/pjs/";
  else if (kind === "ljs") path = "/api/ljs/";
  path += encodeURIComponent(name);
  fetch(path, { method: "DELETE" }).then((r) => r.json()).then((r) => {
    toast(r.ok ? t("success") : r.error);
    if (!r.ok) return;
    refreshState().then(() => {
      // 删除函数且当前在函数定义页时，仅刷新列表，避免覆盖定义函数输入框
      if (kind === "func" && currentTab === "dingyi") refreshFuncList();
      else loadTab(currentTab);
    });
  });
}
function addCacheFromInput(id) {
  const v = ($(id) && $(id).value) || "";
  if (!v) return;
  apiPost("/api/cache", { latex: v, text: v }).then((r) => { toast(r.ok ? t("addCache") : r.error); if (r.ok) refreshState(); });
}
function addCacheData(btn) { addCacheFromInput(btn.getAttribute("data-target")); }
function delFromData(btn) { delItem(btn.getAttribute("data-kind"), btn.getAttribute("data-name")); }
function copyCache(idx) {
  const txt = STATE.cache[idx] ? (STATE.cache[idx][0] || STATE.cache[idx][1]) : "";
  navigator.clipboard && navigator.clipboard.writeText(txt.replace(/\$/g, ""));
  toast(t("copied"));
}
function insertCache(idx) {
  const txt = STATE.cache[idx] ? (STATE.cache[idx][0] || STATE.cache[idx][1]).replace(/\$/g, "") : "";
  if (lastFocusedInput && $(lastFocusedInput)) {
    $(lastFocusedInput).value = txt;
    $(lastFocusedInput).dispatchEvent(new Event("input"));
    toast(t("insert"));
  } else toast(t("error"));
}
function clearCache() {
  fetch("/api/cache", { method: "DELETE" }).then((r) => r.json()).then(() => { refreshState().then(() => loadTab("huancun")); });
}
function saveArchive() {
  fetch("/api/save").then((r) => {
    const blobUrl = URL.createObjectURL(r.blob());
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = "calc_save.cca";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(blobUrl);
    toast(t("success"));
  }).catch(() => toast(t("error")));
}
function loadArchive(input) {
  const file = input.files && input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const data = JSON.parse(reader.result);
      apiPost("/api/load", data).then((r) => {
        toast(r.ok ? t("success") : r.error);
        if (r.ok) refreshState();
      });
    } catch (e) { toast(t("error") + ": " + e.message); }
  };
  reader.readAsText(file);
  input.value = "";
}

function addSysEq() {
  const div = document.createElement("div");
  div.className = "eq-row row";
  div.style.marginBottom = "8px";
  div.innerHTML =
    '<input type="text" class="lhs" value="x+y" placeholder="x+y" style="flex:1">' +
    '<span>=</span>' +
    '<input type="text" class="rhs" value="3" placeholder="3" style="flex:1">' +
    '<button class="ghost danger" onclick="this.parentNode.remove()">' + t("remove") + "</button>";
  $("sysEqs").appendChild(div);
}
function loadSysEqs() {
  $("sysEqs").innerHTML = "";
  addSysEq();
}
function addPlotItem() {
  const div = document.createElement("div");
  div.className = "plot-row row";
  div.style.marginBottom = "8px";
  div.innerHTML =
    '<input type="text" class="pe" value="x**2" placeholder="x**2" style="flex:2">' +
    '<input type="text" class="pv" value="x" placeholder="x" style="flex:1">' +
    '<input type="text" class="pa" value="-10" placeholder="' + t("下限") + '" style="flex:1">' +
    '<input type="text" class="pb" value="10" placeholder="' + t("上限") + '" style="flex:1">' +
    '<input type="text" class="pc" value="" placeholder="#' + t("color") + '" style="flex:1">' +
    '<button class="ghost danger" onclick="this.parentNode.remove()">' + t("remove") + "</button>";
  $("plotItems").appendChild(div);
}

// ============================ 回车快捷键（桌面版同款特性） ============================
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter") return;
  const tag = (e.target && e.target.tagName) || "";
  if (tag !== "INPUT" && tag !== "TEXTAREA") return;
  const btn = document.querySelector("#content button.primary");
  if (btn && typeof btn.onclick === "function") {
    e.preventDefault();
    btn.onclick.call(btn, e);
  }
});

// ============================ 导航与渲染 ============================
function navItemHtml(tab) {
  const title = LANG === "en" ? tab.en : tab.zh;
  return '<div class="nav-item' + (tab.id === currentTab ? " active" : "") +
    '" data-id="' + tab.id + '"><span class="ico">' + tab.icon + '</span><span class="label">' + title + "</span></div>";
}
function renderNav() {
  const nav = $("nav");
  if (!nav) return;
  const groups = { calc: t("grpCalc"), geo: t("grpGeo"), misc: t("grpMisc") };
  let html = "";
  // 积木编辑器置顶
  const blk = TABS.find((x) => x.id === "blockly");
  if (blk) {
    html += '<div class="nav-group-title">★</div>' + navItemHtml(blk);
  }
  Object.keys(groups).forEach((g) => {
    html += '<div class="nav-group-title">' + groups[g] + "</div>";
    TABS.filter((t) => t.group === g).forEach((tab) => { html += navItemHtml(tab); });
  });
  nav.innerHTML = html;
  nav.querySelectorAll(".nav-item").forEach((it) => {
    it.onclick = () => {
      loadTab(it.getAttribute("data-id"));
      document.body.classList.remove("sidebar-open");
    };
  });
  document.querySelectorAll("[data-i18n]").forEach((e) => { e.textContent = t(e.getAttribute("data-i18n")); });
}

function goTab(id) { loadTab(id); }
function loadTab(id) {
  const tab = TABS.find((t) => t.id === id);
  if (!tab) return;
  currentTab = id;
  hidePreviewPop();
  closeMathKB();
  renderNav();
  const c = $("content");
  if (!c) return;
  c.innerHTML = tab.html();
  if (tab.init) tab.init();
  typeset(c);
  c.scrollTop = 0;
}

function applyTheme() {
  document.body.classList.toggle("dark", THEME === "dark");
  const btn = $("themeBtn");
  if (btn) btn.textContent = THEME === "dark" ? "☀" : "🌙";
}

// ============================ 启动 ============================
function boot() {
  applyTheme();
  $("themeBtn").onclick = () => {
    THEME = THEME === "dark" ? "light" : "dark";
    applyTheme(); localStorage.setItem("theme", THEME);
    syncBlocklyTheme();
  };
  $("langBtn").onclick = () => {
    LANG = LANG === "en" ? "zh" : "en";
    localStorage.setItem("lang", LANG);
    $("langBtn").textContent = LANG === "en" ? "中文" : "EN";
    renderNav(); loadTab(currentTab); localizeKB();
    syncBlocklyLang();
  };
  $("langBtn").textContent = LANG === "en" ? "中文" : "EN";
  $("menuBtn").onclick = () => document.body.classList.toggle("sidebar-open");
  $("mathkbClear").onclick = clearMathKB;
  $("mathkbInsert").onclick = insertMath;
  $("mathkbClose").onclick = closeMathKB;
  // 紧贴 MathLive 虚拟键盘的"收起"按钮：仅在键盘可见时显示，并定位到键盘顶部上方
  const kbCollapseBtn = $("#kbCollapse");
  function positionKbCollapse() {
    if (!kbCollapseBtn) return;
    const k = document.querySelector(".ML__keyboard");
    if (!k || !k.classList.contains("is-visible")) { kbCollapseBtn.hidden = true; return; }
    kbCollapseBtn.hidden = false;
    const top = k.getBoundingClientRect().top;
    kbCollapseBtn.style.bottom = (window.innerHeight - top + 8) + "px";
  }
  if (kbCollapseBtn) {
    kbCollapseBtn.onclick = () => closeMathKB();
    const mo = new MutationObserver(positionKbCollapse);
    const startObs = () => {
      const k = document.querySelector(".ML__keyboard");
      if (k) { mo.observe(k, { attributes: true, attributeFilter: ["class"] }); positionKbCollapse(); }
      else setTimeout(startObs, 400);
    };
    startObs();
    window.addEventListener("resize", positionKbCollapse);
  }
  // MathLive 实时显示 LaTeX
  const mf = $("#mf");
  if (mf) {
    mf.addEventListener("input", () => {
      const out = $("#mathkbLatex");
      if (out) out.textContent = mf.value || t("empty");
    });
  }
  localizeKB();
  refreshState().then(() => loadTab("home"));
}

document.addEventListener("DOMContentLoaded", boot);
