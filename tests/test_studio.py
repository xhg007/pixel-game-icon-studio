"""动态配置页测试：配置合并、章节组合、HTTP API。"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

from pixel_game_icon_studio.config import get_style
from pixel_game_icon_studio.studio import (
    ConfigError,
    StudioRequestHandler,
    compose_agents,
    presets_payload,
    render_document,
    save_documents,
    style_from_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def payload(**overrides) -> dict:
    data = {
        "style": "classic",
        "project_name": "图标工厂",
        "target": "agents",
        "sections": [
            "map",
            "commands",
            "styles",
            "visual",
            "colors",
            "blueprints",
            "metadata",
            "prompts",
            "workflow",
            "checklist",
            "troubleshooting",
            "integration",
        ],
        "colors": {},
    }
    data.update(overrides)
    return data


class ConfigPayloadTest(unittest.TestCase):
    def test_defaults_match_preset(self) -> None:
        style = style_from_payload(payload())
        classic = get_style("classic")
        self.assertEqual(style.outline_warm, classic.outline_warm)
        self.assertEqual(style.materials, classic.materials)

    def test_color_overrides(self) -> None:
        style = style_from_payload(
            payload(
                style="neon",
                colors={
                    "outline_warm": "#010203",
                    "outline_cool": "#040506",
                    "materials": {"gold": ["#111111", "#222222", "#333333"]},
                    "potions": {"red": "#444444"},
                    "rarity": {"legend": "#555555"},
                },
            )
        )
        self.assertEqual(style.outline_warm, "#010203")
        self.assertEqual(style.outline_cool, "#040506")
        self.assertEqual(style.materials["gold"], ("#111111", "#222222", "#333333"))
        self.assertEqual(style.potions["red"], "#444444")
        self.assertEqual(style.rarity["legend"], "#555555")
        # 未覆盖的材质保留 neon 预设
        self.assertEqual(style.materials["metal"], get_style("neon").materials["metal"])

    def test_invalid_color_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            style_from_payload(payload(colors={"outline_warm": "red"}))
        with self.assertRaises(ConfigError):
            style_from_payload(payload(colors={"materials": {"metal": ["#111111"]}}))

    def test_unknown_style_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            style_from_payload(payload(style="does-not-exist"))


class ComposeTest(unittest.TestCase):
    def test_all_sections_by_default(self) -> None:
        text = compose_agents(get_style("classic"))
        for title in ("项目地图", "道具蓝图", "提示词模板", "工具集成"):
            self.assertIn(title, text)

    def test_sections_are_filtered_and_renumbered(self) -> None:
        text = compose_agents(
            get_style("classic"),
            project_name="我的图标库",
            sections=["map", "colors", "integration"],
        )
        self.assertIn("# AGENTS.md — 我的图标库", text)
        self.assertIn("## 1. 项目地图", text)
        self.assertIn("## 2. 色彩系统", text)
        self.assertIn("## 3. 工具集成", text)
        self.assertNotIn("道具蓝图", text)
        self.assertNotIn("提示词模板", text)
        # 编号连续，不出现跳号
        self.assertNotIn("## 4.", text)

    def test_project_name_is_sanitized(self) -> None:
        text = compose_agents(get_style("classic"), project_name="# 注入\n标题")
        first_line = text.splitlines()[2]
        self.assertEqual(first_line, "# AGENTS.md — 注入标题")

    def test_config_table_survives_section_filter(self) -> None:
        from pixel_game_icon_studio.agentdoc import build_config_table

        text = compose_agents(
            get_style("classic"),
            sections=["map"],
            config_markdown=build_config_table(
                get_style("classic"),
                art_style="flat",
                palette_key="ui_semantic",
                palette_label="游戏 UI 语义色",
            ),
        )
        self.assertIn("## 当前配置", text)
        self.assertIn("| 画法风格 | 扁平风（`flat`） |", text)
        self.assertIn("## 0. 一句话目标", text)
        self.assertIn("## 1. 项目地图", text)
        self.assertNotIn("## 2. 可用命令", text)

    def test_custom_colors_reach_document(self) -> None:
        _, content = render_document(
            payload(colors={"outline_warm": "#abcdef", "rarity": {"legend": "#fedcba"}})
        )
        self.assertIn("#abcdef", content)
        self.assertIn("#fedcba", content)


class PresetsTest(unittest.TestCase):
    def test_presets_payload_shape(self) -> None:
        data = presets_payload()
        self.assertEqual(data["default"], "classic")
        self.assertEqual(len(data["styles"]), 4)
        keys = [item["key"] for item in data["sections"]]
        self.assertIn("blueprints", keys)
        optional = {item["key"] for item in data["sections"] if item["optional"]}
        self.assertEqual(
            optional,
            {
                "blueprints",
                "prompts",
                "troubleshooting",
                "integration",
                "catalog",
                "design",
            },
        )
        self.assertEqual(len(data["catalogs"]), 2)
        self.assertEqual([t["key"] for t in data["templates"]], ["full", "items", "ui", "spec"])
        self.assertEqual(len(data["art_styles"]), 10)
        self.assertEqual(len(data["palettes"]), 8)
        classic = next(item for item in data["styles"] if item["key"] == "classic")
        self.assertIsInstance(classic["materials"]["metal"], list)


class SaveTest(unittest.TestCase):
    def test_save_documents_writes_agents_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = save_documents(
                payload(
                    project_name="自定义工厂",
                    colors={"outline_warm": "#010203"},
                ),
                tmp,
                ROOT / "catalog",
            )
            self.assertTrue(result["ok"])
            self.assertEqual(result["saved"], ["AGENTS.md"])
            agents = (Path(tmp) / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("# AGENTS.md — 自定义工厂", agents)
            self.assertIn("#010203", agents)
            self.assertFalse((Path(tmp) / "SKILL.md").exists())

    def test_save_all_syncs_tool_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = save_documents(
                {**payload(project_name="保存全部测试"), "install_all": True},
                tmp,
                ROOT / "catalog",
            )
            self.assertTrue(result["ok"])
            self.assertTrue((Path(tmp) / "CLAUDE.md").is_file())
            self.assertTrue((Path(tmp) / "CODEBUDDY.md").is_file())
            self.assertIn("CLAUDE.md", result["installed"])
            self.assertFalse((Path(tmp) / ".claude/skills").exists())

    def test_save_rejects_bad_color(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError):
                save_documents(payload(colors={"outline_warm": "bad"}), tmp, ROOT / "catalog")


class ConfigSyncTest(unittest.TestCase):
    def test_render_document_syncs_five_configs(self) -> None:
        data = payload(
            target="agents",
            style="neon",
            template="items",
            art_style="flat",
            palette="ui_semantic",
            project_name="测试工厂",
        )
        _, agents = render_document(data, catalog_dir=ROOT / "catalog")
        expected = (
            "## 当前配置",
            "| 项目名 | 测试工厂 |",
            "| 风格预设 | 赛博霓虹（`neon`） |",
            "| 文档模板 | 物品图标版（`items`） |",
            "| 画法风格 | 扁平风（`flat`） |",
            "| 色板 | 游戏 UI 语义色（`ui_semantic`） |",
        )
        for needle in expected:
            self.assertIn(needle, agents)


class StudioHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        (root / "preview.html").write_text("<!doctype html><title>gallery</title>", encoding="utf-8")
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            partial(
                StudioRequestHandler,
                directory=str(root),
                catalog_dir=str(ROOT / "catalog"),
            ),
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def get_json(self, path: str) -> dict:
        with urllib.request.urlopen(self.base + path, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json(self, path: str, data: dict) -> tuple[int, dict]:
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_studio_page(self) -> None:
        with urllib.request.urlopen(self.base + "/studio", timeout=5) as response:
            text = response.read().decode("utf-8")
        self.assertEqual(response.status, 200)
        self.assertIn("AGENTS STUDIO", text)
        self.assertIn("/api/render", text)

    def test_presets_endpoint(self) -> None:
        data = self.get_json("/api/presets")
        self.assertEqual(len(data["styles"]), 4)
        self.assertEqual(data["default"], "classic")

    def test_render_endpoint(self) -> None:
        status, data = self.post_json(
            "/api/render",
            payload(colors={"outline_warm": "#0a0b0c"}, sections=["map", "colors"]),
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["filename"], "AGENTS.md")
        self.assertIn("#0a0b0c", data["content"])
        self.assertNotIn("道具蓝图", data["content"])

    def test_render_rejects_bad_color(self) -> None:
        status, data = self.post_json("/api/render", payload(colors={"outline_warm": "nope"}))
        self.assertEqual(status, 400)
        self.assertFalse(data["ok"])
        self.assertIn("outline_warm", data["error"])

    def test_static_files_still_served(self) -> None:
        with urllib.request.urlopen(self.base + "/preview.html", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("gallery", response.read().decode("utf-8"))

    def test_save_endpoint_writes_project_files(self) -> None:
        status, data = self.post_json(
            "/api/save",
            payload(project_name="HTTP 保存测试", colors={"outline_warm": "#0d0e0f"}),
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["saved"], ["AGENTS.md"])
        agents = (Path(self.tmp.name) / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("# AGENTS.md — HTTP 保存测试", agents)
        self.assertIn("#0d0e0f", agents)
        self.assertFalse((Path(self.tmp.name) / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
