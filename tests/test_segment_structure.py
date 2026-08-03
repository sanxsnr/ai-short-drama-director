#!/usr/bin/env python3
"""Regression tests for AI-direct SEG/SHOT/CUT and camera-motion semantics."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts/validate_segment_structure.py"
    spec = importlib.util.spec_from_file_location("validate_segment_structure", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SEGMENT = load_module()


def cut(node: str = "body turn", node_type: str = "body_motion") -> dict:
    return {
        "type": "MATCH-ON-ACTION",
        "action_node": node,
        "action_node_type": node_type,
        "action_progress_continuous": True,
        "screen_direction_continuous": True,
        "placement_visible": True,
        "visual_difference_sufficient": True,
        "axis_status": "same_side",
    }


def shot(
    shot_id: str,
    *,
    stage: str = "dialogue",
    task: str = "hold the current dramatic focus",
    size: object = "MS",
    direction: object = "camera_north",
    motion: object = "locked",
    focal_feel: str = "standard_perspective",
    focal_length: object | None = None,
    focal_transition: str = "",
    cut_in: object = None,
    cut_out: object = None,
    screen_direction: str = "left_to_right",
    axis_side: str = "A",
    action_signature: str = "",
    composition_signature: str = "centered_medium",
) -> dict:
    data = {
        "shot_id": shot_id,
        "shot_task": task,
        "camera_zone": "room_center",
        "camera_direction": direction,
        "shot_size": size,
        "camera_motion": motion,
        "cut_in": cut_in,
        "cut_out": cut_out,
        "focal_feel": focal_feel,
        "action_stage": stage,
        "screen_direction": screen_direction,
        "axis_side": axis_side,
        "composition_signature": composition_signature,
    }
    if focal_length is not None:
        data["focal_length_mm"] = focal_length
    if focal_transition:
        data["focal_transition"] = focal_transition
    if action_signature:
        data["action_signature"] = action_signature
    return data


def segment(content_type: str, shots: list[dict], **extra: object) -> dict:
    data = {
        "segment_id": "SEG_001",
        "duration_seconds": 10,
        "segment_content_type": content_type,
        "shots": shots,
        "shot_count": len(shots),
        "cut_count": max(0, len(shots) - 1),
        "camera_motion_phases": [],
        "time_passage": {"enabled": False},
    }
    data.update(extra)
    return data


def linked_normal_shots(count: int) -> list[dict]:
    items: list[dict] = []
    for index in range(count):
        items.append(
            shot(
                f"SHOT_{index + 1}",
                stage=f"stage_{index + 1}",
                cut_in="CUT" if index else None,
                cut_out=cut() if index < count - 1 else None,
                composition_signature=f"composition_{index + 1}",
            )
        )
    return items


def high_speed_shots(count: int) -> list[dict]:
    sizes = ["WS", "MS", "CU", "MWS", "MCU"]
    directions = ["camera_north", "camera_northeast", "camera_east", "camera_southeast", "camera_south"]
    nodes = [
        ("blade leaves scabbard", "blade"),
        ("forearm blocks", "strike"),
        ("body rolls under attack", "body_motion"),
        ("dust occludes frame", "occlusion"),
    ]
    items: list[dict] = []
    for index in range(count):
        outgoing = None
        if index < count - 1:
            node, node_type = nodes[index % len(nodes)]
            outgoing = cut(node, node_type)
        items.append(
            shot(
                f"SHOT_{index + 1}",
                stage=f"combat_stage_{index + 1}",
                task=f"advance combat stage {index + 1}",
                size=sizes[index % len(sizes)],
                direction=directions[index % len(directions)],
                cut_in="MATCH-ON-ACTION" if index else None,
                cut_out=outgoing,
                action_signature=f"combat_action_{index + 1}",
                composition_signature=f"combat_composition_{index + 1}",
            )
        )
    return items


def fixed_time_passage(**overrides: object) -> dict:
    contract = {
        "enabled": True,
        "method": "visible_day_night_light_cycle",
        "camera_locked_after_move": True,
        "scene_geometry_unchanged": True,
        "character_screen_positions_stable": True,
        "time_transition_visible": True,
    }
    contract.update(overrides)
    return contract


class SegmentStructureTests(unittest.TestCase):
    def test_01_normal_ten_second_dialogue_one_shot_passes(self):
        result = SEGMENT.validate(segment("normal", linked_normal_shots(1)))
        self.assertTrue(result["ok"], result)
        self.assertEqual(1, result["shot_count"])
        self.assertEqual(0, result["cut_count"])

    def test_02_normal_reaction_two_shots_one_cut_passes(self):
        result = SEGMENT.validate(segment("normal", linked_normal_shots(2)))
        self.assertTrue(result["ok"], result)
        self.assertEqual(2, result["shot_count"])
        self.assertEqual(1, result["cut_count"])

    def test_03_normal_three_shots_fails(self):
        result = SEGMENT.validate(segment("normal", linked_normal_shots(3)))
        self.assertFalse(result["ok"])
        self.assertIn("too_many_shots_for_normal_segment", result["error_codes"])

    def test_04_high_speed_fight_five_continuous_action_shots_passes(self):
        result = SEGMENT.validate(segment("high_speed_action", high_speed_shots(5)))
        self.assertTrue(result["ok"], result)
        self.assertEqual(5, result["shot_count"])

    def test_05_same_fight_without_high_speed_marker_fails(self):
        result = SEGMENT.validate(segment("normal", high_speed_shots(5)))
        self.assertFalse(result["ok"])
        self.assertIn("too_many_shots_for_normal_segment", result["error_codes"])

    def test_06_35_50_65mm_in_separate_shots_passes(self):
        shots = high_speed_shots(3)
        for item, focal in zip(shots, (35, 50, 65)):
            item["focal_length_mm"] = focal
        result = SEGMENT.validate(segment("high_speed_action", shots))
        self.assertTrue(result["ok"], result)
        self.assertNotIn("ambiguous_focal_transition", result["warning_codes"])

    def test_07_multiple_focals_in_one_shot_without_transition_warns(self):
        only = shot("SHOT_1", focal_length=[35, 50, 65])
        result = SEGMENT.validate(segment("normal", [only]))
        self.assertTrue(result["ok"], result)
        self.assertIn("ambiguous_focal_transition", result["warning_codes"])

    def test_08_medium_wide_pushes_to_medium_and_remains_one_shot(self):
        only = shot(
            "SHOT_1",
            size={"start": "MWS", "end": "MS"},
            motion="camera_push_in",
            focal_length=[35, 50],
            focal_transition="camera_push_in",
        )
        result = SEGMENT.validate(
            segment(
                "normal",
                [only],
                camera_motion_phases=[
                    {
                        "shot_id": "SHOT_1",
                        "start_state": "medium_wide_two_shot",
                        "movement": "camera_push_in",
                        "end_state": "medium_shot",
                        "lock_after_move": False,
                    }
                ],
            )
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(1, result["shot_count"])

    def test_09_axial_extreme_close_hard_cut_to_medium_wide_passes(self):
        first = shot(
            "SHOT_1",
            stage="pupil_contracts",
            size="ECU",
            cut_out={"type": "CUT", "action_node": "pupil contraction completes"},
        )
        second = shot(
            "SHOT_2",
            stage="body_retreats",
            size="MWS",
            cut_in="CUT",
            composition_signature="full_body_retreat",
        )
        result = SEGMENT.validate(segment("normal", [first, second]))
        self.assertTrue(result["ok"], result)

    def test_10_extreme_close_pullback_to_full_body_is_one_shot(self):
        only = shot(
            "SHOT_1",
            stage="fear_to_retreat",
            size={"start": "ECU", "end": "WS"},
            motion="camera_pull_back",
            focal_length=[85, 35],
            focal_transition="camera_pull_back",
            composition_signature="eye_expands_to_full_body",
        )
        result = SEGMENT.validate(segment("normal", [only]))
        self.assertTrue(result["ok"], result)
        self.assertEqual(1, result["shot_count"])

    def test_11_locked_round_window_day_night_passes_as_one_shot(self):
        only = shot(
            "SHOT_1",
            stage="time_passage",
            task="show repeated day and night through the same round-window composition",
            size="MS",
            motion="locked",
            composition_signature="locked_round_window",
        )
        result = SEGMENT.validate(
            segment(
                "fixed_camera_time_passage",
                [only],
                time_passage=fixed_time_passage(),
            )
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["time_passage_checks"]["camera_locked_after_move"])

    def test_12_push_to_round_window_then_lock_and_time_passes_as_one_shot(self):
        only = shot(
            "SHOT_1",
            stage="push_then_time_passage",
            task="push from bedside to round window, lock, then show day-night changes",
            size={"start": "MS", "end": "window_detail"},
            motion="push_then_lock",
            composition_signature="bedside_to_round_window",
        )
        result = SEGMENT.validate(
            segment(
                "fixed_camera_time_passage",
                [only],
                camera_motion_phases=[
                    {
                        "shot_id": "SHOT_1",
                        "start_state": "bedside_two_shot",
                        "movement": "camera_push_in",
                        "end_state": "round_window_locked_frame",
                        "lock_after_move": True,
                    }
                ],
                time_passage=fixed_time_passage(),
            )
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(1, result["shot_count"])

    def test_13_fixed_time_passage_miswritten_as_three_camera_positions_fails(self):
        result = SEGMENT.validate(
            segment(
                "fixed_camera_time_passage",
                linked_normal_shots(3),
                time_passage=fixed_time_passage(),
            )
        )
        self.assertFalse(result["ok"])
        self.assertIn(
            "fixed_camera_time_passage_requires_single_shot",
            result["error_codes"],
        )

    def test_14_normal_entry_dialogue_and_hide_prop_in_three_shots_fails(self):
        shots = linked_normal_shots(3)
        shots[0]["action_stage"] = "enter_room"
        shots[1]["action_stage"] = "deliver_dialogue"
        shots[2]["action_stage"] = "hide_prop"
        result = SEGMENT.validate(segment("normal", shots))
        self.assertFalse(result["ok"])
        self.assertIn("too_many_shots_for_normal_segment", result["error_codes"])

    def test_declared_counts_cannot_hide_explicit_shot_boundaries(self):
        payload = segment("normal", linked_normal_shots(3))
        payload["shot_count"] = 1
        payload["cut_count"] = 0
        result = SEGMENT.validate(payload)
        self.assertFalse(result["ok"])
        self.assertIn("shot_count_mismatch", result["error_codes"])
        self.assertIn("cut_count_mismatch", result["error_codes"])
        self.assertIn("too_many_shots_for_normal_segment", result["error_codes"])

    def test_module_aliases_cannot_replace_required_segment_shot_fields(self):
        alias_only_shot = {
            "shot_id": "SHOT_1",
            "task_type": "time_passage",
            "camera_zone_id": "round_window_axis",
            "camera_forward_world": "+Y",
            "shot_size": "MS",
            "camera_motion": "push_then_lock",
            "cut_in": None,
            "cut_out": None,
            "focal_feel": "standard_perspective",
            "phase_task": "push_to_window_then_show_day_night",
        }
        result = SEGMENT.validate(
            segment(
                "fixed_camera_time_passage",
                [alias_only_shot],
                time_passage=fixed_time_passage(),
            )
        )
        self.assertFalse(result["ok"])
        self.assertIn("incomplete_shot_structure", result["error_codes"])
        self.assertTrue(any("shot_task" in error for error in result["errors"]))
        self.assertTrue(any("camera_zone" in error for error in result["errors"]))
        self.assertTrue(any("camera_direction" in error for error in result["errors"]))
        self.assertTrue(any("action_stage" in error for error in result["errors"]))

    def test_high_speed_repeated_action_is_rejected(self):
        shots = high_speed_shots(3)
        shots[2]["action_signature"] = shots[1]["action_signature"]
        result = SEGMENT.validate(segment("high_speed_action", shots))
        self.assertFalse(result["ok"])
        self.assertIn("repeated_action", result["error_codes"])

    def test_high_speed_cut_without_action_node_is_rejected(self):
        shots = high_speed_shots(3)
        shots[0]["cut_out"]["action_node"] = ""
        result = SEGMENT.validate(segment("high_speed_action", shots))
        self.assertFalse(result["ok"])
        self.assertIn("missing_action_cut_node", result["error_codes"])

    def test_high_speed_cross_axis_direction_jump_and_invisible_reposition_fail(self):
        shots = high_speed_shots(3)
        shots[0]["cut_out"].update(
            {
                "axis_status": "crossed_without_reestablish",
                "screen_direction_continuous": False,
                "placement_visible": False,
            }
        )
        shots[1]["screen_direction"] = "right_to_left"
        shots[1]["axis_side"] = "B"
        result = SEGMENT.validate(segment("high_speed_action", shots))
        self.assertFalse(result["ok"])
        self.assertIn("cross_axis_in_high_speed_action", result["error_codes"])
        self.assertIn("discontinuous_screen_direction", result["error_codes"])
        self.assertIn("invisible_reposition", result["error_codes"])

    def test_high_speed_near_duplicate_adjacent_shots_fail(self):
        shots = high_speed_shots(3)
        for field in ("shot_size", "camera_direction", "composition_signature"):
            shots[1][field] = shots[0][field]
        result = SEGMENT.validate(segment("high_speed_action", shots))
        self.assertFalse(result["ok"])
        self.assertIn("near_duplicate_action_cut", result["error_codes"])

    def test_fixed_time_passage_requires_locked_geometry_and_visible_transition(self):
        only = shot("SHOT_1", stage="time_passage", motion="locked")
        result = SEGMENT.validate(
            segment(
                "fixed_camera_time_passage",
                [only],
                time_passage=fixed_time_passage(
                    camera_locked_after_move=False,
                    scene_geometry_unchanged=False,
                    character_screen_positions_stable=False,
                    time_transition_visible=False,
                ),
            )
        )
        self.assertFalse(result["ok"])
        self.assertIn("invalid_fixed_camera_time_passage", result["error_codes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
