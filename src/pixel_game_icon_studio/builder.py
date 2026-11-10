"""批量转换 SVG 图标、生成 manifest.json，并汇总规范校验结果。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .svg import Issue, SvgError, read_meta, render_png, validate_svg

DEFAULT_SIZES: tuple[int, ...] = (32, 64, 128)


@dataclass
class BuildReport:
    """一次构建的结果：成功的图标条目、每个文件的问题、manifest 位置。"""

    icons: list[dict] = field(default_factory=list)
    problems: dict[str, list[Issue]] = field(default_factory=dict)
    manifest_path: Path | None = None
    png_count: int = 0

    @property
    def failed_files(self) -> list[str]:
        return [
            name
            for name, issues in self.problems.items()
            if any(issue.is_error for issue in issues)
        ]

    @property
    def warnings(self) -> list[tuple[str, Issue]]:
        return [
            (name, issue)
            for name, issues in self.problems.items()
            for issue in issues
            if not issue.is_error
        ]

    @property
    def ok(self) -> bool:
        return not self.failed_files


def find_svgs(src: str | Path) -> list[Path]:
    src = Path(src)
    if not src.is_dir():
        raise SvgError(f"源目录不存在: {src}")
    svgs = sorted(src.glob("*.svg"))
    if not svgs:
        raise SvgError(f"{src}/ 下没有找到任何 .svg 文件")
    return svgs


def _display_path(path: str | Path, base: str | Path | None = None) -> str:
    """把路径写成相对 manifest 基准目录的形式，供预览页直接引用。"""
    resolved = Path(path).resolve()
    root = Path(base).resolve() if base is not None else Path.cwd()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _normalize_sizes(sizes: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    normalized: list[int] = []
    for size in sizes:
        if size <= 0:
            raise SvgError(f"尺寸必须是正整数，收到 {size}")
        if size not in normalized:
            normalized.append(size)
    if not normalized:
        raise SvgError("至少需要一个输出尺寸")
    return tuple(normalized)


def build(
    src: str | Path = "icons",
    out: str | Path = "png",
    sizes: list[int] | tuple[int, ...] = DEFAULT_SIZES,
    background: str | None = None,
    write_manifest: bool = True,
) -> BuildReport:
    """校验并转换 ``src/*.svg``，失败的图标会被跳过，其余照常输出。"""
    src_path = Path(src)
    out_path = Path(out)
    # preview.html 从项目根（src 的父目录）加载 manifest，路径以此为基准
    base = src_path.resolve().parent
    size_list = _normalize_sizes(sizes)
    report = BuildReport()

    for svg in find_svgs(src_path):
        issues = validate_svg(svg)
        if any(issue.is_error for issue in issues):
            report.problems[svg.name] = issues
            continue

        meta = read_meta(svg)
        png_paths: dict[str, str] = {}
        for size in size_list:
            png = out_path / str(size) / f"{svg.stem}.png"
            try:
                render_png(svg, png, size=size, background=background)
            except (OSError, SvgError) as exc:
                issues.append(Issue("error", f"{size}px 渲染失败: {exc}"))
                continue
            png_paths[str(size)] = _display_path(png, base)
            report.png_count += 1
        if issues:
            report.problems[svg.name] = issues
        report.icons.append(
            {
                "id": svg.stem,
                "name": meta.name,
                "rarity": meta.rarity,
                "svg": _display_path(svg, base),
                "png": {str(size): path for size, path in png_paths.items()},
            }
        )

    if write_manifest:
        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "src_dir": _display_path(src_path, base),
            "out_dir": _display_path(out_path, base),
            "sizes": list(size_list),
            "icons": report.icons,
        }
        manifest_path = src_path / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        report.manifest_path = manifest_path
    return report


def check(src: str | Path = "icons") -> dict[str, list[Issue]]:
    """只校验不转换，返回 ``{文件名: 问题列表}``（通过的文件也会出现，列表为空）。"""
    return {svg.name: validate_svg(svg) for svg in find_svgs(src)}
