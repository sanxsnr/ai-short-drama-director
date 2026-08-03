#!/usr/bin/env python3
"""Regression tests for 30-degree applicability and visual-difference paths."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    path = ROOT / "scripts/validate_cut_geometry.py"
    spec = importlib.util.spec_from_file_location("validate_cut_geometry", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()


def base_payload() -> dict:
    return {
        "transition_id": "CUT01-02",
        "independent_task": True,
        "same_primary_subject": True,
        "same_time": True,
        "same_space": True,
        "same_action_stage": True,
        "same_observation_perspective": True,
        "similar_composition": True,
        "shot_scale_before": "MS",
        "shot_scale_after": "MCU",
        "camera_angle_degrees": 35,
        "axis_status": "same_side",
        "visual_difference_path": "standard",
        "changed_dimensions": ["camera_angle", "shot_scale"],
        "dominant_change": "",
        "editing_device": "none",
        "thirty_degree_status": "applies",
    }


class CutGeometryTests(unittest.TestCase):
    def test_dongsheng_same_axis_large_scale_jump_passes(self):
        payload = base_payload()
        payload.update(
            {
                "transition_id": "DONGSHENG-08A-08B",
                "same_action_stage": False,
                "similar_composition": False,
                "shot_scale_before": "眼部极近特写",
                "shot_scale_after": "中景",
                "camera_angle_degrees": 0,
                "visual_difference_path": "dominant",
                "changed_dimensions": ["shot_scale", "action_stage", "composition_center"],
                "dominant_change": "same_axis_scale_jump",
                "thirty_degree_status": "exempt",
            }
        )
        result = VALIDATOR.validate(payload)
        self.assertTrue(result["ok"], result)
        self.assertEqual("exempt", result["derived_thirty_degree_status"])
        self.assertGreaterEqual(result["scale_difference"], 2)

    def test_near_duplicate_under_30_degrees_is_rejected(self):
        payload = base_payload()
        payload["camera_angle_degrees"] = 10
        result = VALIDATOR.validate(payload)
        self.assertFalse(result["ok"])
        self.assertTrue(any("30度规则适用" in item for item in result["errors"]))

    def test_standard_path_over_30_degrees_passes(self):
        result = VALIDATOR.validate(base_payload())
        self.assertTrue(result["ok"], result)

    def test_eyeline_new_subject_is_not_applicable(self):
        payload = base_payload()
        payload.update(
            {
                "same_primary_subject": False,
                "same_action_stage": False,
                "similar_composition": False,
                "shot_scale_before": "CU",
                "shot_scale_after": "CU",
                "camera_angle_degrees": 0,
                "visual_difference_path": "dominant",
                "changed_dimensions": ["primary_subject", "new_information"],
                "dominant_change": "new_primary_subject",
                "thirty_degree_status": "not_applicable",
            }
        )
        result = VALIDATOR.validate(payload)
        self.assertTrue(result["ok"], result)

    def test_cross_axis_cannot_be_saved_by_30_degrees(self):
        payload = base_payload()
        payload["camera_angle_degrees"] = 45
        payload["axis_status"] = "crossed_without_reestablish"
        result = VALIDATOR.validate(payload)
        self.assertFalse(result["ok"])
        self.assertTrue(any("180度轴线" in item for item in result["errors"]))

    def test_one_level_same_axis_cannot_claim_scale_jump(self):
        payload = base_payload()
        payload.update(
            {
                "same_action_stage": False,
                "similar_composition": False,
                "camera_angle_degrees": 0,
                "visual_difference_path": "dominant",
                "changed_dimensions": ["shot_scale", "action_stage"],
                "dominant_change": "same_axis_scale_jump",
                "thirty_degree_status": "exempt",
            }
        )
        result = VALIDATOR.validate(payload)
        self.assertFalse(result["ok"])
        self.assertTrue(any("至少跨越两级" in item for item in result["errors"]))

    def test_status_mismatch_is_rejected(self):
        payload = base_payload()
        payload["thirty_degree_status"] = "exempt"
        result = VALIDATOR.validate(payload)
        self.assertFalse(result["ok"])
        self.assertTrue(any("适用性声明错误" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
