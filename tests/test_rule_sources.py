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
    def copied_repo(self, tmp: str) -> Path:
        root = Path(tmp) / "repo"
        shutil.copytree(ROOT, root)
        return root

    def test_current_repository_passes(self):
        result = VALIDATOR.validate(ROOT)
        self.assertTrue(result["ok"], result)

    def test_duplicate_cut_rule_in_script_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.copied_repo(tmp)
            path = root / "references/01-script-slicing.md"
            path.write_text(path.read_text(encoding="utf-8") + "\n## 30度规则\n", encoding="utf-8")
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("30度规则" in item for item in result["errors"]))

    def test_duplicate_task_gate_in_spatial_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.copied_repo(tmp)
            path = root / "references/04-blocking-continuity.md"
            path.write_text(
                path.read_text(encoding="utf-8") + "\n## ENTER／EXIT进出场Gate\n",
                encoding="utf-8",
            )
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("进出场Gate" in item for item in result["errors"]))

    def test_missing_task_stage_in_skill_pipeline_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.copied_repo(tmp)
            path = root / "SKILL.md"
            value = path.read_text(encoding="utf-8")
            value = value.replace("→ 14-shot-task-action-coverage.md\n", "")
            value = value.replace(
                "3. 只有`04`输出“几何结论：通过”后，`14`才能验证SHOT任务、动作覆盖、场景观察签名、POV／OTS／INSERT证据与动作状态机。\n",
                "",
            )
            path.write_text(value, encoding="utf-8")
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("14-shot-task" in item or "01→04→14→13" in item for item in result["errors"]))

    def test_stale_cumulative_cut_rule_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.copied_repo(tmp)
            path = root / "references/05-video-prompting.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\n相邻SHOT是否满足30度、景别差异、两变量和信息可见性。\n",
                encoding="utf-8",
            )
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("过时或自我证明式规则" in item for item in result["errors"]))

    def test_subject_change_cannot_return_as_automatic_strong_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.copied_repo(tmp)
            path = root / "references/13-cut-shot-geometry.md"
            path.write_text(
                path.read_text(encoding="utf-8") + "\n主要主体改变即为强视觉差异。\n",
                encoding="utf-8",
            )
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("自我证明式规则" in item for item in result["errors"]))

    def test_narrative_dimension_cannot_return_as_visual_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.copied_repo(tmp)
            path = root / "references/13-cut-shot-geometry.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\n第二项可以是另一视觉维度，也可以是动作阶段变化。\n",
                encoding="utf-8",
            )
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("过时或自我证明式规则" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
