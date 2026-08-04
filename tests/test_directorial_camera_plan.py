#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "validate_directorial_camera_plan",
    ROOT / "scripts/validate_directorial_camera_plan.py",
)
assert spec and spec.loader
VALIDATOR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(VALIDATOR)


def base_plan() -> dict:
    return {
        "plan_id": "PLAN-24",
        "segment_id": "SEG-24",
        "scene_id": "dong_room",
        "segment_content_type": "normal",
        "duration_seconds": 10,
        "director_read": {
            "scene_function": "压缩多日时间并表现董生衰弱",
            "dramatic_turn": "亲密相处转为生命被持续消耗",
            "pov_empathy": "观众从两人关系逐步转向时间流逝",
            "power_movement": "阿琐保持稳定，董生逐渐失去力量",
            "subtext": "表面缠绵，实际吸取生命",
            "scene_intention": "让摄影机从两人关系移向圆窗，并由固定窗位见证数日流逝",
        },
        "scene_space_basis": {
            "bounds_world": {"x": [0, 10], "y": [0, 8], "z": [0, 4]},
            "anchor_ids": ["bed", "round_window"],
            "walkable_zone_ids": ["bed_side_lane"],
            "blocked_volumes": [],
            "relationship_axes": [
                {"axis_id": "room_axis", "source_type": "fixed", "point_a_world": [8, 0, 0], "point_b_world": [8, 8, 0]},
            ],
            "camera_clearance_units": 0.1,
            "actor_clearance_units": 0.25,
            "max_camera_speed_units_per_second": 5,
            "max_actor_speed_units_per_second": 5,
            "max_camera_angular_speed_degrees_per_second": 90,
            "locked_facts": ["床头到圆窗之间存在可通行床侧通道"],
        },
        "beats": [
            {
                "beat_id": "B1",
                "start_seconds": 0,
                "end_seconds": 5,
                "dramatic_task": "从两人关系过渡到时间锚点",
                "primary_subject_id": "dong_and_asuo",
                "required_visible_evidence": ["两人同框", "圆窗逐渐成为构图中心"],
            },
            {
                "beat_id": "B2",
                "start_seconds": 5,
                "end_seconds": 10,
                "dramatic_task": "固定窗位表现日夜交替与衰弱",
                "primary_subject_id": "dongsheng",
                "required_visible_evidence": ["圆窗固定", "日夜交替", "董生状态递进"],
            },
        ],
        "shots": [
            {
                "shot_id": "S1",
                "start_seconds": 0,
                "end_seconds": 10,
                "dramatic_task": "从人物关系移动到时间见证位置",
                "primary_subject_id": "dong_and_asuo",
                "actor_ids": ["dongsheng", "asuo"],
                "beat_ids": ["B1", "B2"],
                "camera_trajectory_intent": {
                    "start_composition": "床头双人中景",
                    "path_intent": "沿床侧通道缓慢推进到圆窗后保持固定",
                    "movement_purpose": "把观众注意力从人物关系转移到时间锚点",
                    "speed_rhythm": "缓慢起步，匀速推进，接近圆窗时减速停稳",
                    "subject_relation_during_shot": "人物逐渐退为环境中的状态证据",
                    "required_action_visibility": ["双人关系", "圆窗", "董生状态变化"],
                    "end_composition": "圆窗主构图，人物处于固定画面关系",
                    "hold_after_arrival_seconds": 5,
                },
                "cut_out_intent": {"enabled": False},
            }
        ],
        "spatial_solution": {
            "status": "solved",
            "failure_codes": [],
            "redesign_constraints": [],
            "shot_solutions": [
                {
                    "shot_id": "S1",
                    "axis_policy": "preserve",
                    "relationship_axis_id": "room_axis",
                    "camera_keyframes": [
                        {"time_seconds": 0, "position_world": [2, 2, 1.6], "forward_world": [0, 1, 0], "framing": "床头双人中景"},
                        {"time_seconds": 5, "position_world": [2, 5, 1.6], "forward_world": [0, 1, 0], "framing": "圆窗主构图"},
                        {"time_seconds": 10, "position_world": [2, 5, 1.6], "forward_world": [0, 1, 0], "framing": "圆窗主构图"},
                    ],
                    "actor_keyframes": [
                        {"actor_id": "dongsheng", "time_seconds": 0, "position_world": [4, 4, 0], "body_forward_world": [0, -1, 0]},
                        {"actor_id": "dongsheng", "time_seconds": 10, "position_world": [4, 4, 0], "body_forward_world": [0, -1, 0]},
                        {"actor_id": "asuo", "time_seconds": 0, "position_world": [4.5, 4, 0], "body_forward_world": [0, -1, 0]},
                        {"actor_id": "asuo", "time_seconds": 10, "position_world": [4.5, 4, 0], "body_forward_world": [0, -1, 0]},
                    ],
                }
            ],
        },
    }


def two_shot_plan() -> dict:
    p = base_plan()
    p["plan_id"] = "PLAN-09"
    p["beats"] = [
        {
            "beat_id": "B1", "start_seconds": 0, "end_seconds": 5,
            "dramatic_task": "董生跌地反应", "primary_subject_id": "dongsheng",
            "required_visible_evidence": ["跌地", "抬头看床"],
        },
        {
            "beat_id": "B2", "start_seconds": 5, "end_seconds": 10,
            "dramatic_task": "反打阿琐下床", "primary_subject_id": "asuo",
            "required_visible_evidence": ["醒来", "脚落床外侧"],
        },
    ]
    p["shots"] = [
        {
            "shot_id": "S1", "start_seconds": 0, "end_seconds": 5,
            "dramatic_task": "拍董生跌地后的目光", "primary_subject_id": "dongsheng",
            "actor_ids": ["dongsheng"], "beat_ids": ["B1"],
            "camera_trajectory_intent": {
                "start_composition": "地面正面中景", "path_intent": "保持固定构图",
                "movement_purpose": "让跌地反应在稳定画面中成立", "speed_rhythm": "固定",
                "subject_relation_during_shot": "保持董生正面", "required_action_visibility": ["抬头"],
                "end_composition": "董生目光锁定床榻", "hold_after_arrival_seconds": 5,
            },
            "cut_out_intent": {
                "enabled": True, "at_seconds": 5, "cut_point_beat_id": "B1",
                "cut_type_intent": "eyeline", "transition_mechanism": "hard_cut",
                "reason": "董生目光锁定床榻后，观察任务转向威胁主体阿琐",
                "next_shot_id": "S2",
            },
        },
        {
            "shot_id": "S2", "start_seconds": 5, "end_seconds": 10,
            "dramatic_task": "低位反打阿琐下床", "primary_subject_id": "asuo",
            "actor_ids": ["asuo"], "beat_ids": ["B2"],
            "camera_trajectory_intent": {
                "start_composition": "董生地面一侧低机位朝床", "path_intent": "保持低位并轻微跟随阿琐落脚",
                "movement_purpose": "维持低位压迫并看清下床动作", "speed_rhythm": "落脚时短促跟随后停稳",
                "subject_relation_during_shot": "阿琐居高临下进入董生方向", "required_action_visibility": ["醒来", "下床"],
                "end_composition": "阿琐脚落床外侧", "hold_after_arrival_seconds": 1,
            },
            "cut_out_intent": {"enabled": False},
        },
    ]
    p["spatial_solution"]["shot_solutions"] = [
        {
            "shot_id": "S1", "axis_policy": "preserve", "relationship_axis_id": "room_axis",
            "camera_keyframes": [
                {"time_seconds": 0, "position_world": [5, 2, 0.5], "forward_world": [0, 1, 0], "framing": "董生地面中景"},
                {"time_seconds": 5, "position_world": [5, 2, 0.5], "forward_world": [0, 1, 0], "framing": "董生地面中景"},
            ],
            "actor_keyframes": [
                {"actor_id": "dongsheng", "time_seconds": 0, "position_world": [5, 4, 0], "body_forward_world": [0, 1, 0]},
                {"actor_id": "dongsheng", "time_seconds": 5, "position_world": [5, 4, 0], "body_forward_world": [0, 1, 0]},
            ],
        },
        {
            "shot_id": "S2", "axis_policy": "preserve", "relationship_axis_id": "room_axis",
            "camera_keyframes": [
                {"time_seconds": 5, "position_world": [5, 4, 0.4], "forward_world": [0, 1, 0], "framing": "低位床榻中全景"},
                {"time_seconds": 9, "position_world": [5.2, 4.2, 0.4], "forward_world": [0, 1, 0], "framing": "低位阿琐全身"},
                {"time_seconds": 10, "position_world": [5.2, 4.2, 0.4], "forward_world": [0, 1, 0], "framing": "低位阿琐全身"},
            ],
            "actor_keyframes": [
                {"actor_id": "asuo", "time_seconds": 5, "position_world": [5, 6, 1], "body_forward_world": [0, -1, 0]},
                {"actor_id": "asuo", "time_seconds": 10, "position_world": [5, 5.5, 0], "body_forward_world": [0, -1, 0]},
            ],
        },
    ]
    return p


class DirectorialCameraPlanTests(unittest.TestCase):
    def assert_error(self, payload: dict, code: str) -> None:
        result = VALIDATOR.validate(payload)
        self.assertFalse(result["ok"], result)
        self.assertIn(code, result["error_codes"], result)

    def test_valid_move_then_hold_passes(self):
        result = VALIDATOR.validate(base_plan())
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["derived_behaviors"][0]["camera_behavior"], "continuous_motion")
        self.assertEqual(result["derived_behaviors"][0]["solved_hold_seconds"], 5)

    def test_wrapper_is_accepted(self):
        result = VALIDATOR.validate({"directorial_camera_plan": base_plan()})
        self.assertTrue(result["ok"], result)

    def test_valid_two_shot_plan_passes(self):
        result = VALIDATOR.validate(two_shot_plan())
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["derived_cut_count"], 1)
        self.assertEqual(result["derived_behaviors"][0]["camera_behavior"], "locked")

    def test_environment_shot_without_axis_or_actors_passes(self):
        p = base_plan()
        p["scene_space_basis"]["relationship_axes"] = []
        p["shots"][0]["actor_ids"] = []
        p["shots"][0]["primary_subject_id"] = "round_window"
        solved = p["spatial_solution"]["shot_solutions"][0]
        solved["axis_policy"] = "not_applicable"
        solved.pop("relationship_axis_id")
        solved["actor_keyframes"] = []
        self.assertTrue(VALIDATOR.validate(p)["ok"])

    def test_legacy_three_mode_contract_fails(self):
        p = base_plan(); p["camera_decision"] = {"mode": "movement"}
        self.assert_error(p, "stale_three_mode_contract")

    def test_missing_director_read_fails(self):
        p = base_plan(); p["director_read"]["scene_intention"] = ""
        self.assert_error(p, "missing_director_read")

    def test_generic_director_intention_fails(self):
        p = base_plan(); p["director_read"]["scene_intention"] = "电影感"
        self.assert_error(p, "missing_director_read")

    def test_generic_camera_purpose_fails(self):
        p = base_plan(); p["shots"][0]["camera_trajectory_intent"]["movement_purpose"] = "电影感"
        self.assert_error(p, "unmotivated_camera_trajectory")

    def test_beat_timeline_gap_fails(self):
        p = base_plan(); p["beats"][1]["start_seconds"] = 6
        self.assert_error(p, "invalid_beat_timeline")

    def test_shot_timeline_gap_fails(self):
        p = two_shot_plan(); p["shots"][1]["start_seconds"] = 6
        self.assert_error(p, "invalid_shot_timeline")

    def test_cut_next_shot_mismatch_fails(self):
        p = two_shot_plan(); p["shots"][0]["cut_out_intent"]["next_shot_id"] = "S9"
        self.assert_error(p, "cut_sequence_mismatch")

    def test_cut_beat_must_belong_to_current_shot(self):
        p = two_shot_plan(); p["shots"][0]["cut_out_intent"]["cut_point_beat_id"] = "B2"
        self.assert_error(p, "cut_sequence_mismatch")

    def test_cut_type_must_be_designed_by_director_layer(self):
        p = two_shot_plan(); p["shots"][0]["cut_out_intent"].pop("cut_type_intent")
        self.assert_error(p, "invalid_cut_type_intent")

    def test_cut_transition_mechanism_is_required(self):
        p = two_shot_plan(); p["shots"][0]["cut_out_intent"].pop("transition_mechanism")
        self.assert_error(p, "invalid_cut_transition_mechanism")

    def test_unmotivated_cut_fails(self):
        p = two_shot_plan(); p["shots"][0]["cut_out_intent"]["reason"] = "更有节奏"
        self.assert_error(p, "unmotivated_cut")

    def test_final_shot_requires_explicit_no_cut(self):
        p = base_plan(); p["shots"][0].pop("cut_out_intent")
        self.assert_error(p, "missing_cut_intent")

    def test_spatial_redesign_feedback_fails_final_validation(self):
        p = base_plan(); p["spatial_solution"] = {
            "status": "return_to_director_plan",
            "failure_codes": ["bed_blocks_path"],
            "redesign_constraints": ["不得穿过床榻"],
            "shot_solutions": [],
        }
        result = VALIDATOR.validate(p)
        self.assertFalse(result["ok"], result)
        self.assertTrue(result["requires_director_redesign"])
        self.assertIn("spatial_plan_requires_redesign", result["error_codes"])

    def test_out_of_bounds_camera_fails(self):
        p = base_plan(); p["spatial_solution"]["shot_solutions"][0]["camera_keyframes"][1]["position_world"] = [20, 5, 1.6]
        self.assert_error(p, "camera_position_out_of_bounds")

    def test_actual_obstacle_intersection_fails(self):
        p = base_plan()
        p["scene_space_basis"]["blocked_volumes"] = [
            {"obstacle_id": "screen", "min_world": [1.9, 3, 1], "max_world": [2.1, 4, 2]},
        ]
        self.assert_error(p, "camera_path_intersects_obstacle")

    def test_actor_path_intersection_with_obstacle_fails(self):
        p = base_plan()
        p["scene_space_basis"]["blocked_volumes"] = [
            {"obstacle_id": "bed_post", "min_world": [3.9, 3.9, 0], "max_world": [4.1, 4.1, 1]},
        ]
        self.assert_error(p, "actor_path_intersects_obstacle")

    def test_actor_pair_relationship_axis_is_computed_from_actor_tracks(self):
        p = base_plan()
        p["scene_space_basis"]["relationship_axes"] = [
            {"axis_id": "character_axis", "source_type": "actor_pair", "actor_a_id": "dongsheng", "actor_b_id": "asuo"},
        ]
        solved = p["spatial_solution"]["shot_solutions"][0]
        solved["relationship_axis_id"] = "character_axis"
        self.assert_error(p, "camera_path_crosses_axis")

    def test_axis_crossing_without_reestablish_fails(self):
        p = base_plan()
        frames = p["spatial_solution"]["shot_solutions"][0]["camera_keyframes"]
        frames[0]["position_world"] = [2, 1, 1.6]
        frames[1]["position_world"] = [9, 1, 1.6]
        frames[2]["position_world"] = [9, 1, 1.6]
        self.assert_error(p, "camera_path_crosses_axis")

    def test_visible_axis_reestablishment_passes(self):
        p = base_plan()
        frames = p["spatial_solution"]["shot_solutions"][0]["camera_keyframes"]
        frames[0]["position_world"] = [2, 1, 1.6]
        frames[1]["position_world"] = [9, 1, 1.6]
        frames[2]["position_world"] = [9, 1, 1.6]
        solved = p["spatial_solution"]["shot_solutions"][0]
        solved["axis_policy"] = "visible_reestablish"
        solved["axis_reestablishment_evidence"] = ["摄影机在画面中连续越过人物关系线并重新建立左右"]
        self.assertTrue(VALIDATOR.validate(p)["ok"])

    def test_axis_reestablishment_without_actual_cross_fails(self):
        p = base_plan()
        solved = p["spatial_solution"]["shot_solutions"][0]
        solved["axis_policy"] = "visible_reestablish"
        solved["axis_reestablishment_evidence"] = ["宣称已经重建"]
        self.assert_error(p, "axis_policy_mismatch")

    def test_camera_speed_limit_fails(self):
        p = base_plan(); p["scene_space_basis"]["max_camera_speed_units_per_second"] = 0.1
        self.assert_error(p, "camera_speed_exceeds_space_limit")

    def test_camera_angular_speed_limit_fails(self):
        p = base_plan(); p["scene_space_basis"]["max_camera_angular_speed_degrees_per_second"] = 10
        frames = p["spatial_solution"]["shot_solutions"][0]["camera_keyframes"]
        frames[1]["time_seconds"] = 1
        frames[1]["forward_world"] = [1, 0, 0]
        frames[2]["forward_world"] = [1, 0, 0]
        self.assert_error(p, "camera_angular_speed_exceeds_space_limit")

    def test_actor_speed_limit_fails(self):
        p = base_plan(); p["scene_space_basis"]["max_actor_speed_units_per_second"] = 0.1
        actors = p["spatial_solution"]["shot_solutions"][0]["actor_keyframes"]
        actors[1]["position_world"] = [9, 4, 0]
        self.assert_error(p, "actor_speed_exceeds_space_limit")

    def test_dynamic_camera_actor_collision_fails(self):
        p = base_plan()
        actors = p["spatial_solution"]["shot_solutions"][0]["actor_keyframes"]
        actors[0]["position_world"] = [2, 5, 1.6]
        actors[1]["position_world"] = [2, 2, 1.6]
        self.assert_error(p, "camera_path_intersects_subject")

    def test_actor_track_must_cover_whole_shot(self):
        p = base_plan(); p["spatial_solution"]["shot_solutions"][0]["actor_keyframes"].pop(1)
        self.assert_error(p, "actor_keyframe_timeline_error")

    def test_hold_intent_with_moving_solution_fails(self):
        p = base_plan(); p["shots"][0]["camera_trajectory_intent"]["path_intent"] = "保持固定构图"
        self.assert_error(p, "camera_intent_solution_mismatch")

    def test_move_intent_with_locked_solution_fails(self):
        p = base_plan()
        frames = p["spatial_solution"]["shot_solutions"][0]["camera_keyframes"]
        for frame in frames:
            frame["position_world"] = [2, 2, 1.6]
        self.assert_error(p, "camera_intent_solution_mismatch")

    def test_hold_duration_must_exist_in_keyframes(self):
        p = base_plan()
        p["spatial_solution"]["shot_solutions"][0]["camera_keyframes"] = [
            {"time_seconds": 0, "position_world": [2, 2, 1.6], "forward_world": [0, 1, 0], "framing": "双人中景"},
            {"time_seconds": 9, "position_world": [2, 4.8, 1.6], "forward_world": [0, 1, 0], "framing": "圆窗构图"},
            {"time_seconds": 10, "position_world": [2, 5, 1.6], "forward_world": [0, 1, 0], "framing": "圆窗构图"},
        ]
        self.assert_error(p, "hold_duration_not_solved")

    def test_missing_actor_spatial_solution_fails(self):
        p = base_plan(); p["spatial_solution"]["shot_solutions"][0]["actor_keyframes"] = []
        self.assert_error(p, "missing_actor_spatial_solution")

    def test_spatial_solution_ids_must_match(self):
        p = base_plan(); p["spatial_solution"]["shot_solutions"][0]["shot_id"] = "WRONG"
        self.assert_error(p, "spatial_solution_shot_mismatch")

    def test_too_many_motion_axes_fail_for_normal(self):
        p = base_plan()
        frames = p["spatial_solution"]["shot_solutions"][0]["camera_keyframes"]
        frames[1]["position_world"] = [3, 5, 2.6]
        frames[2]["position_world"] = [3, 5, 2.6]
        self.assert_error(p, "too_many_camera_motion_axes")

    def test_three_motion_axes_can_pass_for_high_speed_action(self):
        p = base_plan(); p["segment_content_type"] = "high_speed_action"
        frames = p["spatial_solution"]["shot_solutions"][0]["camera_keyframes"]
        frames[1]["position_world"] = [3, 5, 2.6]
        frames[2]["position_world"] = [3, 5, 2.6]
        self.assertTrue(VALIDATOR.validate(p)["ok"])

    def test_legacy_path_flag_must_match_derived_geometry(self):
        p = base_plan(); p["spatial_solution"]["shot_solutions"][0]["path_clear"] = False
        self.assert_error(p, "spatial_solution_flag_mismatch")

    def test_copy_is_independent(self):
        p = copy.deepcopy(base_plan()); p["plan_id"] = "OTHER"
        self.assertTrue(VALIDATOR.validate(p)["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
