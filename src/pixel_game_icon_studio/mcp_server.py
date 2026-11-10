"""MCP server：把图标生成、校验、构建与风格指南暴露给编辑器里的 Agent。

工具函数都是普通 Python 函数，可直接单元测试；``create_server`` 才依赖 mcp SDK。
"""

from __future__ import annotations

import re
from pathlib import Path

from .builder import build, find_svgs
from .config import get_style, style_names
from .samples import IconSpec, check_spec, rows_to_svg
from .svg import RARITIES, SvgError, read_meta, validate_svg

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_INSTRUCTIONS = """图标工厂。可用工具：
- list_icons: 列出 icons/ 下的图标与元数据
- create_icon: 用 16 行字符网格 + 调色板直接生成合法 SVG
- validate_icons: 按项目规范校验
- build_icons: 导出 PNG 并写 manifest
- get_style_guide: 读取当前风格的 AGENTS.md（配色、蓝图、提示词模板）

写图标前先调用 get_style_guide；生成后必须调用 validate_icons。"""


def _issue_dicts(issues) -> list[dict]:
    return [{"level": issue.level, "message": issue.message} for issue in issues]


def list_icons(src: str = "icons") -> dict:
    """列出图标源目录中的 SVG 及其元数据。"""
    src_path = Path(src)
    if not src_path.is_dir():
        return {"ok": False, "error": f"目录不存在: {src}", "icons": []}
    icons: list[dict] = []
    for svg in sorted(src_path.glob("*.svg")):
        meta = read_meta(svg)
        issues = validate_svg(svg)
        icons.append(
            {
                "id": svg.stem,
                "name": meta.name,
                "rarity": meta.rarity,
                "path": svg.as_posix(),
                "errors": sum(1 for issue in issues if issue.is_error),
                "warnings": sum(1 for issue in issues if not issue.is_error),
            }
        )
    return {"ok": True, "src": src_path.as_posix(), "count": len(icons), "icons": icons}


def create_icon(
    slug: str,
    name: str,
    rarity: str,
    rows: list[str],
    palette: dict[str, str],
    src: str = "icons",
    overwrite: bool = False,
) -> dict:
    """由 16 行字符网格生成规范 SVG 并写入 ``src/<slug>.svg``。

    ``.`` 表示透明；其它字符必须在 ``palette`` 中有对应 ``#hex`` 颜色。
    """
    if not _SLUG_RE.match(slug):
        return {"ok": False, "error": f"slug 必须匹配 {_SLUG_RE.pattern}"}
    if not name.strip():
        return {"ok": False, "error": "name 不能为空"}
    rarity = rarity.strip().lower()
    if rarity not in RARITIES:
        return {"ok": False, "error": f"rarity 必须是 {' / '.join(RARITIES)} 之一"}
    if not palette:
        return {"ok": False, "error": "palette 不能为空"}

    try:
        spec = IconSpec(name=name.strip(), rarity=rarity, palette=palette, rows=tuple(rows))
        check_spec(slug, spec)
        text = rows_to_svg(spec)
    except (SvgError, KeyError, TypeError) as exc:
        return {"ok": False, "error": f"像素网格或调色板不合法: {exc}"}

    out = Path(src) / f"{slug}.svg"
    if out.exists() and not overwrite:
        return {"ok": False, "error": f"{out.as_posix()} 已存在；传 overwrite=true 覆盖"}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")

    issues = validate_svg(out)
    errors = [issue for issue in issues if issue.is_error]
    if errors:
        out.unlink(missing_ok=True)
        return {"ok": False, "error": "生成的 SVG 未通过校验，已回滚", "issues": _issue_dicts(issues)}
    return {
        "ok": True,
        "path": out.as_posix(),
        "issues": _issue_dicts(issues),
    }


def validate_icons(src: str = "icons") -> dict:
    """校验整个图标目录，返回结构化错误/警告。"""
    try:
        svgs = find_svgs(src)
    except SvgError as exc:
        return {"ok": False, "error": str(exc), "errors": [], "warnings": []}

    errors: list[dict] = []
    warnings: list[dict] = []
    for svg in svgs:
        for issue in validate_svg(svg):
            item = {"file": svg.name, "message": issue.message}
            (errors if issue.is_error else warnings).append(item)
    return {
        "ok": not errors,
        "checked": len(svgs),
        "errors": errors,
        "warnings": warnings,
    }


def build_icons(
    src: str = "icons",
    out: str = "png",
    sizes: list[int] | None = None,
    background: str | None = None,
) -> dict:
    """导出 PNG 并生成 manifest，返回构建摘要。"""
    try:
        report = build(
            src=src,
            out=out,
            sizes=sizes or (32, 64, 128),
            background=background,
        )
    except SvgError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": report.ok,
        "icons": report.icons,
        "png_count": report.png_count,
        "manifest": report.manifest_path.as_posix() if report.manifest_path else None,
        "failed_files": report.failed_files,
        "problems": {
            name: [str(issue) for issue in issues]
            for name, issues in report.problems.items()
            if issues
        },
    }


def get_style_guide(style: str | None = None) -> str:
    """返回当前风格的完整 AGENTS.md 文本。"""
    from .agentdoc import agents_document

    return agents_document(get_style(style))


def style_list() -> list[dict]:
    """列出可用风格预设。"""
    result = []
    for key in style_names():
        preset = get_style(key)
        result.append({"key": key, "name": preset.name, "summary": preset.summary})
    return result


def create_server():
    """构建 MCPServer 实例（延迟导入 mcp，未安装时不影响其它命令）。"""
    from mcp.server.mcpserver import MCPServer

    from . import __version__

    server = MCPServer(
        name="pixel-game-icon-studio",
        version=__version__,
        instructions=_INSTRUCTIONS,
    )

    @server.tool(name="list_icons", description="列出 icons/ 下的图标及其名称、稀有度与校验状态。")
    def list_icons_tool(src: str = "icons") -> dict:
        return list_icons(src)

    @server.tool(
        name="create_icon",
        description=(
            "用 16 行×16 列的字符网格生成 16×16 像素 SVG。"
            "'.' 为透明，其它字符需在 palette 中映射到 #hex；返回写入路径与校验结果。"
        ),
    )
    def create_icon_tool(
        slug: str,
        name: str,
        rarity: str,
        rows: list[str],
        palette: dict[str, str],
        src: str = "icons",
        overwrite: bool = False,
    ) -> dict:
        return create_icon(slug, name, rarity, rows, palette, src, overwrite)

    @server.tool(name="validate_icons", description="按项目规范校验图标目录，返回错误与警告。")
    def validate_icons_tool(src: str = "icons") -> dict:
        return validate_icons(src)

    @server.tool(name="build_icons", description="导出多尺寸 PNG 并生成 icons/manifest.json。")
    def build_icons_tool(
        src: str = "icons",
        out: str = "png",
        sizes: list[int] | None = None,
        background: str | None = None,
    ) -> dict:
        return build_icons(src, out, sizes, background)

    @server.tool(
        name="get_style_guide",
        description="读取图标风格指南（配色、材质阶、道具蓝图、提示词模板）。",
    )
    def get_style_guide_tool(style: str | None = None) -> str:
        return get_style_guide(style)

    @server.tool(name="list_styles", description="列出可用的图标风格预设。")
    def list_styles_tool() -> list[dict]:
        return style_list()

    @server.resource(
        "pgs://style-guide",
        name="style-guide",
        description="当前风格的 AGENTS.md 全文",
        mime_type="text/markdown",
    )
    def style_guide_resource() -> str:
        return get_style_guide()

    return server


def run(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8001) -> None:
    """启动 MCP server。transport 可选 stdio / sse / streamable-http。"""
    server = create_server()
    if transport == "stdio":
        server.run("stdio")
    else:
        server.run(transport, host=host, port=port)
