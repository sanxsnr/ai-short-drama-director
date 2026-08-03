#!/usr/bin/env python3
"""Validate a structured AI short-drama project-state JSON document."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ALLOWED_STATUSES = {
    "completed",
    "in_progress",
    "not_started",
    "blocked",
    "rework",
}
SKILL_COMMAND_PREFIX = "使用 $ai-short-drama-director"
ALLOWED_SHOT_RULES = {
    "single_shot_per_segment",
    "multiple_shots_per_segment",
    "每个SEG单SHOT",
    "允许SEG内多SHOT",
}


def load_payload(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(payload: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    for field in (
        "project_name",
        "current_version",
        "current_stage",
        "next_milestone",
    ):
        if not nonempty_text(payload.get(field)):
            errors.append(f"缺少有效字段：{field}")

    segment_duration_mode = payload.get("segment_duration_mode")
    if segment_duration_mode not in (None, 10, 15, "10", "15"):
        errors.append("segment_duration_mode 只能是10或15")

    stages = payload.get("stages")
    if not isinstance(stages, list) or not stages:
        errors.append("stages 必须是非空数组")
        stages = []

    names: set[str] = set()
    status_counts: Counter[str] = Counter()
    for index, stage in enumerate(stages, start=1):
        if not isinstance(stage, dict):
            errors.append(f"stages[{index}] 必须是对象")
            continue
        name = str(stage.get("name", "")).strip()
        status = str(stage.get("status", "")).strip()
        if not name:
            errors.append(f"stages[{index}] 缺少 name")
        elif name in names:
            errors.append(f"阶段名称重复：{name}")
        else:
            names.add(name)
        if status not in ALLOWED_STATUSES:
            errors.append(
                f"阶段{name or index}的 status 无效；"
                "使用 completed/in_progress/not_started/blocked/rework"
            )
        else:
            status_counts[status] += 1

        deliverables = stage.get("deliverables", [])
        if deliverables is not None and not isinstance(deliverables, list):
            errors.append(f"阶段{name or index}的 deliverables 必须是数组")
            deliverables = []
        if status == "completed":
            if not deliverables:
                errors.append(f"已完成阶段“{name}”没有交付物证据")
            if stage.get("verified") is not True:
                errors.append(f"已完成阶段“{name}”必须 verified=true")
        if status == "blocked" and not nonempty_text(stage.get("blocker")):
            errors.append(f"被阻塞阶段“{name}”必须写 blocker")
        if status == "rework" and not nonempty_text(stage.get("rework_reason")):
            warnings.append(f"需返工阶段“{name}”建议写 rework_reason")

    slicing_active = any(
        isinstance(stage, dict)
        and any(
            keyword in str(stage.get("name", "")).lower()
            for keyword in ("切片", "分镜", "shot", "cut", "slicing", "storyboard")
        )
        and stage.get("status") in {"completed", "in_progress", "rework"}
        for stage in stages
    )
    current_stage = str(payload.get("current_stage", "")).lower()
    if any(
        keyword in current_stage
        for keyword in ("切片", "分镜", "shot", "cut", "slicing", "storyboard")
    ):
        slicing_active = True

    if slicing_active:
        if segment_duration_mode not in (10, 15, "10", "15"):
            errors.append("进入视听切片或分镜阶段前，必须设置10秒或15秒规格")
        shot_rule = payload.get("shot_rule")
        if shot_rule not in ALLOWED_SHOT_RULES:
            errors.append(
                "进入分镜阶段必须设置 shot_rule："
                "single_shot_per_segment 或 multiple_shots_per_segment"
            )
        spatial_state = payload.get("spatial_state")
        if not isinstance(spatial_state, dict) or not spatial_state:
            errors.append("进入分镜阶段必须提供 spatial_state")
        else:
            resolution = str(spatial_state.get("resolution", "")).strip()
            if resolution not in {"confirmed", "uniquely_derived", "critical_ambiguity"}:
                errors.append(
                    "spatial_state.resolution 必须是 confirmed、"
                    "uniquely_derived 或 critical_ambiguity"
                )
        if not nonempty_text(payload.get("cut_rules_version")):
            warnings.append("建议填写 cut_rules_version，记录CUT唯一真源版本")

    options = payload.get("next_options")
    if not isinstance(options, list) or len(options) != 3:
        errors.append("next_options 必须且只能包含3个可执行选项")
        options = options if isinstance(options, list) else []

    option_ids: set[str] = set()
    recommended_count = 0
    for index, option in enumerate(options, start=1):
        if not isinstance(option, dict):
            errors.append(f"next_options[{index}] 必须是对象")
            continue
        option_id = str(option.get("id", "")).strip()
        if not option_id:
            errors.append(f"next_options[{index}] 缺少 id")
        elif option_id in option_ids:
            errors.append(f"下一步选项 id 重复：{option_id}")
        else:
            option_ids.add(option_id)

        for field in ("action", "deliverable", "reply_command"):
            if not nonempty_text(option.get(field)):
                errors.append(f"选项{option_id or index}缺少 {field}")

        reply_command = str(option.get("reply_command", "")).strip()
        if reply_command and not reply_command.startswith(SKILL_COMMAND_PREFIX):
            errors.append(
                f"选项{option_id or index}的 reply_command 必须以 "
                f"{SKILL_COMMAND_PREFIX!r} 开头"
            )
        if option.get("recommended") is True:
            recommended_count += 1

    if options and recommended_count != 1:
        errors.append("next_options 必须且只能有1个 recommended=true")
    if options and option_ids != {"A", "B", "C"}:
        errors.append("next_options 的 id 必须且只能是 A、B、C")

    source_of_truth = payload.get("source_of_truth")
    if not isinstance(source_of_truth, dict) or not source_of_truth:
        warnings.append("建议填写 source_of_truth，记录真源剧本、空间和锁定资产版本")

    return {
        "ok": not errors,
        "project_name": payload.get("project_name"),
        "stage_count": len(stages),
        "status_counts": dict(status_counts),
        "next_option_count": len(options),
        "segment_duration_mode": segment_duration_mode,
        "shot_rule": payload.get("shot_rule"),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", nargs="?", help="JSON file; omit to read stdin")
    args = parser.parse_args()
    try:
        payload = load_payload(args.json_file)
        result = validate(payload)
    except (OSError, json.JSONDecodeError) as exc:
        result = {"ok": False, "errors": [f"无法读取JSON：{exc}"], "warnings": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
