"""设计体系测试：风格、色板、分类学、文档注入与 CLI。"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from pixel_game_icon_studio.agentdoc import agents_document
from pixel_game_icon_studio.cli import main
from pixel_game_icon_studio.config import get_style
from pixel_game_icon_studio.design import (
    DesignError,
    design_markdown,
    load_design_system,
)
from pixel_game_icon_studio.studio import presets_payload, render_document

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "catalog"


def quiet() -> contextlib.AbstractContextManager:
    return contextlib.redirect_stdout(io.StringIO())


class DesignLoadTest(unittest.TestCase):
    def test_project_design_system(self) -> None:
        system = load_design_system(CATALOG_DIR)
        counts = system.counts()
        self.assertEqual(counts["styles"], 10)
        self.assertEqual(counts["palettes"], 8)
        self.assertEqual(counts["tiers"], 6)
        self.assertEqual(counts["item_groups"], 8)
        self.assertEqual(counts["themes"], 5)

        for style in system.styles:
            self.assertIn(style.supported, {"full", "partial", "future"})
            self.assertGreaterEqual(style.difficulty, 1)
            self.assertLessEqual(style.difficulty, 5)

        for palette in system.palettes:
            self.assertEqual(len(palette.colors), palette.size)
            self.assertTrue(all(color.startswith("#") for color in palette.colors))

    def test_find_style_and_palette(self) -> None:
        system = load_design_system(CATALOG_DIR)
        self.assertEqual(system.find_style("pixel").name, "像素风")
        self.assertEqual(system.find_palette("pico8").size, 16)
        self.assertIsNone(system.find_style(None))
        with self.assertRaises(DesignError):
            system.find_style("no-such-style")
        with self.assertRaises(DesignError):
            system.find_palette("no-such-palette")

    def test_rarity_mapping(self) -> None:
        system = load_design_system(CATALOG_DIR)
        rarity = system.find_palette("wow_rarity")
        self.assertEqual(
            rarity.mapping,
            {
                "common": "#c8c8c8",
                "fine": "#1eff00",
                "rare": "#0070dd",
                "epic": "#a335ee",
                "legend": "#ff8000",
            },
        )


class DesignValidationTest(unittest.TestCase):
    def test_palette_size_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "palettes.json").write_text(
                json.dumps(
                    {
                        "palettes": [
                            {"key": "x", "name": "X", "size": 3, "colors": ["#000000"]}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(DesignError):
                load_design_system(tmp)

    def test_bad_supported_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "styles.json").write_text(
                json.dumps(
                    {
                        "styles": [
                            {
                                "key": "x",
                                "name": "X",
                                "supported": "sometimes",
                                "difficulty": 2,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(DesignError):
                load_design_system(tmp)

    def test_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DesignError):
                load_design_system(tmp)


class DesignMarkdownTest(unittest.TestCase):
    def test_sections_and_current_selection(self) -> None:
        system = load_design_system(CATALOG_DIR)
        text = design_markdown(system, art_style="flat", palette="pico8")
        for heading in (
            "### 画法风格光谱",
            "### 当前画法：扁平风",
            "### 色板库",
            "### 当前色板：PICO-8 默认 16 色",
            "### 稀有度色阶（行业惯例）",
            "### 功能层级",
            "### 道具八大类",
            "### 题材流派",
        ):
            self.assertIn(heading, text)
        self.assertIn("#1d2b53", text)
        self.assertIn("| `legend` | `#ff8000` |", text)
        self.assertIn("武器", text)

    def test_unknown_selection(self) -> None:
        system = load_design_system(CATALOG_DIR)
        with self.assertRaises(DesignError):
            design_markdown(system, art_style="unknown")
        with self.assertRaises(DesignError):
            design_markdown(system, palette="unknown")


class DesignDocInjectionTest(unittest.TestCase):
    def test_agents_design_chapter(self) -> None:
        system = load_design_system(CATALOG_DIR)
        block = design_markdown(system, art_style="pixel", palette="db32")
        agents = agents_document(get_style(), design_markdown=block)
        self.assertIn("## 14. 风格、色板与分类学", agents)
        self.assertIn("DawnBringer 32", agents)

    def test_studio_payload_injects_design(self) -> None:
        base = {
            "style": "classic",
            "project_name": "测试",
            "target": "agents",
            "template": "spec",
            "sections": None,
            "colors": {},
            "art_style": "mbe",
            "palette": "arne16",
        }
        _, content = render_document(base, catalog_dir=CATALOG_DIR)
        self.assertIn("## 14. 风格、色板与分类学", content)
        self.assertIn("当前画法：MBE 风", content)
        self.assertIn("当前色板：Arne 16", content)

    def test_presets_payload_design_blocks(self) -> None:
        data = presets_payload(CATALOG_DIR)
        self.assertEqual(len(data["art_styles"]), 10)
        self.assertEqual(len(data["palettes"]), 8)
        self.assertEqual(data["design"]["art_style"], "pixel")


class DesignCliTest(unittest.TestCase):
    def test_design_table(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["design"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("画法风格（10）", text)
        self.assertIn("色板（8）", text)
        self.assertIn("道具 8 大类", text)

    def test_design_markdown_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "design.md"
            with quiet():
                code = main(
                    [
                        "design",
                        "--format",
                        "markdown",
                        "--art-style",
                        "line",
                        "--palette",
                        "gameboy_dmg",
                        "--out",
                        str(target),
                    ]
                )
            self.assertEqual(code, 0)
            text = target.read_text(encoding="utf-8")
            self.assertIn("当前画法：线性 / 描边", text)
            self.assertIn("当前色板：Game Boy DMG", text)

    def test_design_json(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["design", "--format", "json"])
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(len(data["styles"]), 10)
        self.assertEqual(len(data["palettes"]), 8)


if __name__ == "__main__":
    unittest.main()
