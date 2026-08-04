#!/usr/bin/env python3
"""Regression tests for SHOT task, action coverage, and viewpoint fitness."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts/validate_shot_task.py"
    spec = importlib.util.spec_from_file_location("validate_shot_task", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TASK = load_module()


def base_camera(station_id: str = "STATION_ENTRY") -> dict:
    return {
        "region_id": "ROOM_SIDE_A",
        "station_id": station_id,
        "position_world": [10.5, 4.5, 1.6],
        "forward_world": [1, 0, 0],
        "height": 1.6,
        "shot_scale": "medium",
        "foreground_subject_id": "",
        "background_anchor_id": "east_door_frame",
        "motion_mode": "locked",
        "psychological_distance": "observational",
        "primary_scene_anchor_id": "east_door_threshold",
        "visible_anchor_ids": [
            "east_door_threshold",
            "east_door_frame",
            "entry_path",
        ],
    }


def fitness(*, changed: bool = True, requires_new: bool = True, repeat_intent: str = "") -> dict:
    return {
        "task_requires_new_observation": requires_new,
        "selected_station_serves_task": True,
        "observation_signature_changed": changed,
        "foreground_relation_changed": False,
        "psychological_distance_changed": False,
        "same_station_repetition_intent": repeat_intent,
    }


def entry_contract() -> dict:
    return {
        "shot_id": "SHOT_02",
        "task_type": "ENTER",
        "scene_id": "torture_room",
        "time_id": "night_01",
        "primary_subject_id": "su_qingyue",
        "viewpoint": "objective",
        "camera": base_camera(),
        "viewpoint_fitness": fitness(),
        "required_evidence": [
            "door_frame_visible",
            "threshold_crossing_visible",
            "entry_direction_visible",
            "inside_stop_visible",
        ],
        "visible_evidence": [
            "door_frame_visible",
            "threshold_crossing_visible",
            "entry_direction_visible",
            "inside_stop_visible",
        ],
        "action": {
            "actor_id": "su_qingyue",
            "start_zone_id": "outside_east",
            "boundary_id": "east_door_threshold",
            "end_zone_id": "inside_east",
            "state_before": "outside",
            "state_after": "inside",
            "state_path": "actors.su_qingyue.zone_state",
            "movement_world": [-1, 0, 0],
            "crossing_visible": True,
            "path_visible": True,
            "movement_crosses_boundary": True,
        },
    }


class ShotTaskTests(unittest.TestCase):
    def test_correct_door_entry_passes(self):
        result = TASK.validate(entry_contract())
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["derived_independent_task"])
        self.assertTrue(result["viewpoint_fitness_passed"])
        self.assertEqual("STATION_ENTRY", result["observation_signature"]["camera_station_id"])

    def test_side_character_shot_without_boundary_fails_entry(self):
        contract = entry_contract()
        contract["camera"].update(
            {
                "station_id": "STATION_POST_SIDE",
                "primary_scene_anchor_id": "su_qingyue",
                "background_anchor_id": "su_qingyue",
                "visible_anchor_ids": ["su_qingyue"],
            }
        )
        contract["visible_evidence"] = ["inside_stop_visible"]
        contract["action"]["crossing_visible"] = False
        contract["action"]["path_visible"] = False
        result = TASK.validate(contract)
        self.assertFalse(result["ok"])
        self.assertTrue(any("边界锚点" in item for item in result["errors"]))
        self.assertTrue(any("主要场景锚点" in item for item in result["errors"]))

    def test_actor_already_inside_cannot_enter_again(self):
        contract = entry_contract()
        contract["action"]["state_before"] = "inside"
        result = TASK.validate(contract)
        self.assertFalse(result["ok"])
        self.assertTrue(any("不得重复进场" in item for item in result["errors"]))

    def test_eyeline_reveal_requires_target_key_state(self):
        contract = {
            "shot_id": "SHOT_B",
            "task_type": "EYELINE_REVEAL",
            "scene_id": "bedroom",
            "time_id": "night_01",
            "primary_subject_id": "fox_tail",
            "viewpoint": "objective",
            "camera": {
                **base_camera("STATION_DONGSHENG_POV_SIDE"),
                "position_world": [3, 5, 1.5],
                "forward_world": [0, 1, 0],
                "height": 1.5,
                "background_anchor_id": "fox_tail",
                "primary_scene_anchor_id": "fox_tail",
                "visible_anchor_ids": ["fox_tail"],
            },
            "viewpoint_fitness": fitness(),
            "required_evidence": ["tail_visible"],
            "visible_evidence": ["tail_visible"],
            "action": {
                "previous_eyeline_locked": True,
                "target_id": "fox_tail",
                "target_visible": True,
                "target_direction_matches": True,
                "target_key_state_visible": False,
            },
        }
        result = TASK.validate(contract)
        self.assertFalse(result["ok"])
        self.assertTrue(any("关键状态" in item for item in result["errors"]))

    def test_ots_label_without_geometry_evidence_fails(self):
        contract = entry_contract()
        contract["task_type"] = "DIALOGUE"
        contract["viewpoint"] = "OTS"
        contract["viewpoint_evidence"] = {
            "foreground_character_id": "shen_yuan",
            "foreground_shoulder_visible": False,
            "focus_subject_id": "su_qingyue",
            "axis_valid": True,
        }
        contract["camera"]["foreground_subject_id"] = "shen_yuan"
        contract["action"] = {
            "dialogue_focus_reason": "关键回答",
            "focus_subject_visible": True,
            "new_visual_task_visible": True,
            "mechanical_speaker_switch": False,
        }
        result = TASK.validate(contract)
        self.assertFalse(result["ok"])
        self.assertTrue(any("foreground_shoulder_visible" in item for item in result["errors"]))

    def test_dialogue_same_view_without_reason_fails(self):
        contract = entry_contract()
        contract["task_type"] = "DIALOGUE"
        contract["viewpoint_fitness"] = fitness(changed=False, requires_new=True)
        contract["action"] = {
            "dialogue_focus_reason": "换人说话",
            "focus_subject_visible": True,
            "new_visual_task_visible": True,
            "mechanical_speaker_switch": False,
        }
        result = TASK.validate(contract)
        self.assertFalse(result["ok"])
        self.assertIn("mechanical_dialogue_view_repetition", result["errors"])

    def test_dialogue_same_station_with_explicit_standoff_intent_passes(self):
        contract = entry_contract()
        contract["task_type"] = "DIALOGUE"
        contract["viewpoint_fitness"] = fitness(
            changed=False,
            requires_new=True,
            repeat_intent="保持审讯式固定观察，强化权力僵持",
        )
        contract["action"] = {
            "dialogue_focus_reason": "关键威胁落地",
            "focus_subject_visible": True,
            "new_visual_task_visible": True,
            "mechanical_speaker_switch": False,
        }
        result = TASK.validate(contract)
        self.assertTrue(result["ok"], result)

    def test_missing_camera_station_fails(self):
        contract = entry_contract()
        contract["camera"]["station_id"] = ""
        result = TASK.validate(contract)
        self.assertFalse(result["ok"])
        self.assertTrue(any("camera.station_id" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
