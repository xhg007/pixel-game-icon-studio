# 图标工厂（pixel-game-icon-studio）

把游戏道具描述变成 **16×16 像素风 SVG 图标**，自动校验格式、导出多尺寸 PNG，
并在本地图库中预览。同时提供 **多工具 agent 入口安装**、**MCP server** 和 **精细 AGENTS.md**，
让 Claude Code、Cursor、Codex、CodeBuddy、Reasonix 等编码 Agent 能直接按项目规范画图标。

项目由 [uv](https://docs.astral.sh/uv/) 管理，PNG 渲染只依赖 Pillow，
Windows / macOS / Linux 均无需额外原生库。

> **clone 即用**：仓库自带 `AGENTS.md`，以及 `CLAUDE.md`、`CODEBUDDY.md`、`GEMINI.md`、
> `.cursor/rules/` 等 agent 入口。用编程工具打开本项目后，Agent 会直接读到项目规范，
> 在 `icons/` 里生成 SVG，再用 `pgs build` 转 PNG、`pgs serve` 预览。

## 快速开始

```bash
uv sync                              # 安装依赖
uv run pgs samples                   # 1. 生成 10 个示例图标到 icons/
uv run pgs build                     # 2. 校验并导出 png/{32,64,128}/ + icons/manifest.json
uv run pgs serve                     # 3. 打开 /studio（配置页）或 /preview.html（图库）

uv run pgs install --tools all       # 可选：重新生成各工具 agent 入口 + 写 MCP 配置
uv run pgs catalog                   # 可选：查看内置物品 / UI 图标目录
uv run pgs design                    # 可选：查看风格 / 色板 / 分类学
uv run pgs mcp                       # 可选：启动 MCP server（stdio）
```

也可以用模块方式运行：`uv run python -m pixel_game_icon_studio build`。

## 命令

| 命令 | 作用 |
|---|---|
| `uv run pgs samples [--out icons]` | 生成内置 10 个示例 SVG |
| `uv run pgs check [--src icons]` | 只做规范校验，错误时退出码为 1 |
| `uv run pgs build [--src icons] [--out png] [--sizes 32 64 128] [--bg "#1a140c"]` | 校验 + 导出 PNG + 写 `icons/manifest.json` |
| `uv run pgs serve [--root .] [--port 8000] [--bind 127.0.0.1] [--no-browser]` | 启动图库 + AGENTS.md 动态配置页 |
| `uv run pgs install [--tools all] [--style classic] [--template full] [--force] [--dry-run]` | 生成各工具 agent 入口并合并 MCP 配置 |
| `uv run pgs agents-md [--out AGENTS.md] [--style classic] [--template full\|items\|ui\|spec]` | 生成精细 AGENTS.md（配色、蓝图、提示词模板、图标目录） |
| `uv run pgs catalog [--kind items\|ui\|all] [--category KEY] [--search 文本] [--format table\|json\|csv] [--out PATH]` | 列出、搜索或导出图标目录 |
| `uv run pgs design [--art-style pixel] [--palette pico8] [--format table\|markdown\|json] [--out PATH]` | 查看画法风格、色板与分类学 |
| `uv run pgs restyle [--src icons] [--out icons] [--style neon] [--palette ui_semantic] [--art-style flat]` | 按画法重绘 icons，默认先备份 |
| `uv run pgs styles` | 列出风格预设 |
| `uv run pgs mcp [--transport stdio\|sse\|streamable-http] [--port 8001]` | 启动 MCP server |

`pgs agents-md` 默认**直接覆盖**同名文件（`AGENTS.md`），无需 `--force`；
`pgs install` 对手写规则文件仍保留保护，需显式 `--force`。

## 图标目录（物品 / UI）

仓库内置两份可直接引用的命名与配色目录，按类别拆分：

| 文件 | 内容 | 数量 |
|---|---|---|
| `catalog/items.json` | 物品：药水、武器、防具、材料、货币、食物、任务、魔法、工具 | 52 |
| `catalog/ui.json` | UI：导航、操作、状态、媒体、社交、设置、商业、文件 | 50 |
| `catalog/items.csv` / `catalog/ui.csv` | 表格副本，便于批量编辑或导入表格软件 | 同左 |

每条记录包含 `slug`、`name`、`category`、`rarity`（物品）、`keywords`、`silhouette`、
`palette`（亮 / 中 / 暗三色）和 `notes`。目录在加载时会校验 slug 唯一、颜色格式与稀有度取值。

```bash
uv run pgs catalog                          # 分类统计
uv run pgs catalog --kind ui --search 箭头   # 关键词搜索
uv run pgs catalog --format csv --out catalog/all.csv
```

文档模板（`--template` 或 `/studio` 页面）：

| 模板 | 注入的目录 |
|---|---|
| `full` | 物品 + UI（默认） |
| `items` | 仅物品图标 |
| `ui` | 仅 UI 交互图标 |
| `spec` | 不注入目录，纯规范 |

```bash
uv run pgs agents-md --template items    # 物品图标版 AGENTS.md
uv run pgs agents-md --template ui       # UI 交互图标版 AGENTS.md
```

## 设计体系（风格 / 色板 / 分类学）

调研结论已固化为三份结构化数据，Agent 可直接读取：

| 文件 | 内容 |
|---|---|
| `catalog/styles.json` | 10 种画法风格：像素、扁平、线性、手绘、拟物、Q 版、MBE、等距、卡通渲染、暗黑哥特；含视觉特征、适用场景、LLM 难度与项目支持度 |
| `catalog/palettes.json` | 8 套色板：Game Boy DMG、PICO-8 16/32、DB32、Arne 16、Sweetie 16、游戏 UI 语义色、WoW 稀有度色阶 |
| `catalog/taxonomy.json` | 功能层级 6 类、RPG 道具八大类、题材流派 5 种 |

```bash
uv run pgs design                                            # 一览
uv run pgs design --format markdown --art-style flat --palette pico8 --out design.md
```

生成文档时同样可以指定三层参数：

```bash
uv run pgs agents-md --art-style pixel --palette db32
uv run pgs agents-md --template ui --art-style line --palette gameboy_dmg
```

`/studio` 页面新增「画法风格」「色板」下拉，切换后实时注入文档第 14 章。

> ⚠️ **改画法不会自动重绘已有图标**：文档里的风格只影响提示词与规范。
> 要让 `icons/` 真正变成扁平/线性等风格，需要运行 `pgs restyle`：
>
> ```bash
> uv run pgs restyle --style neon --palette ui_semantic --art-style flat
> ```
>
> 该命令默认先把原图标备份到 `icons_backup/`，再覆盖 `icons/`。

> 当前 SVG 管线**原生支持像素风**；扁平、线性、Q 版、MBE、暗黑哥特可用 rect 近似；
> 手绘、拟物、等距、卡通渲染在数据中标记为 `future`，需要后续扩展渲染管线。

## AGENTS.md 动态配置页

`pgs serve` 启动后提供两个页面：

| 地址 | 用途 |
|---|---|
| `/studio` | **动态配置页**：项目名、风格预设、轮廓色、9 种材质三阶、元素色、5 种稀有度色、章节开关；修改后实时预览，可复制或下载 |
| `/preview.html` | 图标图库，按稀有度着色并支持多尺寸查看 |

配置页生成的文档与 `pgs agents-md` **同源**（`agentdoc.py`），
支持两种落盘方式：

- **保存到项目**：把当前配置生成的 `AGENTS.md` 直接写入项目根（覆盖同名文件）；
- **保存全部**：保存根 AGENTS.md 后，再同步到所有工具的 agent 入口（`CLAUDE.md`、`CODEBUDDY.md`、
  `GEMINI.md`、`.cursor/rules/` 等）与 MCP 配置；手写规则文件会被跳过并在状态栏提示。

后端 API：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/presets` | 返回全部风格预设、材质/元素/稀有度标签与章节清单 |
| POST | `/api/render` | 提交配置，返回 `{ok, filename, content}`；颜色非法时返回 400 |
| POST | `/api/save` | 提交配置，写入项目根；额外传 `"install_all": true` 同步工具目录 |

```json
{
  "style": "neon",
  "project_name": "我的图标库",
  "target": "agents",
  "sections": ["map", "commands", "styles", "visual", "colors"],
  "colors": {
    "outline_warm": "#141018",
    "materials": {"gold": ["#fff8c8", "#f8d84a", "#b8901a"]},
    "rarity": {"legend": "#ffd84a"}
  }
}
```

## Agent 集成

### 安装矩阵

`uv run pgs install --tools all` 会生成以下文件（`--tools` 可只选其一）：

| 工具 | 生成路径 | 包装方式 |
|---|---|---|
| Claude Code | `CLAUDE.md` | 完整项目说明 |
| Cursor | `.cursor/rules/pixel-game-icon.mdc` | 规则（带 globs frontmatter） |
| Windsurf | `.windsurf/rules/pixel-game-icon.md` | 规则 |
| GitHub Copilot | `.github/instructions/pixel-game-icon.instructions.md` | 指令（applyTo） |
| Cline | `.clinerules/pixel-game-icon.md` | 规则 |
| Kiro | `.kiro/steering/pixel-game-icon.md` | Steering |
| Gemini CLI | `GEMINI.md` | 完整项目说明 |
| CodeBuddy（腾讯） | `CODEBUDDY.md` | 完整项目说明 |
| Reasonix | `AGENTS.md` | 完整项目说明（读取根 AGENTS.md） |
| Codex / 通用 | `AGENTS.md` | 完整项目说明 |

同时写入 MCP 配置（已有 JSON 会安全合并，不会覆盖其它 server）：

| 文件 | 顶层键 | 说明 |
|---|---|---|
| `.mcp.json` | `mcpServers` | Claude Code、Reasonix（两者都读取项目根配置） |
| `.cursor/mcp.json` | `mcpServers` | Cursor |
| `.vscode/mcp.json` | `servers` | VS Code / Copilot |
| `.codebuddy/mcp.json` | `mcpServers` | CodeBuddy |
| `.pgs/mcp.json` | `mcpServers` | 通用片段 |

生成的 agent 入口/规则文件带 `generated by pgs` 标记；重复安装幂等，已存在的手写文件需要
`--force` 才会覆盖。用 `--dry-run` 可先查看将写入的路径。

### MCP server

```bash
uv run pgs mcp                                        # stdio，供编辑器启动
uv run pgs mcp --transport streamable-http --port 8001
```

| 工具 | 作用 |
|---|---|
| `list_icons(src="icons")` | 列出图标及名称、稀有度、校验状态 |
| `create_icon(slug, name, rarity, rows, palette, overwrite=false)` | 由 16 行字符网格直接生成合法 SVG |
| `validate_icons(src="icons")` | 返回结构化错误/警告 |
| `build_icons(src, out, sizes, background)` | 导出 PNG 并写 manifest |
| `get_style_guide(style)` | 返回当前风格的完整 AGENTS.md |
| `list_styles()` | 列出风格预设 |

资源：`pgs://style-guide`（Markdown 全文）。

MCP 配置示例：

```json
{
  "mcpServers": {
    "pixel-game-icon": {
      "command": "uv",
      "args": ["run", "pgs", "mcp"]
    }
  }
}
```

## 风格预设

| key | 名称 | 适用题材 |
|---|---|---|
| `classic` | 经典 16-bit 奇幻 | 温暖饱和、轮廓清晰，默认风格 |
| `dark-fantasy` | 暗黑奇幻 | 低饱和、冷紫阴影、铁灰金属 |
| `pastel` | 明亮柔和 | 高明度、低对比、无纯黑轮廓 |
| `neon` | 赛博霓虹 | 深底、高饱和、冷白高光 |

风格会影响生成的 AGENTS.md 与各工具入口中给出的轮廓色、材质三阶、稀有度色与元素色：

```bash
uv run pgs agents-md --style dark-fantasy --force
uv run pgs install --tools cursor --style pastel
```

## AGENTS.md 里有什么

`AGENTS.md` 是给编码 Agent 的精细工作说明，包含：

- 项目地图与可用命令；
- 视觉硬约束：画布、rect-only、坐标、调色板、透明度；
- 像素级配方：轮廓、受光、亮暗比例、阶梯曲线、高光、留白；
- 当前风格的完整色彩系统：材质三阶、稀有度强调色、元素色、用色规则；
- 18 类道具蓝图（物品 10 + UI 8，由 catalog 全量生成）：每类给出剪影公式、建议占比、
  关键像素、常见失败与必须生成的完整 slug 清单；
- 3 套可直接复制的提示词模板：单图标、批量图标、稀有度变体；
- 常用物品 / UI 交互图标目录（可按模板注入）：名字、slug、稀有度、配色与剪影；
- 自检清单与「症状 → 原因 → 修复」对照表。

## 目录结构

```
icons/                          图标源文件 + 自动生成的 manifest.json
png/{32,64,128}/                导出的 PNG
catalog/
  items.json                    物品图标目录（52）
  ui.json                       UI 交互图标目录（50）
  items.csv / ui.csv            表格副本
  styles.json                   10 种画法风格
  palettes.json                 8 套色板（PICO-8 / DB32 / WoW 稀有度…）
  taxonomy.json                 功能层级 / 道具八大类 / 题材流派
src/pixel_game_icon_studio/
  svg.py                        16×16 SVG 子集：元数据、校验、Pillow 光栅化
  builder.py                    批量构建、manifest 生成
  samples.py                    10 个内置示例的像素数据
  config.py                     4 套风格预设（材质阶、稀有度、元素色）
  agentdoc.py                   AGENTS.md 生成
  studio.py                     动态配置页 + /api/presets + /api/render
  installer.py                  多工具技能目录 + MCP 配置安装
  mcp_server.py                 MCP 工具与 server
  cli.py                        samples/build/check/serve/install/agents-md/styles/mcp
  __main__.py                   python -m 入口
preview.html                    图库预览页（读取 icons/manifest.json）
AGENTS.md                       由 pgs agents-md 生成
tests/                          unittest 测试
```

## 设计要点

- **元数据单一来源**：`data-name` / `data-rarity` 写在 SVG 根元素上，`build` 解析后写入
  `manifest.json`，预览页按它渲染名称与稀有度色。
- **格式即契约**：`check` 校验画布尺寸、rect-only、`height=1`、坐标越界、调色板色数与
  未登记颜色、同行同色未合并等规则；不合规的图标不会进入 manifest。
- **像素锐利**：按 16×16 网格逐 rect 绘制，再用最近邻放大到目标尺寸，不经过抗锯齿。
- **文档即代码**：AGENTS.md 由 `agentdoc.py` 生成，风格切换后重新生成即可，
  避免文档与校验器/示例数据漂移。
- **PNG 后端**：只实现本项目所需的 SVG 子集（rect + fill），因此不需要 cairosvg / cairo
  原生库，`uv sync` 后即可跨平台导出。
