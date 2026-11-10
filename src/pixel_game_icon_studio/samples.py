"""10 个内置示例图标：像素行数据 -> 规范 SVG。

每个图标是一张 16×16 字符网格：
``.`` 表示透明，其余字符在 ``palette`` 中查色。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .svg import CANVAS, SvgError

SLUGS = (
    "potion_healing",
    "potion_mana",
    "sword_iron",
    "shield_mercenary",
    "coin_gold",
    "key_brass",
    "scroll_ancient",
    "gem_emerald",
    "meat_roast",
    "ring_of_embers",
)


@dataclass(frozen=True)
class IconSpec:
    name: str
    rarity: str
    palette: dict[str, str]
    rows: tuple[str, ...]


ICONS: dict[str, IconSpec] = {
    "potion_healing": IconSpec(
        name="治疗药水",
        rarity="common",
        palette={
            "o": "#2e1f10",
            "g": "#e8433f",
            "G": "#ff7a6e",
            "D": "#a32b2a",
            "w": "#8f5a2a",
            "W": "#c98d4b",
            "x": "#ffe9d6",
        },
        rows=(
            "................",
            "......oooo......",
            "......oWWo......",
            "......owwo......",
            ".....o....o.....",
            "....o......o....",
            "...oGggggggDo...",
            "...oGggggggDo...",
            "...oGxxggggDo...",
            "...oGggggggDo...",
            "...oGggggggDo...",
            "...oGggggggDo...",
            "....oDDDDDDo....",
            ".....oooooo.....",
            "................",
            "................",
        ),
    ),
    "potion_mana": IconSpec(
        name="法力药水",
        rarity="rare",
        palette={
            "o": "#1c1c24",
            "g": "#3f74e0",
            "G": "#79a6ff",
            "D": "#274a9c",
            "w": "#5f7477",
            "W": "#9db8bb",
            "x": "#d8ecec",
        },
        rows=(
            "................",
            "......oooo......",
            "......oWWo......",
            "......owwo......",
            ".....o....o.....",
            "....o......o....",
            "...oGggggggDo...",
            "...oGggggggDo...",
            "...oGxxggggDo...",
            "...oGggggggDo...",
            "...oGggggggDo...",
            "...oGggggggDo...",
            "....oDDDDDDo....",
            ".....oooooo.....",
            "................",
            "................",
        ),
    ),
    "sword_iron": IconSpec(
        name="铁剑",
        rarity="common",
        palette={
            "o": "#1c1c24",
            "x": "#eef2f8",
            "g": "#8d99ad",
            "D": "#4a4f5c",
            "S": "#c98d4b",
            "s": "#8f5a2a",
            "Y": "#f0b23e",
        },
        rows=(
            "................",
            ".......xx.......",
            "......oxxo......",
            ".....oxxgDo.....",
            ".....oxxgDo.....",
            ".....oxxgDo.....",
            ".....oxxgDo.....",
            ".....oxxgDo.....",
            ".....oxxgDo.....",
            ".....oxxgDo.....",
            "...oYYYYYYYYo...",
            "......oSso......",
            "......oSso......",
            "......oSso......",
            ".....oYYYYo.....",
            "......oooo......",
        ),
    ),
    "shield_mercenary": IconSpec(
        name="佣兵盾",
        rarity="fine",
        palette={
            "o": "#1c1c24",
            "g": "#3f7a4a",
            "G": "#63a86b",
            "D": "#27522f",
            "Y": "#f0b23e",
        },
        rows=(
            "................",
            "..oooooooooooo..",
            "..oggggggggggo..",
            "..oGggggggggDo..",
            "..oGgggYYgggDo..",
            "..oGggYYYYggDo..",
            "..oGgggYYgggDo..",
            "..oGggggggggDo..",
            "...oGggggggDo...",
            "...oGggggggDo...",
            "...oGggggggDo...",
            "....oGgggDo.....",
            ".....oGggDo.....",
            "......oooo......",
            "................",
            "................",
        ),
    ),
    "coin_gold": IconSpec(
        name="金币",
        rarity="common",
        palette={
            "o": "#5a3a06",
            "g": "#f0b23e",
            "G": "#ffd77a",
            "D": "#a87712",
            "x": "#fff3c4",
        },
        rows=(
            "................",
            "................",
            ".....oooooo.....",
            "....oGGGGGGo....",
            "...oGggggggDo...",
            "..oGggggggggDo..",
            "..oGggGGGGggDo..",
            "..oGggGxxGggDo..",
            "..oGggGxxGggDo..",
            "..oGggGGGGggDo..",
            "..oGggggggggDo..",
            "...oGggggggDo...",
            "....oGggggDo....",
            ".....oooooo.....",
            "................",
            "................",
        ),
    ),
    "key_brass": IconSpec(
        name="黄铜钥匙",
        rarity="fine",
        palette={
            "o": "#3a2a10",
            "g": "#c98d4b",
            "G": "#e8b06a",
            "D": "#8f5a2a",
        },
        rows=(
            "................",
            "................",
            "................",
            "................",
            "...oooo.........",
            "..oGGGGo........",
            ".oGG...Go.......",
            ".oGG...Gooooooo.",
            ".oGG...GoGGGGGG.",
            ".oGG...Gooooooo.",
            "..oGGGGo...gggg.",
            "...oooo....oooo.",
            "................",
            "................",
            "................",
            "................",
        ),
    ),
    "scroll_ancient": IconSpec(
        name="古老卷轴",
        rarity="rare",
        palette={
            "o": "#5a3a1e",
            "P": "#e8d9b5",
            "W": "#fff3d6",
            "D": "#b8a173",
        },
        rows=(
            "................",
            "...oooooooooo...",
            "..oWWWWWWWWWWo..",
            "..oDDDDDDDDDDo..",
            "...oWPPPPPPDo...",
            "...oWPPPPPPDo...",
            "...oWPDDDDPDDo..",
            "...oWPPPPPPDo...",
            "...oWPDDDDPDDo..",
            "...oWPPPPPPDo...",
            "...oWPDDDDPDDo..",
            "...oWPPPPPPDo...",
            "...oWPPPPPPDo...",
            "..oDDDDDDDDDDo..",
            "..oWWWWWWWWWWo..",
            "...oooooooooo...",
        ),
    ),
    "gem_emerald": IconSpec(
        name="绿宝石",
        rarity="epic",
        palette={
            "o": "#0e2e1c",
            "g": "#2fa36b",
            "G": "#6fe0a8",
            "D": "#166a45",
            "x": "#c8ffe0",
        },
        rows=(
            "................",
            "................",
            "......oooo......",
            ".....oGGGGo.....",
            "....oGGGGGGo....",
            "...oggggggggo...",
            "..oggggggggggo..",
            "..oGgggxxgggDo..",
            "..oGggggggggDo..",
            "...oGggggggDo...",
            "....oGggggDo....",
            ".....oDDDDo.....",
            "......oDDo......",
            ".......oo.......",
            "................",
            "................",
        ),
    ),
    "meat_roast": IconSpec(
        name="烤肉",
        rarity="common",
        palette={
            "o": "#3a1f12",
            "g": "#a85a32",
            "G": "#d08050",
            "D": "#6e351e",
            "b": "#efe6d0",
        },
        rows=(
            "................",
            "...........ooo..",
            "..........obbbo.",
            "..........obbbo.",
            ".........obbbo..",
            ".........obbo...",
            "...ooooooobbo...",
            "..oGGGGGGobbo...",
            ".oGgggggggo.....",
            ".oGgggggggo.....",
            ".oGgggggggo.....",
            ".oGggggggDo.....",
            "..oDDDDDDo......",
            "...oooooo.......",
            "................",
            "................",
        ),
    ),
    "ring_of_embers": IconSpec(
        name="余烬之戒",
        rarity="legend",
        palette={
            "o": "#4a2a06",
            "Y": "#f0b23e",
            "y": "#fff3c4",
            "D": "#a87712",
            "R": "#ff5a3c",
        },
        rows=(
            "................",
            "................",
            ".......oo.......",
            "......oRRo......",
            ".....oRRRRo.....",
            ".....oDDDDo.....",
            "....oooooooo....",
            "...oYYYYYYYYo...",
            "..oyYYYYYYYYo...",
            "..oyY......Yo...",
            "..oyY......Yo...",
            "..oyY......Yo...",
            "..oYYYYYYYYYo...",
            "...oDDDDDDDDo...",
            "....oooooooo....",
            "................",
        ),
    ),
}


def check_spec(slug: str, spec: IconSpec) -> None:
    """检查像素网格结构：16 行 × 16 列，且字符都在调色板中。"""
    if len(spec.rows) != CANVAS:
        raise SvgError(f"{slug}: 需要 {CANVAS} 行，实际 {len(spec.rows)} 行")
    for y, row in enumerate(spec.rows):
        if len(row) != CANVAS:
            raise SvgError(f"{slug}: 第 {y} 行宽度是 {len(row)}，应为 {CANVAS}")
        for char in row:
            if char != "." and char not in spec.palette:
                raise SvgError(f"{slug}: 第 {y} 行出现未定义的颜色字符 {char!r}")


#: 兼容旧名字
_check_spec = check_spec


def rows_to_svg(spec: IconSpec) -> str:
    """把像素行转换成规范 SVG，同一行相邻同色格子合并为一个 rect。"""
    rects: list[str] = []
    for y, row in enumerate(spec.rows):
        x = 0
        while x < len(row):
            char = row[x]
            if char == ".":
                x += 1
                continue
            end = x
            while end < len(row) and row[end] == char:
                end += 1
            rects.append(
                f'  <rect x="{x}" y="{y}" width="{end - x}" height="1" '
                f'fill="{spec.palette[char]}"/>'
            )
            x = end
    palette_note = ", ".join(f"{key}={value}" for key, value in spec.palette.items())
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" '
        'width="16" height="16" shape-rendering="crispEdges" '
        f'data-name="{spec.name}" data-rarity="{spec.rarity}">\n'
        f"  <!-- palette: {palette_note} -->\n"
        + "\n".join(rects)
        + "\n</svg>\n"
    )


def write_samples(out: str | Path = "icons") -> list[Path]:
    """生成全部示例 SVG，返回写入的文件路径。"""
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for slug in SLUGS:
        spec = ICONS[slug]
        check_spec(slug, spec)
        path = out_path / f"{slug}.svg"
        path.write_text(rows_to_svg(spec), encoding="utf-8")
        written.append(path)
    return written
