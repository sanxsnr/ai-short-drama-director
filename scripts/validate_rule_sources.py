#!/usr/bin/env python3
"""Validate unique rule ownership and the scene-level camera-coverage pipeline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "skill": ROOT / "SKILL.md",
    "script": ROOT / "references/01-script-slicing.md",
    "spatial": ROOT / "references/04-blocking-continuity.md",
    "video": ROOT / "references/05-video-prompting.md",
    "qc": ROOT / "references/06-qc-repair-post.md",
    "storyboard": ROOT / "references/07-storyboard-image-prompts.md",
    "output": ROOT / "references/12-output-format-and-choice-footer.md",
    "cut": ROOT / "references/13-cut-shot-geometry.md",
    "task": ROOT / "references/14-shot-task-action-coverage.md",
    "director": ROOT / "references/15-directorial-camera-plan.md",
    "segment_validator": ROOT / "scripts/validate_segment_structure.py",
    "director_validator": ROOT / "scripts/validate_directorial_camera_plan.py",
    "coverage_validator": ROOT / "scripts/validate_camera_coverage_sequence.py",
    "director_cut_validator": ROOT / "scripts/validate_director_cut_intent.py",
    "cut_validator": ROOT / "scripts/validate_cut_geometry.py",
    "shot_task_validator": ROOT / "scripts/validate_shot_task.py",
    "spatial_validator": ROOT / "scripts/validate_spatial_geometry.py",
    "agent": ROOT / "agents/openai.yaml",
    "production_template": ROOT / "assets/production-document-template.md",
}

STALE_FILES = (
    "references/15-camera-movement-directing.md",
    "scripts/validate_camera_movement.py",
    "tests/test_camera_movement.py",
)

FORBIDDEN = {
    "skill": ["## CUT优先分镜规则", "## 空间确认Gate", "## ENTER／EXIT进出场Gate"],
    "script": ["## 相邻SHOT视觉差异闸门", "## ENTER／EXIT进出场Gate"],
    "spatial": ["## 有效CUT触发条件", "## CUT类型", "## SHOT任务合同", "## 导演读解"],
    "director": ["## 场景方向与坐标", "## ENTER／EXIT进出场Gate", "## 相邻SHOT视觉差异闸门"],
    "cut": ["## 场景方向与坐标", "## 人物空间状态", "## SHOT任务合同", "## 导演读解"],
    "task": ["## 场景方向与坐标", "## 有效CUT触发条件", "## CUT类型", "## 导演读解"],
}

REQUIRED_REFERENCES = {
    "skill": [
        "references/01-script-slicing.md", "references/04-blocking-continuity.md",
        "references/15-directorial-camera-plan.md", "references/14-shot-task-action-coverage.md",
        "references/13-cut-shot-geometry.md", "validate_camera_coverage_sequence.py",
    ],
    "script": ["04-blocking-continuity.md", "15-directorial-camera-plan.md", "14-shot-task-action-coverage.md", "13-cut-shot-geometry.md"],
    "spatial": ["02-visual-style.md", "03-asset-design.md", "15-directorial-camera-plan.md", "14-shot-task-action-coverage.md", "13-cut-shot-geometry.md", "validate_camera_coverage_sequence.py"],
    "director": ["01-script-slicing.md", "02-visual-style.md", "03-asset-design.md", "04-blocking-continuity.md", "14-shot-task-action-coverage.md", "13-cut-shot-geometry.md", "validate_camera_coverage_sequence.py"],
    "task": ["04-blocking-continuity.md", "15-directorial-camera-plan.md", "13-cut-shot-geometry.md", "validate_camera_coverage_sequence.py"],
    "cut": ["04-blocking-continuity.md", "15-directorial-camera-plan.md", "14-shot-task-action-coverage.md", "validate_camera_coverage_sequence.py"],
    "video": ["01-script-slicing.md", "15-directorial-camera-plan.md", "04-blocking-continuity.md"],
    "qc": ["01-script-slicing.md", "15-directorial-camera-plan.md"],
    "storyboard": ["01-script-slicing.md", "15-directorial-camera-plan.md"],
    "output": ["01-script-slicing.md"],
}

SEGMENT_POLICY_CONTRACT = (
    "SEG_SHOT_COUNT_POLICY_V1", "segment_content_type=normal", "shot_count <= 2",
    "cut_count <= 1", "too_many_shots_for_normal_segment",
    "segment_content_type=high_speed_action", "segment_content_type=fixed_camera_time_passage",
    "FIXED_CAMERA_TIME_PASSAGE", "camera_locked_after_move=true", "scene_geometry_unchanged=true",
)
SEGMENT_COUNT_LIMIT_MARKERS = (
    "shot_count <= 2", "cut_count <= 1", "shot_count = 1", "cut_count = 0",
    "too_many_shots_for_normal_segment",
)
DIRECTOR_CONTRACT = (
    "DIRECTORIAL_CAMERA_PLAN_V2", "DIRECTORIAL_CAMERA_PIPELINE_V3",
    "## 第二步：15A场景摄影覆盖预设计", "## 第四步：15B设计统一镜头方案",
    "scene_camera_grammar", "camera_station_candidates", "planned_station_sequence",
    "shot_scale_curve", "psychological_distance_curve", "shot_solution_lock",
    "observation_signature", "camera_station_inherited_from_previous",
    "不得再把`locked | movement | cut_to_new_shot`作为上游三选一输入",
)
SPATIAL_CONTRACT = (
    "04A｜场景基础空间模型", "04B｜人物与摄影机XYZ轨迹求解",
    "camera_allowed_regions", "camera_station_candidates", "camera_station_id",
    "scene_space_basis", "spatial_solution", "camera_keyframes", "actor_keyframes",
    "axis_policy", "return_to_director_plan", "人物—剧情对象—运动—摄影机几何求解",
    "推导可见面", "当前SHOT方案锁", "CUT后默认不继承",
)
TASK_CONTRACT = (
    "## SHOT任务合同", "derived_independent_task", "## 视角适配Gate",
    "selected_station_serves_task", "new_observation_not_demonstrated",
    "mechanical_dialogue_view_repetition", "## ENTER／EXIT进出场Gate",
    "## DIALOGUE对白任务Gate", "## 视角标签证据", "## 状态机与重复动作",
)
CUT_CONTRACT = (
    "审核`15-directorial-camera-plan.md`已经设计的CUT点是否有效",
    "## 相邻SHOT视觉差异闸门", "`14`任务覆盖通过",
    "主体名称改变不能自动证明新镜头成立", "## 视觉差异充分性",
    "无意的近似机位跳切", "本文件不在没有15方案时自行新增CUT",
    "director_cut_intent", "cut_type_intent", "transition_mechanism",
    "station_or_observation", "固定角度阈值", "审核失败时输出返工原因并返回15重做",
)
DIRECTOR_CUT_VALIDATOR_CONTRACT = (
    "director_cut_intent", "CUT_TYPE_INTENTS", "CUT_TRANSITION_MECHANISMS",
    "match_on_action", "action_match", "EYELINE_REVEAL", "REACTION",
    "viewpoint_evidence_passed", "dissolve只适用于明确的时间或空间转换",
    '"director_cut_intent_valid"', '"cut_type_intent"',
    '"transition_mechanism"', '"action_match_valid"',
)
DIRECTOR_VALIDATOR_CONTRACT = (
    "def validate", "stale_three_mode_contract", "spatial_plan_requires_redesign",
    "camera_keyframe_timeline_error", "camera_intent_solution_mismatch",
    "camera_path_intersects_obstacle", "camera_path_intersects_subject",
    "actor_path_intersects_obstacle", "axis_policy_mismatch",
    "camera_station_candidates", "scene_camera_grammar", "shot_solution_lock",
    "observation_signature", "camera_coverage_validation",
)
COVERAGE_VALIDATOR_CONTRACT = (
    "def validate", "repetitive_observation_sequence", "single_station_scene_coverage",
    "camera_inherited_without_directorial_reason", "invalid_solution_lock_scope",
    "camera_station_id", "camera_region_id", "psychological_distance",
    "rolling_windows", "unique_camera_station_count",
)
SHOT_TASK_VALIDATOR_CONTRACT = (
    "def validate", "viewpoint_fitness", "selected_station_does_not_serve_task",
    "new_observation_not_demonstrated", "mechanical_dialogue_view_repetition",
    "camera.station_id", '"viewpoint_fitness_passed"',
)
SKILL_PIPELINE_CONTRACT = (
    "04A 场景基础空间模型", "15A 场景摄影覆盖与机位调度",
    "15B 逐SHOT摄影机程序与CUT意图", "04B 人物与摄影机XYZ轨迹求解",
    "14-shot-task-action-coverage.md", "13-cut-shot-geometry.md",
    "场景级摄影覆盖重复检查", "validate_camera_coverage_sequence.py",
    "当前SHOT方案锁", "camera_station_id", "observation_signature",
)

STALE_GLOBAL_PHRASES = (
    "一个10秒编号镜只能有一个SHOT", "每个10秒SEG必须且只能包含1个SHOT",
    "景别改变就必须CUT", "焦段变化代表运镜", "焦段不同代表机位不同",
    "反方向机位就是越轴", "日夜交替必须使用多机位蒙太奇",
    "普通10秒可以任意包含多个SHOT", "主要主体改变即为强视觉差异",
    "主体改变自动通过", "viewpoint字符串不同即视为视角变化",
    "自然语言场景名称不同即视为换场", "camera_decision_contract",
    "CAMERA_DECISION_GATE_V1", "mode: locked | movement | cut_to_new_shot",
    "主动比较固定机位、连续运镜与CUT候选",
    "axis_side_preserved:", "axis_reestablished:", "duration_feasible:",
    "required_action_visible:", "唯一" + "方案锁", "thirty_" + "degree_applicable",
    "thirty_" + "degree_status", "camera_angle_" + str(3 * 10) + "_plus",
    str(3 * 10) + "度规则", str(3 * 10) + "度适用性",
    str(3 * 10) + "度角度路径", str(3 * 10) + "-degree rule",
)


def validate(root: Path = ROOT) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    texts: dict[str, str] = {}

    for relative in STALE_FILES:
        if (root / relative).exists():
            errors.append(f"保留了已废弃的三模式文件：{relative}")

    for name, path_template in FILES.items():
        path = root / path_template.relative_to(ROOT)
        if not path.exists():
            errors.append(f"缺少核心规则文件：{path.relative_to(root)}")
            continue
        texts[name] = path.read_text(encoding="utf-8")

    for name, phrases in FORBIDDEN.items():
        value = texts.get(name, "")
        for phrase in phrases:
            if phrase in value:
                errors.append(f"{FILES[name].relative_to(ROOT)}重复定义不属于本文件的规则：{phrase}")

    for name, refs in REQUIRED_REFERENCES.items():
        value = texts.get(name, "")
        for ref in refs:
            if ref not in value:
                errors.append(f"{FILES[name].relative_to(ROOT)}缺少唯一真源引用：{ref}")

    skill = texts.get("skill", "")
    for phrase in SKILL_PIPELINE_CONTRACT:
        if phrase not in skill:
            errors.append(f"SKILL.md缺少场景摄影覆盖流水线合同：{phrase}")
    pipeline_sequence = (
        "01-script-slicing.md\n"
        "→ 02／03 视觉风格与场景资产锁定\n"
        "→ 04A 场景基础空间模型\n"
        "→ 15A 场景摄影覆盖与机位调度\n"
        "→ 15B 逐SHOT摄影机程序与CUT意图\n"
        "→ 04B 人物与摄影机XYZ轨迹求解\n"
        "→ 14-shot-task-action-coverage.md\n"
        "→ 13-cut-shot-geometry.md\n"
        "→ 场景级摄影覆盖重复检查"
    )
    if pipeline_sequence not in skill:
        errors.append("SKILL.md职责顺序必须明确为01→02／03→04A→15A→15B→04B→14→13→场景覆盖→01。")

    for name, contract, label in (
        ("director", DIRECTOR_CONTRACT, "导演合同"),
        ("spatial", SPATIAL_CONTRACT, "双阶段空间合同"),
        ("task", TASK_CONTRACT, "任务与视角适配合同"),
        ("cut", CUT_CONTRACT, "CUT审核合同"),
        ("script", SEGMENT_POLICY_CONTRACT, "SEG结构合同"),
        ("director_validator", DIRECTOR_VALIDATOR_CONTRACT, "导演可执行合同"),
        ("coverage_validator", COVERAGE_VALIDATOR_CONTRACT, "场景覆盖验证合同"),
        ("shot_task_validator", SHOT_TASK_VALIDATOR_CONTRACT, "任务验证合同"),
        ("director_cut_validator", DIRECTOR_CUT_VALIDATOR_CONTRACT, "导演CUT审核合同"),
    ):
        value = texts.get(name, "")
        for phrase in contract:
            if phrase not in value:
                errors.append(f"{FILES[name].relative_to(ROOT)}缺少{label}：{phrase}")

    segment_validator = texts.get("segment_validator", "")
    for phrase in (
        "def validate_count_policy", "too_many_shots_for_normal_segment",
        "ambiguous_focal_transition", "fixed_camera_time_passage_requires_single_shot",
        '"count_source": "explicit_shot_boundaries_only"',
    ):
        if phrase not in segment_validator:
            errors.append(f"scripts/validate_segment_structure.py缺少可执行合同：{phrase}")

    validator_self = (root / "scripts/validate_rule_sources.py").resolve()
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml", ".py"}:
            continue
        if any(part in {".git", "__pycache__", "tests"} for part in path.parts):
            continue
        if path.parent.name == "scripts" and path.name in {"validate_directorial_camera_plan.py", "validate_rule_sources.py"}:
            continue
        if path.resolve() == validator_self:
            continue
        value = path.read_text(encoding="utf-8")
        for phrase in STALE_GLOBAL_PHRASES:
            if phrase in value:
                errors.append(f"{path.relative_to(root)}保留了过时规则：{phrase}")
        if path.suffix.lower() in {".md", ".yaml", ".yml"} and path.relative_to(root) != Path("references/01-script-slicing.md"):
            for marker in SEGMENT_COUNT_LIMIT_MARKERS:
                if marker in value:
                    errors.append(f"{path.relative_to(root)}重复维护SEG数量上限：{marker}；数量规则只能存在于references/01-script-slicing.md")

    for readme_name in ("README.md", "README_EN.md"):
        path = root / readme_name
        if not path.exists():
            errors.append(f"缺少{readme_name}")
            continue
        value = path.read_text(encoding="utf-8")
        for phrase in (
            "15-directorial-camera-plan.md", "validate_directorial_camera_plan.py",
            "validate_camera_coverage_sequence.py", "validate_spatial_geometry.py",
            "validate_shot_task.py", "validate_cut_geometry.py", "validate_segment_structure.py",
        ):
            if phrase not in value:
                errors.append(f"{readme_name}缺少场景摄影覆盖说明：{phrase}")

    for relative in (
        "scripts/validate_directorial_camera_plan.py", "scripts/validate_camera_coverage_sequence.py",
        "scripts/validate_spatial_geometry.py", "scripts/validate_shot_task.py",
        "scripts/validate_director_cut_intent.py", "scripts/validate_cut_geometry.py",
        "scripts/validate_segment_structure.py",
    ):
        if not (root / relative).exists():
            errors.append(f"缺少验证器：{relative}")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
