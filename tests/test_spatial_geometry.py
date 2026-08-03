#!/usr/bin/env python3
"""Regression tests for subject/target/movement/camera geometry."""

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


GEOMETRY = load_module("validate_spatial_geometry", "scripts/validate_spatial_geometry.py")


def dongsheng_payload() -> dict:
    return {
        "scene_id": "董生卧房-第08镜",
        "subject": {
            "id": "董生",
            "position": [0, 0, 0],
            "facing": [0, 1, 0],
            "story_target": "床榻",
            "gaze_target": "床榻",
            "distance_target": "床榻",
            "movement": [0, -1, 0],
            "movement_mode": "backward",
            "distance_relation": "away",
            "must_face_story_target": True,
        },
        "targets": {
            "床榻": {"position": [0, 5, 0]},
        },
        "camera": {
            "id": "D",
            "position": [0, 4, 1.5],
            "claimed_visible_face": "front_or_near_front",
            "same_direction_as_story_target": True,
            "subject_appears_to_look_toward_lens": True,
        },
        "locked_solution": True,
        "alternative_camera_solutions": [],
    }


class SpatialGeometryTests(unittest.TestCase):
    def test_dongsheng_front_retreat_passes(self):
        result = GEOMETRY.validate(dongsheng_payload())
        self.assertTrue(result["ok"], result)
        self.assertEqual("front", result["derived"]["visible_face"])
        self.assertEqual("backward", result["derived"]["movement_to_facing"])
        self.assertEqual("away", result["derived"]["distance_relation"])
        self.assertTrue(result["derived"]["lens_gaze_motivated"])

    def test_side_camera_cannot_claim_front(self):
        payload = dongsheng_payload()
        payload["camera"]["position"] = [5, 0, 1.5]
        payload["camera"]["same_direction_as_story_target"] = False
        payload["camera"]["subject_appears_to_look_toward_lens"] = False
        result = GEOMETRY.validate(payload)
        self.assertFalse(result["ok"])
        self.assertTrue(any("只能看到side" in item for item in result["errors"]))

    def test_lateral_move_cannot_claim_backward_away(self):
        payload = dongsheng_payload()
        payload["subject"]["movement"] = [1, 0, 0]
        result = GEOMETRY.validate(payload)
        self.assertFalse(result["ok"])
        errors = "\n".join(result["errors"])
        self.assertIn("实际为lateral", errors)
        self.assertIn("实际为unchanged", errors)

    def test_unmotivated_lens_gaze_is_rejected(self):
        payload = dongsheng_payload()
        payload["camera"]["position"] = [5, 0, 1.5]
        payload["camera"]["claimed_visible_face"] = "side"
        payload["camera"]["same_direction_as_story_target"] = False
        payload["camera"]["subject_appears_to_look_toward_lens"] = True
        result = GEOMETRY.validate(payload)
        self.assertFalse(result["ok"])
        self.assertTrue(any("无动机看镜头" in item for item in result["errors"]))

    def test_locked_solution_rejects_alternative_camera(self):
        payload = dongsheng_payload()
        payload["alternative_camera_solutions"] = [
            {"id": "B", "description": "房间侧面横拍"}
        ]
        result = GEOMETRY.validate(payload)
        self.assertFalse(result["ok"])
        self.assertTrue(any("不得同时提供替代摄影机方案" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
