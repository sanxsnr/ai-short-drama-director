# 主动运镜导演层仓库升级报告

## 结论

本次仓库更新把`ai-short-drama-director`从“识别已写运镜并做合规检查”，升级为“读取剧情与空间事实后，主动比较固定机位、连续运镜与CUT候选”。

```text
01 剧情／时长／SEG
→ 04 世界坐标／轴线／障碍／合法路径
→ 15 固定／运镜／CUT主动决策
→ 14 动作与信息覆盖
→ 13 显式CUT几何审核
→ 01 封装SEG
```

## 外部参考

研究了两个MIT许可项目：

- Emily2040／seedance-2.0：`skills/seedance-camera/SKILL.md`、`references/directing-engine.md`
- MapleShaw／seedance2.0-prompt-skill：`references/camera-codec.md`

仓库采用的是方法思想和项目内重新设计的合同，不把外部Skill作为运行依赖，也不整段复制外部规则。来源与边界见`THIRD_PARTY_REFERENCES.md`及`docs/camera-movement-reference-analysis.md`。

## 仓库实际变更

- 更新`SKILL.md`，把`15-camera-movement-directing.md`加入唯一规则真源和强制加载顺序。
- 新增`references/15-camera-movement-directing.md`。
- 新增`scripts/validate_camera_movement.py`。
- 新增`tests/test_camera_movement.py`，包含16项主动运镜专项回归。
- 新增第三方参考说明和方法对照文档。

## 新增能力

- 主动输出`locked | movement | cut_to_new_shot`三选一结论。
- 运镜必须说明叙事动机、起点、路径、速度阶段、主体关系、终点和锁定。
- 检查穿墙、穿床、穿人物、越轴、路径不可执行、动作丢失、运镜时长不足和摄影机／人物运动冲突。
- 普通SEG最多一个主运动轴加一个辅助运动轴；高速动作例外必须证明必要性和动作可读性。
- 支持“前段运镜、到达后锁定、随后日夜变化”的单SHOT结构。
- 拦截同一观察任务被无理由切碎，以及不同观察任务被强行连续运镜。
- “电影感”等空泛理由不能单独通过。
- 精确焦段继续只作视觉感觉提示，不替代路径、景别或CUT。

## 验证结果

在与仓库`main`一致的本地副本中运行：

```text
python -m compileall -q scripts tests
python -m unittest discover -s tests -p 'test_*.py' -q
python scripts/validate_rule_sources.py
```

结果：

- Python编译：通过。
- 完整回归测试：89项全部通过，其中新增运镜测试16项。
- 规则真源检查：0错误、0警告。

## 当前边界

本次更新解决主动运镜决策与路径验证，但尚未新增两个独立模块：用户原始导演意图锁定Gate，以及普通SEG的独立任务密度／对白时间预算Gate。它们应在后续单独实现，不能伪装成本次已经完成。
