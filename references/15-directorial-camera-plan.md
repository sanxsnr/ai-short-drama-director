# 导演镜头方案与摄影机轨迹

## 唯一职责

本文件是以下内容的唯一规则真源：

- 读取剧本、动作链、对白、场景功能和基础空间模型后，主动决定这一段**怎么拍、摄影机怎么走、在哪里切**。
- 把导演意图、SHOT顺序、每个SHOT的摄影机轨迹意图和CUT意图写成一个统一的`directorial_camera_plan`。
- 将固定机位、连续运镜和CUT放进同一时间序列中求解，而不是先做三选一，再分别计算。
- 当空间坐标无法实现导演方案时，接收`04-blocking-continuity.md`的失败反馈并重新设计，不把失败责任交给用户。
- 生成`scripts/validate_directorial_camera_plan.py`所需的`DIRECTORIAL_CAMERA_PLAN_V1`合同。

本文件读取`01-script-slicing.md`提供的剧本、动作链、对白与视听节拍，同时继承`02-visual-style.md`和`03-asset-design.md`已经锁定的视觉、角色、道具与场景布局资产。本文件不负责精确计算XYZ坐标、障碍碰撞、关系轴侧和人物可见面；这些由`04-blocking-continuity.md`的空间求解阶段完成。本文件不自行证明任务画面是否拍到；这些由`14-shot-task-action-coverage.md`验证。本文件必须提出CUT语义类型和连接方式意图；`13-cut-shot-geometry.md`负责根据动作进度、空间和相邻画面证据审核该意图是否成立。本文件不自行裁定30度、同轴景别路径或相邻SHOT视觉差异。

## 核心定义：一套摄影机程序，不是三套模式

一个完整镜头方案是一条按时间排列的摄影机程序：

```text
导演读解
→ 视觉节拍
→ SHOT 1中的连续摄影机轨迹
→ CUT事件
→ SHOT 2中的连续摄影机轨迹
→ ……
```

对任一SHOT，在时间区间`t_start ≤ t ≤ t_end`内，摄影机具有连续状态：

```text
C(t) = 位置XYZ + 世界朝向 + 高度 + 构图／景别 + 与主体关系
```

由同一结构自然推导：

- `C(t)`全程不变：固定机位。
- `C(t)`连续变化：运镜。
- 前一个连续区间结束、下一个连续区间开始：CUT。

因此不得再把`locked | movement | cut_to_new_shot`作为上游三选一输入，也不得建立三套独立判断器。固定、运镜和CUT只是同一镜头方案最终呈现出的三种结果。

## 总流程｜DIRECTORIAL_CAMERA_PIPELINE_V2

```text
01：灵感／小说 → 改编方案 → 可拍摄剧本 → 对白与视听动作链
→ 02／03：锁定视觉风格、角色／道具资产和场景布局资产
→ 04A：根据锁定场景资产建立基础空间模型（尺寸、锚点、可通行区、人物初始区）
→ 15：导演思维一次性设计怎么拍、怎么运、怎么切
→ 04B：把导演方案求解为人物与摄影机XYZ、朝向和连续轨迹
→ 若不可执行：04B返回失败原因 → 15重做方案 → 04B再求解
→ 14：验证每个SHOT和运镜阶段是否真正拍到任务证据
→ 13：审核每个已设计CUT的切点、类型、轴线与视觉差异
→ 01：按时长封装SEG
```

该循环由Skill主动完成。用户不需要先选择固定、运镜还是CUT；Skill必须给出一个完整专业方案。用户不满意时可以要求修改，但不能把导演决策反向推给用户。

## 第一步：导演读解

技术选择之前，先回答：

1. **场景功能**：本场在整段故事中负责引入、推进、转折还是兑现？
2. **核心转变**：这一场从什么状态变为什么状态？
3. **POV与共情位置**：观众主要站在谁的体验里？
4. **权力移动**：谁掌握主动，主动权何时转移？
5. **潜台词**：人物说出的内容与真实欲望之间有什么差异？
6. **统一导演意图**：用一句可执行的话说明本场要让观众看见或感受到什么。

“电影感、动态感、高级感、震撼”不是导演意图。合法意图必须能推导出画面行为，例如：

```text
让观众先与董生一起确认眼前异常，随后把威胁主动权交给床上的阿琐。
```

## 第二步：拆视觉节拍

将动作链转换为时间顺序明确的视觉节拍：

```text
beat_id
起止时间
剧情任务
主要主体
动作起点／过程／结果
观众必须看到的证据
情绪或权力变化
```

视觉节拍不是SHOT。多个节拍可以由同一条连续摄影机轨迹完成；当导演认为必须改变观察任务、视角、时间、空间或节奏呼吸时，才设计SHOT边界与CUT事件。

## 第三步：设计统一镜头方案

导演层必须同时决定：

- 每个SHOT承担什么导演任务；
- 从什么构图开始；
- 摄影机在该SHOT内保持、推进、后退、横移、跟随、升降、摇摄、环绕或组合运动；
- 运动过程中观众看见什么；
- 在什么构图结束；
- 是否在终点停稳；
- CUT发生在哪个动作、视线、反应、信息、时间或空间节点；
- CUT后新的观察任务是什么。

导演层可以提出概念性摄影机位置与路径，但不得伪造精确XYZ，也不得宣称路径已经通过障碍、轴线或可见面计算。

## 第四步：空间求解与回退

`04B`读取导演方案后必须求解：

- 人物和摄影机的起点、终点与中间关键帧XYZ；
- 摄影机和人物线段轨迹与障碍包围盒是否相交；
- 摄影机与动态人物轨迹的同步最小距离是否小于安全距离；
- 摄影机线速度、转向角速度和人物速度是否超过场景允许值；
- 摄影机世界朝向；
- 人物身体朝向、视线和移动向量；
- 路径是否穿墙、穿床、穿人或阻挡演员；
- 是否保持关系轴侧，或是否在画面中完成空间重建；
- 目标景别和必要动作是否真实可见；
- 轨迹与时长是否可执行。

若求解失败，输出：

```yaml
spatial_solution:
  status: return_to_director_plan
  failed_shot_id:
  failure_codes:
  blocking_facts:
  redesign_constraints:
```

15必须根据失败事实重做导演方案。禁止04私自改CUT、改主体、改镜头目的，禁止把“请用户选择另一种拍法”作为默认解决方式。

## 统一合同｜DIRECTORIAL_CAMERA_PLAN_V1

```yaml
directorial_camera_plan:
  plan_id:
  segment_id:
  scene_id:
  segment_content_type: normal | high_speed_action | fixed_camera_time_passage
  duration_seconds:

  director_read:
    scene_function:
    dramatic_turn:
    pov_empathy:
    power_movement:
    subtext:
    scene_intention:

  scene_space_basis:
    bounds_world:
      x: [0, 10]
      y: [0, 8]
      z: [0, 4]
    anchor_ids: []
    walkable_zone_ids: []
    blocked_volumes:
      - obstacle_id:
        min_world: [x, y, z]
        max_world: [x, y, z]
    relationship_axes:
      - axis_id:
        source_type: fixed
        point_a_world: [x, y, z]
        point_b_world: [x, y, z]
      - axis_id:
        source_type: actor_pair
        actor_a_id:
        actor_b_id:
    camera_clearance_units:
    actor_clearance_units:
    max_camera_speed_units_per_second:
    max_actor_speed_units_per_second:
    max_camera_angular_speed_degrees_per_second:
    locked_facts: []

  beats:
    - beat_id:
      start_seconds:
      end_seconds:
      dramatic_task:
      primary_subject_id:
      required_visible_evidence: []

  shots:
    - shot_id:
      start_seconds:
      end_seconds:
      dramatic_task:
      primary_subject_id:
      actor_ids: []
      beat_ids: []

      camera_trajectory_intent:
        start_composition:
        path_intent:
        movement_purpose:
        speed_rhythm:
        subject_relation_during_shot:
        required_action_visibility: []
        end_composition:
        hold_after_arrival_seconds:

      cut_out_intent:
        enabled:
        at_seconds:
        cut_point_beat_id:
        cut_type_intent: normal | match_on_action | reaction | eyeline | insert | space | time | pov | occlusion
        transition_mechanism: hard_cut | action_match | eyeline | sound_bridge | occlusion | dissolve
        reason:
        next_shot_id:

  spatial_solution:
    status: solved | return_to_director_plan
    failure_codes: []
    redesign_constraints: []
    shot_solutions:
      - shot_id:
        axis_policy: preserve | visible_reestablish | not_applicable
        relationship_axis_id:
        axis_reestablishment_evidence: []
        camera_keyframes:
          - time_seconds:
            position_world: [x, y, z]
            forward_world: [x, y, z]
            framing:
        actor_keyframes:
          - actor_id:
            time_seconds:
            position_world: [x, y, z]
            body_forward_world: [x, y, z]
```

### 合同解释

- `shots`是导演决定的连续观察区间。
- `camera_trajectory_intent`在每个SHOT中只使用一套结构；固定机位写“保持该构图”，运镜写连续路径意图。
- `cut_out_intent`是SHOT之间的边界事件，不是另一套摄影机模式。
- `spatial_solution`由04B填写；15不得自报路径安全。碰撞、速度、轴线侧和固定／运动结果必须由XYZ关键帧计算得出。
- `actor_ids`列出该SHOT必须进行XYZ求解的故事人物；无人环境镜头使用空数组。
- `relationship_axes`既可由固定锚点定义，也可由`actor_pair`的人物实时位置形成；动态轴由04B随时间求解。
- `axis_policy=not_applicable`时允许场景没有关系轴；`preserve`要求同侧，`visible_reestablish`要求实际跨轴并给出画面内重建证据。
- `derived_independent_task`不属于本合同，由14从画面证据推导。
- `cut_type_intent`和`transition_mechanism`属于导演方案，负责回答“怎么切”；13根据任务、动作和几何证据审核，若不成立则返回15重做，不在13内部临时发明另一种CUT。

## 导演如何决定运镜与CUT

导演不是先问“用哪一种模式”，而是顺着节拍设计观看过程：

1. 当前观众应该站在哪里？
2. 这一节拍中注意力需要保持还是连续转移？
3. 摄影机移动本身是否承载发现、靠近、远离、跟随、揭示或权力变化？
4. 同一连续观察能否完整覆盖动作结果？
5. 何时出现新的独立观察任务？
6. 哪个动作、视线、反应或信息节点是最自然的切点？
7. CUT后为什么必须从新的位置、方向或景别继续？

运镜和CUT可以在同一SEG中共同出现。例如：

```text
SHOT A：中景缓慢推进到近景，人物完成怀疑到确认
→ 在目光锁定目标时CUT
SHOT B：同侧反打目标人物的动作结果
```

这不是“先算运镜，再另算CUT”，而是一份统一导演方案中的连续轨迹与边界事件。

## 多轴运动限制

摄影机轨迹可用空间坐标变化描述：

- Z：靠近／远离；
- Y：升高／降低；
- X：横移／绕行；
- 朝向：PAN／TILT／ROLL；
- 焦点和焦段感：只作视觉辅助，不代替空间轨迹。

普通短SEG通常保持一个主要运动意图，最多叠加一个必要辅助轴。三轴同时大幅变化必须有明确动作与叙事原因，并由04B和14证明可执行、可读。禁止为了“电影感”堆叠推进、环绕、升高、横移和手持晃动。

## 时长逻辑

每个SHOT必须满足：

```text
SHOT时长
≥ 摄影机运动所需时间
＋ 关键动作可见时间
＋ 到达终点后的必要停稳
＋ 对白与反应时间
```

同一SHOT的摄影机关键帧时间必须严格递增，并覆盖该SHOT的完整起止时间。若到达终点后要求固定5秒，空间解必须显式提供到达时刻和后续相同摄影机状态，不能只写`hold_after_arrival_seconds: 5`。

## 典型例子

### 第08镜：特写到跌倒

导演方案可以是：

```text
SHOT A：眼部极近特写，瞳孔骤缩
→ 瞳孔反应完成时硬切
SHOT B：同轴正面中全景，完整展示后退、失衡和跌坐
```

也可以设计一个极速后拉的连续SHOT，但空间求解和动作可读性必须通过。导演应比较冲击力、生成稳定性和动作覆盖后给出主方案，而不是让用户先选。

### 第24镜：床头到圆窗

```text
SHOT 1：床头双人关系构图开始
→ 摄影机沿床侧通道缓慢推进至圆窗
→ 到达圆窗构图后锁定
→ 同一构图中日夜交替、人物状态递进
```

04B必须把床、通道、圆窗、人物和摄影机轨迹计算为XYZ关键帧；若通道不足，返回15重做路径，而不是改成三个无理由近景。

## 输出与验证

运行：

```bash
python3 scripts/validate_directorial_camera_plan.py directorial-camera-plan.json
```

主要错误码：

```text
stale_three_mode_contract
missing_director_read
invalid_scene_space_basis
invalid_beat_timeline
invalid_shot_timeline
missing_camera_trajectory_intent
missing_cut_intent
cut_sequence_mismatch
unmotivated_cut
invalid_cut_type_intent
invalid_cut_transition_mechanism
spatial_plan_requires_redesign
spatial_solution_shot_mismatch
camera_keyframe_timeline_error
camera_position_out_of_bounds
camera_path_intersects_subject
camera_path_intersects_obstacle
actor_path_intersects_obstacle
camera_path_crosses_axis
axis_policy_mismatch
camera_speed_exceeds_space_limit
camera_angular_speed_exceeds_space_limit
actor_speed_exceeds_space_limit
camera_intent_solution_mismatch
missing_actor_spatial_solution
actor_keyframe_timeline_error
hold_duration_not_solved
too_many_camera_motion_axes
```

## 本文件自检

- [ ] 已从剧本和视觉节拍主动提出完整拍法，不把选择交给用户。
- [ ] 已同时设计SHOT、每个SHOT内的摄影机轨迹和CUT节点。
- [ ] 没有使用`locked | movement | cut_to_new_shot`三选一旧合同。
- [ ] 04A已提供基础空间尺寸与锚点。
- [ ] 04B已把导演方案求解为人物与摄影机XYZ关键帧。
- [ ] 空间不可执行时已回退15重做，而不是让04私自改方案。
- [ ] 14已验证动作与任务证据。
- [ ] 13已审核所有CUT的几何与视觉差异。
