#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_director_cut_intent", ROOT / "scripts/validate_director_cut_intent.py")
assert spec and spec.loader
MOD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MOD)


def direction(degrees: float) -> list[float]:
    radians = math.radians(degrees)
    return [math.sin(radians), math.cos(radians), 0]


def dialogue_task() -> dict:
    return {
        "shot_id": "S2", "task_type": "DIALOGUE", "scene_id": "room", "time_id": "t1",
        "primary_subject_id": "b", "viewpoint": "objective",
        "camera": {"region_id": "z2", "station_id": "STATION_B", "position_world": [1, 1, 1], "forward_world": direction(0), "height": 1.6, "shot_scale": "MS", "foreground_subject_id": "none", "background_anchor_id": "b", "motion_mode": "locked", "psychological_distance": "relationship", "primary_scene_anchor_id": "b", "visible_anchor_ids": ["b"]},
        "viewpoint_fitness": {"task_requires_new_observation": True, "selected_station_serves_task": True, "observation_signature_changed": True, "foreground_relation_changed": False, "psychological_distance_changed": False, "same_station_repetition_intent": ""},
        "required_evidence": ["focus_subject_visible", "new_visual_task_visible"],
        "visible_evidence": ["focus_subject_visible", "new_visual_task_visible"],
        "action": {"dialogue_focus_reason": "关键回答成为新重心", "focus_subject_visible": True, "new_visual_task_visible": True, "mechanical_speaker_switch": False},
    }


def eyeline_task() -> dict:
    p = dialogue_task()
    p.update(task_type="EYELINE_REVEAL", primary_subject_id="tail")
    p["camera"].update(primary_scene_anchor_id="tail", background_anchor_id="tail", visible_anchor_ids=["tail"])
    p["required_evidence"] = ["target_visible", "target_key_state_visible"]
    p["visible_evidence"] = ["target_visible", "target_key_state_visible"]
    p["action"] = {"previous_eyeline_locked": True, "target_id": "tail", "target_visible": True, "target_direction_matches": True, "target_key_state_visible": True}
    return p


def payload(cut_type="normal", mechanism="hard_cut", task=None) -> dict:
    return {
        "director_cut_intent": {
            "from_shot_id": "S1", "to_shot_id": "S2", "cut_type_intent": cut_type,
            "transition_mechanism": mechanism, "reason": "当前观察任务完成后切到新的已验证任务",
        },
        "from_shot": {"id": "S1", "scene_id": "room", "time_id": "t1"},
        "to_shot": {"id": "S2", "scene_id": "room", "time_id": "t1", "task_contract": task or dialogue_task()},
    }


class DirectorCutIntentTests(unittest.TestCase):
    def assert_error(self, data: dict, phrase: str):
        result = MOD.validate(data)
        self.assertFalse(result["ok"], result)
        self.assertTrue(any(phrase in item for item in result["errors"]), result)

    def test_normal_cut_passes(self):
        self.assertTrue(MOD.validate(payload())["ok"])

    def test_missing_intent_fails(self):
        p = payload(); p.pop("director_cut_intent")
        self.assert_error(p, "director_cut_intent")

    def test_generic_reason_fails(self):
        p = payload(); p["director_cut_intent"]["reason"] = "更有节奏"
        self.assert_error(p, "节奏感")

    def test_eyeline_requires_eyeline_task(self):
        self.assert_error(payload("eyeline", "eyeline"), "EYELINE_REVEAL")

    def test_valid_eyeline_passes(self):
        self.assertTrue(MOD.validate(payload("eyeline", "eyeline", eyeline_task()))["ok"])

    def test_match_on_action_requires_contract(self):
        self.assert_error(payload("match_on_action", "action_match"), "action_match合同")

    def test_valid_match_on_action_passes(self):
        p = payload("match_on_action", "action_match")
        p["director_cut_intent"]["action_match"] = {
            "action_id": "reach", "progress_before": 0.4, "progress_after": 0.5,
            "direction_continuous": True, "speed_continuous": True,
            "body_state_continuous": True, "prop_state_continuous": True,
        }
        result = MOD.validate(p)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["action_match_valid"])

    def test_dissolve_same_time_dialogue_fails(self):
        self.assert_error(payload("normal", "dissolve"), "dissolve")


if __name__ == "__main__":
    unittest.main(verbosity=2)
