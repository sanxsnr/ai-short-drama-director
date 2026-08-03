# 运镜导演决策与摄影机路径规则

## 唯一职责

本文件是以下内容的唯一规则真源：

- 在固定机位、连续运镜和CUT候选之间主动做导演决策。
- 说明摄影机为什么移动、为什么保持、为什么停止，以及为什么不用另一个方案。
- 定义连续运镜的起始构图、运动路径、速度、主体关系、终点构图和终点锁定。
- 检查普通SEG的多轴运动冲突、运镜与人物运动冲突以及AI可执行性。
- 生成`scripts/validate_camera_movement.py`所需的`camera_decision_contract`。

本文件不重新定义人物世界坐标、关系轴、摄影机允许区、障碍物和可见面；这些由`04-blocking-continuity.md`决定。本文件不自行证明SHOT完成动作任务；这些由`14-shot-task-action-coverage.md`验证。本文件也不决定CUT类型、30度适用性或相邻SHOT视觉差异；只有显式CUT候选通过14后，才交给`13-cut-shot-geometry.md`。

## 核心原则

> 摄影机运动不是装饰词。先确定场景要让观众注意、感受或发现什么，再决定观众的观察位置是否需要连续改变。

“电影感”“动态感”“高级感”“更震撼”不能单独构成运镜理由。合法理由必须指向一个可见任务，例如：

- 靠近人物的认知或情绪转折；
- 揭示此前被遮挡的空间、人物或道具；
- 保持与移动主体的距离和动作可读性；
- 从人物关系构图过渡到时间或空间锚点；
- 拉远以展示动作后果或更大的威胁关系；
- 到达一个必须锁定的构图，随后让光线、时间或表演状态变化。

## 强制加载顺序

```text
01-script-slicing.md
→ 04-blocking-continuity.md
→ 15-camera-movement-directing.md
→ 14-shot-task-action-coverage.md
→ 13-cut-shot-geometry.md
→ 返回01封装SEG
```

15只能在04已经提供合法机位区、路径空间、关系轴和状态继承后做决策。14负责证明运动过程中的关键动作和信息可见；13只审核被15标记为`cut_to_new_shot`且通过14的CUT候选。

## 固定／运镜／CUT决策Gate｜CAMERA_DECISION_GATE_V1

按顺序回答：

1. 主要主体是否改变？
2. 标准`scene_id`或`time_id`是否改变？
3. 观察对象或导演任务是否改变？
4. 当前变化是否只是距离、景别、构图重心、高度或空间信息的连续变化？
5. 04是否存在连续、无遮挡、不过轴、不过墙且不穿过人物的摄影机路径？
6. 运镜过程本身是否具有叙事价值，而不是只为了增加运动？
7. 运镜能否在SEG时长内完成，并让14要求的关键动作持续可见？
8. CUT是否具有明确优势，例如观察任务独立、动作冲击更强、AI稳定性更高或必须切到反应／POV／INSERT？

选择逻辑：

```text
任务、时空和观察对象不变
＋只是连续重构画面
＋路径可执行
＋运镜过程有叙事价值
→ movement

当前构图已经完整，摄影机移动不会增加必要信息
→ locked

观察任务明显改变，或连续路径不可能／时间不足／动作不可读，
或CUT具有明确叙事与稳定性优势
→ cut_to_new_shot
```

“优先评估运镜”不等于“强制运镜”。例如眼部极近特写到同轴全身跌倒，极速后拉和硬切都可成立；应比较冲击力、动作覆盖、生成稳定性和时长后选择。

## 摄影机决策合同

```yaml
camera_decision_contract:
  shot_id:
  segment_content_type: normal | high_speed_action | fixed_camera_time_passage
  duration_seconds:

  camera_decision:
    mode: locked | movement | cut_to_new_shot
    reason:
    narrative_function:
    rejected_alternative:

  decision_context:
    same_subject:
    same_time:
    same_space:
    same_observation_task:
    continuous_reframe_only:
    new_independent_task:
    movement_path_feasible:
    movement_has_narrative_value:
    cut_narrative_advantage:
    time_passage_after_lock:

  camera_motion:
    enabled:
    movement_type:
    start_camera_zone:
    start_direction:
    start_height:
    start_framing:
    start_subject_relation:

    path:
      path_description:
      spatial_axes: [Z]
      path_clear:
      axis_side_preserved:
      axis_reestablished:
      intersects_subject:
      intersects_obstacle:
      orbit_degrees:

    speed_profile:
      start_speed:
      middle_speed:
      end_speed:

    subject_relation_during_move:
    information_revealed_during_move:
    action_visible_during_move:
    required_action_during_move:

    movement_duration_seconds:
    minimum_required_seconds:

    end_camera_zone:
    end_direction:
    end_height:
    end_framing:
    end_subject_relation:

    lock_after_move:
    lock_duration_seconds:

  subject_motion:
    direction:
    speed:
    camera_relative_motion_conflict:
```

## 起点与终点

任何`movement`必须同时明确：

- 起始摄影机区域、世界朝向或已锁定方向、高度、景别和主体关系；
- 摄影机沿什么路径移动，哪些空间轴发生变化；
- 移动中持续观察什么、揭示什么以及必须看清的动作；
- 终点摄影机区域、方向、高度、景别和主体关系；
- 是否到达后锁定，以及锁定多少秒。

只写“缓慢推进”“镜头拉远”“环绕拍摄”而没有起点和终点，判`missing_start_framing`、`missing_end_framing`或`missing_motion_path`。

## 路径与空间硬约束

运镜路径必须引用04的世界空间结论，并证明：

- `path_clear=true`；
- 不穿墙、床榻、门框、布景、道具或其他障碍；
- `intersects_subject=false`；
- 关系轴侧保持不变，或在画面中完成明确的重新建立；
- 摄影机不会挡住人物既定移动路线；
- 起点和终点均位于04允许区。

“穿越式运镜”不能作为跳过空间硬约束的借口。除非项目明确采用非写实转场，并由04重新定义空间机制，否则仍判`impossible_camera_path`。

## 速度与时长

速度必须按阶段描述：

```text
缓慢起步 → 匀速推进 → 接近终点时减速并停稳
```

不得在没有阶段说明时同时写“缓慢”和“快速”。

```text
movement_duration_seconds >= minimum_required_seconds
```

最低时间应包含摄影机起步、主体关键动作可见时间、终点稳定和必要停顿。时间不足判`movement_duration_insufficient`；不得通过慢动作、重复动作或无意义漂移填充时长。

## 主体关系与动作覆盖

运镜不是单独的视觉层。必须说明：

- 摄影机与主体的相对距离如何变化；
- 人物移动时摄影机是跟随、让开、迎向还是保持；
- 14要求的动作节点是否在运动中持续可见；
- 是否因为摄影机与人物同时高速对向运动而压缩、遮挡或丢失动作。

若关键动作不可见，判`movement_loses_required_action`。若人物高速后退而摄影机同时高速推进，导致动作距离和重心不可读，判`camera_and_subject_motion_conflict`。

## 多轴运动限制

本文件中的空间轴用于描述摄影机路径变化：

- `Z`：靠近／远离；
- `Y`：升高／降低；
- `X`：横移或绕主体方位变化；
- `PAN_TILT_ROLL`：原地旋转只在确有必要时单列。

普通SEG默认：

```text
一个主要运动轴
＋最多一个辅助运动轴
```

三个或更多空间运动轴同时变化，默认判`too_many_camera_motion_axes`。高速动作可以例外，但必须同时声明`segment_content_type=high_speed_action`、给出多轴必要性，并通过04和14的动作可读性检查。

禁止无动机堆叠：

```text
推进＋环绕＋升高＋横移＋手持晃动
```

近景或极近特写中的大幅环绕容易导致人脸与空间崩坏；默认给出`close_range_large_orbit_risk`警告，必要时改用中近景以上或缩小环绕角度。

## 固定机位

`locked`不是“什么都没设计”。必须说明为什么保持固定以及画面内由谁或什么承担变化。

适用情形包括：

- 对白、口型或细微表演稳定性优先；
- 当前构图已经完整展示关系；
- 让人物进入／离开固定画框形成调度；
- 光线、时间或状态在同一构图中变化；
- 摄影机静止本身形成压迫、等待或观察感。

固定机位仍需通过04和14，不能因为不移动而忽略空间、动作和可见性。

## 移动后锁定

以下结构仍是一个SHOT：

```text
床头双人构图
→ 摄影机连续推进到圆窗
→ 到达目标构图后锁定
→ 日夜、灯光和人物状态发生变化
```

当`time_passage_after_lock=true`时：

```text
lock_after_move=true
lock_duration_seconds > 0
```

否则判`missing_lock_after_move`。普通运镜到达明确终点但未说明是否锁定时，输出同名警告，不自动判CUT。

## CUT候选

选择`cut_to_new_shot`时必须证明：

- 下一观察任务确实独立，或CUT具有明确的冲击、稳定性、反应、POV、INSERT、空间或时间优势；
- 不是仅因为景别改变、焦段改变或“想更有节奏”；
- 如果只是同一主体、同一时空、同一任务的连续重构，而且04存在清楚路径，则无理由CUT判`unnecessary_cut_for_continuous_reframe`。

15只产生CUT候选。下一SHOT仍必须通过14，之后13才能决定CUT类型和视觉差异。

## 焦段与视觉感

精确焦段只能作为软提示：

```text
广角空间感
标准透视
轻长焦压缩感
浅景深特写感
```

焦段变化不得代替：

- 摄影机路径；
- 景别起点与终点；
- CUT边界；
- 世界坐标与关系轴；
- 动作可见性。

同一SHOT列出多个焦段但没有连续变焦、摄影机推近／后退或CUT说明时，仍由`05-video-prompting.md`和`validate_segment_structure.py`输出`ambiguous_focal_transition`。

## 输出与验证

运行：

```bash
python3 scripts/validate_camera_movement.py camera-decision.json
```

主要错误码：

```text
missing_camera_movement_purpose
missing_start_framing
missing_end_framing
missing_motion_path
impossible_camera_path
camera_path_crosses_axis
camera_path_intersects_subject
camera_path_intersects_obstacle
movement_duration_insufficient
movement_loses_required_action
too_many_camera_motion_axes
camera_and_subject_motion_conflict
missing_lock_after_move
unmotivated_camera_movement
unnecessary_cut_for_continuous_reframe
forced_movement_across_distinct_tasks
conflicting_camera_movements
```

## 本文件自检

- [ ] 已先读取04的世界空间与合法路径结论。
- [ ] 已主动比较locked、movement与cut_to_new_shot。
- [ ] 选择理由指向可见叙事任务，不是空泛电影感。
- [ ] 运镜起点、路径、速度、主体关系、终点和锁定完整。
- [ ] 普通SEG没有无理由超过两个运动轴。
- [ ] 运镜过程不会丢失14要求的关键动作。
- [ ] CUT候选没有用焦段或轻微景别变化自我证明。
- [ ] 显式CUT候选继续交给14和13，不在本文件越权通过。
