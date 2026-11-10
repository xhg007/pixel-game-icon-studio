"""本项目约定的 16×16 像素 SVG 子集：元数据解析、规范校验与 Pillow 光栅化。

约定（与 AGENTS.md 保持一致）：
- 画布固定 16×16；
- 只用 ``<rect>``，每个 rect 高 1px，坐标为正整数；
- 根元素带 ``data-name`` 与 ``data-rarity``；
- 调色板写在 ``<!-- palette: k=#hex ... -->`` 注释里，最多 12 色；
- 背景透明，不使用 filter/gradient/style。
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageColor, ImageDraw

CANVAS = 16
RARITIES = ("common", "fine", "rare", "epic", "legend")
MAX_PALETTE_COLORS = 12

_PALETTE_RE = re.compile(r"<!--\s*palette\s*:\s*(.*?)-->", re.S | re.I)
_PALETTE_ENTRY_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*=\s*(#[0-9a-fA-F]{3,8})")
_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

#: 根元素之外出现即视为违规的标签（本项目只画 rect）
ALLOWED_TAGS = frozenset({"svg", "rect"})


class SvgError(ValueError):
    """SVG 无法解析为本项目约定的图标格式。"""


@dataclass(frozen=True)
class IconMeta:
    name: str
    rarity: str = "common"


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float
    fill: str


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warning"
    message: str

    @property
    def is_error(self) -> bool:
        return self.level == "error"

    def __str__(self) -> str:
        return f"[{self.level}] {self.message}"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_root(path: str | Path) -> ET.Element:
    """解析 XML 根元素，失败时抛出带位置信息的 :class:`SvgError`。"""
    try:
        return ET.fromstring(_read_text(path))
    except ET.ParseError as exc:
        raise SvgError(f"XML 解析失败: {exc}") from exc


def parse_palette(text: str) -> dict[str, str]:
    """读取 ``<!-- palette: o=#2e1f10 g=#e8433f -->`` 注释。"""
    match = _PALETTE_RE.search(text)
    if not match:
        return {}
    return {key: value.lower() for key, value in _PALETTE_ENTRY_RE.findall(match.group(1))}


def read_meta(path: str | Path) -> IconMeta:
    """从根元素读取中文名与稀有度；缺失时给出可用的兜底值。"""
    root = load_root(path)
    name = (root.get("data-name") or "").strip() or Path(path).stem
    rarity = (root.get("data-rarity") or "common").strip().lower()
    return IconMeta(name=name, rarity=rarity)


def _number(element: ET.Element, attr: str, path: str | Path) -> float:
    raw = element.get(attr)
    if raw is None:
        raise SvgError(f"{Path(path).name}: <rect> 缺少 {attr} 属性")
    try:
        return float(raw)
    except ValueError as exc:
        raise SvgError(f"{Path(path).name}: {attr}={raw!r} 不是数字") from exc


def parse_rects(path: str | Path) -> list[Rect]:
    """把 SVG 中的所有 rect 读成 :class:`Rect` 列表（仅用于渲染，不做规范校验）。"""
    root = load_root(path)
    rects: list[Rect] = []
    for element in root.iter():
        if _local_name(element.tag) != "rect":
            continue
        fill = element.get("fill")
        if not fill:
            raise SvgError(f"{Path(path).name}: <rect> 缺少 fill 属性")
        rects.append(
            Rect(
                x=_number(element, "x", path),
                y=_number(element, "y", path),
                width=_number(element, "width", path),
                height=_number(element, "height", path),
                fill=fill,
            )
        )
    return rects


def _rgba(color: str) -> tuple[int, ...]:
    try:
        return ImageColor.getrgb(color)
    except ValueError as exc:
        raise SvgError(f"无法识别的颜色: {color!r}") from exc


def rasterize(
    rects: Iterable[Rect],
    size: int = CANVAS,
    background: str | None = None,
) -> Image.Image:
    """按 16×16 网格绘制 rect，再用最近邻放大到 ``size``，保证像素锐利。"""
    if size <= 0:
        raise ValueError("size 必须为正整数")
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    for rect in rects:
        color = _rgba(rect.fill)
        if len(color) == 3:
            color = (*color, 255)
        x0, y0 = round(rect.x), round(rect.y)
        x1, y1 = round(rect.x + rect.width) - 1, round(rect.y + rect.height) - 1
        draw.rectangle((x0, y0, x1, y1), fill=color)
    if size != CANVAS:
        canvas = canvas.resize((size, size), Image.Resampling.NEAREST)
    if background:
        flat = Image.new("RGBA", canvas.size, (*_rgba(background)[:3], 255))
        flat.alpha_composite(canvas)
        return flat
    return canvas


def render_png(
    svg_path: str | Path,
    png_path: str | Path,
    size: int,
    background: str | None = None,
) -> Path:
    """把单个 SVG 渲染成 PNG，返回输出路径。"""
    out = Path(png_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rasterize(parse_rects(svg_path), size=size, background=background).save(out, format="PNG")
    return out


def _is_int(value: float) -> bool:
    return float(value).is_integer()


def validate_svg(path: str | Path) -> list[Issue]:
    """按 AGENTS.md 的硬性格式约束检查一个 SVG，返回错误/警告列表。"""
    path = Path(path)
    issues: list[Issue] = []
    try:
        text = _read_text(path)
        root = ET.fromstring(text)
    except (OSError, ET.ParseError) as exc:
        return [Issue("error", f"无法读取或解析: {exc}")]

    if _local_name(root.tag) != "svg":
        issues.append(Issue("error", f"根元素必须是 <svg>，实际是 <{_local_name(root.tag)}>"))

    viewbox = (root.get("viewBox") or "").replace(",", " ").split()
    if viewbox != ["0", "0", "16", "16"]:
        issues.append(Issue("error", f'viewBox 必须是 "0 0 16 16"，实际是 {root.get("viewBox")!r}'))
    for attr in ("width", "height"):
        if (root.get(attr) or "").strip() != str(CANVAS):
            issues.append(Issue("error", f'{attr} 必须是 "{CANVAS}"，实际是 {root.get(attr)!r}'))

    name = (root.get("data-name") or "").strip()
    if not name:
        issues.append(Issue("error", "根元素缺少非空的 data-name（中文道具名）"))
    rarity = (root.get("data-rarity") or "").strip().lower()
    if rarity not in RARITIES:
        issues.append(
            Issue("error", f"data-rarity 必须是 {' / '.join(RARITIES)} 之一，实际是 {rarity!r}")
        )

    palette = parse_palette(text)
    if not palette:
        issues.append(Issue("error", "缺少 <!-- palette: k=#hex ... --> 调色板注释"))
    else:
        colors = set(palette.values())
        if len(colors) > MAX_PALETTE_COLORS:
            issues.append(
                Issue("error", f"调色板最多 {MAX_PALETTE_COLORS} 色，实际 {len(colors)} 色")
            )
        for key, color in palette.items():
            if not _HEX_RE.match(color):
                issues.append(Issue("error", f"调色板 {key}={color} 不是 #hex 颜色"))
    allowed_colors = set(palette.values())

    children = list(root)
    for child in children:
        tag = _local_name(child.tag)
        if tag not in ALLOWED_TAGS:
            issues.append(Issue("error", f"只允许 <rect>，发现 <{tag}>"))
        elif tag == "rect" and child.get("filter"):
            issues.append(Issue("error", "<rect> 不允许使用 filter"))

    rects = [child for child in children if _local_name(child.tag) == "rect"]
    if not rects:
        issues.append(Issue("error", "没有任何 <rect>，图标是空的"))

    for index, rect in enumerate(rects, start=1):
        label = f"第 {index} 个 <rect>"
        values: dict[str, float] = {}
        for attr in ("x", "y", "width", "height"):
            raw = rect.get(attr)
            if raw is None:
                issues.append(Issue("error", f"{label} 缺少 {attr}"))
                continue
            try:
                values[attr] = float(raw)
            except ValueError:
                issues.append(Issue("error", f"{label} 的 {attr}={raw!r} 不是数字"))
                continue
            if not _is_int(values[attr]):
                issues.append(Issue("error", f"{label} 的 {attr}={raw} 必须是整数"))

        fill = (rect.get("fill") or "").lower()
        if not fill:
            issues.append(Issue("error", f"{label} 缺少 fill"))
        elif allowed_colors and fill not in allowed_colors:
            issues.append(Issue("error", f"{label} 的 fill={fill} 不在 palette 注释中"))
        elif fill and not _HEX_RE.match(fill):
            issues.append(Issue("error", f"{label} 的 fill={fill} 不是 #hex 颜色"))

        if "width" in values and values["width"] <= 0:
            issues.append(Issue("error", f"{label} 的 width 必须为正数"))
        if "height" in values and values["height"] != 1:
            issues.append(Issue("error", f"{label} 的 height 必须是 1，实际是 {values['height']:g}"))
        if "x" in values and "width" in values:
            if values["x"] < 0 or values["x"] + values["width"] > CANVAS:
                issues.append(Issue("error", f"{label} 横向越界: x={values['x']:g}, width={values['width']:g}"))
        if "y" in values and "height" in values:
            if values["y"] < 0 or values["y"] + values["height"] > CANVAS:
                issues.append(Issue("error", f"{label} 纵向越界: y={values['y']:g}, height={values['height']:g}"))

    issues.extend(_unmerged_runs(rects))
    return issues


def _unmerged_runs(rects: list[ET.Element]) -> list[Issue]:
    """检查同一行中相邻且同色的 rect 是否忘了合并（只报警告）。"""
    issues: list[Issue] = []
    rows: dict[int, list[tuple[float, float, str]]] = {}
    for rect in rects:
        try:
            y = int(float(rect.get("y", "0")))
            x = float(rect.get("x", "0"))
            width = float(rect.get("width", "0"))
        except ValueError:
            continue
        fill = (rect.get("fill") or "").lower()
        rows.setdefault(y, []).append((x, width, fill))

    for y, spans in sorted(rows.items()):
        spans.sort()
        for (x1, w1, f1), (x2, _, f2) in zip(spans, spans[1:]):
            if x1 + w1 == x2 and f1 == f2:
                issues.append(
                    Issue("warning", f"第 {y} 行 x={x1:g} 与 x={x2:g} 同色相邻，应合并为一个 rect")
                )
    return issues


def check_svg(path: str | Path) -> list[Issue]:
    """校验别名，便于 CLI 与测试使用。"""
    return validate_svg(path)
