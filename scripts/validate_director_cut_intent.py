#!/usr/bin/env python3
"""Audit the director-authored CUT intent before geometric CUT validation."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUT_TYPE_INTENTS = {
    "normal", "match_on_action", "reaction", "eyeline", "insert",
    "space", "time", "pov", "occlusion",
}
CUT_TRANSITION_MECHANISMS = {
    "hard_cut", "action_match", "eyeline", "sound_bridge", "occlusion", "dissolve",
}
GENERIC = {"更有节奏", "节奏感", "电影感", "动态感", "高级感", "好看", "cinematic", "dynamic"}


def _load_task_validator():
    path = ROOT / "scripts/validate_shot_task.py"
    spec = importlib.util.spec_from_file_location("validate_shot_task_for_cut_intent", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TASK = _load_task_validator()


def text(value: object) -> str:
    return str(value or "").strip()


def progress(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 1 else None


def generic_reason(value: object) -> bool:
    compact = text(value).lower().replace(" ", "")
    return not compact or compact in {item.lower().replace(" ", "") for item in GENERIC}


def validate(payload: dict) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    intent = payload.get("director_cut_intent") if isinstance(payload.get("director_cut_intent"), dict) else {}
    before = payload.get("from_shot") if isinstance(payload.get("from_shot"), dict) else {}
    after = payload.get("to_shot") if isinstance(payload.get("to_shot"), dict) else {}

    if not intent:
        errors.append("director_cut_intent必须由15导演镜头方案提供")

    before_id = text(before.get("id") or before.get("shot_id"))
    after_id = text(after.get("id") or after.get("shot_id"))
    from_id = text(intent.get("from_shot_id"))
    to_id = text(intent.get("to_shot_id"))
    if not before_id or not after_id:
        errors.append("from_shot和to_shot必须提供id／shot_id")
    if from_id != before_id:
        errors.append("director_cut_intent.from_shot_id必须匹配from_shot")
    if to_id != after_id:
        errors.append("director_cut_intent.to_shot_id必须匹配to_shot")

    cut_type = text(intent.get("cut_type_intent"))
    mechanism = text(intent.get("transition_mechanism"))
    if cut_type not in CUT_TYPE_INTENTS:
        errors.append("cut_type_intent无效")
    if mechanism not in CUT_TRANSITION_MECHANISMS:
        errors.append("transition_mechanism无效")
    if generic_reason(intent.get("reason")):
        errors.append("CUT理由不能只写节奏感或电影感")

    task_contract = after.get("task_contract") if isinstance(after.get("task_contract"), dict) else {}
    task_result = TASK.validate(task_contract) if task_contract else {
        "ok": False,
        "derived_independent_task": False,
        "viewpoint_evidence_passed": False,
        "task_type": "",
        "scene_id": text(after.get("scene_id")),
        "time_id": text(after.get("time_id")),
        "errors": ["to_shot缺少task_contract"],
    }
    if not task_result.get("ok") or task_result.get("derived_independent_task") is not True:
        errors.append("14任务覆盖Gate未通过，CUT意图不能成立")
    task_type = text(task_result.get("task_type")).upper()
    viewpoint = text(task_contract.get("viewpoint"))

    if cut_type == "eyeline" and task_type != "EYELINE_REVEAL":
        errors.append("EYELINE CUT要求下一SHOT为EYELINE_REVEAL任务")
    if cut_type == "reaction" and task_type != "REACTION":
        errors.append("REACTION CUT要求下一SHOT为REACTION任务")
    if cut_type == "insert" and not (task_type == "PROP_ACTION" or viewpoint == "INSERT"):
        errors.append("INSERT CUT要求PROP_ACTION任务或真实INSERT视角证据")
    if cut_type == "pov" and not (viewpoint == "POV" and task_result.get("viewpoint_evidence_passed") is True):
        errors.append("POV CUT要求真实POV视角证据")
    if cut_type == "space":
        before_scene = text(before.get("scene_id"))
        after_scene = text(after.get("scene_id"))
        if before_scene == after_scene and task_type not in {"ENTER", "EXIT", "ESTABLISH"}:
            errors.append("SPACE CUT必须有真实空间变化、边界任务或重新建立空间")
    if cut_type == "time":
        if text(before.get("time_id")) == text(after.get("time_id")):
            errors.append("TIME CUT要求time_id真实变化")
    if cut_type == "occlusion" and mechanism != "occlusion":
        errors.append("OCCLUSION CUT必须使用occlusion转接机制")

    if mechanism == "dissolve" and cut_type not in {"time", "space"}:
        errors.append("dissolve只适用于明确的时间或空间转换")
    if mechanism == "eyeline" and cut_type != "eyeline":
        errors.append("eyeline转接机制只适用于EYELINE CUT")
    if mechanism == "action_match" and cut_type != "match_on_action":
        errors.append("action_match机制只适用于MATCH-ON-ACTION")

    action_match_valid = False
    if cut_type == "match_on_action":
        match = intent.get("action_match") if isinstance(intent.get("action_match"), dict) else {}
        required = ("action_id", "progress_before", "progress_after", "direction_continuous", "speed_continuous", "body_state_continuous", "prop_state_continuous")
        if not match or any(field not in match for field in required):
            errors.append("MATCH-ON-ACTION必须提供完整action_match合同")
        else:
            before_progress = progress(match.get("progress_before"))
            after_progress = progress(match.get("progress_after"))
            if not text(match.get("action_id")):
                errors.append("action_match.action_id不能为空")
            if before_progress is None or after_progress is None:
                errors.append("action_match进度必须位于0到1之间")
            elif before_progress >= 1:
                errors.append("动作已经完成，不能再标MATCH-ON-ACTION")
            elif after_progress + 1e-9 < before_progress:
                errors.append("MATCH-ON-ACTION不能重置动作进度")
            for field in ("direction_continuous", "speed_continuous", "body_state_continuous", "prop_state_continuous"):
                if match.get(field) is not True:
                    errors.append(f"action_match.{field}必须为true")
            action_match_valid = not any("action_match" in item or "MATCH-ON-ACTION" in item or "动作已经完成" in item for item in errors)

    return {
        "ok": not errors,
        "director_cut_intent_valid": not errors,
        "cut_type_intent": cut_type,
        "transition_mechanism": mechanism,
        "action_match_valid": action_match_valid,
        "task_coverage_passed": bool(task_result.get("ok")),
        "task_type": task_type,
        "errors": errors,
        "warnings": warnings,
    }


def load_payload(path: str | None) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else json.load(sys.stdin)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", nargs="?")
    args = parser.parse_args()
    try:
        result = validate(load_payload(args.json_file))
    except (OSError, json.JSONDecodeError) as exc:
        result = {"ok": False, "errors": [f"invalid_json: {exc}"], "warnings": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
