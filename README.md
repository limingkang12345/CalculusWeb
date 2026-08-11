# 微积分计算器 · Flask Web 版

将 `src/` 目录下的桌面应用（PySide6）**完整重写**为 Flask 网页应用，计算内核直接复用原项目的纯 Python/SymPy 模块，数学行为与桌面版 1:1 一致，并支持部署到 **PythonAnywhere**。

## 功能总览（与桌面版对应）

| 功能 | 页面 | 对应桌面 UI |
|------|------|-------------|
| 函数定义（含 f(3) 调用 / 嵌套调用） | 函数定义 | `dingyi` |
| 求导（显函数 / 隐函数 / 代入求值） | 求导 | `qiudao` |
| 积分（定积分 / 不定积分） | 积分 | `jifen` |
| 表达式变形（13 种方法） | 函数变形 | `bianxing` |
| 方程 / 微分方程求解 | 方程 | `fangcheng` |
| 方程组求解 | 方程组 | `fangchengzu` |
| 不等式求解 | 不等式 | `budengshi` |
| 不等式组求解 | 不等式组 | `budengshizu` |
| 符号计算（四引擎） | 函数计算 | `jisuan` |
| 函数性质分析（值域/单调/奇偶/周期/最值） | 函数定义 → 函数属性 | `dingyi` |
| 解三角形（ASA/AAS/SAS/SSA/SSS） | 解三角形 | `jiesanjiaoxing` |
| 向量定义与运算（加/减/数乘/点积/叉积/夹角/投影/单位向量） | 向量 | `dingyixiangliang` |
| 函数绘图（多函数、定义域、网格） | 函数绘图 | `huitu_hanshu` |
| 平面几何定义（19 种构造） | 平面几何定义 | `dingyi_pj` |
| 平面几何计算（32 种运算） | 平面几何计算 | `pjjisuan` |
| 平面几何绘图 | 平面几何绘图 | `huitu_pj` |
| 立体几何定义（12 种构造） | 立体几何定义 | `dingyi_lj` |
| 立体几何计算（22 种运算，含斜二测） | 立体几何计算 | `ljjisuan` |
| 立体几何绘图（3D） | 立体几何绘图 | `huitu_lj` |
| 积木化表达式构建（计算/求导/积分/化简/解方程） | 积木编辑器 | `blockly` |
| 表达式缓存区 | 缓存区 | `huancun` |
| 工程存档 / 读档（JSON 下载/上传） | 存档 / 加载 | `saves` |
| 主题（浅色/深色）、语言（中/英） | 设置 | `shezhi` |
| 帮助 | 帮助 | `help` |

> 其余桌面版特性：LaTeX 直接输入（表达式前加 `$`）、分母自动有理化（`radsimp`）、回车快捷键触发计算、表达式实时预览（MathJax），均已复现。

### 界面与交互（Web 版增强）

- **现代化界面**：渐变主题、圆角卡片、动态阴影、悬停/点击反馈，支持浅色/深色主题切换。
- **MathLive 公式键盘**：复用桌面版 `src/math_input/mathlive` 库（本地化、离线可用）。点击任意输入框旁的 **ƒ** 按钮，页面底部弹出 MathLive 虚拟键盘（`virtual-keyboard-mode="always"`，与桌面版一致）；点“插入”后由后端 `/api/latex2expr` 将 LaTeX 解析为**原生 SymPy 表达式**填入输入框。
- **公式浮层预览**：点击输入框时其上方实时浮现公式预览框（MathJax 渲染），随输入实时更新。
- **输入行内按钮**：每个表达式输入框旁均有 **ƒ（公式键盘）** 与 **加入缓存** 按钮，缓存区可复制 / 插入回任意输入框。
- **积木编辑器置顶**：侧边栏第一位（★），支持计算 / 求导 / 积分 / 化简 / 解方程 / 因式分解。
- **外部链接**：侧边栏、顶栏、首页、设置、帮助均提供 GitHub / 在线文档 / PyPI 链接。
- **手机端竖屏适配**：侧边栏收起为抽屉（☰ 展开）、输入框全宽、公式键盘与预览浮层自适应、触控友好。

## 目录结构

```
CalculusWeb/
├── app.py              # 本地运行入口（python app.py）
├── wsgi.py             # PythonAnywhere WSGI 入口
├── requirements.txt    # Python 依赖
├── README.md
├── core/
│   ├── sympify.py      # 表达式解析（LaTeX / 函数调用预处理 / 有理化）
│   └── render.py       # matplotlib 主题配色（无 Qt 依赖）
├── functions/          # 计算内核（原样复用桌面版，去除 PySide6 依赖）
│   ├── derivative.py   # 求导
│   ├── integral.py     # 积分
│   ├── functions.py    # 函数性质分析
│   ├── simplification.py
│   ├── solvers.py      # 方程/不等式/微分方程/解三角形
│   ├── planes.py       # 平面几何
│   ├── solids.py       # 立体几何（含斜二测画法）
│   ├── paint2D.py      # 平面几何绘图
│   └── paint3D.py      # 立体几何 3D 绘图
├── webapp/
│   ├── server.py       # Flask 应用工厂
│   ├── api.py          # 计算 API
│   ├── geometry.py     # 平面/立体几何对象创建与计算
│   ├── state.py        # 每会话共享状态
│   └── util.py         # 解析 / LaTeX / 图片工具
├── templates/index.html
└── static/
    ├── css/style.css
    ├── js/app.js
    ├── js/i18n.js
    ├── mathjax.js           # 本地 MathJax（离线可用）
    ├── mathlive/            # MathLive 公式键盘（复用桌面版，本地化）
    └── favicon.ico
```

## 本地运行

```bash
cd CalculusWeb
pip install -r requirements.txt
python app.py
```

浏览器自动打开 `http://127.0.0.1:5000`（亦可手动访问）。

## 部署到 PythonAnywhere

### 1. 上传代码

在 PythonAnywhere 的 **Consoles → Bash** 中：

```bash
git clone <你的仓库地址>   # 或通过 Files 页面上传压缩包并解压
cd <项目目录>
```

### 2. 创建虚拟环境并安装依赖

```bash
mkvirtualenv --python=python3.10 calcweb
pip install -r requirements.txt
```

> 免费账户亦可使用系统 Python：`pip install --user -r requirements.txt`。

### 3. 配置 WSGI

进入 **Web → 你的站点 → Code → WSGI configuration file**，清空后填入：

```python
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from webapp.server import app
```

（仓库内已提供 `wsgi.py`，可直接将 WSGI 路径指向项目目录下的 `wsgi.py`。）

### 4. 静态文件

Web 选项卡中设置 **Static files**：

| URL | 目录 |
|-----|------|
| `/static/` | `/home/<你的用户名>/<项目目录>/static/` |

### 5. 重启

点击 Web 页面的 **Reload** 即可访问 `https://<你的用户名>.pythonanywhere.com/`。

### 注意事项

- 应用状态（函数定义、向量、几何对象、缓存）保存在**服务端内存**，按浏览器会话（cookie）隔离。
  免费账户为单进程，状态可正常保持；若使用多 worker 配置，请开启 sticky sessions。
- 首次使用建议在 Bash 中执行 `python -c "from webapp.server import app"` 验证依赖与导入无误。
- PythonAnywhere 使用 Linux；`matplotlib` 的 CJK 字体若缺失，绘图中的中文标签可能显示为方框，
  可 `pip install` 后自行安装中文字体（不影响计算功能）。

## 技术说明

- **后端**：Flask + SymPy + Matplotlib（Agg 后端），复用桌面版 `core/sympify.py` 与 `functions/*` 计算内核。
- **前端**：原生 HTML/CSS/JS，MathJax 本地渲染公式（离线可用），几何图形由服务端 matplotlib 渲染为图片返回。
- **会话**：`webapp/state.py` 以 `session`（cookie）为键保存每用户状态，线程安全。
- **存档**：`GET /api/save` 导出 JSON（`.cca` 兼容格式），`POST /api/load` 导入。

## 许可证

GPLv3（与桌面版一致）。
