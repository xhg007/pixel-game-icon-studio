"""按画法风格重绘现有 SVG 图标。

当前支持：
- ``pixel``：按目标颜色预设/色板重新着色，保留亮暗阶；
- ``flat``：把主色系（g/G/D/x）压成一个主色，去掉高光与暗部，保留轮廓与次要材质。
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import StylePreset, get_style
from .svg import validate_svg

_PALETTE_RE = re.compile(r"<!--\s*palette\s*:\s*(.*?)-->", re.S | re.I)
_ENTRY_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*=\s*(#[0-9a-fA-F]{6})")
_RECT_RE = re.compile(
    r'<rect\s+x="(\d+)"\s+y="(\d+)"\s+width="(\d+)"\s+height="1"\s+fill="(#[0-9a-fA-F]{6})"\s*/>'
)
_SUPPORTED = {"pixel", "flat"}
_MAIN_KEYS = {"g", "G", "D", "x", "d"}


class RestyleError(ValueError):
    """无法按指定画法重绘。"""


@dataclass
class RestyleReport:
    written: list[Path] = field(default_factory=list)
    backup: Path | None = None
    skipped: list[str] = field(default_factory=list)


def _rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))


def _luminance(color: str) -> float:
    r, g, b = _rgb(color)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def _distance(a: str, b: str) -> int:
    ar, ag, ab = _rgb(a)
    br, bg, bb = _rgb(b)
    return 2 * (ar - br) ** 2 + 4 * (ag - bg) ** 2 + 3 * (ab - bb) ** 2


def _nearest(old: str, pool: list[str], exclude: str | None = None) -> str:
    candidates = [color for color in pool if color != exclude] or pool
    return min(candidates, key=lambda color: _distance(old, color))


def load_palette_colors(key: str | None, catalog_dir: str | Path | None) -> tuple[str, ...]:
    if not key:
        return ()
    directory = Path(catalog_dir) if catalog_dir else Path.cwd() / "catalog"
    path = directory / "palettes.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RestyleError(f"无法读取 {path}: {exc}") from exc
    for palette in data.get("palettes") or []:
        if isinstance(palette, dict) and palette.get("key") == key:
            return tuple(str(color).lower() for color in palette.get("colors") or [])
    raise RestyleError(f"未知色板 {key!r}")


def _pool(style: StylePreset, palette_colors: tuple[str, ...]) -> list[str]:
    colors: list[str] = list(palette_colors)
    for group in style.materials.values():
        colors.extend(group)
    colors.extend(style.potions.values())
    colors.extend(style.rarity.values())
    seen: dict[str, None] = {}
    for color in colors:
        seen.setdefault(color.lower(), None)
    return list(seen)


def _outline(old: str, style: StylePreset) -> str:
    r, _, b = _rgb(old)
    return style.outline_cool if b > r else style.outline_warm


def _map_palette(
    palette: dict[str, str],
    style: StylePreset,
    pool: list[str],
    art_style: str,
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    primary = _nearest(palette["g"], pool) if "g" in palette else None

    for key, old in palette.items():
        if key == "o":
            mapping[key] = _outline(old, style)
        elif art_style == "flat" and key in _MAIN_KEYS and primary:
            mapping[key] = primary
        else:
            mapping[key] = _nearest(old, pool)

    if art_style == "flat" and primary:
        for key in _MAIN_KEYS & set(palette):
            mapping[key] = primary
        for key, old in palette.items():
            if key in _MAIN_KEYS or key == "o":
                continue
            chosen = _nearest(old, pool)
            if chosen == primary:
                chosen = _nearest(old, pool, exclude=primary)
            mapping[key] = chosen
    return mapping


def _merge_rects(text: str) -> str:
    """把同一行相邻同色的 rect 合并，避免 flat 化后出现大量冗余 rect。"""
    rows: dict[int, list[tuple[int, int, str]]] = {}
    for match in _RECT_RE.finditer(text):
        x, y, width = int(match.group(1)), int(match.group(2)), int(match.group(3))
        rows.setdefault(y, []).append((x, width, match.group(4).lower()))
    if not rows:
        return text

    body: list[str] = []
    for y in sorted(rows):
        merged: list[tuple[int, int, str]] = []
        for x, width, fill in sorted(rows[y]):
            if merged and merged[-1][0] + merged[-1][1] == x and merged[-1][2] == fill:
                merged[-1] = (merged[-1][0], merged[-1][1] + width, fill)
            else:
                merged.append((x, width, fill))
        for x, width, fill in merged:
            body.append(f'  <rect x="{x}" y="{y}" width="{width}" height="1" fill="{fill}"/>')

    head = text[: text.index("<rect")]
    return head + "\n".join(body) + "\n</svg>\n"


def _restyle_text(text: str, style: StylePreset, pool: list[str], art_style: str) -> str:
    match = _PALETTE_RE.search(text)
    if not match:
        raise RestyleError("缺少 palette 注释")
    palette = {key: value.lower() for key, value in _ENTRY_RE.findall(match.group(1))}
    if not palette:
        raise RestyleError("palette 注释为空")
    mapping = _map_palette(palette, style, pool, art_style)

    comment = "<!-- palette: " + " ".join(f"{k}={v}" for k, v in mapping.items()) + " -->"
    text = _PALETTE_RE.sub(comment, text, count=1)

    color_map: dict[str, str] = {}
    for key, old in palette.items():
        if key != "o":
            color_map[old] = mapping[key]
    for key, old in palette.items():
        if key == "o":
            color_map[old] = mapping[key]

    def replace_fill(match_obj: re.Match[str]) -> str:
        old = match_obj.group(1).lower()
        return f'fill="{color_map.get(old, old)}"'

    return _merge_rects(re.sub(r'fill="(#[0-9a-fA-F]{6})"', replace_fill, text))


def restyle_icons(
    src: str | Path = "icons",
    out: str | Path | None = None,
    style_key: str = "classic",
    palette_key: str | None = None,
    art_style: str = "flat",
    catalog_dir: str | Path | None = None,
    backup: bool = True,
) -> RestyleReport:
    """按目标画法重绘 ``src/*.svg``，默认覆盖到 ``out``（缺省同 src）。"""
    art_style = (art_style or "pixel").lower()
    if art_style not in _SUPPORTED:
        raise RestyleError(f"暂只支持 pixel / flat 重绘，收到 {art_style!r}")
    style = get_style(style_key)
    palette_colors = load_palette_colors(palette_key, catalog_dir)
    pool = _pool(style, palette_colors)

    src_path = Path(src)
    out_path = Path(out) if out else src_path
    svgs = sorted(src_path.glob("*.svg"))
    if not svgs:
        raise RestyleError(f"{src_path} 下没有 SVG")
    out_path.mkdir(parents=True, exist_ok=True)

    report = RestyleReport()
    if backup and out_path.exists() and any(out_path.glob("*.svg")):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = out_path.parent / "icons_backup" / stamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        for path in out_path.glob("*.svg"):
            shutil.copy2(path, backup_dir / path.name)
        manifest = out_path / "manifest.json"
        if manifest.exists():
            shutil.copy2(manifest, backup_dir / "manifest.json")
        report.backup = backup_dir

    for svg in svgs:
        target = out_path / svg.name
        try:
            text = _restyle_text(svg.read_text(encoding="utf-8"), style, pool, art_style)
        except RestyleError as exc:
            report.skipped.append(f"{svg.name}: {exc}")
            continue
        target.write_text(text, encoding="utf-8", newline="\n")
        issues = validate_svg(target)
        errors = [issue for issue in issues if issue.is_error]
        if errors:
            target.write_text(svg.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
            report.skipped.append(f"{svg.name}: " + "; ".join(issue.message for issue in errors))
            continue
        report.written.append(target)
    return report
