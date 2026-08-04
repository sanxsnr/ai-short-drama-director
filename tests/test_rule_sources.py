#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_rule_sources", ROOT / "scripts/validate_rule_sources.py")
assert spec and spec.loader
VALIDATOR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(VALIDATOR)


class RuleSourceTests(unittest.TestCase):
    def copied_repo(self, temp: str) -> Path:
        root = Path(temp) / "repo"
        shutil.copytree(ROOT, root)
        return root

    def test_current_repository_passes(self):
        self.assertTrue(VALIDATOR.validate(ROOT)["ok"])

    def test_missing_director_stage_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.copied_repo(temp)
            path = root / "SKILL.md"
            path.write_text(path.read_text().replace("→ 15-directorial-camera-plan.md\n", ""))
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("15" in item or "职责顺序" in item for item in result["errors"]))

    def test_missing_04b_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.copied_repo(temp)
            path = root / "SKILL.md"
            path.write_text(path.read_text().replace("→ 04B 人物与摄影机XYZ轨迹求解\n", ""))
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("04B" in item for item in result["errors"]))

    def test_legacy_three_mode_file_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.copied_repo(temp)
            (root / "references/15-camera-movement-directing.md").write_text("legacy")
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("已废弃" in item for item in result["errors"]))

    def test_legacy_mode_phrase_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.copied_repo(temp)
            path = root / "references/05-video-prompting.md"
            path.write_text(path.read_text() + "\ncamera_decision_contract\n")
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("过时规则" in item for item in result["errors"]))

    def test_seg_limit_cannot_be_duplicated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.copied_repo(temp)
            path = root / "references/06-qc-repair-post.md"
            path.write_text(path.read_text() + "\nshot_count <= 2\n")
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("重复维护SEG数量上限" in item for item in result["errors"]))

    def test_director_cut_validator_contract_is_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.copied_repo(temp)
            path = root / "scripts/validate_director_cut_intent.py"
            path.write_text(path.read_text().replace("director_cut_intent", "removed_cut_intent"))
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("导演CUT审核合同" in item for item in result["errors"]))

    def test_director_file_cannot_claim_spatial_rule_title(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.copied_repo(temp)
            path = root / "references/15-directorial-camera-plan.md"
            path.write_text(path.read_text() + "\n## 场景方向与坐标\n")
            result = VALIDATOR.validate(root)
            self.assertFalse(result["ok"])
            self.assertTrue(any("场景方向与坐标" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
