import tempfile
import unittest
from pathlib import Path

from pixel_game_icon_studio.coverage import check_coverage

CATALOG = Path(__file__).resolve().parent.parent / "catalog"
TOTAL = 102


class CoverageTest(unittest.TestCase):
    def test_missing_from_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = check_coverage(tmp, CATALOG)
            self.assertEqual(len(report.expected), TOTAL)
            self.assertEqual(report.covered, 0)
            self.assertEqual(len(report.missing), TOTAL)
            self.assertFalse(report.ok)

    def test_ui_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = check_coverage(tmp, CATALOG, kinds=["ui"])
            self.assertEqual(len(report.expected), 50)
            self.assertEqual(set(report.counts_by_kind()), {"ui"})

    def test_full_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = check_coverage(tmp, CATALOG)
            for item in report.expected:
                (Path(tmp) / f"{item.slug}.svg").write_text("<svg/>", encoding="utf-8")
            complete = check_coverage(tmp, CATALOG)
            self.assertTrue(complete.ok)
            self.assertEqual(complete.covered, TOTAL)
            self.assertEqual(complete.missing, [])
            self.assertEqual(complete.extra, [])

    def test_extra_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "unknown_icon.svg").write_text("<svg/>", encoding="utf-8")
            report = check_coverage(tmp, CATALOG)
            self.assertEqual(report.extra, ["unknown_icon"])
            self.assertFalse(report.ok)

    def test_counts_by_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = check_coverage(tmp, CATALOG)
            self.assertEqual(report.counts_by_kind(), {"items": (0, 52), "ui": (0, 50)})


if __name__ == "__main__":
    unittest.main()
