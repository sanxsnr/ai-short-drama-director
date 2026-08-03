#!/usr/bin/env python3
"""Regression tests for adjacent-shot visual-difference paths."""

from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts/validate_cut_geometry.py"
    spec = importlib.util.spec_from_file_location("validate_cut_geometry", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CUT = load_module()


def camera_vector(degrees: float) -> list[float]:
    radians = math.radians(degrees)
    return [math.sin(radians), math.cos(radians), 0]


def payload(
    *,
    from_subject: str = "董生",
    to_subject: str = "董生",
    from_angle: float = 0,
    to_angle: float = 0,
    from_scale: str = "MS",
    to_scale: str = "MS",
    from_viewpoint: str = "objective",
    to_viewpoint: str = "objective",
    from_time_space: str = "bedroom-night",
    to_time_space: str = "bedroom-night",
    from_stage: str = "watching",
    to_stage: str = "watching",
    declared_changes: list[str] | None = None,
    claimed_path: str = "",
    intentional_jump: bool = False,
    jump_cut_purpose: str = "",
) -> dict:
    return {
        "from_shot": {
            "id": "SHOT_A",
            "primary_subject": from_subject,
            "subject_to_camera": camera_vector(from_angle),
            "shot_scale": from_scale,
            "viewpoint": from_viewpoint,
            "time_space": from_time_space,
            "action_stage": from_stage,
        },
        "to_shot": {
            "id": "SHOT_B",
            "primary_subject": to_subject,
            "subject_to_camera": camera_vector(to_angle),
            "shot_scale": to_scale,
            "viewpoint": to_viewpoint,
            "time_space": to_time_space,
            "action_stage": to_stage,
        },
        "independent_task": True,
        "intentional_jump_cut": intentional_jump,
        "jump_cut_purpose": jump_cut_purpose,
        "declared_changes": declared_changes or [],
        "claimed_difference_path": claimed_path,
    }


class CutGeometryTests(unittest.TestCase):
    def test_dongsheng_axial_extreme_close_to_medium_passes(self):
        result = CUT.validate(
            payload(
                from_scale="ECU",
                to_scale="MS",
                from_stage="fear_in_eyes",
                to_stage="retreat_and_fall",
                claimed_path="同轴大景别",
            )
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual("axial_scale", result["derived_difference_path"])
        self.assertEqual(4, result["shot_scale_step_difference"])
        self.assertAlmostEqual(0, result["camera_angle_degrees"], places=2)
        self.assertFalse(result["thirty_degree_applicable"])

    def test_same_subject_thirty_five_degree_path_passes(self):
        result = CUT.validate(
            payload(to_angle=35, claimed_path="angle")
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual("angle", result["derived_difference_path"])
        self.assertTrue(result["thirty_degree_applicable"])

    def test_ten_degree_and_one_scale_step_fails_as_near_jump(self):
        result = CUT.validate(
            payload(to_angle=10, from_scale="MS", to_scale="MCU")
        )
        self.assertFalse(result["ok"])
        self.assertEqual("invalid_near_jump", result["derived_difference_path"])
        self.assertTrue(any("无意近似跳切" in item for item in result["errors"]))

    def test_twenty_degree_plus_adjacent_scale_passes_combined(self):
        result = CUT.validate(
            payload(
                to_angle=20,
                from_scale="MS",
                to_scale="MCU",
                from_stage="listening",
                to_stage="decision",
                claimed_path="combined",
            )
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual("combined", result["derived_difference_path"])
        self.assertTrue(result["thirty_degree_applicable"])

    def test_subject_change_makes_thirty_degree_not_applicable(self):
        result = CUT.validate(
            payload(
                from_subject="董生",
                to_subject="狐尾",
                from_scale="CU",
                to_scale="CU",
                claimed_path="subject_or_viewpoint",
            )
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual("subject_or_viewpoint", result["derived_difference_path"])
        self.assertFalse(result["thirty_degree_applicable"])

    def test_viewpoint_change_makes_thirty_degree_not_applicable(self):
        result = CUT.validate(
            payload(
                from_viewpoint="objective",
                to_viewpoint="POV",
                claimed_path="subject_or_viewpoint",
            )
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual("subject_or_viewpoint", result["derived_difference_path"])

    def test_intentional_jump_requires_purpose(self):
        result = CUT.validate(payload(intentional_jump=True, claimed_path="intentional_jump"))
        self.assertFalse(result["ok"])
        self.assertTrue(any("jump_cut_purpose" in item for item in result["errors"]))

    def test_intentional_jump_with_purpose_passes(self):
        result = CUT.validate(
            payload(
                intentional_jump=True,
                jump_cut_purpose="压缩等待时间并制造断裂感",
                claimed_path="intentional_jump",
            )
        )
        self.assertTrue(result["ok"], result)

    def test_claimed_path_mismatch_is_rejected(self):
        result = CUT.validate(
            payload(from_scale="ECU", to_scale="MS", claimed_path="angle")
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("声明的视觉差异路径" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
