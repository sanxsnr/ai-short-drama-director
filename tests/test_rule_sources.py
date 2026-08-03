#!/usr/bin/env python3
"""Regression tests for unique markdown rule-source ownership."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    path = ROOT / "scripts/validate_rule_sources.py"
    spec = importlib.util.spec_from_file_location("validate_rule_sources", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()


class RuleSourceTests(unittest.TestCase):
    def test_current_repository_passes(self):
        result = VALIDATOR.validate(ROOT)
        self.assertTrue(result["ok"], result)

    def test_duplicate_cut_rule_in_script_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "references").mkdir(parents=True)

            (root / "SKILL.md").write_text(
                "references/01-script-slicing.md\n"
                "references/04-blocking-continuity.md\n"
                "references/13-cut-shot-geometry.md\n"
                "其他文件只能引用这些真源，不得另写一套同类规则\n",
                encoding="utf-8",
            )
            (root / "references/01-script-slicing.md").write_text(
                "04-blocking-continuity.md\n13-cut-shot-geometry.md\n## 30度规则\n",
                encoding="utf-8",
            )
            (root / "references/04-blocking-continuity.md").write_text(
                "13-cut-shot-geometry.md\n",
                encoding="utf-8",
            )
            (root / "references/13-cut-shot-geometry.md").write_text(
                "04-blocking-continuity.md\n",
                encoding="utf-8",
            )

            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("30度规则" in item for item in result["errors"]))

    def test_stale_cumulative_cut_rule_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            shutil.copytree(ROOT, root)
            path = root / "references/05-video-prompting.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\n相邻SHOT是否满足30度、景别差异、两变量和信息可见性。\n",
                encoding="utf-8",
            )
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(
                any("过时或累计式视觉差异规则" in item for item in result["errors"])
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
