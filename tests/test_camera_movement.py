#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_camera_movement", ROOT / "scripts/validate_camera_movement.py")
assert spec and spec.loader
VALIDATOR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(VALIDATOR)


def base(mode="movement"):
    return {
        "shot_id": "SHOT-01",
        "segment_content_type": "normal",
        "duration_seconds": 10,
        "camera_decision": {"mode": mode, "reason": "连续揭示空间锚点", "narrative_function": "把注意力从人物关系移到圆窗", "rejected_alternative": "CUT会打断时间连续性"},
        "decision_context": {
            "same_subject": True, "same_time": True, "same_space": True,
            "same_observation_task": True, "continuous_reframe_only": True,
            "new_independent_task": False, "movement_path_feasible": True,
            "movement_has_narrative_value": True, "cut_narrative_advantage": False,
            "time_passage_after_lock": False,
        },
        "camera_motion": {
            "enabled": mode == "movement", "movement_type": "缓慢推进",
            "start_camera_zone": "bed_head", "start_direction": "toward_window",
            "start_height": "eye", "start_framing": "双人中景", "start_subject_relation": "两人同框",
            "path": {"path_description": "沿床侧通道推进至圆窗", "spatial_axes": ["Z"], "path_clear": True, "axis_side_preserved": True, "axis_reestablished": False, "intersects_subject": False, "intersects_obstacle": False},
            "speed_profile": {"start_speed": "缓慢起步", "middle_speed": "匀速", "end_speed": "减速停稳"},
            "subject_relation_during_move": "逐渐离开人物关系构图", "information_revealed_during_move": ["圆窗"],
            "required_action_during_move": False, "action_visible_during_move": True,
            "movement_duration_seconds": 5, "minimum_required_seconds": 4,
            "end_camera_zone": "window", "end_direction": "toward_window", "end_height": "eye",
            "end_framing": "圆窗主构图", "end_subject_relation": "人物退为环境元素",
            "lock_after_move": True, "lock_duration_seconds": 5,
        },
    }


class CameraMovementTests(unittest.TestCase):
    def assert_error(self, payload, code):
        result = VALIDATOR.validate(payload)
        self.assertFalse(result["ok"], result)
        self.assertIn(code, result["error_codes"])

    def test_movement_passes(self):
        self.assertTrue(VALIDATOR.validate(base())["ok"])

    def test_locked_dialogue_passes(self):
        p = base("locked")
        p["camera_decision"].update(reason="稳定口型与细微表演", narrative_function="让人物在固定构图内完成对白")
        p["decision_context"].update(continuous_reframe_only=False, movement_has_narrative_value=False)
        p["camera_motion"] = {"enabled": False}
        self.assertTrue(VALIDATOR.validate(p)["ok"])

    def test_generic_purpose_fails(self):
        p = base(); p["camera_decision"].update(reason="电影感", narrative_function="电影感")
        self.assert_error(p, "unmotivated_camera_movement")

    def test_missing_start_framing_fails(self):
        p = base(); p["camera_motion"]["start_framing"] = ""
        self.assert_error(p, "missing_start_framing")

    def test_obstacle_fails(self):
        p = base(); p["camera_motion"]["path"]["intersects_obstacle"] = True
        self.assert_error(p, "camera_path_intersects_obstacle")

    def test_axis_crossing_fails(self):
        p = base(); p["camera_motion"]["path"].update(axis_side_preserved=False, axis_reestablished=False)
        self.assert_error(p, "camera_path_crosses_axis")

    def test_three_axes_fail_for_normal(self):
        p = base(); p["camera_motion"]["path"]["spatial_axes"] = ["X", "Y", "Z"]
        self.assert_error(p, "too_many_camera_motion_axes")

    def test_three_axes_pass_for_justified_high_speed(self):
        p = base(); p["segment_content_type"] = "high_speed_action"
        p["decision_context"]["multi_axis_justified"] = True
        p["camera_motion"]["action_readability_preserved"] = True
        p["camera_motion"]["path"]["spatial_axes"] = ["X", "Y", "Z"]
        self.assertTrue(VALIDATOR.validate(p)["ok"])

    def test_time_passage_requires_lock(self):
        p = base(); p["segment_content_type"] = "fixed_camera_time_passage"
        p["decision_context"]["time_passage_after_lock"] = True
        p["camera_motion"]["lock_after_move"] = False
        self.assert_error(p, "missing_lock_after_move")

    def test_distinct_tasks_cannot_be_forced_into_move(self):
        p = base(); p["decision_context"].update(new_independent_task=True, same_observation_task=False)
        self.assert_error(p, "forced_movement_across_distinct_tasks")

    def test_unnecessary_cut_fails(self):
        p = base("cut_to_new_shot"); p["camera_motion"] = {"enabled": False}
        self.assert_error(p, "unnecessary_cut_for_continuous_reframe")

    def test_valid_reverse_cut_passes(self):
        p = base("cut_to_new_shot"); p["camera_motion"] = {"enabled": False}
        p["decision_context"].update(same_observation_task=False, continuous_reframe_only=False, new_independent_task=True, movement_has_narrative_value=False, cut_narrative_advantage=True)
        p["camera_decision"].update(reason="从董生跌地反打阿琐下床", narrative_function="切换威胁对象与低位压迫关系")
        self.assertTrue(VALIDATOR.validate(p)["ok"])

    def test_action_visibility_fails(self):
        p = base(); p["camera_motion"].update(required_action_during_move=True, action_visible_during_move=False)
        self.assert_error(p, "movement_loses_required_action")

    def test_subject_motion_conflict_fails(self):
        p = base(); p["subject_motion"] = {"camera_relative_motion_conflict": True}
        self.assert_error(p, "camera_and_subject_motion_conflict")

    def test_duration_fails(self):
        p = base(); p["camera_motion"].update(movement_duration_seconds=3, minimum_required_seconds=4)
        self.assert_error(p, "movement_duration_insufficient")

    def test_large_close_orbit_warns(self):
        p = base(); p["camera_motion"].update(start_framing="CU")
        p["camera_motion"]["path"]["orbit_degrees"] = 120
        result = VALIDATOR.validate(p)
        self.assertTrue(result["ok"], result)
        self.assertIn("close_range_large_orbit_risk", result["warning_codes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
