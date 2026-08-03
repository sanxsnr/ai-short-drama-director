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
    from_time: str = "night",
    to_time: str = "night",
    from_space: str = "bedroom",
    to_space: str = "bedroom",
    from_stage: str = "watching",
    to_stage: str = "watching",
    claimed_path: str = "",
    editing_device: str = "none",
    editing_device_purpose: str = "",
    graphic_match_basis: str = "",
    axis_status: str = "same_side",
    axis_required: bool = True,
    from_extra: dict | None = None,
    to_extra: dict | None = None,
) -> dict:
    from_shot = {
        "id": "SHOT_A",
        "primary_subject": from_subject,
        "subject_to_camera": camera_vector(from_angle),
        "shot_scale": from_scale,
        "viewpoint": from_viewpoint,
        "time": from_time,
        "space": from_space,
        "action_stage": from_stage,
    }
    to_shot = {
        "id": "SHOT_B",
        "primary_subject": to_subject,
        "subject_to_camera": camera_vector(to_angle),
        "shot_scale": to_scale,
        "viewpoint": to_viewpoint,
        "time": to_time,
        "space": to_space,
        "action_stage": to_stage,
    }
    from_shot.update(from_extra or {})
    to_shot.update(to_extra or {})
    return {
        "transition_id": "CUT_A_B",
        "from_shot": from_shot,
        "to_shot": to_shot,
        "independent_task": True,
        "axis_status": axis_status,
        "axis_required": axis_required,
        "editing_device": editing_device,
        "editing_device_purpose": editing_device_purpose,
        "graphic_match_basis": graphic_match_basis,
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
        result = CUT.validate(payload(to_angle=35, claimed_path="angle"))
        self.assertTrue(result["ok"], result)
        self.assertEqual("angle", result["derived_difference_path"])
        self.assertTrue(result["thirty_degree_applicable"])
        self.assertEqual("met", result["thirty_degree_status"])

    def test_ten_degree_and_one_scale_step_fails_as_near_jump(self):
        result = CUT.validate(
            payload(to_angle=10, from_scale="MS", to_scale="MCU")
        )
        self.assertFalse(result["ok"])
        self.assertEqual("invalid_near_jump", result["derived_difference_path"])
        self.assertTrue(any("无意近似跳切" in item for item in result["errors"]))

    def test_action_stage_cannot_replace_visual_difference(self):
        result = CUT.validate(
            payload(to_angle=5, from_stage="watching", to_stage="retreating")
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("不能代替画面差异" in item for item in result["errors"]))

    def test_one_scale_step_plus_action_stage_is_not_enough(self):
        result = CUT.validate(
            payload(
                from_scale="MS",
                to_scale="MCU",
                from_stage="watching",
                to_stage="decision",
            )
        )
        self.assertFalse(result["ok"])
        self.assertEqual(["shot_scale_1"], result["moderate_visual_changes"])

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
        self.assertEqual(
            "not_met_but_equivalent_visual_path", result["thirty_degree_status"]
        )

    def test_one_scale_step_plus_composition_change_passes_combined(self):
        result = CUT.validate(
            payload(
                from_scale="MS",
                to_scale="MCU",
                from_extra={"composition_center": "two_shot_center"},
                to_extra={"composition_center": "solo_left_third"},
                claimed_path="combined",
            )
        )
        self.assertTrue(result["ok"], result)
        self.assertIn("composition_center", result["moderate_visual_changes"])

    def test_subject_change_makes_thirty_degree_not_applicable(self):
        result = CUT.validate(
            payload(
                from_subject="董生",
                to_subject="狐尾",
                from_scale="CU",
                to_scale="CU",
                claimed_path="subject_or_viewpoint",
                axis_status="not_applicable",
                axis_required=False,
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

    def test_time_change_is_separate_from_space_change(self):
        result = CUT.validate(
            payload(to_time="morning", claimed_path="subject_or_viewpoint")
        )
        self.assertTrue(result["ok"], result)
        self.assertFalse(result["same_time"])
        self.assertTrue(result["same_space"])

    def test_space_change_is_separate_from_time_change(self):
        result = CUT.validate(
            payload(to_space="courtyard", claimed_path="subject_or_viewpoint")
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["same_time"])
        self.assertFalse(result["same_space"])

    def test_cross_axis_cannot_be_saved_by_large_angle(self):
        result = CUT.validate(
            payload(
                to_angle=45,
                claimed_path="angle",
                axis_status="crossed_without_reestablish",
            )
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("180度轴线" in item for item in result["errors"]))

    def test_axis_required_rejects_not_applicable(self):
        result = CUT.validate(payload(axis_status="not_applicable", axis_required=True))
        self.assertFalse(result["ok"])
        self.assertTrue(any("axis_required=true" in item for item in result["errors"]))

    def test_intentional_jump_requires_purpose(self):
        result = CUT.validate(
            payload(
                editing_device="intentional_jump_cut",
                claimed_path="intentional_jump",
            )
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("editing_device_purpose" in item for item in result["errors"]))

    def test_intentional_jump_with_purpose_passes(self):
        result = CUT.validate(
            payload(
                editing_device="intentional_jump_cut",
                editing_device_purpose="压缩等待时间并制造断裂感",
                claimed_path="intentional_jump",
            )
        )
        self.assertTrue(result["ok"], result)

    def test_graphic_match_requires_basis(self):
        result = CUT.validate(
            payload(
                editing_device="graphic_match",
                editing_device_purpose="以圆形构图连接两处空间",
                claimed_path="graphic_match",
            )
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("graphic_match_basis" in item for item in result["errors"]))

    def test_graphic_match_with_basis_passes(self):
        result = CUT.validate(
            payload(
                editing_device="graphic_match",
                editing_device_purpose="以圆形构图连接两处空间",
                graphic_match_basis="圆窗与月亮保持相同画面位置和尺寸",
                claimed_path="graphic_match",
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
