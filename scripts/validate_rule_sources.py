#!/usr/bin/env python3
"""Validate unique rule-source ownership and cross-file production contracts."""

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
    "beginner": ROOT / "references/11-beginner-guided-mode.md",
    "output": ROOT / "references/12-output-format-and-choice-footer.md",
    "cut": ROOT / "references/13-cut-shot-geometry.md",
    "task": ROOT / "references/14-shot-task-action-coverage.md",
    "agent": ROOT / "agents/openai.yaml",
    "production_template": ROOT / "assets/production-document-template.md",
}

FORBIDDEN = {
    "skill": [
        "## CUT优先分镜规则",
        "### 禁止相邻镜头",
        "## 空间确认Gate",
        "## ENTER／EXIT进出场Gate",
    ],
    "script": [
        "## 30度规则",
        "## 相邻SHOT视觉差异闸门",
        "## ENTER／EXIT进出场Gate",
        "## 跨SHOT状态继承",
        "## 信息可见性",
    ],
    "spatial": [
        "## 有效CUT触发条件",
        "## CUT类型",
        "## 相邻SHOT视觉差异闸门",
        "## ENTER／EXIT进出场Gate",
        "## SHOT任务合同",
    ],
    "cut": [
        "## 场景方向与坐标",
        "## 人物空间状态",
        "## 道具空间状态",
        "## ENTER／EXIT进出场Gate",
        "## SHOT任务合同",
    ],
    "task": [
        "## 场景方向与坐标",
        "## 人物空间状态",
        "## 有效CUT触发条件",
        "## CUT类型",
        "## 相邻SHOT视觉差异闸门",
        "## 30度角度路径",
    ],
}

REQUIRED_REFERENCES = {
    "skill": [
        "references/01-script-slicing.md",
        "references/04-blocking-continuity.md",
        "references/14-shot-task-action-coverage.md",
        "references/13-cut-shot-geometry.md",
    ],
    "script": [
        "04-blocking-continuity.md",
        "14-shot-task-action-coverage.md",
        "13-cut-shot-geometry.md",
    ],
    "spatial": ["14-shot-task-action-coverage.md", "13-cut-shot-geometry.md"],
    "task": ["04-blocking-continuity.md", "13-cut-shot-geometry.md"],
    "cut": ["04-blocking-continuity.md", "14-shot-task-action-coverage.md"],
}

AMBIGUOUS_SEG_SHOT_PHRASES = (
    "一个10秒SHOT内部不得再出现第二个CUT",
    "一个10秒SHOT内部不得出现第二次CUT",
    "同一SHOT内不得再出现",
    "SHOT内部不得再出现第二个CUT",
)

SINGLE_SHOT_SEG_CONTRACT = (
    "每个10秒SEG必须且只能包含1个SHOT",
    "SEG内部不包含CUT",
)

SPATIAL_GEOMETRY_CONTRACT = (
    "人物—剧情对象—运动—摄影机几何求解",
    "推导可见面",
    "唯一方案锁",
    "无动机看镜头",
    "camera_position_world",
    "camera_forward_world",
    "场景观察签名",
    "标准空间ID与动作状态机",
)

TASK_COVERAGE_CONTRACT = (
    "## SHOT任务合同",
    "derived_independent_task",
    "## ENTER／EXIT进出场Gate",
    "## EYELINE_REVEAL视线揭示Gate",
    "## DIALOGUE对白任务Gate",
    "## 视角标签证据",
    "## 状态机与重复动作",
    "主体改变只表示“可能需要新镜头”",
    "camera_forward_world",
)

CUT_DIFFERENCE_CONTRACT = (
    "## 相邻SHOT视觉差异闸门",
    "`14`任务覆盖通过",
    "主体名称改变不能自动证明新镜头成立",
    "scene_id",
    "time_id",
    "## 视觉差异充分性",
    "无意的近似机位跳切",
)

SKILL_PIPELINE_CONTRACT = (
    "01-script-slicing.md",
    "04-blocking-continuity.md",
    "14-shot-task-action-coverage.md",
    "13-cut-shot-geometry.md",
    "derived_independent_task=true",
    "validate_spatial_geometry.py",
    "validate_shot_task.py",
    "validate_cut_geometry.py",
)

STALE_GLOBAL_PHRASES = (
    "相邻SHOT是否满足30度、景别差异、两变量",
    "每次CUT至少改变两个有效视觉变量",
    "禁止相邻机位和相邻景别",
    "无相邻机位、相邻景别或近似构图",
    "满足30度和两变量规则",
    "标准两变量路径要求每次CUT至少改变两个有效维度",
    "第二项可以是另一视觉维度，也可以是",
    "主要主体改变即为强视觉差异",
    "主体改变自动通过",
    "viewpoint字符串不同即视为视角变化",
    "自然语言场景名称不同即视为换场",
)


def appears_before(text: str, first: str, second: str) -> bool:
    first_index = text.find(first)
    second_index = text.find(second)
    return first_index >= 0 and second_index >= 0 and first_index < second_index


def validate(root: Path = ROOT) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    texts: dict[str, str] = {}
    for name, relative in FILES.items():
        path = root / relative.relative_to(ROOT)
        if not path.exists():
            errors.append(f"缺少核心规则文件：{path.relative_to(root)}")
            continue
        texts[name] = path.read_text(encoding="utf-8")

    for name, phrases in FORBIDDEN.items():
        current = texts.get(name, "")
        for phrase in phrases:
            if phrase in current:
                errors.append(
                    f"{FILES[name].relative_to(ROOT)} 重复定义了不属于本文件的规则标题：{phrase}"
                )

    for name, refs in REQUIRED_REFERENCES.items():
        current = texts.get(name, "")
        for ref in refs:
            if ref not in current:
                errors.append(f"{FILES[name].relative_to(ROOT)} 缺少唯一真源引用：{ref}")

    skill_text = texts.get("skill", "")
    for phrase in SKILL_PIPELINE_CONTRACT:
        if phrase not in skill_text:
            errors.append(f"SKILL.md 缺少分镜流水线合同：{phrase}")

    if not (
        appears_before(skill_text, "2. `04`锁定", "3. 只有`04`")
        and appears_before(skill_text, "3. 只有`04`", "4. 只有`14`")
        and appears_before(skill_text, "4. 只有`14`", "5. 返回`01`")
    ):
        errors.append("SKILL.md 的分镜职责顺序必须明确为01→04→14→13→01。")

    spatial_text = texts.get("spatial", "")
    for phrase in SPATIAL_GEOMETRY_CONTRACT:
        if phrase not in spatial_text:
            errors.append(f"references/04-blocking-continuity.md 缺少空间合同：{phrase}")

    task_text = texts.get("task", "")
    for phrase in TASK_COVERAGE_CONTRACT:
        if phrase not in task_text:
            errors.append(f"references/14-shot-task-action-coverage.md 缺少任务合同：{phrase}")

    cut_text = texts.get("cut", "")
    for phrase in CUT_DIFFERENCE_CONTRACT:
        if phrase not in cut_text:
            errors.append(f"references/13-cut-shot-geometry.md 缺少CUT合同：{phrase}")

    if not (
        appears_before(cut_text, "`04`已确认的空间状态", "`14`已验证的SHOT任务")
        and appears_before(cut_text, "`14`已验证的SHOT任务", "本文件的CUT和机位几何规则")
    ):
        errors.append("13必须把04空间事实和14任务覆盖置于CUT决策之前。")

    if "不是相邻SHOT之间的30度剪辑规则" not in spatial_text:
        errors.append("04必须区分单机位可见面角度与相邻SHOT的30度剪辑规则。")

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml"}:
            continue
        if any(part in {".git", "tests", "__pycache__"} for part in path.parts):
            continue
        value = path.read_text(encoding="utf-8")
        for phrase in STALE_GLOBAL_PHRASES:
            if phrase in value:
                errors.append(
                    f"{path.relative_to(root)} 保留了过时或自我证明式规则：{phrase}"
                )

    for name in ("skill", "script", "cut"):
        current = texts.get(name, "")
        for phrase in AMBIGUOUS_SEG_SHOT_PHRASES:
            if phrase in current:
                errors.append(f"{FILES[name].relative_to(ROOT)} 混淆了SEG／SHOT／CUT：{phrase}")

    for name in ("script", "cut"):
        current = texts.get(name, "")
        for phrase in SINGLE_SHOT_SEG_CONTRACT:
            if phrase not in current:
                errors.append(
                    f"{FILES[name].relative_to(ROOT)} 缺少单SHOT SEG明确合同：{phrase}"
                )

    for path_name in ("README.md", "README_EN.md"):
        path = root / path_name
        if not path.exists():
            continue
        current = path.read_text(encoding="utf-8")
        for phrase in (
            "validate_spatial_geometry.py",
            "validate_shot_task.py",
            "validate_cut_geometry.py",
        ):
            if phrase not in current:
                errors.append(f"{path_name} 缺少验证器说明：{phrase}")

    validators = (
        "scripts/validate_spatial_geometry.py",
        "scripts/validate_shot_task.py",
        "scripts/validate_cut_geometry.py",
    )
    for relative in validators:
        if not (root / relative).exists():
            errors.append(f"缺少验证器：{relative}")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
