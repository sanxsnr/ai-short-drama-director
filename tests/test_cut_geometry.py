#!/usr/bin/env python3
"""Regression tests for CUT geometry after SHOT-task validation."""

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


def direction(degrees: float) -> list[float]:
    radians = math.radians(degrees)
    return [math.sin(radians), math.cos(radians), 0]


def dialogue_task(
    *,
    shot_id: str = "SHOT_B",
    subject: str = "dongsheng",
    scene_id: str = "bedroom",
    time_id: str = "night_01",
    viewpoint: str = "objective",
    camera_zone: str = "bed_side",
    camera_position: list[float] | None = None,
    camera_forward: list[float] | None = None,
    primary_anchor: str = "dongsheng",
    visible_anchors: list[str] | None = None,
    viewpoint_evidence: dict | None = None,
) -> dict:
    contract = {
        "shot_id": shot_id,
        "task_type": "DIALOGUE",
        "scene_id": scene_id,
        "time_id": time_id,
        "primary_subject_id": subject,
        "viewpoint": viewpoint,
        "camera": {
            "zone_id": camera_zone,
            "position_world": camera_position or [3, 3, 1.6],
            "forward_world": camera_forward or [0, 1, 0],
            "primary_scene_anchor_id": primary_anchor,
            "visible_anchor_ids": visible_anchors or [primary_anchor],
        },
        "required_evidence": ["focus_subject_visible", "new_visual_task_visible"],
        "visible_evidence": ["focus_subject_visible", "new_visual_task_visible"],
        "action": {
            "dialogue_focus_reason": "关键回答或决定成为新的画面重心",
            "focus_subject_visible": True,
            "new_visual_task_visible": True,
            "mechanical_speaker_switch": False,
        },
    }
    if viewpoint_evidence is not None:
        contract["viewpoint_evidence"] = viewpoint_evidence
    return contract


def eyeline_task(
    *,
    shot_id: str = "SHOT_B",
    subject: str = "fox_tail",
    scene_id: str = "bedroom",
    time_id: str = "night_01",
    camera_zone: str = "bed_side",
    camera_position: list[float] | None = None,
    camera_forward: list[float] | None = None,
    primary_anchor: str = "fox_tail",
    visible_anchors: list[str] | None = None,
) -> dict:
    return {
        "shot_id": shot_id,
        "task_type": "EYELINE_REVEAL",
        "scene_id": scene_id,
        "time_id": time_id,
        "primary_subject_id": subject,
        "viewpoint": "objective",
        "camera": {
            "zone_id": camera_zone,
            "position_world": camera_position or [3, 3, 1.6],
            "forward_world": camera_forward or [0, 1, 0],
            "primary_scene_anchor_id": primary_anchor,
            "visible_anchor_ids": visible_anchors or [primary_anchor],
        },
        "required_evidence": ["target_visible", "target_key_state_visible"],
        "visible_evidence": ["target_visible", "target_key_state_visible"],
        "action": {
            "previous_eyeline_locked": True,
            "target_id": subject,
            "target_visible": True,
            "target_direction_matches": True,
            "target_key_state_visible": True,
        },
    }


def entry_task(*, valid: bool = True) -> dict:
    contract = {
        "shot_id": "SHOT_B",
        "task_type": "ENTER",
        "scene_id": "torture_room",
        "time_id": "night_01",
        "primary_subject_id": "su_qingyue",
        "viewpoint": "objective",
        "camera": {
            "zone_id": "east_door_inside" if valid else "post_side",
            "position_world": [10.5, 4.5, 1.6] if valid else [4.5, 3.0, 1.6],
            "forward_world": [1, 0, 0],
            "primary_scene_anchor_id": "east_door_threshold" if valid else "su_qingyue",
            "visible_anchor_ids": (
                ["east_door_threshold", "east_door_frame", "entry_path"]
                if valid
                else ["su_qingyue"]
            ),
        },
        "required_evidence": [
            "door_frame_visible",
            "threshold_crossing_visible",
            "entry_direction_visible",
        ],
        "visible_evidence": (
            ["door_frame_visible", "threshold_crossing_visible", "entry_direction_visible"]
            if valid
            else ["entry_direction_visible"]
        ),
        "action": {
            "actor_id": "su_qingyue",
            "start_zone_id": "outside_east",
            "boundary_id": "east_door_threshold",
            "end_zone_id": "inside_east",
            "state_before": "outside",
            "state_after": "inside",
            "state_path": "actors.su_qingyue.zone_state",
            "movement_world": [-1, 0, 0],
            "crossing_visible": valid,
            "path_visible": valid,
            "movement_crosses_boundary": True,
        },
    }
    return contract


def shot(
    *,
    shot_id: str,
    subject: str = "dongsheng",
    angle: float = 0,
    forward_angle: float = 0,
    scale: str = "MS",
    viewpoint: str = "objective",
    stage: str = "watching",
    scene_id: str = "bedroom",
    time_id: str = "night_01",
    camera_zone: str = "bed_side",
    camera_position: list[float] | None = None,
    primary_anchor: str | None = None,
    visible_anchors: list[str] | None = None,
    task_contract: dict | None = None,
    extra: dict | None = None,
) -> dict:
    anchor = primary_anchor or subject
    data = {
        "id": shot_id,
        "primary_subject": subject,
        "subject_to_camera": direction(angle),
        "shot_scale": scale,
        "viewpoint": viewpoint,
        "action_stage": stage,
        "scene_id": scene_id,
        "time_id": time_id,
        "camera_zone_id": camera_zone,
        "camera_position_world": camera_position or [3, 3, 1.6],
        "camera_forward_world": direction(forward_angle),
        "primary_scene_anchor_id": anchor,
        "visible_anchor_ids": visible_anchors or [anchor],
    }
    if task_contract is not None:
        data["task_contract"] = task_contract
        if task_contract.get("task_type") == "ENTER":
            data["start_state"] = {"actors": {"su_qingyue": {"zone_state": "outside"}}}
            data["end_state"] = {"actors": {"su_qingyue": {"zone_state": "inside"}}}
        elif task_contract.get("task_type") == "EXIT":
            data["start_state"] = {"actors": {"su_qingyue": {"zone_state": "inside"}}}
            data["end_state"] = {"actors": {"su_qingyue": {"zone_state": "outside"}}}
    data.update(extra or {})
    return data


def payload(
    *,
    from_shot: dict | None = None,
    to_shot: dict | None = None,
    claimed_path: str = "",
    editing_device: str = "none",
    editing_device_purpose: str = "",
    graphic_match_basis: str = "",
    axis_status: str = "same_side",
    axis_required: bool = True,
) -> dict:
    return {
        "transition_id": "CUT_A_B",
        "from_shot": from_shot
        or shot(shot_id="SHOT_A", task_contract=None),
        "to_shot": to_shot
        or shot(
            shot_id="SHOT_B",
            task_contract=dialogue_task(),
        ),
        "axis_status": axis_status,
        "axis_required": axis_required,
        "editing_device": editing_device,
        "editing_device_purpose": editing_device_purpose,
        "graphic_match_basis": graphic_match_basis,
        "claimed_difference_path": claimed_path,
    }


class CutGeometryTests(unittest.TestCase):
    def test_dongsheng_axial_extreme_close_to_medium_passes(self):
        before = shot(shot_id="SHOT_A", scale="ECU", stage="fear_in_eyes")
        task = dialogue_task()
        task["action"]["dialogue_focus_reason"] = "眼部心理反应转为完整身体动作"
        after = shot(
            shot_id="SHOT_B",
            scale="MS",
            stage="retreat_and_fall",
            task_contract=task,
        )
        result = CUT.validate(payload(from_shot=before, to_shot=after, claimed_path="同轴大景别"))
        self.assertTrue(result["ok"], result)
        self.assertEqual("axial_scale", result["derived_difference_path"])
        self.assertEqual(4, result["shot_scale_step_difference"])

    def test_same_subject_thirty_five_degree_path_passes(self):
        after = shot(
            shot_id="SHOT_B",
            angle=35,
            forward_angle=35,
            camera_position=[4, 2, 1.6],
            task_contract=dialogue_task(camera_position=[4, 2, 1.6], camera_forward=direction(35)),
        )
        result = CUT.validate(payload(to_shot=after, claimed_path="angle"))
        self.assertTrue(result["ok"], result)
        self.assertEqual("angle", result["derived_difference_path"])

    def test_ten_degree_and_one_scale_step_fails_as_near_jump(self):
        after = shot(
            shot_id="SHOT_B",
            angle=10,
            forward_angle=10,
            scale="MCU",
            task_contract=dialogue_task(camera_forward=direction(10)),
        )
        result = CUT.validate(payload(to_shot=after))
        self.assertFalse(result["ok"])
        self.assertEqual("invalid_near_jump", result["derived_difference_path"])

    def test_action_stage_cannot_replace_visual_difference(self):
        after = shot(
            shot_id="SHOT_B",
            angle=5,
            forward_angle=5,
            stage="retreating",
            task_contract=dialogue_task(camera_forward=direction(5)),
        )
        result = CUT.validate(payload(to_shot=after))
        self.assertFalse(result["ok"])

    def test_twenty_degree_plus_adjacent_scale_passes_combined(self):
        after = shot(
            shot_id="SHOT_B",
            angle=20,
            forward_angle=20,
            scale="MCU",
            stage="decision",
            task_contract=dialogue_task(camera_forward=direction(20)),
        )
        result = CUT.validate(payload(to_shot=after, claimed_path="combined"))
        self.assertTrue(result["ok"], result)
        self.assertEqual("combined", result["derived_difference_path"])

    def test_subject_change_without_task_coverage_is_rejected(self):
        before = shot(
            shot_id="SHOT_A",
            subject="shen_yuan",
            scene_id="torture_room",
            camera_zone="post_side",
            primary_anchor="shen_yuan",
            visible_anchors=["shen_yuan", "wooden_post"],
        )
        after = shot(
            shot_id="SHOT_B",
            subject="su_qingyue",
            scene_id="torture_room",
            camera_zone="post_side",
            primary_anchor="su_qingyue",
            visible_anchors=["su_qingyue"],
            task_contract=entry_task(valid=False),
        )
        result = CUT.validate(payload(from_shot=before, to_shot=after))
        self.assertFalse(result["ok"])
        self.assertEqual("invalid_task_coverage", result["derived_difference_path"])
        self.assertTrue(any("14任务覆盖Gate" in item for item in result["errors"]))

    def test_entry_task_state_must_match_actual_shot_state(self):
        before = shot(
            shot_id="SHOT_A",
            subject="shen_yuan",
            scene_id="torture_room",
            camera_zone="post_front",
            primary_anchor="shen_yuan",
            visible_anchors=["shen_yuan", "wooden_post"],
        )
        task = entry_task(valid=True)
        after = shot(
            shot_id="SHOT_B",
            subject="su_qingyue",
            scene_id="torture_room",
            camera_zone="east_door_inside",
            camera_position=[10.5, 4.5, 1.6],
            forward_angle=90,
            primary_anchor="east_door_threshold",
            visible_anchors=["east_door_threshold", "east_door_frame", "entry_path"],
            task_contract=task,
        )
        after["start_state"]["actors"]["su_qingyue"]["zone_state"] = "inside"
        result = CUT.validate(payload(from_shot=before, to_shot=after))
        self.assertFalse(result["ok"])
        self.assertFalse(result["task_coverage_passed"])
        self.assertTrue(any("实际起始状态" in item for item in result["errors"]))

    def test_task_contract_cannot_describe_a_different_camera_than_actual_shot(self):
        before = shot(
            shot_id="SHOT_A",
            subject="shen_yuan",
            scene_id="torture_room",
            camera_zone="post_front",
            primary_anchor="shen_yuan",
            visible_anchors=["shen_yuan", "wooden_post"],
        )
        task = entry_task(valid=True)
        after = shot(
            shot_id="SHOT_B",
            subject="su_qingyue",
            scene_id="torture_room",
            camera_zone="post_side",
            camera_position=[4.5, 3.0, 1.6],
            primary_anchor="su_qingyue",
            visible_anchors=["su_qingyue"],
            task_contract=task,
        )
        result = CUT.validate(payload(from_shot=before, to_shot=after))
        self.assertFalse(result["ok"])
        self.assertFalse(result["task_coverage_passed"])
        self.assertTrue(any("task_contract" in item for item in result["errors"]))

    def test_correct_door_entry_cut_passes(self):
        before = shot(
            shot_id="SHOT_A",
            subject="shen_yuan",
            scene_id="torture_room",
            camera_zone="post_front",
            camera_position=[4, 3, 1.6],
            forward_angle=90,
            primary_anchor="shen_yuan",
            visible_anchors=["shen_yuan", "wooden_post"],
        )
        task = entry_task(valid=True)
        after = shot(
            shot_id="SHOT_B",
            subject="su_qingyue",
            scene_id="torture_room",
            camera_zone="east_door_inside",
            camera_position=[10.5, 4.5, 1.6],
            forward_angle=90,
            primary_anchor="east_door_threshold",
            visible_anchors=["east_door_threshold", "east_door_frame", "entry_path"],
            task_contract=task,
        )
        result = CUT.validate(
            payload(from_shot=before, to_shot=after, claimed_path="subject_or_viewpoint")
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["task_coverage_passed"])
        self.assertEqual("ENTER", result["task_type"])

    def test_valid_eyeline_reveal_can_keep_scene_direction(self):
        before = shot(shot_id="SHOT_A", subject="dongsheng", primary_anchor="dongsheng")
        task = eyeline_task()
        after = shot(
            shot_id="SHOT_B",
            subject="fox_tail",
            primary_anchor="fox_tail",
            visible_anchors=["fox_tail"],
            task_contract=task,
        )
        result = CUT.validate(
            payload(from_shot=before, to_shot=after, claimed_path="subject_or_viewpoint")
        )
        self.assertTrue(result["ok"], result)

    def test_viewpoint_label_without_ots_evidence_is_rejected(self):
        task = dialogue_task(viewpoint="OTS")
        task["viewpoint_evidence"] = {
            "foreground_character_id": "shen_yuan",
            "foreground_shoulder_visible": False,
            "focus_subject_id": "su_qingyue",
            "axis_valid": True,
        }
        after = shot(
            shot_id="SHOT_B",
            viewpoint="OTS",
            task_contract=task,
        )
        result = CUT.validate(payload(to_shot=after))
        self.assertFalse(result["ok"])
        self.assertTrue(any("真实POV／OTS／INSERT" in item for item in result["errors"]))

    def test_scene_label_change_does_not_fake_scene_change(self):
        before = shot(
            shot_id="SHOT_A",
            extra={"space": "刑房"},
        )
        after = shot(
            shot_id="SHOT_B",
            angle=5,
            forward_angle=5,
            extra={"space": "刑房内"},
            task_contract=dialogue_task(camera_forward=direction(5)),
        )
        result = CUT.validate(payload(from_shot=before, to_shot=after))
        self.assertFalse(result["ok"])
        self.assertTrue(result["same_scene_id"])

    def test_scene_id_change_is_strong_after_task_passes(self):
        after_task = dialogue_task(
            scene_id="courtyard",
            camera_zone="courtyard_center",
            primary_anchor="courtyard_gate",
            visible_anchors=["courtyard_gate"],
        )
        after = shot(
            shot_id="SHOT_B",
            scene_id="courtyard",
            camera_zone="courtyard_center",
            primary_anchor="courtyard_gate",
            visible_anchors=["courtyard_gate"],
            task_contract=after_task,
        )
        result = CUT.validate(payload(to_shot=after, claimed_path="subject_or_viewpoint"))
        self.assertTrue(result["ok"], result)
        self.assertFalse(result["same_scene_id"])

    def test_cross_axis_cannot_be_saved_by_task_or_angle(self):
        after = shot(
            shot_id="SHOT_B",
            angle=45,
            forward_angle=45,
            task_contract=dialogue_task(camera_forward=direction(45)),
        )
        result = CUT.validate(
            payload(to_shot=after, claimed_path="angle", axis_status="crossed_without_reestablish")
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("180度轴线" in item for item in result["errors"]))

    def test_intentional_jump_requires_purpose(self):
        result = CUT.validate(
            payload(editing_device="intentional_jump_cut", claimed_path="intentional_jump")
        )
        self.assertFalse(result["ok"])

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
                editing_device_purpose="以圆形构图连接空间",
                claimed_path="graphic_match",
            )
        )
        self.assertFalse(result["ok"])

    def test_graphic_match_with_basis_passes(self):
        result = CUT.validate(
            payload(
                editing_device="graphic_match",
                editing_device_purpose="以圆形构图连接空间",
                graphic_match_basis="圆窗与月亮保持相同位置和尺寸",
                claimed_path="graphic_match",
            )
        )
        self.assertTrue(result["ok"], result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
