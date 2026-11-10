"""设计体系：画法风格、色板与图标分类学，供文档与配置页组合。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_SUPPORT_LABELS = {"full": "原生支持", "partial": "可用 rect 近似", "future": "需扩展"}


class DesignError(ValueError):
    """设计库 JSON 不合法。"""


@dataclass(frozen=True)
class ArtStyle:
    key: str
    name: str
    visual: str
    best_for: str
    examples: str
    difficulty: int
    difficulty_label: str
    supported: str
    rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class Palette:
    key: str
    name: str
    kind: str  # pixel | semantic | rarity
    size: int
    colors: tuple[str, ...]
    color_names: tuple[str, ...] = ()
    notes: str = ""
    source: str = ""
    mapping: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Tier:
    key: str
    name: str
    summary: str
    precision: str
    scale: str


@dataclass(frozen=True)
class ItemGroup:
    key: str
    name: str
    share: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    visual: str
    examples: str


@dataclass
class DesignSystem:
    styles: tuple[ArtStyle, ...] = ()
    palettes: tuple[Palette, ...] = ()
    tiers: tuple[Tier, ...] = ()
    item_groups: tuple[ItemGroup, ...] = ()
    themes: tuple[Theme, ...] = ()

    def find_style(self, key: str | None) -> ArtStyle | None:
        if not key:
            return None
        for style in self.styles:
            if style.key == key:
                return style
        raise DesignError(f"未知画法风格 {key!r}，可选: {', '.join(s.key for s in self.styles)}")

    def find_palette(self, key: str | None) -> Palette | None:
        if not key:
            return None
        for palette in self.palettes:
            if palette.key == key:
                return palette
        raise DesignError(f"未知色板 {key!r}，可选: {', '.join(p.key for p in self.palettes)}")

    def counts(self) -> dict[str, int]:
        return {
            "styles": len(self.styles),
            "palettes": len(self.palettes),
            "tiers": len(self.tiers),
            "item_groups": len(self.item_groups),
            "themes": len(self.themes),
        }


def _hex(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _HEX_RE.match(value.strip()):
        raise DesignError(f"{where} 必须是 #rrggbb 颜色，收到 {value!r}")
    return value.strip().lower()


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DesignError(f"{path.name}: 无法读取或解析 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DesignError(f"{path.name}: 顶层必须是对象")
    return data


def _load_styles(path: Path) -> tuple[ArtStyle, ...]:
    data = _load_json(path)
    raw = data.get("styles")
    if not isinstance(raw, list) or not raw:
        raise DesignError(f"{path.name}: styles 必须是非空数组")
    styles: list[ArtStyle] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise DesignError(f"{path.name}: style 必须是对象")
        key = str(entry.get("key") or "").strip()
        name = str(entry.get("name") or "").strip()
        if not key or not name:
            raise DesignError(f"{path.name}: style 缺少 key/name")
        supported = str(entry.get("supported") or "partial")
        if supported not in _SUPPORT_LABELS:
            raise DesignError(f"{path.name}: {key} 的 supported 必须是 full/partial/future")
        try:
            difficulty = int(entry.get("difficulty") or 3)
        except (TypeError, ValueError) as exc:
            raise DesignError(f"{path.name}: {key} 的 difficulty 必须是 1~5") from exc
        if not 1 <= difficulty <= 5:
            raise DesignError(f"{path.name}: {key} 的 difficulty 必须是 1~5")
        rules = entry.get("rules") or []
        if not isinstance(rules, list):
            raise DesignError(f"{path.name}: {key} 的 rules 必须是数组")
        styles.append(
            ArtStyle(
                key=key,
                name=name,
                visual=str(entry.get("visual") or ""),
                best_for=str(entry.get("best_for") or ""),
                examples=str(entry.get("examples") or ""),
                difficulty=difficulty,
                difficulty_label=str(entry.get("difficulty_label") or f"{difficulty}/5"),
                supported=supported,
                rules=tuple(str(rule) for rule in rules),
            )
        )
    return tuple(styles)


def _load_palettes(path: Path) -> tuple[Palette, ...]:
    data = _load_json(path)
    raw = data.get("palettes")
    if not isinstance(raw, list) or not raw:
        raise DesignError(f"{path.name}: palettes 必须是非空数组")
    palettes: list[Palette] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise DesignError(f"{path.name}: palette 必须是对象")
        key = str(entry.get("key") or "").strip()
        name = str(entry.get("name") or "").strip()
        if not key or not name:
            raise DesignError(f"{path.name}: palette 缺少 key/name")
        colors = entry.get("colors")
        if not isinstance(colors, list) or not colors:
            raise DesignError(f"{path.name}: {key} 的 colors 必须是非空数组")
        colors = tuple(_hex(color, f"{path.name}:{key}") for color in colors)
        try:
            size = int(entry.get("size") or len(colors))
        except (TypeError, ValueError) as exc:
            raise DesignError(f"{path.name}: {key} 的 size 必须是整数") from exc
        if size != len(colors):
            raise DesignError(f"{path.name}: {key} 的 size={size} 与颜色数 {len(colors)} 不一致")
        names = entry.get("color_names") or []
        if not isinstance(names, list):
            raise DesignError(f"{path.name}: {key} 的 color_names 必须是数组")
        if names and len(names) != len(colors):
            raise DesignError(f"{path.name}: {key} 的 color_names 数量与 colors 不一致")
        mapping = entry.get("mapping") or {}
        if not isinstance(mapping, dict):
            raise DesignError(f"{path.name}: {key} 的 mapping 必须是对象")
        palettes.append(
            Palette(
                key=key,
                name=name,
                kind=str(entry.get("kind") or "pixel"),
                size=size,
                colors=colors,
                color_names=tuple(str(item) for item in names),
                notes=str(entry.get("notes") or ""),
                source=str(entry.get("source") or ""),
                mapping={k: _hex(v, f"{path.name}:{key}.{k}") for k, v in mapping.items()},
            )
        )
    return tuple(palettes)


def _load_taxonomy(path: Path) -> tuple[tuple[Tier, ...], tuple[ItemGroup, ...], tuple[Theme, ...]]:
    data = _load_json(path)
    tiers = tuple(
        Tier(
            key=str(entry.get("key") or ""),
            name=str(entry.get("name") or ""),
            summary=str(entry.get("summary") or ""),
            precision=str(entry.get("precision") or ""),
            scale=str(entry.get("scale") or ""),
        )
        for entry in data.get("tiers") or []
        if isinstance(entry, dict) and entry.get("key")
    )
    groups = tuple(
        ItemGroup(
            key=str(entry.get("key") or ""),
            name=str(entry.get("name") or ""),
            share=str(entry.get("share") or ""),
            items=tuple(str(item) for item in entry.get("items") or []),
        )
        for entry in data.get("item_groups") or []
        if isinstance(entry, dict) and entry.get("key")
    )
    themes = tuple(
        Theme(
            key=str(entry.get("key") or ""),
            name=str(entry.get("name") or ""),
            visual=str(entry.get("visual") or ""),
            examples=str(entry.get("examples") or ""),
        )
        for entry in data.get("themes") or []
        if isinstance(entry, dict) and entry.get("key")
    )
    return tiers, groups, themes


def load_design_system(directory: str | Path | None = None) -> DesignSystem:
    """加载 styles.json / palettes.json / taxonomy.json；缺文件时对应部分为空。"""
    if directory is None:
        directory = Path.cwd() / "catalog"
    path = Path(directory)
    if not path.is_dir():
        raise DesignError(f"目录不存在: {path}")

    styles_path = path / "styles.json"
    palettes_path = path / "palettes.json"
    taxonomy_path = path / "taxonomy.json"
    styles = _load_styles(styles_path) if styles_path.is_file() else ()
    palettes = _load_palettes(palettes_path) if palettes_path.is_file() else ()
    if taxonomy_path.is_file():
        tiers, groups, themes = _load_taxonomy(taxonomy_path)
    else:
        tiers, groups, themes = (), (), ()
    if not (styles or palettes or tiers):
        raise DesignError(f"{path} 下没有 styles.json / palettes.json / taxonomy.json")
    return DesignSystem(
        styles=styles,
        palettes=palettes,
        tiers=tiers,
        item_groups=groups,
        themes=themes,
    )


def _support_label(style: ArtStyle) -> str:
    return _SUPPORT_LABELS.get(style.supported, style.supported)


def _style_section(style: ArtStyle) -> str:
    lines = [
        f"### 当前画法：{style.name}",
        "",
        f"- 视觉特征：{style.visual}",
        f"- 适用场景：{style.best_for}",
        f"- 代表作品：{style.examples}",
        f"- LLM 生成难度：{style.difficulty_label}（{style.difficulty}/5）",
        f"- 本项目支持：{_support_label(style)}",
        "",
        "规则：",
        "",
    ]
    lines.extend(f"{index}. {rule}" for index, rule in enumerate(style.rules, start=1))
    return "\n".join(lines)


def _palette_section(palette: Palette) -> str:
    lines = [
        f"### 当前色板：{palette.name}",
        "",
        f"- 类型：{palette.kind}，共 {palette.size} 色",
        f"- 来源：{palette.source}",
        f"- 说明：{palette.notes}",
        "",
    ]
    if palette.color_names:
        rows = ["| 用途 | 颜色 |", "|---|---|"]
        rows.extend(
            f"| {name} | `{color}` |" for name, color in zip(palette.color_names, palette.colors)
        )
        lines.extend(rows)
    else:
        lines.append("色值：" + " ".join(f"`{color}`" for color in palette.colors))
    if palette.mapping:
        lines.append("")
        lines.append("本项目 5 档稀有度映射：")
        lines.append("")
        lines.append("| data-rarity | 颜色 |")
        lines.append("|---|---|")
        lines.extend(f"| `{key}` | `{color}` |" for key, color in palette.mapping.items())
    return "\n".join(lines)


def design_markdown(
    system: DesignSystem,
    art_style: str | None = None,
    palette: str | None = None,
) -> str:
    """生成「风格、色板与分类学」章节正文（不含顶级编号）。"""
    current_style = system.find_style(art_style)
    current_palette = system.find_palette(palette)
    blocks: list[str] = []

    if system.styles:
        blocks.append("### 画法风格光谱")
        blocks.append("")
        blocks.append("| 风格 | 视觉特征 | 适用场景 | LLM 难度 | 本项目支持 |")
        blocks.append("|---|---|---|---|---|")
        for style in system.styles:
            blocks.append(
                f"| {style.name}（`{style.key}`） | {style.visual} | {style.best_for} | "
                f"{style.difficulty_label} | {_support_label(style)} |"
            )
        blocks.append("")
        selected = current_style or system.find_style("pixel") or system.styles[0]
        blocks.append(_style_section(selected))

    if system.palettes:
        blocks.append("")
        blocks.append("### 色板库")
        blocks.append("")
        blocks.append("| 色板 | 色数 | 类型 | 特点 |")
        blocks.append("|---|---|---|---|")
        for item in system.palettes:
            blocks.append(
                f"| {item.name}（`{item.key}`） | {item.size} | {item.kind} | {item.notes} |"
            )
        if current_palette:
            blocks.append("")
            blocks.append(_palette_section(current_palette))

        rarity = next((item for item in system.palettes if item.kind == "rarity"), None)
        if rarity:
            blocks.append("")
            blocks.append("### 稀有度色阶（行业惯例）")
            blocks.append("")
            blocks.append("| 档位 | 颜色 |")
            blocks.append("|---|---|")
            for name, color in zip(rarity.color_names or tuple(), rarity.colors):
                blocks.append(f"| {name} | `{color}` |")
            if rarity.mapping:
                blocks.append("")
                blocks.append("本项目 `data-rarity` 映射：")
                blocks.append("")
                blocks.append("| data-rarity | 颜色 |")
                blocks.append("|---|---|")
                blocks.extend(f"| `{key}` | `{color}` |" for key, color in rarity.mapping.items())

    if system.tiers:
        blocks.append("")
        blocks.append("### 功能层级")
        blocks.append("")
        blocks.append("| 类别 | 说明 | 精度 | 数量级 |")
        blocks.append("|---|---|---|---|")
        for tier in system.tiers:
            blocks.append(f"| {tier.name} | {tier.summary} | {tier.precision} | {tier.scale} |")

    if system.item_groups:
        blocks.append("")
        blocks.append("### 道具八大类")
        blocks.append("")
        blocks.append("| 大类 | 数量占比 | 子类清单 |")
        blocks.append("|---|---|---|")
        for group in system.item_groups:
            blocks.append(f"| {group.name} | {group.share} | {'、'.join(group.items)} |")

    if system.themes:
        blocks.append("")
        blocks.append("### 题材流派")
        blocks.append("")
        blocks.append("| 流派 | 视觉关键词 | 代表 |")
        blocks.append("|---|---|---|")
        for theme in system.themes:
            blocks.append(f"| {theme.name} | {theme.visual} | {theme.examples} |")

    return "\n".join(blocks).strip()
