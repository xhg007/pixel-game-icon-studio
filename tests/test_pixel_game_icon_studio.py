"""核心逻辑的单元测试：示例数据、格式校验、Pillow 渲染、manifest 构建。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pixel_game_icon_studio import samples
from pixel_game_icon_studio.builder import DEFAULT_SIZES, build, check
from pixel_game_icon_studio.svg import (
    CANVAS,
    Issue,
    parse_palette,
    parse_rects,
    rasterize,
    validate_svg,
)

SVG_HEAD = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" '
    'width="16" height="16" shape-rendering="crispEdges" '
    'data-name="测试" data-rarity="common">'
)
SVG_TAIL = "</svg>"


def write_svg(directory: str | Path, name: str, body: str) -> Path:
    directory = Path(directory)
    path = directory / f"{name}.svg"
    path.write_text(f"{SVG_HEAD}\n{body}\n{SVG_TAIL}\n", encoding="utf-8")
    return path


def errors_of(issues: list[Issue]) -> list[str]:
    return [issue.message for issue in issues if issue.is_error]


class SamplesTest(unittest.TestCase):
    def test_all_specs_are_16_by_16(self) -> None:
        for slug in samples.SLUGS:
            spec = samples.ICONS[slug]
            with self.subTest(slug=slug):
                self.assertEqual(len(spec.rows), CANVAS)
                self.assertTrue(all(len(row) == CANVAS for row in spec.rows))

    def test_generated_samples_pass_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            written = samples.write_samples(tmp)
            self.assertEqual(len(written), len(samples.SLUGS))
            for path in written:
                with self.subTest(path=path.name):
                    issues = validate_svg(path)
                    self.assertEqual(errors_of(issues), [])

    def test_manifest_metadata_matches_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            samples.write_samples(tmp)
            results = check(tmp)
            self.assertEqual(len(results), len(samples.SLUGS))
            for issues in results.values():
                self.assertEqual(errors_of(issues), [])


class RenderTest(unittest.TestCase):
    def test_rasterize_preserves_pixel_colors_and_scales(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = samples.write_samples(tmp)[0]
            rects = parse_rects(path)
            small = rasterize(rects, size=CANVAS)
            large = rasterize(rects, size=64)
            self.assertEqual(small.size, (CANVAS, CANVAS))
            self.assertEqual(large.size, (64, 64))
            # potion_healing 第 1 行 x=6 是轮廓色 #2e1f10
            self.assertEqual(small.getpixel((6, 1)), (46, 31, 16, 255))
            # 最近邻放大：左上角 4×4 块保持同色
            self.assertEqual(large.getpixel((24, 4)), large.getpixel((27, 7)))

    def test_background_is_flattened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = samples.write_samples(tmp)[0]
            image = rasterize(parse_rects(path), size=16, background="#1a140c")
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.getpixel((0, 0)), (26, 20, 12, 255))

    def test_palette_comment_is_parsed(self) -> None:
        text = "<!-- palette: o=#2E1F10, g=#e8433f -->"
        self.assertEqual(parse_palette(text), {"o": "#2e1f10", "g": "#e8433f"})


class ValidationTest(unittest.TestCase):
    def test_valid_minimal_icon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                tmp,
                "ok",
                "<!-- palette: o=#000000 -->\n"
                '<rect x="0" y="0" width="16" height="1" fill="#000000"/>',
            )
            self.assertEqual(validate_svg(path), [])

    def test_out_of_bounds_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                tmp,
                "bad",
                "<!-- palette: o=#000000 -->\n"
                '<rect x="14" y="0" width="4" height="1" fill="#000000"/>',
            )
            messages = errors_of(validate_svg(path))
            self.assertTrue(any("越界" in message for message in messages), messages)

    def test_unregistered_color_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                tmp,
                "bad",
                "<!-- palette: o=#000000 -->\n"
                '<rect x="0" y="0" width="4" height="1" fill="#ffffff"/>',
            )
            messages = errors_of(validate_svg(path))
            self.assertTrue(any("不在 palette" in message for message in messages), messages)

    def test_non_one_height_and_foreign_tag_are_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                tmp,
                "bad",
                "<!-- palette: o=#000000 -->\n"
                '<rect x="0" y="0" width="4" height="2" fill="#000000"/>\n'
                '<circle cx="8" cy="8" r="2" fill="#000000"/>',
            )
            messages = errors_of(validate_svg(path))
            self.assertTrue(any("height 必须是 1" in message for message in messages), messages)
            self.assertTrue(any("<circle>" in message for message in messages), messages)

    def test_bad_rarity_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.svg"
            path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" '
                'width="16" height="16" data-name="坏" data-rarity="mythic">\n'
                "<!-- palette: o=#000000 -->\n"
                '<rect x="0" y="0" width="4" height="1" fill="#000000"/>\n'
                "</svg>\n",
                encoding="utf-8",
            )
            messages = errors_of(validate_svg(path))
            self.assertTrue(any("data-rarity" in message for message in messages), messages)

    def test_unmerged_same_color_is_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_svg(
                tmp,
                "warn",
                "<!-- palette: o=#000000 -->\n"
                '<rect x="0" y="0" width="2" height="1" fill="#000000"/>\n'
                '<rect x="2" y="0" width="2" height="1" fill="#000000"/>',
            )
            issues = validate_svg(path)
            self.assertEqual(errors_of(issues), [])
            self.assertTrue(any("应合并" in issue.message for issue in issues))


class BuildTest(unittest.TestCase):
    def test_build_writes_pngs_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "icons"
            out = Path(tmp) / "png"
            samples.write_samples(src)
            report = build(src=src, out=out, sizes=[16, 64])

            self.assertTrue(report.ok)
            self.assertEqual(len(report.icons), len(samples.SLUGS))
            self.assertEqual(report.png_count, len(samples.SLUGS) * 2)

            manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["icons"]), len(samples.SLUGS))
            self.assertEqual(manifest["sizes"], [16, 64])

            first = manifest["icons"][0]
            self.assertTrue((src.parent / first["svg"]).is_file())
            self.assertEqual(set(first["png"]), {"16", "64"})
            for png in first["png"].values():
                self.assertTrue((src.parent / png).is_file(), png)

    def test_build_skips_invalid_icons(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "icons"
            samples.write_samples(src)
            write_svg(
                src,
                "broken",
                "<!-- palette: o=#000000 -->\n"
                '<rect x="0" y="0" width="40" height="1" fill="#000000"/>',
            )
            report = build(src=src, out=Path(tmp) / "png", sizes=[16])

            self.assertFalse(report.ok)
            self.assertEqual(report.failed_files, ["broken.svg"])
            ids = {icon["id"] for icon in report.icons}
            self.assertNotIn("broken", ids)

    def test_default_sizes_are_unchanged(self) -> None:
        self.assertEqual(tuple(DEFAULT_SIZES), (32, 64, 128))


if __name__ == "__main__":
    unittest.main()
