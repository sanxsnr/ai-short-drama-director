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
)


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

    final_prompt = str(payload.get("final_prompt", ""))
    compact_prompt = compact(final_prompt)
    for marker in INTERNAL_MARKERS:
        if marker.lower() in final_prompt.lower():
            errors.append(f"生产版提示词包含内部标记：{marker}")

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
        role = str(ref.get("role", "")).strip()
        if not ref_id:
            errors.append(f"references[{index}] 缺少 id")
        elif ref_id in reference_ids:
            errors.append(f"参考素材 id 重复：{ref_id}")
        else:
            reference_ids.add(ref_id)
        if not role:
            errors.append(f"参考素材{ref_id or index}缺少唯一 role")
        roles = ref.get("roles")
        if isinstance(roles, list) and len(roles) > 1:
            errors.append(f"参考素材{ref_id or index}承担多个职责：{roles}")
        if ref.get("status") == "obsolete":
            errors.append(f"参考素材{ref_id or index}已作废，不得进入当前输入包")

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

    context_scope = payload.get("context_scope", {})
    if context_scope is not None and not isinstance(context_scope, dict):
        errors.append("context_scope 必须是对象")
        context_scope = {}
    segment_count = context_scope.get("segment_count")
    if isinstance(segment_count, int) and segment_count > 2:
        warnings.append("当前输入包超过2个制片段；确认更早内容确实为当前任务必需")
    if context_scope.get("includes_obsolete_versions") is True:
        errors.append("当前输入包包含已作废版本")
    if context_scope.get("uses_concise_asset_summaries") is False:
        warnings.append("建议使用精简资产小结，避免把完整长资产提示词塞入视频会话")

    return {
        "ok": not errors,
        "segment_id": payload.get("segment_id"),
        "target_duration": target_duration,
        "reference_count": len(references),
        "missing_assets": missing_assets,
        "dialogue_line_count": len(dialogue_lines),
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
