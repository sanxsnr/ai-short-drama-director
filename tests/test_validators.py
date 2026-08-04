#!/usr/bin/env python3
"""Regression tests for CUT, spatial continuity and output-contract validators."""

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


TIMELINE = load_module("validate_timeline", "scripts/validate_timeline.py")
CONTINUITY = load_module("validate_continuity", "scripts/validate_continuity.py")
PROJECT = load_module("validate_project_state", "scripts/validate_project_state.py")
PROMPT = load_module("validate_prompt_package", "scripts/validate_prompt_package.py")


class TimelineValidatorTests(unittest.TestCase):
    def test_valid_terminal_segment_passes(self):
        result = TIMELINE.validate(
            {
                "segment_mode": "10s",
                "target_duration": 10,
                "content_type": "mixed",
                "segment_content_type": "normal",
                "segment_terminal": True,
                "shots": [
                    {
                        "start": 0,
                        "end": 5,
                        "cut_type": "EYELINE",
                        "cut_point": "沈渊抬眼锁定门口",
                    },
                    {
                        "start": 5,
                        "end": 10,
                        "dialogue": "醒了？月圆之夜，你这炉鼎的血，我要了。",
                        "cut_type": "END",
                    },
                ],
            }
        )
        self.assertTrue(result["ok"], result)

    def test_legacy_single_shot_rule_does_not_override_normal_policy(self):
        result = TIMELINE.validate(
            {
                "segment_mode": "10s",
                "target_duration": 10,
                "content_type": "mixed",
                "segment_content_type": "normal",
                "shot_rule": "single_shot_per_segment",
                "segment_terminal": True,
                "shots": [
                    {"start": 0, "end": 5, "cut_type": "CUT", "cut_point": "节点"},
                    {"start": 5, "end": 10, "cut_type": "END"},
                ],
            }
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue(any("legacy_shot_rule_ignored" in item for item in result["warnings"]))

    def test_nonterminal_segment_requires_last_cut_metadata(self):
        result = TIMELINE.validate(
            {
                "segment_mode": "10s",
                "target_duration": 10,
                "content_type": "mixed",
                "segment_content_type": "normal",
                "segment_terminal": False,
                "shots": [
                    {"start": 0, "end": 5, "cut_type": "CUT", "cut_point": "节点"},
                    {"start": 5, "end": 10},
                ],
            }
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("SHOT 2缺少 cut_type" in item for item in result["errors"]))
        self.assertTrue(any("SHOT 2缺少具体 cut_point" in item for item in result["errors"]))


class ContinuityValidatorTests(unittest.TestCase):
    def test_omitted_old_subject_state_is_rejected(self):
        end_state = {
            "shen": {
                "position": "木桩处",
                "bound": True,
                "wet": True,
                "gaze": "门口",
                "posture": "站立",
            },
            "door": {"state": "open"},
            "su": {"position": "门口", "facing": "沈渊"},
        }
        result = CONTINUITY.validate(
            {
                "shots": [
                    {"id": "SHOT02", "start_state": {}, "end_state": end_state},
                    {
                        "id": "SHOT03",
                        "start_state": {"su": {"position": "门口", "facing": "沈渊"}},
                        "end_state": {"su": {"position": "门口", "facing": "沈渊"}},
                    },
                ],
                "transitions": [
                    {
                        "from": "SHOT02",
                        "to": "SHOT03",
                        "type": "continuous",
                        "inherit": [
                            "shen.position",
                            "shen.bound",
                            "shen.wet",
                            "shen.gaze",
                            "shen.posture",
                            "door.state",
                            "su.position",
                            "su.facing",
                        ],
                    }
                ],
            }
        )
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("SHOT03.start_state 缺少继承路径：shen.bound" in item for item in result["errors"])
        )


class ProjectStateValidatorTests(unittest.TestCase):
    def test_bare_abc_commands_are_rejected(self):
        result = PROJECT.validate(
            {
                "project_name": "测试",
                "current_version": "v1",
                "current_stage": "完整分镜",
                "next_milestone": "完成CUT审核",
                "segment_duration_mode": 10,
                "current_segment_content_type": "normal",
                "spatial_state": {"resolution": "uniquely_derived"},
                "shot_task_rules_version": "v1",
                "cut_rules_version": "v1",
                "stages": [
                    {"name": "完整分镜", "status": "in_progress", "deliverables": []}
                ],
                "next_options": [
                    {
                        "id": "A",
                        "action": "修复",
                        "deliverable": "修订版",
                        "reply_command": "A",
                        "recommended": True,
                    },
                    {
                        "id": "B",
                        "action": "站位",
                        "deliverable": "空间图",
                        "reply_command": "B",
                        "recommended": False,
                    },
                    {
                        "id": "C",
                        "action": "样例",
                        "deliverable": "样例",
                        "reply_command": "C",
                        "recommended": False,
                    },
                ],
                "source_of_truth": {"script": "v1"},
            }
        )
        self.assertFalse(result["ok"])
        self.assertEqual(
            3,
            sum("reply_command 必须以" in item for item in result["errors"]),
        )


class PromptPackageValidatorTests(unittest.TestCase):
    def test_valid_standard_package_passes(self):
        result = PROMPT.validate(
            {
                "segment_id": "SEG01",
                "platform": "Seedance 2.0",
                "source_of_truth_version": "v1",
                "source_text": "原剧本",
                "final_prompt": (
                    "沈渊被反捆在木桩上，抬眼看向门口。"
                    "苏清月站在门口说：醒了？月圆之夜，你这炉鼎的血，我要了。"
                ),
                "target_duration": 10,
                "generation_mode": "standard",
                "segment_content_type": "normal",
                "segment_terminal": True,
                "references": [
                    {"id": "char1", "role": "character"},
                    {"id": "scene1", "role": "scene"},
                ],
                "required_assets": ["沈渊", "苏清月"],
                "provided_assets": ["沈渊", "苏清月"],
                "dialogue_lines": [
                    {
                        "speaker": "苏清月",
                        "text": "醒了？月圆之夜，你这炉鼎的血，我要了。",
                    }
                ],
                "expected_entities": ["沈渊", "苏清月"],
                "forbidden_entities": ["首帧100%继承"],
                "shots": [
                    {
                        "id": "SHOT02",
                        "scene_id": "torture_room",
                        "time_id": "night_01",
                        "camera_region_id": "post_side",
                        "camera_station_id": "post_front",
                        "camera_forward_world": [1, 0, 0],
                        "primary_scene_anchor_id": "shen_yuan",
                        "task_validation": {
                            "validator": "validate_shot_task.py",
                            "task_type": "REACTION",
                            "derived_independent_task": True,
                        },
                        "cut_point": "沈渊视线锁定门口",
                        "cut_type": "EYELINE",
                    },
                    {
                        "id": "SHOT03",
                        "scene_id": "torture_room",
                        "time_id": "night_01",
                        "camera_region_id": "door_side",
                        "camera_station_id": "east_door_inside",
                        "camera_forward_world": [1, 0, 0],
                        "primary_scene_anchor_id": "east_door_threshold",
                        "task_validation": {
                            "validator": "validate_shot_task.py",
                            "task_type": "ENTER",
                            "derived_independent_task": True,
                        },
                        "cut_type": "END",
                    },
                ],
                "context_scope": {
                    "segment_count": 1,
                    "uses_concise_asset_summaries": True,
                },
            }
        )
        self.assertTrue(result["ok"], result)

    def test_command_leak_and_standard_frame_are_rejected(self):
        result = PROMPT.validate(
            {
                "segment_id": "SEG01",
                "platform": "Seedance 2.0",
                "source_of_truth_version": "v1",
                "source_text": "原剧本",
                "final_prompt": "使用 $ai-short-drama-director，按首帧生成。苏清月说：醒了？",
                "target_duration": 10,
                "generation_mode": "standard",
                "segment_content_type": "normal",
                "shot_rule": "single_shot_per_segment",
                "segment_terminal": True,
                "references": [{"id": "frame1", "role": "first_frame"}],
                "required_assets": ["沈渊", "苏清月"],
                "provided_assets": ["苏清月"],
                "dialogue_lines": [
                    {
                        "speaker": "苏清月",
                        "text": "醒了？月圆之夜，你这炉鼎的血，我要了。",
                    }
                ],
                "shots": [
                    {"id": "SHOT02"},
                    {"id": "SHOT03", "cut_type": "END"},
                ],
                "context_scope": {
                    "segment_count": 3,
                    "includes_obsolete_versions": True,
                    "uses_concise_asset_summaries": False,
                },
            }
        )
        self.assertFalse(result["ok"])
        errors = "\n".join(result["errors"])
        self.assertIn("使用 $ai-short-drama-director", errors)
        self.assertIn("普通多镜头流程不得默认加入首尾帧", errors)
        self.assertNotIn("必须且只能包含1个SHOT", errors)
        self.assertTrue(any("legacy_shot_rule_ignored" in item for item in result["warnings"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
