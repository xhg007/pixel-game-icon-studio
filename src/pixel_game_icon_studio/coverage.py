"""检查 icons/ 是否覆盖 catalog 中的全部条目。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .catalog import CatalogError, CatalogIcon, load_catalog


@dataclass(frozen=True)
class CoverageItem:
    slug: str
    name: str
    kind: str
    category: str


@dataclass
class CoverageReport:
    expected: list[CoverageItem] = field(default_factory=list)
    actual: list[str] = field(default_factory=list)
    missing: list[CoverageItem] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)

    @property
    def covered(self) -> int:
        return len(self.expected) - len(self.missing)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.extra

    def counts_by_kind(self) -> dict[str, tuple[int, int]]:
        """返回 ``{kind: (已覆盖, 总数)}``。"""
        counts: dict[str, list[int]] = {}
        missing_slugs = {item.slug for item in self.missing}
        for item in self.expected:
            total, done = counts.get(item.kind, (0, 0))
            counts[item.kind] = (total + 1, done + (0 if item.slug in missing_slugs else 1))
        return {kind: (done, total) for kind, (total, done) in counts.items()}


def check_coverage(
    src: str | Path = "icons",
    catalog_dir: str | Path | None = None,
    kinds: Iterable[str] | None = None,
) -> CoverageReport:
    """对比 catalog 清单与 ``src/*.svg``，返回缺失与多余条目。"""
    directory = Path(catalog_dir) if catalog_dir else Path.cwd() / "catalog"
    catalog = load_catalog(directory, kinds)
    expected = [
        CoverageItem(
            slug=icon.slug,
            name=icon.name,
            kind=icon.kind,
            category=icon.category_name,
        )
        for icon in catalog.icons
    ]
    src_path = Path(src)
    actual = sorted(path.stem for path in src_path.glob("*.svg"))
    actual_set = set(actual)
    expected_slugs = {item.slug for item in expected}
    return CoverageReport(
        expected=expected,
        actual=actual,
        missing=[item for item in expected if item.slug not in actual_set],
        extra=[slug for slug in actual if slug not in expected_slugs],
    )
