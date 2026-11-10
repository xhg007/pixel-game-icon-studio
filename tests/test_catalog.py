"""图标目录测试：加载校验、检索、Markdown/CSV、模板注入与 CLI。"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from pixel_game_icon_studio.agentdoc import agents_document
from pixel_game_icon_studio.catalog import (
    CatalogError,
    TEMPLATES,
    kinds_for_template,
    load_catalog,
)
from pixel_game_icon_studio.cli import main
from pixel_game_icon_studio.config import get_style
from pixel_game_icon_studio.studio import render_document

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "catalog"


def quiet() -> contextlib.AbstractContextManager:
    return contextlib.redirect_stdout(io.StringIO())


def catalog_payload(**overrides) -> dict:
    data = {
        "version": 1,
        "kind": "items",
        "title": "测试目录",
        "description": "测试",
        "categories": [
            {
                "key": "potion",
                "name": "药水",
                "description": "",
                "icons": [
                    {
                        "slug": "potion_test",
                        "name": "测试药水",
                        "rarity": "common",
                        "keywords": ["测试"],
                        "silhouette": "瓶",
                        "palette": ["#ffffff", "#888888", "#000000"],
                        "notes": "",
                    }
                ],
            }
        ],
    }
    data.update(overrides)
    return data


class CatalogLoadTest(unittest.TestCase):
    def test_project_catalog(self) -> None:
        catalog = load_catalog(CATALOG_DIR)
        self.assertEqual(catalog.kinds(), ["items", "ui"])
        self.assertEqual(catalog.counts(), {"items": 52, "ui": 50})
        self.assertEqual(len(catalog.icons), 102)
        slugs = [icon.slug for icon in catalog.icons]
        self.assertEqual(len(slugs), len(set(slugs)))
        for icon in catalog.icons:
            self.assertEqual(len(icon.palette), 3)
            self.assertTrue(all(color.startswith("#") for color in icon.palette))

    def test_find_by_kind_and_query(self) -> None:
        catalog = load_catalog(CATALOG_DIR)
        ui_icons = catalog.find(kinds=["ui"])
        self.assertEqual(len(ui_icons), 50)
        arrows = catalog.find(kinds=["ui"], query="箭头")
        self.assertGreaterEqual(len(arrows), 4)
        self.assertTrue(all(icon.kind == "ui" for icon in arrows))
        potions = catalog.find(category="potion")
        self.assertEqual(len(potions), 6)

    def test_markdown_full_and_compact(self) -> None:
        catalog = load_catalog(CATALOG_DIR)
        full = catalog.markdown(["items"], detail="full")
        self.assertIn("potion_healing", full)
        self.assertIn("`#e8433f`", full)
        self.assertNotIn("ui_home", full)

        compact = catalog.markdown(["ui"], detail="compact")
        self.assertIn("`ui_home`", compact)
        self.assertIn("首页", compact)
        self.assertNotIn("potion_healing", compact)

    def test_csv_export(self) -> None:
        catalog = load_catalog(CATALOG_DIR)
        text = catalog.csv()
        lines = text.strip().splitlines()
        self.assertEqual(len(lines), 103)
        self.assertTrue(lines[0].startswith("kind,category,category_name,slug,name"))
        self.assertIn("potion_healing", text)

    def test_templates(self) -> None:
        self.assertEqual(kinds_for_template("full"), ("items", "ui"))
        self.assertEqual(kinds_for_template("items"), ("items",))
        self.assertEqual(kinds_for_template("ui"), ("ui",))
        self.assertEqual(kinds_for_template("spec"), ())
        with self.assertRaises(CatalogError):
            kinds_for_template("unknown")
        self.assertEqual(set(TEMPLATES), {"full", "items", "ui", "spec"})


class CatalogValidationTest(unittest.TestCase):
    def load(self, data: dict):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return load_catalog(tmp)

    def test_missing_palette(self) -> None:
        data = catalog_payload()
        data["categories"][0]["icons"][0]["palette"] = ["#ffffff"]
        with self.assertRaises(CatalogError):
            self.load(data)

    def test_bad_hex(self) -> None:
        data = catalog_payload()
        data["categories"][0]["icons"][0]["palette"] = ["white", "#888888", "#000000"]
        with self.assertRaises(CatalogError):
            self.load(data)

    def test_bad_rarity(self) -> None:
        data = catalog_payload()
        data["categories"][0]["icons"][0]["rarity"] = "mythic"
        with self.assertRaises(CatalogError):
            self.load(data)

    def test_duplicate_slug_across_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            text = json.dumps(catalog_payload(), ensure_ascii=False)
            (Path(tmp) / "a.json").write_text(text, encoding="utf-8")
            (Path(tmp) / "b.json").write_text(text, encoding="utf-8")
            with self.assertRaises(CatalogError):
                load_catalog(tmp)


class CatalogDocTest(unittest.TestCase):
    def test_agents_appends_catalog_chapter(self) -> None:
        catalog = load_catalog(CATALOG_DIR)
        text = agents_document(get_style(), catalog_markdown=catalog.markdown(["items"]))
        self.assertIn("## 13. 图标目录", text)
        self.assertIn("potion_healing", text)
        self.assertNotIn("ui_home", text)

    def test_studio_templates(self) -> None:
        base = {
            "style": "classic",
            "project_name": "测试",
            "target": "agents",
            "sections": None,
            "colors": {},
        }
        _, items_doc = render_document({**base, "template": "items"}, catalog_dir=CATALOG_DIR)
        _, ui_doc = render_document({**base, "template": "ui"}, catalog_dir=CATALOG_DIR)
        _, spec_doc = render_document({**base, "template": "spec"}, catalog_dir=CATALOG_DIR)
        self.assertIn("potion_healing", items_doc)
        self.assertNotIn("ui_home", items_doc)
        catalog_part = ui_doc.split("## 13. 图标目录", 1)[1]
        self.assertIn("ui_home", catalog_part)
        self.assertNotIn("potion_healing", catalog_part)
        self.assertNotIn("## 13. 图标目录", spec_doc)


class CatalogCliTest(unittest.TestCase):
    def test_catalog_command_table(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["catalog"])
        self.assertEqual(code, 0)
        self.assertIn("102 个图标", out.getvalue())

    def test_catalog_csv_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "catalog.csv"
            with quiet():
                code = main(["catalog", "--format", "csv", "--out", str(target)])
            self.assertEqual(code, 0)
            self.assertEqual(len(target.read_text(encoding="utf-8").splitlines()), 103)

    def test_agents_md_template_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "AGENTS.md"
            with quiet():
                code = main(
                    ["agents-md", "--template", "items", "--out", str(target)]
                )
            self.assertEqual(code, 0)
            text = target.read_text(encoding="utf-8")
            self.assertIn("## 13. 图标目录", text)
            self.assertIn("potion_healing", text)
            self.assertNotIn("ui_home", text)

    def test_agents_md_template_ui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "AGENTS.md"
            with quiet():
                code = main(["agents-md", "--template", "ui", "--out", str(target)])
            self.assertEqual(code, 0)
            text = target.read_text(encoding="utf-8")
            self.assertIn("`ui_home`", text)
            self.assertNotIn("potion_healing", text.split("## 13. 图标目录")[1])


if __name__ == "__main__":
    unittest.main()
