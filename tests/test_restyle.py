"""按画法重绘测试：flat 合并、pixel 保留明暗、备份与 CLI。"""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from pixel_game_icon_studio import samples
from pixel_game_icon_studio.cli import main
from pixel_game_icon_studio.restyle import RestyleError, restyle_icons
from pixel_game_icon_studio.svg import parse_palette, validate_svg

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"


def quiet() -> contextlib.AbstractContextManager:
    return contextlib.redirect_stdout(io.StringIO())


class RestyleTest(unittest.TestCase):
    def test_flat_merges_main_colors_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            out = Path(tmp) / "icons"
            samples.write_samples(src)

            report = restyle_icons(
                src=src,
                out=out,
                style_key="neon",
                palette_key="ui_semantic",
                art_style="flat",
                catalog_dir=CATALOG,
                backup=False,
            )
            self.assertEqual(len(report.written), 10)
            self.assertEqual(report.skipped, [])

            palette = parse_palette((out / "potion_healing.svg").read_text(encoding="utf-8"))
            self.assertEqual(palette["g"], palette["G"])
            self.assertEqual(palette["g"], palette["D"])
            self.assertEqual(palette["g"], palette["x"])
            self.assertIn(palette["o"], {"#141018", "#0a1018"})

            for path in report.written:
                self.assertEqual(validate_svg(path), [])

    def test_pixel_keeps_bright_and_dark_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            out = Path(tmp) / "icons"
            samples.write_samples(src)
            restyle_icons(
                src=src,
                out=out,
                style_key="neon",
                palette_key="ui_semantic",
                art_style="pixel",
                catalog_dir=CATALOG,
                backup=False,
            )
            palette = parse_palette((out / "potion_healing.svg").read_text(encoding="utf-8"))
            self.assertNotEqual(palette["g"], palette["D"])

    def test_backup_is_created_on_second_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            out = Path(tmp) / "icons"
            samples.write_samples(src)
            restyle_icons(src=src, out=out, style_key="neon", art_style="flat",
                          catalog_dir=CATALOG, backup=True)
            report = restyle_icons(src=src, out=out, style_key="neon", art_style="flat",
                                   catalog_dir=CATALOG, backup=True)
            self.assertIsNotNone(report.backup)
            assert report.backup is not None
            self.assertEqual(len(list(report.backup.glob("*.svg"))), 10)

    def test_unsupported_art_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            samples.write_samples(src)
            with self.assertRaises(RestyleError):
                restyle_icons(src=src, out=Path(tmp) / "out", art_style="line")

    def test_cli_restyle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "icons"
            samples.write_samples(src)
            with quiet():
                code = main(
                    [
                        "restyle",
                        "--src",
                        str(src),
                        "--out",
                        str(src),
                        "--style",
                        "neon",
                        "--palette",
                        "ui_semantic",
                        "--art-style",
                        "flat",
                        "--no-backup",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(validate_svg(src / "coin_gold.svg"), [])


if __name__ == "__main__":
    unittest.main()
