#!/usr/bin/env python3
"""Regression tests for reference role cardinality and schema."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROMPT = load_module("validate_prompt_package_roles", "scripts/validate_prompt_package.py")


def base_payload(references: list[dict]) -> dict:
    return {
        "segment_id": "SEG01",
        "platform": "Seedance 2.0",
        "source_of_truth_version": "v1",
        "source_text": "原剧本",
        "final_prompt": "沈渊站在门内观察苏清月。",
        "target_duration": 10,
        "generation_mode": "standard",
        "shot_rule": "single_shot_per_segment",
        "segment_terminal": True,
        "references": references,
        "required_assets": ["沈渊", "苏清月"],
        "provided_assets": ["沈渊", "苏清月"],
        "dialogue_lines": [],
        "shots": [{"id": "SHOT01", "cut_type": "END"}],
        "context_scope": {
            "segment_count": 1,
            "uses_concise_asset_summaries": True,
        },
    }


class PromptReferenceRoleTests(unittest.TestCase):
    def test_single_string_role_passes(self):
        result = PROMPT.validate(
            base_payload(
                [
                    {"id": "char1", "role": "character"},
                    {"id": "scene1", "role": "scene"},
                ]
            )
        )
        self.assertTrue(result["ok"], result)

    def test_role_array_with_multiple_values_is_rejected(self):
        result = PROMPT.validate(
            base_payload([{"id": "mixed1", "role": ["character", "scene"]}])
        )
        self.assertFalse(result["ok"])
        errors = "\n".join(result["errors"])
        self.assertIn("承担多个职责", errors)
        self.assertIn("role 必须是非空字符串，不能是数组", errors)

    def test_plural_roles_field_is_rejected(self):
        result = PROMPT.validate(
            base_payload(
                [
                    {
                        "id": "mixed2",
                        "role": "character",
                        "roles": ["character", "scene"],
                    }
                ]
            )
        )
        self.assertFalse(result["ok"])
        errors = "\n".join(result["errors"])
        self.assertIn("承担多个职责", errors)
        self.assertIn("未定义字段 roles", errors)

    def test_plural_roles_single_value_still_rejected_as_schema_error(self):
        result = PROMPT.validate(
            base_payload([{"id": "legacy1", "roles": ["character"]}])
        )
        self.assertFalse(result["ok"])
        errors = "\n".join(result["errors"])
        self.assertIn("未定义字段 roles", errors)
        self.assertIn("缺少唯一 role", errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
