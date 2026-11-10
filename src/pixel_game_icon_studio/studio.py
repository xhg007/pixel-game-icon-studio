"""动态配置页：组合风格、配色与章节，实时生成 AGENTS.md。

`pgs serve` 会把本模块的 ``StudioRequestHandler`` 挂到本地 HTTP 服务上：

- ``GET  /studio``       配置页面
- ``GET  /api/presets``  风格预设、材质/元素/稀有度标签、章节清单
- ``POST /api/render``   按配置生成 AGENTS.md，返回 ``{filename, content}``
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .agentdoc import agents_document, build_config_table
from .catalog import (
    TEMPLATES,
    CatalogError,
    kinds_for_template,
    load_catalog,
)
from .design import (
    DesignError,
    design_markdown as build_design_markdown,
    load_design_system,
)
from .config import (
    DEFAULT_STYLE,
    MATERIAL_LABELS,
    POTION_LABELS,
    STYLES,
    StylePreset,
    get_style,
)

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_NAME_RE = re.compile(r"[\r\n#<>]")

RARITY_LABELS: dict[str, str] = {
    "common": "普通",
    "fine": "精良",
    "rare": "稀有",
    "epic": "史诗",
    "legend": "传说",
}

#: key -> AGENTS.md 章节标题（用于按开关裁剪）
SECTION_TITLES: dict[str, str] = {
    "map": "项目地图",
    "commands": "可用命令",
    "styles": "风格预设",
    "visual": "视觉语言（硬约束）",
    "colors": "色彩系统",
    "blueprints": "道具蓝图",
    "metadata": "元数据与命名",
    "prompts": "提示词模板",
    "workflow": "工作流",
    "checklist": "自检清单",
    "troubleshooting": "常见失败与修复",
    "integration": "工具集成",
    "catalog": "图标目录",
    "design": "风格、色板与分类学",
}

#: 可关闭的章节；其余章节始终生成
OPTIONAL_SECTIONS: tuple[str, ...] = (
    "blueprints",
    "prompts",
    "troubleshooting",
    "integration",
    "catalog",
    "design",
)


class ConfigError(ValueError):
    """配置项不合法（页面会显示为 400）。"""


def _hex(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HEX_RE.match(value.strip()):
        raise ConfigError(f"{field} 必须是 #rrggbb 颜色，收到 {value!r}")
    return value.strip().lower()


def _clean_name(value: Any) -> str:
    name = _NAME_RE.sub("", str(value or "")).strip()[:48]
    return name or "图标工厂"


def style_from_payload(payload: dict[str, Any]) -> StylePreset:
    """把页面提交的配置合并到预设上，返回一个临时 StylePreset。"""
    if not isinstance(payload, dict):
        raise ConfigError("请求体必须是 JSON 对象")
    base = get_style(payload.get("style"))
    colors = payload.get("colors") or {}
    if not isinstance(colors, dict):
        raise ConfigError("colors 必须是对象")

    materials = dict(base.materials)
    raw_materials = colors.get("materials") or {}
    if not isinstance(raw_materials, dict):
        raise ConfigError("colors.materials 必须是对象")
    for key, values in raw_materials.items():
        if key not in materials:
            continue
        if not isinstance(values, (list, tuple)) or len(values) != 3:
            raise ConfigError(f"materials.{key} 需要 3 个颜色（亮/中/暗）")
        materials[key] = tuple(_hex(v, f"materials.{key}") for v in values)  # type: ignore[assignment]

    potions = dict(base.potions)
    raw_potions = colors.get("potions") or {}
    if not isinstance(raw_potions, dict):
        raise ConfigError("colors.potions 必须是对象")
    for key, value in raw_potions.items():
        if key in potions:
            potions[key] = _hex(value, f"potions.{key}")

    rarity = dict(base.rarity)
    raw_rarity = colors.get("rarity") or {}
    if not isinstance(raw_rarity, dict):
        raise ConfigError("colors.rarity 必须是对象")
    for key, value in raw_rarity.items():
        if key in rarity:
            rarity[key] = _hex(value, f"rarity.{key}")

    return replace(
        base,
        outline_warm=_hex(colors.get("outline_warm", base.outline_warm), "outline_warm"),
        outline_cool=_hex(colors.get("outline_cool", base.outline_cool), "outline_cool"),
        materials=materials,
        potions=potions,
        rarity=rarity,
    )


def compose_agents(
    style: StylePreset,
    project_name: str = "图标工厂",
    sections: list[str] | tuple[str, ...] | None = None,
    catalog_markdown: str | None = None,
    design_markdown: str | None = None,
    art_style: str | None = None,
    config_markdown: str | None = None,
    blueprint_markdown: str | None = None,
) -> str:
    """生成 AGENTS.md；``sections`` 为 None 时保留全部章节，否则只保留选中章节。"""
    project_name = _clean_name(project_name)
    text = agents_document(
        style,
        catalog_markdown=catalog_markdown,
        design_markdown=design_markdown,
        art_style=art_style,
        config_markdown=config_markdown,
        blueprint_markdown=blueprint_markdown,
    )
    text = text.replace("# AGENTS.md — 图标工厂", f"# AGENTS.md — {project_name}", 1)
    if sections is None:
        return text

    keep = {key for key in sections if key in SECTION_TITLES}
    if keep == set(SECTION_TITLES):
        return text

    blocks = re.split(r"\n(?=## )", text)
    if len(blocks) < 2:
        return text
    head = blocks[0]
    front: list[str] = []
    rest: list[str] = []
    for block in blocks[1:]:
        if block.startswith("## 当前配置") or block.startswith("## 0. "):
            front.append(block)
        else:
            rest.append(block)

    kept: list[str] = []
    for block in rest:
        match = re.match(r"## \d+\. (.+)", block)
        if not match:
            continue
        title = match.group(1).strip()
        key = next(
            (
                k
                for k, t in SECTION_TITLES.items()
                if title == t or title.startswith(t)
            ),
            None,
        )
        if key in keep:
            kept.append(block)

    numbered: list[str] = []
    for index, block in enumerate(kept, start=1):
        numbered.append(re.sub(r"^## \d+\. ", f"## {index}. ", block, count=1))
    return "\n".join([head, *front, *numbered]).rstrip() + "\n"


def _catalog_markdown(
    template: str,
    catalog_dir: str | Path | None,
) -> str | None:
    kinds = kinds_for_template(template)
    if not kinds:
        return None
    directory = Path(catalog_dir) if catalog_dir else Path.cwd() / "catalog"
    try:
        catalog = load_catalog(directory, kinds)
    except CatalogError:
        return None
    return catalog.markdown(kinds, detail="full")


def _design_text(
    catalog_dir: str | Path | None,
    art_style: str | None,
    palette: str | None,
) -> str | None:
    directory = Path(catalog_dir) if catalog_dir else Path.cwd() / "catalog"
    try:
        system = load_design_system(directory)
    except DesignError:
        return None
    try:
        return build_design_markdown(system, art_style, palette)
    except DesignError as exc:
        raise ConfigError(str(exc)) from exc


def _blueprint_markdown(
    template: str, catalog_dir: str | Path | None, detail: str = "full"
) -> str | None:
    kinds = kinds_for_template(template)
    if not kinds:
        return None
    directory = Path(catalog_dir) if catalog_dir else Path.cwd() / "catalog"
    try:
        catalog = load_catalog(directory, kinds)
    except CatalogError:
        return None
    return catalog.blueprint_markdown(kinds, detail=detail)


def _palette_label(palette_key: str | None, catalog_dir: str | Path | None) -> str | None:
    if not palette_key:
        return None
    directory = Path(catalog_dir) if catalog_dir else Path.cwd() / "catalog"
    try:
        system = load_design_system(directory)
        palette = system.find_palette(palette_key)
        return palette.name if palette else None
    except DesignError:
        return None


def render_document(
    payload: dict[str, Any],
    catalog_dir: str | Path | None = None,
) -> tuple[str, str]:
    """按配置生成 AGENTS.md，返回 (文件名, 内容)。"""
    style = style_from_payload(payload)
    template = str(payload.get("template") or "full").lower()
    if template not in TEMPLATES:
        raise ConfigError(f"未知模板 {template!r}，可选: {', '.join(TEMPLATES)}")
    catalog_markdown = _catalog_markdown(template, catalog_dir)
    design_markdown = _design_text(
        catalog_dir,
        payload.get("art_style"),
        payload.get("palette"),
    )
    project_name = _clean_name(payload.get("project_name"))
    palette_key = str(payload.get("palette") or "").strip() or None
    blueprint_full = _blueprint_markdown(template, catalog_dir, "full")
    config_markdown = build_config_table(
        style,
        project_name=project_name,
        template_key=template,
        art_style=payload.get("art_style"),
        palette_key=palette_key,
        palette_label=_palette_label(palette_key, catalog_dir),
    )

    sections = payload.get("sections")
    if sections is not None and not isinstance(sections, list):
        raise ConfigError("sections 必须是数组")
    return "AGENTS.md", compose_agents(
        style,
        project_name=project_name,
        sections=sections,
        catalog_markdown=catalog_markdown,
        design_markdown=design_markdown,
        art_style=payload.get("art_style"),
        config_markdown=config_markdown,
        blueprint_markdown=blueprint_full,
    )


def build_documents(
    payload: dict[str, Any],
    catalog_dir: str | Path | None = None,
) -> dict[str, str]:
    """生成 AGENTS.md。"""
    _, agents = render_document(payload, catalog_dir=catalog_dir)
    return {"AGENTS.md": agents}


#: 保存全部时排除 agents 目标，避免覆盖根目录里带自定义项目名的 AGENTS.md
_INSTALL_TOOLS = "claude,cursor,windsurf,copilot,cline,kiro,gemini,codebuddy,reasonix"


def save_documents(
    payload: dict[str, Any],
    root: str | Path,
    catalog_dir: str | Path | None = None,
) -> dict[str, Any]:
    """把当前配置生成的 AGENTS.md 写入项目根；可选同步所有工具目录。"""
    root_path = Path(root).resolve()
    documents = build_documents(payload, catalog_dir)

    saved: list[str] = []
    for name, content in documents.items():
        path = root_path / name
        path.write_text(content, encoding="utf-8", newline="\n")
        saved.append(name)

    installed: list[str] = []
    skipped: list[str] = []
    if payload.get("install_all"):
        from .installer import install

        style = style_from_payload(payload)
        report = install(
            root=root_path,
            tools=_INSTALL_TOOLS,
            style=style,
            template=str(payload.get("template") or "full"),
            catalog_dir=catalog_dir,
            art_style=payload.get("art_style"),
            palette=payload.get("palette"),
        )
        for result in report.results:
            try:
                relative = result.path.relative_to(root_path).as_posix()
            except ValueError:
                relative = result.path.as_posix()
            if result.status in {"created", "updated"}:
                installed.append(relative)
            elif result.status == "skipped":
                skipped.append(relative)

    return {
        "ok": True,
        "saved": saved,
        "installed": installed,
        "skipped": skipped,
        "root": root_path.as_posix(),
    }


def presets_payload(catalog_dir: str | Path | None = None) -> dict[str, Any]:
    """页面初始化所需的全部预设、标签、模板与目录统计。"""
    styles = []
    for key, preset in STYLES.items():
        styles.append(
            {
                "key": key,
                "name": preset.name,
                "summary": preset.summary,
                "mood": preset.mood,
                "outline_warm": preset.outline_warm,
                "outline_cool": preset.outline_cool,
                "materials": {k: list(v) for k, v in preset.materials.items()},
                "potions": preset.potions,
                "rarity": preset.rarity,
            }
        )

    catalogs: list[dict] = []
    directory = Path(catalog_dir) if catalog_dir else Path.cwd() / "catalog"
    try:
        catalog = load_catalog(directory)
    except CatalogError:
        catalog = None
    if catalog:
        catalogs = [
            {
                "kind": catalog_file.kind,
                "title": catalog_file.title,
                "icons": len(catalog_file.icons),
                "categories": len(catalog_file.categories),
            }
            for catalog_file in catalog.files
        ]

    art_styles: list[dict] = []
    palettes: list[dict] = []
    try:
        design = load_design_system(directory)
    except DesignError:
        design = None
    if design:
        art_styles = [
            {
                "key": style.key,
                "name": style.name,
                "difficulty": style.difficulty,
                "difficulty_label": style.difficulty_label,
                "supported": style.supported,
            }
            for style in design.styles
        ]
        palettes = [
            {
                "key": palette.key,
                "name": palette.name,
                "kind": palette.kind,
                "size": palette.size,
                "colors": list(palette.colors),
            }
            for palette in design.palettes
        ]

    return {
        "default": DEFAULT_STYLE,
        "styles": styles,
        "material_labels": MATERIAL_LABELS,
        "potion_labels": POTION_LABELS,
        "rarity_labels": RARITY_LABELS,
        "art_styles": art_styles,
        "palettes": palettes,
        "design": {"art_style": "pixel", "palette": ""},
        "templates": [
            {"key": key, "label": value["label"], "kinds": list(value["kinds"])}
            for key, value in TEMPLATES.items()
        ],
        "catalogs": catalogs,
        "sections": [
            {
                "key": key,
                "label": title,
                "optional": key in OPTIONAL_SECTIONS,
            }
            for key, title in SECTION_TITLES.items()
        ],
    }


class StudioRequestHandler(SimpleHTTPRequestHandler):
    """静态文件 + /studio + /api/*；通过 ``directory=`` 限定服务根目录。"""

    server_version = "PixelIconStudio/1.0"

    def __init__(self, *args: Any, catalog_dir: str | Path | None = None, **kwargs: Any) -> None:
        self.catalog_dir = Path(catalog_dir) if catalog_dir else Path.cwd() / "catalog"
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # 保持安静，避免每次实时预览都刷一行
        return

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/studio", "/studio/"):
            self._send_html(STUDIO_HTML)
            return
        if path == "/api/presets":
            self._send_json(presets_payload(self.catalog_dir))
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in ("/api/render", "/api/save"):
            self.send_error(404, "Not Found")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
            if path == "/api/render":
                filename, content = render_document(payload, catalog_dir=self.catalog_dir)
                result: dict[str, Any] = {
                    "ok": True,
                    "filename": filename,
                    "content": content,
                }
            else:
                result = save_documents(
                    payload,
                    getattr(self, "directory", "."),
                    self.catalog_dir,
                )
        except (ConfigError, ValueError, json.JSONDecodeError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)
            return
        except OSError as exc:
            self._send_json({"ok": False, "error": f"写入失败: {exc}"}, status=500)
            return
        self._send_json(result)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


STUDIO_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>图标工厂 · AGENTS.md 动态配置</title>
<style>
:root{
  --bg:#141009;--panel:#1e1811;--panel2:#231b12;--line:#6b5636;--line-dark:#241b10;
  --ink:#e8dcc0;--dim:#9a8a6a;--gold:#f0b23e;--ok:#63d66e;--err:#ff7a6e;
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:"Courier New",ui-monospace,monospace;
  font-size:13px;height:100vh;display:flex;flex-direction:column}
header{display:flex;align-items:center;gap:14px;padding:12px 16px;border-bottom:2px solid var(--line-dark);
  background:var(--panel)}
header h1{font-size:17px;letter-spacing:1px;text-shadow:2px 2px 0 #000}
header h1 span{color:var(--gold)}
header .spacer{flex:1}
header a{color:var(--dim);text-decoration:none;font-size:12px}
header a:hover{color:var(--gold)}
main{flex:1;display:flex;min-height:0}
#panel{width:420px;flex:none;overflow:auto;padding:14px;border-right:2px solid var(--line-dark);
  background:var(--panel2)}
#panel h2{font-size:12px;color:var(--gold);letter-spacing:1px;margin:16px 0 8px;
  border-bottom:1px dashed var(--line);padding-bottom:4px}
#panel h2:first-child{margin-top:0}
.row{display:flex;align-items:center;gap:8px;margin:6px 0}
.row label{color:var(--dim);width:88px;font-size:12px;flex:none}
.row input[type=text],.row select{flex:1;min-width:0;background:#15100b;color:var(--ink);
  border:1px solid var(--line);padding:4px 6px;font-family:inherit;font-size:12px}
.row input[type=color]{width:30px;height:24px;border:1px solid var(--line);background:none;padding:0}
.hint{color:var(--dim);font-size:11px;margin:0 0 8px 96px;line-height:1.4}
.triple{display:grid;grid-template-columns:76px repeat(3,1fr);gap:6px;align-items:center;margin:5px 0}
.triple .nm{color:var(--dim);font-size:12px}
.triple .cell{display:flex;gap:3px;align-items:center}
.triple input[type=color]{width:26px;height:22px;border:1px solid var(--line);background:none;padding:0}
.triple input[type=text]{width:100%;background:#15100b;color:var(--ink);border:1px solid var(--line);
  padding:3px 4px;font-family:inherit;font-size:11px}
.checks{display:grid;grid-template-columns:1fr 1fr;gap:4px 10px;margin:6px 0}
.checks label{display:flex;align-items:center;gap:6px;color:var(--dim);font-size:12px;cursor:pointer}
.checks input{accent-color:var(--gold)}
.checks label.locked{opacity:.55;cursor:default}
#preview{flex:1;display:flex;flex-direction:column;min-width:420px}
#bar{display:flex;align-items:center;gap:10px;padding:8px 12px;border-bottom:2px solid var(--line-dark);
  background:var(--panel);flex-wrap:wrap}
#status{color:var(--dim);font-size:12px}
#bar .spacer{flex:1}
button{cursor:pointer;font-family:inherit;font-size:12px;color:var(--ink);background:var(--panel2);
  border:none;padding:6px 12px;white-space:nowrap;
  box-shadow:0 0 0 2px var(--line),0 0 0 4px var(--line-dark)}
button:hover{box-shadow:0 0 0 2px var(--gold),0 0 0 4px var(--line-dark)}
button.primary{color:#1a1206;background:var(--gold)}
pre{flex:1;overflow:auto;padding:16px;font-size:12px;line-height:1.55;white-space:pre;
  background:#100c08}
pre .err{color:var(--err)}
@media (max-width:900px){
  main{flex-direction:column}
  #panel{width:auto;max-height:46vh;border-right:none;border-bottom:2px solid var(--line-dark)}
  #preview{min-width:0}
  header h1{font-size:15px}
  header .spacer{display:none}
}
</style>
</head>
<body>
<header>
  <h1>图标工厂 <span>AGENTS STUDIO</span></h1>
  <span class="spacer"></span>
  <a href="/preview.html">← 图标图库</a>
</header>
<main>
  <aside id="panel">
    <h2>项目</h2>
    <div class="row"><label>项目名</label><input id="project-name" type="text" value="图标工厂"></div>
    <div class="row"><label>风格预设</label><select id="style-select"></select></div>
    <div class="row"><label>文档模板</label><select id="template"></select></div>
    <div class="row"><label>画法风格</label><select id="art-style"></select></div>
    <div class="row"><label>色板</label><select id="palette"></select></div>
    <div class="hint" id="catalog-hint"></div>

    <h2>轮廓色</h2>
    <div id="outline-fields"></div>

    <h2>材质阶（亮 / 中 / 暗）</h2>
    <div id="material-fields"></div>

    <h2>元素色</h2>
    <div id="potion-fields"></div>

    <h2>稀有度强调色</h2>
    <div id="rarity-fields"></div>

    <h2>章节组合</h2>
    <div id="section-fields" class="checks"></div>
  </aside>
  <section id="preview">
    <div id="bar">
      <span id="status">加载中…</span>
      <span class="spacer"></span>
      <button id="reset">重置为预设</button>
      <button id="copy">复制</button>
      <button id="download">下载</button>
      <button id="save" class="primary">保存到项目</button>
      <button id="save-all">保存全部</button>
    </div>
    <pre id="out"></pre>
  </section>
</main>
<script>
const $ = (sel) => document.querySelector(sel);
const HEX = /^#[0-9a-f]{6}$/i;
let presets = null;
let currentStyle = null;
let filename = "AGENTS.md";
let timer = null;
const state = { colors: { materials: {}, potions: {}, rarity: {} } };

function colorCell(value, onChange) {
  const wrap = document.createElement("div");
  wrap.className = "cell";
  const picker = document.createElement("input");
  picker.type = "color";
  picker.value = value;
  const hex = document.createElement("input");
  hex.type = "text";
  hex.value = value;
  picker.oninput = () => { hex.value = picker.value; onChange(picker.value); };
  hex.onchange = () => {
    if (!HEX.test(hex.value)) { hex.value = picker.value; return; }
    picker.value = hex.value;
    onChange(hex.value.toLowerCase());
  };
  wrap.append(picker, hex);
  return wrap;
}

function simpleRow(label, value, onChange) {
  const row = document.createElement("div");
  row.className = "row";
  const nm = document.createElement("label");
  nm.textContent = label;
  row.append(nm, colorCell(value, onChange));
  return row;
}

function tripleRow(label, values, onChange) {
  const row = document.createElement("div");
  row.className = "triple";
  const nm = document.createElement("div");
  nm.className = "nm";
  nm.textContent = label;
  row.append(nm);
  values.forEach((value, index) => {
    row.append(colorCell(value, (v) => onChange(index, v)));
  });
  return row;
}

function buildFields(style) {
  state.colors = {
    outline_warm: style.outline_warm,
    outline_cool: style.outline_cool,
    materials: {},
    potions: {},
    rarity: {},
  };

  const outline = $("#outline-fields");
  outline.replaceChildren(
    simpleRow("暖色物体", style.outline_warm, (v) => { state.colors.outline_warm = v; schedule(); }),
    simpleRow("冷色物体", style.outline_cool, (v) => { state.colors.outline_cool = v; schedule(); }),
  );

  const materials = $("#material-fields");
  materials.replaceChildren();
  Object.keys(style.materials).forEach((key) => {
    state.colors.materials[key] = [...style.materials[key]];
    materials.append(tripleRow(
      presets.material_labels[key] || key,
      style.materials[key],
      (index, value) => { state.colors.materials[key][index] = value; schedule(); },
    ));
  });

  const potions = $("#potion-fields");
  potions.replaceChildren();
  Object.keys(style.potions).forEach((key) => {
    state.colors.potions[key] = style.potions[key];
    potions.append(simpleRow(
      presets.potion_labels[key] || key,
      style.potions[key],
      (v) => { state.colors.potions[key] = v; schedule(); },
    ));
  });

  const rarity = $("#rarity-fields");
  rarity.replaceChildren();
  Object.keys(style.rarity).forEach((key) => {
    state.colors.rarity[key] = style.rarity[key];
    rarity.append(simpleRow(
      (presets.rarity_labels[key] || key) + " · " + key,
      style.rarity[key],
      (v) => { state.colors.rarity[key] = v; schedule(); },
    ));
  });
}

function buildSections() {
  const wrap = $("#section-fields");
  wrap.replaceChildren();
  presets.sections.forEach((section) => {
    const label = document.createElement("label");
    if (!section.optional) label.className = "locked";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = true;
    box.disabled = !section.optional;
    box.value = section.key;
    box.className = "sec";
    box.onchange = schedule;
    const text = document.createElement("span");
    text.textContent = section.label;
    label.append(box, text);
    wrap.append(label);
  });
}

function applyStyle(key) {
  currentStyle = presets.styles.find((s) => s.key === key) || presets.styles[0];
  buildFields(currentStyle);
  schedule();
}

function payload() {
  return {
    style: $("#style-select").value,
    project_name: $("#project-name").value,
    template: $("#template").value,
    art_style: $("#art-style").value,
    palette: $("#palette").value,
    sections: [...document.querySelectorAll(".sec:checked")].map((x) => x.value),
    colors: {
      outline_warm: state.colors.outline_warm,
      outline_cool: state.colors.outline_cool,
      materials: state.colors.materials,
      potions: state.colors.potions,
      rarity: state.colors.rarity,
    },
  };
}

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(render, 220);
}

async function render() {
  const out = $("#out");
  const status = $("#status");
  status.textContent = "生成中…";
  try {
    const response = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload()),
    });
    const data = await response.json();
    if (!data.ok) {
      out.textContent = "配置错误：" + data.error;
      status.textContent = "生成失败";
      return;
    }
    filename = data.filename;
    out.textContent = data.content;
    status.textContent = data.filename + " · " + data.content.length + " 字符";
  } catch (error) {
    out.textContent = "请求失败：" + error;
    status.textContent = "请求失败";
  }
}

function reset() {
  applyStyle($("#style-select").value);
  document.querySelectorAll(".sec").forEach((box) => {
    if (!box.disabled) box.checked = true;
  });
  schedule();
}

async function copyDoc() {
  try {
    await navigator.clipboard.writeText($("#out").textContent);
    $("#status").textContent = "已复制到剪贴板";
  } catch (error) {
    $("#status").textContent = "复制失败，请手动选择";
  }
}

function downloadDoc() {
  const blob = new Blob([$("#out").textContent], { type: "text/markdown;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

async function saveDocs(installAll) {
  const status = $("#status");
  status.textContent = installAll ? "正在保存并同步工具目录…" : "正在保存…";
  try {
    const response = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload(), install_all: installAll }),
    });
    const data = await response.json();
    if (!data.ok) {
      status.textContent = "保存失败：" + data.error;
      return;
    }
    let text = "已写入：" + data.saved.join("、");
    if (data.installed && data.installed.length) {
      text += "；同步 " + data.installed.length + " 个工具文件";
    }
    if (data.skipped && data.skipped.length) {
      text += "；跳过 " + data.skipped.length + " 个手写文件";
    }
    status.textContent = text;
  } catch (error) {
    status.textContent = "保存失败：" + error;
  }
}

async function init() {
  presets = await (await fetch("/api/presets")).json();
  const select = $("#style-select");
  presets.styles.forEach((style) => {
    const option = document.createElement("option");
    option.value = style.key;
    option.textContent = style.name + " · " + style.key;
    select.append(option);
  });
  select.value = presets.default;
  buildSections();

  const templateSelect = $("#template");
  presets.templates.forEach((template) => {
    const option = document.createElement("option");
    option.value = template.key;
    option.textContent = template.label;
    templateSelect.append(option);
  });
  templateSelect.value = "full";
  templateSelect.onchange = schedule;

  const artSelect = $("#art-style");
  presets.art_styles.forEach((style) => {
    const option = document.createElement("option");
    option.value = style.key;
    option.textContent = style.name + " · " + style.difficulty_label;
    artSelect.append(option);
  });
  artSelect.value = (presets.design && presets.design.art_style) || "pixel";
  artSelect.onchange = schedule;

  const paletteSelect = $("#palette");
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "（仅列出，不指定）";
  paletteSelect.append(none);
  presets.palettes.forEach((palette) => {
    const option = document.createElement("option");
    option.value = palette.key;
    option.textContent = palette.name + " · " + palette.size + " 色";
    paletteSelect.append(option);
  });
  paletteSelect.value = (presets.design && presets.design.palette) || "";
  paletteSelect.onchange = schedule;

  const counts = presets.catalogs.map((c) => c.title + " " + c.icons + " 个").join(" · ");
  $("#catalog-hint").textContent = counts || "未找到 catalog/ 目录，暂不注入图标目录";

  select.onchange = () => applyStyle(select.value);
  $("#project-name").oninput = schedule;
  $("#reset").onclick = reset;
  $("#copy").onclick = copyDoc;
  $("#download").onclick = downloadDoc;
  $("#save").onclick = () => saveDocs(false);
  $("#save-all").onclick = () => saveDocs(true);
  applyStyle(presets.default);
}

init().catch((error) => {
  $("#out").textContent = "初始化失败：" + error;
  $("#status").textContent = "初始化失败";
});
</script>
</body>
</html>
"""
