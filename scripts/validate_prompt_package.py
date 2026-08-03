#!/usr/bin/env python3
"""Validate a structured video-prompt input package."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

WHITESPACE_RE = re.compile(r"\s+")
INTERNAL_MARKERS = (
    "<Asset_Setup>",
    "<RAW_PAYLOAD>",
    "<画图提示词>",
    "<资产小结>",
    "Transparent Proxy",
    "底层数据透传代理",
    "使用 $ai-short-drama-director",
)
FRAME_ROLES = {"first_frame", "last_frame", "首帧", "尾帧"}
FRAME_MODES = {"i2v", "flf2v", "video_extension", "首帧", "首尾帧", "视频延长"}
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


def compact(text: object) -> str:
    return WHITESPACE_RE.sub("", str(text or ""))


def text_list(value: object, field: str, errors: list[str]) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{field} 必须是字符串数组")
        return []
    return [item.strip() for item in value if item.strip()]


def clean_role_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def validate_reference_role(ref: dict, label: str, errors: list[str]) -> str:
    """Return the canonical single role, rejecting plural or multi-value schemas."""

    if "roles" in ref:
        raw_roles = ref.get("roles")
        if isinstance(raw_roles, list):
            role_items = clean_role_items(raw_roles)
            if len(role_items) > 1:
                errors.append(f"参考素材{label}承担多个职责：{role_items}")
            errors.append(
                f"参考素材{label}使用了未定义字段 roles；"
                "职责字段必须使用单数 role，且值为非空字符串"
            )
        else:
            errors.append(
                f"参考素材{label}的 roles 字段无效；"
                "职责字段必须使用单数 role，且值为非空字符串"
            )

    raw_role = ref.get("role")
    if isinstance(raw_role, str):
        role = raw_role.strip()
        if not role:
            errors.append(f"参考素材{label}缺少唯一 role")
        return role

    if isinstance(raw_role, list):
        role_items = clean_role_items(raw_role)
        if len(role_items) > 1:
            errors.append(f"参考素材{label}承担多个职责：{role_items}")
        errors.append(f"参考素材{label}的 role 必须是非空字符串，不能是数组")
        return ""

    if raw_role is None:
        errors.append(f"参考素材{label}缺少唯一 role")
    else:
        errors.append(f"参考素材{label}的 role 必须是非空字符串")
    return ""


def validate(payload: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    for field in (
        "segment_id",
        "platform",
        "source_of_truth_version",
        "source_text",
        "final_prompt",
    ):
        if not compact(payload.get(field)):
            errors.append(f"缺少有效字段：{field}")

    try:
        target_duration = float(payload.get("target_duration", 0))
        if target_duration <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("target_duration 必须是大于0的数字")
        target_duration = 0

    generation_mode = str(payload.get("generation_mode", "standard")).strip().lower()
    shot_rule = payload.get("shot_rule")
    segment_terminal = payload.get("segment_terminal")
    if shot_rule is not None and shot_rule not in ALLOWED_SHOT_RULES:
        errors.append(
            "shot_rule 必须是 single_shot_per_segment 或 "
            "multiple_shots_per_segment"
        )

    final_prompt = str(payload.get("final_prompt", ""))
    compact_prompt = compact(final_prompt)
    for marker in INTERNAL_MARKERS:
        if marker.lower() in final_prompt.lower():
            errors.append(f"生产版提示词包含内部标记或对话命令：{marker}")

    references = payload.get("references")
    if not isinstance(references, list):
        errors.append("references 必须是数组")
        references = []
    reference_ids: set[str] = set()
    for index, ref in enumerate(references, start=1):
        if not isinstance(ref, dict):
            errors.append(f"references[{index}] 必须是对象")
            continue
        ref_id = str(ref.get("id", "")).strip()
        label = ref_id or str(index)
        if not ref_id:
            errors.append(f"references[{index}] 缺少 id")
        elif ref_id in reference_ids:
            errors.append(f"参考素材 id 重复：{ref_id}")
        else:
            reference_ids.add(ref_id)

        role = validate_reference_role(ref, label, errors)
        role_normalized = role.lower()

        if ref.get("status") == "obsolete":
            errors.append(f"参考素材{label}已作废，不得进入当前输入包")
        if role_normalized in FRAME_ROLES and generation_mode not in FRAME_MODES:
            errors.append(
                f"参考素材{label}使用{role}职责，但 generation_mode={generation_mode!r}；"
                "普通多镜头流程不得默认加入首尾帧"
            )

    required_assets = set(text_list(payload.get("required_assets"), "required_assets", errors))
    provided_assets = set(text_list(payload.get("provided_assets"), "provided_assets", errors))
    missing_assets = sorted(required_assets - provided_assets)
    if missing_assets:
        errors.append(f"缺少必需资产：{', '.join(missing_assets)}")

    dialogue_lines = payload.get("dialogue_lines", [])
    if not isinstance(dialogue_lines, list):
        errors.append("dialogue_lines 必须是数组")
        dialogue_lines = []
    missing_dialogue: list[str] = []
    for index, line in enumerate(dialogue_lines, start=1):
        if not isinstance(line, dict):
            errors.append(f"dialogue_lines[{index}] 必须是对象")
            continue
        speaker = str(line.get("speaker", "")).strip()
        text = str(line.get("text", "")).strip()
        if not speaker or not text:
            errors.append(f"dialogue_lines[{index}] 缺少 speaker 或 text")
            continue
        if compact(text) not in compact_prompt:
            missing_dialogue.append(f"{speaker}：{text}")
    if missing_dialogue:
        errors.append("生产版提示词遗漏原台词：" + "｜".join(missing_dialogue))

    expected_entities = text_list(payload.get("expected_entities"), "expected_entities", errors)
    forbidden_entities = text_list(payload.get("forbidden_entities"), "forbidden_entities", errors)
    for entity in expected_entities:
        if compact(entity) not in compact_prompt:
            warnings.append(f"生产版提示词未显式出现预期实体：{entity}")
    for entity in forbidden_entities:
        if compact(entity) in compact_prompt:
            errors.append(f"生产版提示词出现禁止实体：{entity}")

    shots = payload.get("shots")
    if shots is not None:
        if not isinstance(shots, list) or not shots:
            errors.append("shots 存在时必须是非空数组")
        else:
            if not isinstance(segment_terminal, bool):
                errors.append("提供shots时必须明确 segment_terminal=true/false")
            if shot_rule in {"single_shot_per_segment", "每个SEG单SHOT"} and len(shots) != 1:
                errors.append(
                    f"shot_rule={shot_rule} 时每个SEG必须且只能包含1个SHOT，"
                    f"当前为{len(shots)}个"
                )

            shot_ids: set[str] = set()
            for index, shot in enumerate(shots, start=1):
                if not isinstance(shot, dict):
                    errors.append(f"shots[{index}] 必须是对象")
                    continue
                shot_id = str(shot.get("id", "")).strip()
                if not shot_id:
                    errors.append(f"shots[{index}] 缺少 id")
                elif shot_id in shot_ids:
                    errors.append(f"SHOT id 重复：{shot_id}")
                else:
                    shot_ids.add(shot_id)

                for field in (
                    "scene_id",
                    "time_id",
                    "camera_zone_id",
                    "camera_forward_world",
                    "primary_scene_anchor_id",
                ):
                    if shot.get(field) in (None, "", []):
                        errors.append(f"SHOT {shot_id or index}缺少世界空间字段：{field}")

                task_validation = shot.get("task_validation")
                if not isinstance(task_validation, dict):
                    errors.append(f"SHOT {shot_id or index}缺少 task_validation")
                else:
                    if task_validation.get("derived_independent_task") is not True:
                        errors.append(
                            f"SHOT {shot_id or index}未取得 derived_independent_task=true"
                        )
                    if not str(task_validation.get("task_type", "")).strip():
                        errors.append(f"SHOT {shot_id or index}缺少 task_validation.task_type")
                    if task_validation.get("validator") != "validate_shot_task.py":
                        errors.append(
                            f"SHOT {shot_id or index}的task_validation必须来自validate_shot_task.py"
                        )

                is_last = index == len(shots)
                cut_point = str(shot.get("cut_point", "")).strip()
                cut_type = str(shot.get("cut_type", "")).strip().upper()
                if is_last and segment_terminal is True:
                    if cut_type != "END":
                        errors.append(f"终镜SHOT {shot_id or index}必须使用 cut_type=END")
                else:
                    if not cut_point:
                        errors.append(f"SHOT {shot_id or index}缺少 cut_point")
                    if not cut_type:
                        errors.append(f"SHOT {shot_id or index}缺少 cut_type")
                    elif cut_type == "END":
                        errors.append(
                            f"非终点SHOT {shot_id or index}不得使用 cut_type=END"
                        )

    context_scope = payload.get("context_scope", {})
    if context_scope is not None and not isinstance(context_scope, dict):
        errors.append("context_scope 必须是对象")
        context_scope = {}
    segment_count = context_scope.get("segment_count")
    if isinstance(segment_count, int) and segment_count > 2:
        warnings.append("当前输入包超过2个SEG；确认更早内容确实为当前任务必需")
    if context_scope.get("includes_obsolete_versions") is True:
        errors.append("当前输入包包含已作废版本")
    if context_scope.get("uses_concise_asset_summaries") is False:
        warnings.append("建议使用精简资产小结，避免完整长资产提示词污染视频会话")

    return {
        "ok": not errors,
        "segment_id": payload.get("segment_id"),
        "target_duration": target_duration,
        "generation_mode": generation_mode,
        "reference_count": len(references),
        "missing_assets": missing_assets,
        "dialogue_line_count": len(dialogue_lines),
        "shot_count": len(shots) if isinstance(shots, list) else 0,
        "shot_rule": shot_rule,
        "segment_terminal": segment_terminal,
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
