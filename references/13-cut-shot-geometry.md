# CUT切镜与相邻SHOT视觉几何审核

## 唯一职责

本文件只负责审核`15-directorial-camera-plan.md`已经设计的CUT点是否有效：

- 读取15的`director_cut_intent`，确认`cut_type_intent`、`transition_mechanism`、切点与导演理由完整。
- 读取`14-shot-task-action-coverage.md`的任务覆盖结论，确认下一SHOT已被证明具有独立导演任务。
- 读取`04-blocking-continuity.md`的空间解，检查关系轴、运动方向、摄影机世界位置、状态继承和信息可见性。
- 审核普通CUT、MATCH-ON-ACTION、REACTION、EYELINE、INSERT、SPACE、TIME、POV与遮挡CUT。
- 审核相邻SHOT视觉差异、30度适用性、同轴大景别路径、组合差异、图形匹配和有意跳切。

本文件不在没有15方案时自行新增CUT，不负责决定整场怎么拍，也不重新计算人物或摄影机XYZ。审核失败时输出返工原因并返回15重做，不在13内部临时发明另一种CUT。

## 审核顺序

```text
15 director_cut_intent
→ scripts/validate_director_cut_intent.py
→ 04空间与轴线结果
→ 14任务覆盖与动作状态机
→ 本文件CUT几何审核
→ scripts/validate_cut_geometry.py
→ 通过／返回15重做
```

CUT成立必须同时满足：

1. 15已经提出明确的`director_cut_intent`。
2. 当前动作、视线、反应、信息、时间或空间节点形成可识别结果。
3. 下一SHOT通过`14`任务覆盖，`derived_independent_task=true`。
4. 04证明状态、方向、轴线和空间关系合法。
5. 相邻SHOT通过至少一条有效视觉差异路径。

主体名称改变、换说话人、viewpoint字符串改变或自然语言场景标签改变都不能自动证明CUT成立。

## director_cut_intent合同

```yaml
director_cut_intent:
  from_shot_id:
  to_shot_id:
  cut_type_intent: normal | match_on_action | reaction | eyeline | insert | space | time | pov | occlusion
  transition_mechanism: hard_cut | action_match | eyeline | sound_bridge | occlusion | dissolve
  reason:
  action_match:
    action_id:
    progress_before:
    progress_after:
    direction_continuous:
    speed_continuous:
    body_state_continuous:
    prop_state_continuous:
```

- `reason`必须说明为什么当前节点需要切换观察，不能只写“更有节奏”“电影感”。
- `cut_type_intent`由15提出；13审核其语义和几何是否成立。
- `transition_mechanism`说明CUT如何发生，不等于CUT类型。
- `dissolve`只适用于明确的时间或空间转换。
- `match_on_action`必须提供`action_match`，动作进度不能回退、重置或在前镜已经完成。

运行：

```bash
python3 scripts/validate_director_cut_intent.py director-cut-intent.json
python3 scripts/validate_cut_geometry.py cut-geometry.json
```

## 有效CUT触发条件

### 动作完成点

人物到达并停稳、坐下、站起、跌倒、门完成开合、道具完成拿取／放置／交接，都可形成候选切点。动作结果未形成时，不得把普通CUT写成完成点。

### 动作阶段转换

行走转观察、发现转靠近、对话转行动、对峙转动手等可以形成候选切点；若下一阶段没有独立镜头任务，应继续当前SHOT。

### 视线落点

人物目光已经锁定目标后，15可设计`eyeline` CUT。下一SHOT必须通过`14`的`EYELINE_REVEAL`任务，展示目标、方向与关键状态。

### 有剧情作用的反应

关键信息造成立场、情绪、权力或行动目标改变时，可设计`reaction` CUT。普通眨眼、呼吸和无剧情作用的微表情不单独成镜。

### 对白重心转换

关键问题、核心回答、谎言被识破、威胁成立、听者反应更重要或对话转行动时可以CUT。禁止因为说话者变化就机械正反打。

### 新主体、新信息、空间和时间

关键人物、道具、异常细节或威胁成为新的已验证任务时可CUT。跨越明确边界可用SPACE CUT；真实时间跳跃、梦境或回忆切换可用TIME CUT。同一固定构图中的日夜变化不是TIME CUT。

### 遮挡与声音桥

门板、人物、柱子、床幔或黑暗遮满画面时可设计遮挡CUT；声音可提前或延后。连接手段不能替代下一SHOT独立任务。

## CUT类型审核

- **normal**：当前阶段已经完成，下一SHOT承接结果。
- **match_on_action**：未完成动作跨机位继续，必须保持方向、速度、身体和道具状态。
- **reaction**：下一SHOT必须是通过14验证的REACTION任务。
- **eyeline**：下一SHOT必须是通过14验证的EYELINE_REVEAL任务。
- **insert**：关键道具／手部成为独立任务，或具有真实INSERT证据。
- **space**：真实scene_id变化、边界跨越或空间重新建立。
- **time**：time_id真实变化。
- **pov**：下一SHOT具有真实POV来源和目标证据。
- **occlusion**：遮挡机制真实成立。

## MATCH-ON-ACTION

动作未完成时才允许跨机位：

```text
前镜：动作已开始，progress_before < 1
→ CUT
→ 后镜：同一action_id从progress_after继续，progress_after >= progress_before
```

必须继承：

- 动作方向与速度。
- 身体重心和手脚位置。
- 道具、门窗或机关进度。
- 人物所在空间和接触关系。

禁止动作重置、重复起点、无过程换位或前镜已经完成后仍标MATCH-ON-ACTION。

## 相邻SHOT视觉差异闸门

任何CUT在任务和轴线先通过后，至少满足一条视觉差异路径。各路径是替代关系，不是累计门槛。

### 1. angle

同一主体、近似景别、连续时空时，主体处摄影机夹角通常达到约30度可形成明确角度路径。30度只在该类比较中适用，不高于180度轴线。

### 2. axial_scale

同轴或近同轴CUT允许通过大景别跨级形成强差异。例如眼部ECU硬切到完整身体动作的MS／MLS／FS。小幅相邻景别同轴跳切通常无效。

### 3. subject_or_viewpoint

下一SHOT通过14证明了新主体、新视角或新场景任务，并且画面证据真实可见，可形成强差异。主体名称或标签变化本身不算。

### 4. combined

角度、景别、构图、主体占比、前后景关系等多项中等差异组合后可以充分。不能把“改变两项”写成所有CUT的机械门槛。

### 5. intentional_jump

有意跳切必须明确导演目的，例如压缩等待、制造断裂或主观失衡。没有目的就是无意近似跳切。

### 6. graphic_match

必须提供真实图形匹配依据，例如圆窗与月亮在画面中的位置、尺寸和轮廓对应。

## 30度适用性

30度规则适用于同一主体、相近景别、连续时空且采用角度路径的相邻SHOT。以下情况可以不适用：

- 同轴大景别跨级。
- 已验证的新主体、POV／OTS／INSERT或空间／时间变化。
- 图形匹配或有意跳切。

反方向同侧反打不等于越轴。摄影机方向近似相反时，仍应以04的关系轴侧和屏幕关系判断是否合法。

## 180度轴线优先

若04判定`crossed_without_reestablish`，任何任务、角度或景别差异都不能挽救CUT。合法状态包括：

```text
same_side
reestablished
not_applicable
```

越轴需要镜头内可见穿越、人物走位改变轴线、中性机位或重新建立空间。

## 与14和04的边界

- 14决定下一SHOT是否真的拍到了任务，不接受`independent_task=true`自报。
- 04决定人物、摄影机、关系轴、可见面和状态继承是否合法。
- 13只审核15提出的CUT意图及相邻几何。
- 13不能因为几何差异够大而绕过任务失败，也不能因为任务成立而绕过轴线失败。

## 输出字段

```yaml
transition_id:
director_cut_intent:
task_coverage_passed:
task_type:
axis_status:
thirty_degree_applicable:
camera_angle_difference_degrees:
shot_scale_step_difference:
derived_difference_path:
director_cut_intent_valid:
action_match_valid:
errors: []
warnings: []
```

主要错误包括：

```text
invalid_task_coverage
invalid_near_jump
invalid_director_cut_intent
invalid_cut_type_intent
invalid_cut_transition_mechanism
invalid_action_match
cross_axis_without_reestablish
```

## 自检

- [ ] 15已设计CUT类型、连接机制、切点和理由。
- [ ] `validate_director_cut_intent.py`通过。
- [ ] 14任务覆盖通过。
- [ ] 04状态、方向、轴线和空间继承通过。
- [ ] 相邻SHOT通过至少一条真实视觉差异路径。
- [ ] MATCH-ON-ACTION动作进度没有重置。
- [ ] 反打没有被仅凭拍摄方向误判越轴。
- [ ] 审核失败已返回15重做，没有在13临时改方案。

## 视觉差异充分性

`14`任务覆盖通过是CUT审核前提。主体名称改变不能自动证明新镜头成立；只有真实任务证据和视觉路径共同成立时才通过。审核目标是拦截无意的近似机位跳切，而不是机械禁止相邻景别。
