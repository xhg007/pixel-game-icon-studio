"""图标风格预设：配色、材质阶与风格规则，供 AGENTS.md 与 MCP 共用。"""

from __future__ import annotations

from dataclasses import dataclass

MATERIAL_LABELS: dict[str, str] = {
    "neutral": "中性色",
    "metal": "金属",
    "gold": "金色",
    "wood": "木头",
    "glass": "玻璃",
    "stone": "石材",
    "cloth": "布料",
    "paper": "纸张",
    "leather": "皮革",
}

POTION_LABELS: dict[str, str] = {
    "red": "红 / 生命",
    "green": "绿 / 自然",
    "blue": "蓝 / 法力",
    "purple": "紫 / 奥术",
}


@dataclass(frozen=True)
class StylePreset:
    key: str
    name: str
    summary: str
    mood: str
    outline_warm: str
    outline_cool: str
    materials: dict[str, tuple[str, str, str]]
    potions: dict[str, str]
    rarity: dict[str, str]
    rules: tuple[str, ...]

    def material_rows(self) -> list[tuple[str, str, str, str]]:
        """返回 (中文名, 亮部, 中色, 暗部) 行，按固定顺序。"""
        return [
            (MATERIAL_LABELS[key], *self.materials[key])
            for key in MATERIAL_LABELS
            if key in self.materials
        ]


STYLES: dict[str, StylePreset] = {
    "classic": StylePreset(
        key="classic",
        name="经典 16-bit 奇幻",
        summary="温暖、饱和、轮廓清晰，最接近 90 年代 16-bit RPG 道具栏。",
        mood="冒险、手绘感、暖光",
        outline_warm="#2e1f10",
        outline_cool="#1c1c24",
        materials={
            "neutral": ("#e8e2d4", "#9a9488", "#4a463e"),
            "metal": ("#eef2f8", "#8d99ad", "#4a4f5c"),
            "gold": ("#fff3c4", "#f0b23e", "#a87712"),
            "wood": ("#c98d4b", "#8f5a2a", "#5a3617"),
            "glass": ("#d8ecec", "#9db8bb", "#5f7477"),
            "stone": ("#d8d4c8", "#9a968a", "#5c5a52"),
            "cloth": ("#e58a7a", "#b04a42", "#6e2a28"),
            "paper": ("#fff3d6", "#e8d9b5", "#b8a173"),
            "leather": ("#d0a06a", "#9a6432", "#5c3a18"),
        },
        potions={
            "red": "#e8433f",
            "green": "#4ce88e",
            "blue": "#3f74e0",
            "purple": "#a06ae8",
        },
        rarity={
            "common": "#c8c8c8",
            "fine": "#63d66e",
            "rare": "#5aa9e6",
            "epic": "#b874e8",
            "legend": "#f0a13a",
        },
        rules=(
            "暖色物体（木、皮、纸）用暖轮廓 #2e1f10；冷色物体（金属、玻璃）用冷轮廓 #1c1c24。",
            "亮部约占主体 25%，集中在左上 1~2 行；暗部约占 25%，压在右下。",
            "高光用同色系最亮阶，单点高光必须成对出现，避免噪点。",
        ),
    ),
    "dark-fantasy": StylePreset(
        key="dark-fantasy",
        name="暗黑奇幻",
        summary="低饱和、冷紫阴影、铁灰金属，适合魂系与暗黑地牢题材。",
        mood="压抑、古老、低照度",
        outline_warm="#1a1410",
        outline_cool="#0e1016",
        materials={
            "neutral": ("#cfd3d8", "#7c828c", "#3a3e46"),
            "metal": ("#d9dee8", "#7f8798", "#3c4250"),
            "gold": ("#e8d08a", "#b08a3a", "#6a4c12"),
            "wood": ("#8a6240", "#5c3f28", "#33231a"),
            "glass": ("#a8c4c8", "#6a878c", "#37494c"),
            "stone": ("#b8b6ae", "#787670", "#41403c"),
            "cloth": ("#8a5a6a", "#5c3644", "#2f1c24"),
            "paper": ("#d8cbb0", "#b09e80", "#6e6048"),
            "leather": ("#8a6440", "#5c4028", "#33241a"),
        },
        potions={
            "red": "#c93a4a",
            "green": "#3fae7a",
            "blue": "#3a6ac9",
            "purple": "#8a5ac9",
        },
        rarity={
            "common": "#9aa0a8",
            "fine": "#4fae6a",
            "rare": "#4a86c9",
            "epic": "#9a6ad0",
            "legend": "#c9973a",
        },
        rules=(
            "整体明度压低，亮部不超过主体 15%，暗部可占 35%；禁止纯黑 #000000。",
            "阴影偏冷紫：主色暗阶向 #2a2038 靠，而不是简单加黑。",
            "轮廓可以融入暗部，但主体与背景的剪影边界必须保持 1px 可辨。",
        ),
    ),
    "pastel": StylePreset(
        key="pastel",
        name="明亮柔和",
        summary="高明度、低对比、无纯黑轮廓，适合休闲、模拟经营与合家欢题材。",
        mood="轻松、治愈、柔和",
        outline_warm="#5a4038",
        outline_cool="#38404e",
        materials={
            "neutral": ("#fffdf8", "#d8d2c8", "#8a847c"),
            "metal": ("#f2f6fb", "#c3ccd9", "#8a95a6"),
            "gold": ("#fff2c8", "#f4cf7a", "#c49a3a"),
            "wood": ("#e2b98a", "#c08a5a", "#8a5c38"),
            "glass": ("#e8f6f4", "#b9d8d4", "#82a8a4"),
            "stone": ("#f0eee8", "#c8c4ba", "#969188"),
            "cloth": ("#f4b6b0", "#d98a86", "#a85c5c"),
            "paper": ("#fffdf0", "#f2e8cc", "#cbbd9a"),
            "leather": ("#e0b890", "#b88a60", "#8a6240"),
        },
        potions={
            "red": "#f27a7a",
            "green": "#6fd9a0",
            "blue": "#6fa8f2",
            "purple": "#b98af2",
        },
        rarity={
            "common": "#c8c8c8",
            "fine": "#6fd99a",
            "rare": "#6fb0f2",
            "epic": "#c39af2",
            "legend": "#f2b86a",
        },
        rules=(
            "轮廓不用纯黑，用比暗部再深一阶的彩色；轮廓对比度不超过金属暗阶。",
            "亮部可以放大到 30%，并允许相邻两阶过渡，整体对比度保持柔和。",
            "避免高饱和纯色大面积铺底；主色尽量落在 60%~80% 明度。",
        ),
    ),
    "neon": StylePreset(
        key="neon",
        name="赛博霓虹",
        summary="深底、高饱和、冷白高光，适合科幻、赛博朋克与节奏游戏。",
        mood="锋利、电子、发光",
        outline_warm="#141018",
        outline_cool="#0a1018",
        materials={
            "neutral": ("#e8f8ff", "#8aa8b8", "#2a3a48"),
            "metal": ("#d8f8ff", "#7aa8b8", "#2a4858"),
            "gold": ("#fff8c8", "#f8d84a", "#b8901a"),
            "wood": ("#a86a4a", "#6a3a28", "#2a1810"),
            "glass": ("#b8fcff", "#5ad8e8", "#1a6a78"),
            "stone": ("#b8c8d0", "#6a7a88", "#2a3640"),
            "cloth": ("#ff8ad8", "#c84aa8", "#6a1a58"),
            "paper": ("#f8f0ff", "#d8c8e8", "#8a7aa8"),
            "leather": ("#c88a5a", "#8a5a38", "#3a2418"),
        },
        potions={
            "red": "#ff4a6a",
            "green": "#4affa8",
            "blue": "#4a9aff",
            "purple": "#c86aff",
        },
        rarity={
            "common": "#b8c8d0",
            "fine": "#4affa8",
            "rare": "#4ac8ff",
            "epic": "#c86aff",
            "legend": "#ffd84a",
        },
        rules=(
            "高光统一用冷白（偏青），不要用暖白；暗部压到近黑但保留色相。",
            "用 1px 邻近亮色模拟发光边，禁止 filter / 渐变 / 半透明叠加。",
            "同一图标最多 2 个高饱和主色，其余用中性色托底，防止糊成一片。",
        ),
    ),
}

DEFAULT_STYLE = "classic"


def get_style(key: str | None = None) -> StylePreset:
    """按 key 取风格预设，未知 key 抛出带可选值的 ValueError。"""
    name = (key or DEFAULT_STYLE).strip().lower()
    if name not in STYLES:
        options = " / ".join(STYLES)
        raise ValueError(f"未知风格 {key!r}，可选: {options}")
    return STYLES[name]


def style_names() -> list[str]:
    return list(STYLES)
