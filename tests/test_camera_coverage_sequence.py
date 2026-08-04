#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "validate_camera_coverage_sequence",
    ROOT / "scripts/validate_camera_coverage_sequence.py",
)
assert spec and spec.loader
VALIDATOR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(VALIDATOR)


def coverage_shot(
    shot_id: str,
    station: str,
    position: list[float],
    forward: list[float],
    *,
    scale: str = "MS",
    subject: str = "A",
    foreground: str = "none",
    background: str = "wall_a",
    viewpoint: str = "objective",
    motion: str = "locked",
    psychological_distance: str = "relationship",
    inherited: bool = False,
    repetition_intent: str = "",
    repetition_payoff: str = "",
) -> dict:
    return {
        "shot_id": shot_id,
        "solution_lock_scope": "shot",
        "camera_station_id": station,
        "camera_region_id": "same_axis_side",
        "camera_position_world": position,
        "camera_forward_world": forward,
        "camera_height": position[2],
        "shot_scale": scale,
        "primary_subject_id": subject,
        "foreground_subject_id": foreground,
        "background_anchor_id": background,
        "viewpoint_type": viewpoint,
        "motion_mode": motion,
        "psychological_distance": psychological_distance,
        "camera_station_inherited_from_previous": inherited,
        "repetition_intent": repetition_intent,
        "repetition_payoff": repetition_payoff,
    }


class CameraCoverageSequenceTests(unittest.TestCase):
    def test_multi_station_medium_shot_coverage_passes(self):
        shots = [
            coverage_shot("S1", "A_OTS_DONG", [2, 2, 1.5], [0, 1, 0], subject="asuo", foreground="dong_shoulder", background="bed"),
            coverage_shot("S2", "B_OTS_ASUO", [6, 2, 1.5], [0, 1, 0], subject="dong", foreground="asuo_shoulder", background="door_wall"),
            coverage_shot("S3", "C_TWO_SHOT", [4, 1, 1.6], [0, 1, 0], subject="both", background="bed_and_door"),
            coverage_shot("S4", "D_LOW_FLOOR", [3, 3, 0.5], [0, 1, 0], subject="dong", background="bed_leg", psychological_distance="vulnerability"),
            coverage_shot("S5", "E_BED_FOOT", [4, 6, 1.4], [0, -1, 0], subject="both", background="room_depth", motion="track"),
        ]
        result = VALIDATOR.validate({"scene_id": "dong_room", "shots": shots})
        self.assertTrue(result["ok"], result)
        self.assertEqual(5, result["unique_camera_station_count"])

    def test_same_station_same_view_only_swapping_subject_fails(self):
        shots = [
            coverage_shot("S1", "G_A", [2, 2, 1.5], [0, 1, 0], subject="asuo", foreground="dong_shoulder", background="wood_wall"),
            coverage_shot("S2", "G_A", [2, 2, 1.5], [0, 1, 0], subject="dong", foreground="dong_shoulder", background="wood_wall", inherited=True),
            coverage_shot("S3", "G_A", [2, 2, 1.5], [0, 1, 0], subject="asuo", foreground="dong_shoulder", background="wood_wall", inherited=True),
            coverage_shot("S4", "G_A", [2, 2, 1.5], [0, 1, 0], subject="dong", foreground="dong_shoulder", background="wood_wall", inherited=True),
        ]
        result = VALIDATOR.validate({"scene_id": "dong_room", "shots": shots})
        self.assertFalse(result["ok"], result)
        self.assertIn("repetitive_observation_sequence", result["error_codes"])
        self.assertIn("single_station_scene_coverage", result["error_codes"])

    def test_repeated_fixed_station_with_explicit_time_passage_intent_passes(self):
        shots = [coverage_shot("S1", "TIME_MASTER", [4, 2, 1.6], [0, 1, 0], subject="room")]
        for index in range(2, 5):
            shots.append(
                coverage_shot(
                    f"S{index}", "TIME_MASTER", [4, 2, 1.6], [0, 1, 0],
                    subject="room", inherited=True,
                    repetition_intent="固定同构图见证时间流逝",
                    repetition_payoff="人物状态与昼夜变化累积形成叙事回报",
                )
            )
        result = VALIDATOR.validate({"scene_id": "time_passage", "shots": shots})
        self.assertTrue(result["ok"], result)

    def test_camera_inheritance_after_cut_requires_reason(self):
        shots = [
            coverage_shot("S1", "A", [2, 2, 1.5], [0, 1, 0]),
            coverage_shot("S2", "A", [2, 2, 1.5], [0, 1, 0], inherited=True),
        ]
        result = VALIDATOR.validate({"scene_id": "room", "shots": shots})
        self.assertFalse(result["ok"], result)
        self.assertIn("camera_inherited_without_directorial_reason", result["error_codes"])

    def test_solution_lock_must_be_shot_scoped(self):
        shot = coverage_shot("S1", "A", [2, 2, 1.5], [0, 1, 0])
        shot["solution_lock_scope"] = "scene"
        result = VALIDATOR.validate({"scene_id": "room", "shots": [shot]})
        self.assertFalse(result["ok"], result)
        self.assertIn("invalid_solution_lock_scope", result["error_codes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
