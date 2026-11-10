"""图标目录：加载 catalog/*.json，校验、检索、导出 Markdown / CSV。"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .svg import RARITIES

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

#: 分类 -> (剪影公式, 建议占比, 关键像素, 常见失败)
CATEGORY_RULES: dict[str, tuple[str, str, str, str]] = {
    "potion": ("瓶塞 + 瓶颈 + 圆肚瓶身", "高 12~13 行，宽 6~8 格", "塞子 4 格宽、瓶颈 2 格宽、液面留 1 行高光", "瓶颈与瓶身断开、液面缺失、瓶底溢出轮廓"),
    "weapon_melee": ("刃 + 护手 + 握柄 + 柄头", "高 13~14 行，刃宽 3~4 格", "刃尖 1-2-2 阶梯、护手 8~10 格、握柄 2 格宽", "刃身过宽、护手与刃同色、柄头缺失"),
    "weapon_ranged": ("弓臂 + 弦 / 弩臂 + 托柄 / 弹体", "主体 10~12 格", "弧形用 1px 阶梯、弓弦 1px、弹药独立可辨", "弧形用宽 rect 伪造、弹药与武器粘连"),
    "armor": ("上宽下尖的盾面 / 头盔 + 面甲 / 可穿戴肩线", "顶部 10~12 格，底部收成 2 格", "左右各收 1 格、徽记 4×4、边缘 1px 包边", "四角收太快像菱形、徽记贴边、左右不对称"),
    "material": ("材质块面 + 矿脉 / 切面 / 纹理", "主体 8×8 以上", "切面 2~3 个、纹理 1px、同类材料统一轮廓", "糊成纯色块、纹理过密、材质不可辨"),
    "currency": ("圆形 / 菱形剪影 + 中心符号", "直径 10~12 格，留 2 格边距", "圆用 2-4-10-12 阶梯、中心符号 4×4", "圆角变方、中心符号糊成实心、边缘抖动"),
    "food": ("主体块面 + 骨 / 叶 / 签等识别物", "主体 8×8 以上，识别物伸出 3~4 格", "受光面在上、焦痕用暗部点缀、识别物与主体相接", "识别物悬空、主体纯圆、暗部盖满"),
    "quest": ("环 + 柄 + 齿 / 卷边 + 封蜡", "总长 12~14 格，环直径 6~7 格", "环内孔 3×4、柄高 2~3 格、齿向下凸 2 格", "环是实心圆、齿与柄同高、内孔太小"),
    "magic": ("环 / 链 / 杖 + 宝石 / 符文", "主体 10~12 格", "宝石嵌在环顶、链 1px 断续、内孔保持透明", "宝石分离、内孔太小、链环断开"),
    "tool": ("握持部分 + 工作部分", "主体 10~12 格", "工作部分 3~4 格、柄 2 格、两者必须可区分", "整体糊成一根、工作部分过小"),
    "navigation": ("箭头 / 屋顶 / 三条线 / 圆环", "主体 10~12 格", "线宽 2px、箭头尖端 1px 阶梯、内孔透明", "箭头钝头、图标贴边、线条粗细不一"),
    "action": ("符号 + 容器（加号 / 磁盘 / 箭头）", "主体 10~12 格", "符号至少 4×4、容器与符号颜色区分", "符号过小、符号与容器同色、语义混淆"),
    "state": ("形状 + 符号（圆 / 三角 / 方框 + 勾叉叹号）", "主体 10~12 格", "符号线宽 2px、形状本身可区分状态", "只靠颜色区分、符号糊成一团"),
    "media": ("三角 / 双竖线 / 方块 / 喇叭", "主体 8~10 格", "正立可辨、线宽 2px、不使用文字", "图形倾斜、用文字代替、声波缺失"),
    "social": ("头 + 肩 / 气泡 + 尾巴 / 心形 / 节点", "主体 10~12 格", "头部 6×6、气泡尾巴在左下、节点 3×3", "人物无肩线、气泡尾巴缺失、节点悬空"),
    "settings": ("齿轮 / 漏斗 / 双箭头 / 日历 / 时钟", "主体 10~12 格", "齿轮 8 齿、中心孔 4×4、机械特征可辨", "简化成抽象块、齿距不均、中心孔缺失"),
    "commerce": ("车篮 + 轮 / 包体 + 提手 / 礼盒 + 缎带 / 票券", "主体 10~12 格", "轮子 2×2、缎带十字贯穿、票券缺口 2 个", "交易语义丢失、轮子贴边、缎带断裂"),
    "file": ("矩形 + 折角 / 文件夹凸舌 / 山峰 / 链环", "主体 10~12 格", "折角 3×3、凸舌偏左 3 格、链环重叠 1 格", "折角过大、凸舌居中、链环断开"),
}

DEFAULT_CATEGORY_RULE = (
    "先保证 32px 下剪影可辨，再补 2×2 以上的内部细节",
    "主体占 10~12 格，四周留 1 格",
    "1px 轮廓、左上受光、同行同色合并",
    "主体过小、细节过碎、轮廓缺失",
)


#: 文档模板：决定注入哪些目录
TEMPLATES: dict[str, dict] = {
    "full": {"label": "完整版（物品 + UI）", "kinds": ("items", "ui")},
    "items": {"label": "物品图标版", "kinds": ("items",)},
    "ui": {"label": "UI 交互图标版", "kinds": ("ui",)},
    "spec": {"label": "纯规范版（不含目录）", "kinds": ()},
}


class CatalogError(ValueError):
    """目录 JSON 不合法。"""


@dataclass(frozen=True)
class CatalogIcon:
    slug: str
    name: str
    kind: str
    category: str
    category_name: str
    silhouette: str = ""
    palette: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    rarity: str | None = None
    notes: str = ""

    def matches(self, query: str) -> bool:
        needle = query.strip().lower()
        if not needle:
            return True
        haystack = " ".join(
            [self.slug, self.name, self.category_name, self.silhouette, self.notes, *self.keywords]
        ).lower()
        return needle in haystack


@dataclass(frozen=True)
class CatalogCategory:
    key: str
    name: str
    description: str
    icons: tuple[CatalogIcon, ...]


@dataclass(frozen=True)
class CatalogFile:
    kind: str
    title: str
    description: str
    path: Path
    categories: tuple[CatalogCategory, ...]

    @property
    def icons(self) -> list[CatalogIcon]:
        return [icon for category in self.categories for icon in category.icons]


@dataclass
class Catalog:
    files: tuple[CatalogFile, ...] = field(default_factory=tuple)

    @property
    def icons(self) -> list[CatalogIcon]:
        return [icon for catalog_file in self.files for icon in catalog_file.icons]

    def kinds(self) -> list[str]:
        return [catalog_file.kind for catalog_file in self.files]

    def counts(self) -> dict[str, int]:
        return {catalog_file.kind: len(catalog_file.icons) for catalog_file in self.files}

    def find(
        self,
        kinds: Iterable[str] | None = None,
        category: str | None = None,
        query: str | None = None,
    ) -> list[CatalogIcon]:
        allowed = set(kinds) if kinds is not None else None
        result: list[CatalogIcon] = []
        for icon in self.icons:
            if allowed is not None and icon.kind not in allowed:
                continue
            if category and icon.category != category:
                continue
            if query and not icon.matches(query):
                continue
            result.append(icon)
        return result

    def markdown(self, kinds: Iterable[str] | None = None, detail: str = "full") -> str:
        """生成目录章节正文（不含顶级编号，供 AGENTS.md 注入）。"""
        allowed = set(kinds) if kinds is not None else None
        blocks: list[str] = []
        for catalog_file in self.files:
            if allowed is not None and catalog_file.kind not in allowed:
                continue
            blocks.append(f"### {catalog_file.title}")
            blocks.append("")
            blocks.append(catalog_file.description)
            for category in catalog_file.categories:
                blocks.append("")
                blocks.append(f"#### {category.name}")
                blocks.append("")
                if category.description:
                    blocks.append(category.description)
                    blocks.append("")
                if detail == "compact":
                    names = "、".join(f"{icon.name}（`{icon.slug}`）" for icon in category.icons)
                    blocks.append(names)
                    continue
                blocks.append("| slug | 中文名 | 稀有度 | 亮 / 中 / 暗 | 剪影 |")
                blocks.append("|---|---|---|---|---|")
                for icon in category.icons:
                    rarity = icon.rarity or "-"
                    palette = " / ".join(f"`{color}`" for color in icon.palette) or "-"
                    blocks.append(
                        f"| `{icon.slug}` | {icon.name} | {rarity} | {palette} | {icon.silhouette} |"
                    )
        return "\n".join(blocks).strip()

    def blueprint_markdown(
        self, kinds: Iterable[str] | None = None, detail: str = "full"
    ) -> str:
        """按 catalog 分类生成蓝图。

        ``detail=full`` 列出每类必须生成的全部 slug（AGENTS.md 用）；
        ``detail=compact`` 只给规则与数量，slug 清单交给「图标目录」（技能清单用）。
        """
        allowed = set(kinds) if kinds is not None else None
        blocks: list[str] = []
        for catalog_file in self.files:
            if allowed is not None and catalog_file.kind not in allowed:
                continue
            blocks.append(f"### {catalog_file.title}")
            blocks.append("")
            blocks.append(catalog_file.description)
            for category in catalog_file.categories:
                silhouette, scale, pixels, failure = CATEGORY_RULES.get(
                    category.key, DEFAULT_CATEGORY_RULE
                )
                blocks.append("")
                blocks.append(f"#### {category.name}（{len(category.icons)} 个）")
                blocks.append("")
                blocks.append(f"- 剪影：{silhouette}")
                blocks.append(f"- 占比：{scale}")
                blocks.append(f"- 关键像素：{pixels}")
                blocks.append(f"- 失败模式：{failure}")
                if detail == "compact":
                    blocks.append(
                        f"- 条目：{len(category.icons)} 个（完整 slug 见「图标目录」）"
                    )
                else:
                    blocks.append(
                        "- 必须生成："
                        + "、".join(
                            f"{icon.name}（`{icon.slug}`）" for icon in category.icons
                        )
                    )
        return "\n".join(blocks).strip()

    def csv(self, kinds: Iterable[str] | None = None) -> str:
        """导出扁平 CSV，便于表格软件编辑。"""
        allowed = set(kinds) if kinds is not None else None
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(
            ["kind", "category", "category_name", "slug", "name", "rarity",
             "keywords", "silhouette", "palette", "notes"]
        )
        for icon in self.icons:
            if allowed is not None and icon.kind not in allowed:
                continue
            writer.writerow(
                [
                    icon.kind,
                    icon.category,
                    icon.category_name,
                    icon.slug,
                    icon.name,
                    icon.rarity or "",
                    " ".join(icon.keywords),
                    icon.silhouette,
                    " ".join(icon.palette),
                    icon.notes,
                ]
            )
        return buffer.getvalue()


def _hex(value: object, where: str) -> str:
    if not isinstance(value, str) or not _HEX_RE.match(value.strip()):
        raise CatalogError(f"{where} 必须是 #rrggbb 颜色，收到 {value!r}")
    return value.strip().lower()


def _load_file(path: Path) -> CatalogFile:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"{path.name}: 无法读取或解析 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CatalogError(f"{path.name}: 顶层必须是对象")

    kind = str(data.get("kind") or "").strip()
    if not kind:
        raise CatalogError(f"{path.name}: 缺少 kind")
    title = str(data.get("title") or kind)
    description = str(data.get("description") or "")
    raw_categories = data.get("categories")
    if not isinstance(raw_categories, list) or not raw_categories:
        raise CatalogError(f"{path.name}: categories 必须是非空数组")

    categories: list[CatalogCategory] = []
    for raw_category in raw_categories:
        if not isinstance(raw_category, dict):
            raise CatalogError(f"{path.name}: category 必须是对象")
        key = str(raw_category.get("key") or "").strip()
        name = str(raw_category.get("name") or "").strip()
        if not key or not name:
            raise CatalogError(f"{path.name}: category 缺少 key 或 name")
        raw_icons = raw_category.get("icons")
        if not isinstance(raw_icons, list) or not raw_icons:
            raise CatalogError(f"{path.name}: 分类 {key} 的 icons 必须是非空数组")

        icons: list[CatalogIcon] = []
        for raw_icon in raw_icons:
            if not isinstance(raw_icon, dict):
                raise CatalogError(f"{path.name}: {key} 下的图标必须是对象")
            slug = str(raw_icon.get("slug") or "").strip()
            icon_name = str(raw_icon.get("name") or "").strip()
            if not slug or not icon_name:
                raise CatalogError(f"{path.name}: {key} 下存在缺少 slug/name 的图标")
            palette = raw_icon.get("palette") or []
            if not isinstance(palette, list) or len(palette) != 3:
                raise CatalogError(f"{path.name}: {slug} 需要 3 个颜色（亮/中/暗）")
            rarity = raw_icon.get("rarity")
            if rarity is not None:
                rarity = str(rarity).strip().lower()
                if rarity not in RARITIES:
                    raise CatalogError(f"{path.name}: {slug} 的 rarity={rarity!r} 不合法")
            keywords = raw_icon.get("keywords") or []
            if not isinstance(keywords, list):
                raise CatalogError(f"{path.name}: {slug} 的 keywords 必须是数组")
            icons.append(
                CatalogIcon(
                    slug=slug,
                    name=icon_name,
                    kind=kind,
                    category=key,
                    category_name=name,
                    silhouette=str(raw_icon.get("silhouette") or ""),
                    palette=tuple(_hex(color, f"{path.name}:{slug}") for color in palette),
                    keywords=tuple(str(word) for word in keywords),
                    rarity=rarity,
                    notes=str(raw_icon.get("notes") or ""),
                )
            )
        categories.append(
            CatalogCategory(
                key=key,
                name=name,
                description=str(raw_category.get("description") or ""),
                icons=tuple(icons),
            )
        )
    return CatalogFile(
        kind=kind,
        title=title,
        description=description,
        path=path,
        categories=tuple(categories),
    )


def _looks_like_catalog(path: Path) -> bool:
    """图标目录必须含 categories；设计库（styles/palettes/taxonomy）会被跳过。

    JSON 损坏时返回 True，交给 `_load_file` 抛出带文件名的错误。
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True
    except OSError:
        return True
    return isinstance(data, dict) and isinstance(data.get("categories"), list)


def load_catalog(
    directory: str | Path | None = None,
    kinds: Iterable[str] | None = None,
) -> Catalog:
    """加载目录文件；``directory`` 可以是目录或单个 JSON 文件。"""
    if directory is None:
        directory = Path.cwd() / "catalog"
    path = Path(directory)
    if path.is_file():
        paths = [path]
    elif path.is_dir():
        paths = [item for item in sorted(path.glob("*.json")) if _looks_like_catalog(item)]
    else:
        raise CatalogError(f"目录不存在: {path}")
    if not paths:
        raise CatalogError(f"{path} 下没有图标目录 JSON（需包含 categories）")

    allowed = set(kinds) if kinds is not None else None
    files: list[CatalogFile] = []
    seen: set[str] = set()
    for item in paths:
        catalog_file = _load_file(item)
        if allowed is not None and catalog_file.kind not in allowed:
            continue
        for icon in catalog_file.icons:
            if icon.slug in seen:
                raise CatalogError(f"slug 重复: {icon.slug}（{item.name}）")
            seen.add(icon.slug)
        files.append(catalog_file)
    if not files:
        raise CatalogError(f"{path} 下没有匹配的目录文件")
    return Catalog(files=tuple(files))


def kinds_for_template(template: str | None) -> tuple[str, ...]:
    key = (template or "full").strip().lower()
    if key not in TEMPLATES:
        raise CatalogError(f"未知模板 {template!r}，可选: {', '.join(TEMPLATES)}")
    return tuple(TEMPLATES[key]["kinds"])
