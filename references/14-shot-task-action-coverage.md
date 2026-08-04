# SHOT任务、动作覆盖与视角适配规则

## 唯一职责

本文件是以下内容的唯一规则真源：

- 验证`15-directorial-camera-plan.md`设计的SHOT是否真的拍到了任务。
- 验证导演选择的摄影点是否服务当前任务，而不是继续复用最安全的旧视角。
- 从画面证据推导下一SHOT是否具有独立导演任务。
- 验证同一SHOT的连续摄影机轨迹阶段是否完成阶段任务，且没有被误报为独立SHOT。
- 验证ENTER、EXIT、EYELINE_REVEAL、REACTION、CONTACT、PROP_ACTION、MOVEMENT、DIALOGUE、ESTABLISH等任务。
- 验证人物／道具动作状态机，防止重复进入、重复跌倒、重复拿取或动作重置。
- 验证POV、OTS、INSERT和subjective标签具有真实画面证据。

本文件读取`04-blocking-continuity.md`的XYZ空间解、`camera_station_id`和完整`observation_signature`，也读取15的SHOT任务和摄影机轨迹意图。本文件不重新设计怎么拍、怎么运或怎么切；这些只由15决定。本文件不计算人物正面、关系轴或摄影机允许区；这些只由04决定。本文件不审核CUT类型和相邻SHOT视觉差异；这些只由`13-cut-shot-geometry.md`完成。

任何CUT必须先通过04空间求解，再通过本文件任务与视角适配，最后交给13审核。

## 核心原则

> 写了“镜头任务”不等于完成镜头任务。只有当前构图真正展示了任务要求的主体、空间锚点、动作过程和结果，而且所选摄影点对该任务有导演意义，下一SHOT才成立。

禁止自我证明：

```text
independent_task: true
主体改变了，所以镜头成立
viewpoint写成OTS，所以已经形成过肩
换了说话人，所以必须反打
仍在同一轴线侧，所以继续复用同一摄影点
自然语言场景名称不同，所以已经换场
```

必须推导：

```text
任务类型
→ 必要画面证据
→ 04B机位和XYZ轨迹能否看见
→ 当前camera_station_id是否服务任务
→ 观察签名是否产生需要的观察变化
→ 动作起点、经过节点与终点是否连续
→ 状态机是否允许
→ derived_independent_task=true／false
```

`derived_independent_task`只用于验证显式新SHOT。一个SHOT内的推、拉、摇、移、跟、升降、环绕、景别自然变化或移动后锁定使用`motion_phase_task`，不得因为阶段变化自动新增SHOT。

## 场景世界机位合同

涉及人物移动、空间边界、视线揭示、关系镜头、主体切换或对话反打的SHOT必须引用04B：

```text
scene_id
time_id
camera_region_id
camera_station_id
camera_position_world
camera_forward_world
camera_height
primary_scene_anchor_id
visible_anchor_ids
```

`camera_region_id`只是合法区域；`camera_station_id`才是本SHOT的具体摄影点。位于同一轴线侧或同一合法区域，不等于使用同一个摄影点。

每个SHOT必须提供完整观察签名：

```yaml
observation_signature:
  camera_station_id:
  camera_region_id:
  camera_position_world: [x, y, z]
  camera_forward_world: [x, y, z]
  camera_height:
  shot_scale:
  primary_subject_id:
  foreground_subject_id:
  background_anchor_id:
  viewpoint_type:
  motion_mode:
  psychological_distance:
```

相同景别可以连续使用。判断变化的对象不是“中景／近景”名称，而是摄影点、世界朝向、前景关系、背景透视、主次主体、摄影机高度、运动方式和心理距离构成的观察签名。

## SHOT任务合同

```yaml
shot_id:
task_type:
scene_id:
time_id:
primary_subject_id:
viewpoint: objective | POV | OTS | INSERT | subjective
camera:
  region_id:
  station_id:
  position_world: [x, y, z]
  forward_world: [x, y, z]
  height:
  shot_scale:
  foreground_subject_id:
  background_anchor_id:
  motion_mode:
  psychological_distance:
  primary_scene_anchor_id:
  visible_anchor_ids: []
viewpoint_fitness:
  task_requires_new_observation: true | false
  selected_station_serves_task: true | false
  observation_signature_changed: true | false
  foreground_relation_changed: true | false
  psychological_distance_changed: true | false
  same_station_repetition_intent:
required_evidence: []
visible_evidence: []
action: {}
```

验证器输出：

```text
derived_independent_task
viewpoint_evidence_passed
viewpoint_fitness_passed
missing_evidence
observation_signature
```

模型、用户或下游提示词不得直接指定`derived_independent_task=true`。task_contract必须与实际SHOT的摄影机、场景、主体和状态一致。

## 视角适配Gate

所有显式新SHOT必须填写`viewpoint_fitness`。

硬要求：

1. `selected_station_serves_task=true`：当前摄影点确实能清楚展示任务证据。
2. 当`task_requires_new_observation=true`时，以下至少一项必须成立：
   - `observation_signature_changed=true`；
   - `foreground_relation_changed=true`；
   - `psychological_distance_changed=true`；
   - 提供明确的`same_station_repetition_intent`，说明为何刻意重复同一摄影点。
3. 仅更换主要说话人、主体名称或前景肩部标签，不能自动证明观察关系已经改变。
4. 当前SHOT可与上一SHOT同为中景，但应来自不同摄影点或形成不同前景、背景透视、主次关系或心理距离。
5. 同一摄影点的重复若用于审讯、僵持、监控、时间流逝或形式化重复，必须写明重复意图；是否在整场中过量，由`validate_camera_coverage_sequence.py`检查。

失败错误码：

```text
selected_station_does_not_serve_task
new_observation_not_demonstrated
mechanical_dialogue_view_repetition
```

## 连续运镜阶段任务合同

同一SHOT有多个轨迹阶段时记录：

```yaml
phase_id:
shot_id:
phase_task:
start_state:
movement:
end_state:
required_evidence: []
visible_evidence: []
lock_after_move:
```

要求：

1. 阶段必要证据可见。
2. `start_state → movement → end_state`连续，没有摄影机瞬移、人物重置或场景突变。
3. 没有显式CUT时保持同一`shot_id`。
4. 景别和焦段感随连续轨迹变化不产生新SHOT。
5. 到达后锁定时不继续漂移。

阶段覆盖通过只说明同一SHOT内部完整，不等于形成独立新SHOT。

## 通用任务证据Gate

所有任务必须满足：

1. `required_evidence`全部存在于`visible_evidence`。
2. 主要场景锚点真实进入画面。
3. 当前景别、遮挡、焦点和光线能够展示证据。
4. 动作结果没有在上一SHOT已经完成。
5. 人物位置、道具归属和动作状态符合04继承状态。
6. 任务证据是画面事实，不只是情绪名称、台词意义或导演解释。
7. 当前`camera_station_id`与15选择、04B空间解一致。

## ENTER／EXIT进出场Gate

完整ENTER：

```text
outside → crossing boundary → inside
```

完整EXIT：

```text
inside → crossing boundary → outside
```

必须锁定：actor_id、start_zone_id、boundary_id、end_zone_id、movement_world、state_before、state_after、state_path，并证明`crossing_visible=true`、`path_visible=true`和`movement_crosses_boundary=true`。

起点与终点必须位于边界两侧；边界锚点必须可见且成为主要场景锚点。摄影机不能遮挡路线。已经inside不得重复完整ENTER，已经outside不得重复EXIT。合同状态必须与实际SHOT的start_state／end_state一致。

## EYELINE_REVEAL视线揭示Gate

必须证明：

```text
previous_eyeline_locked=true
target_id明确
target_visible=true
target_direction_matches=true
target_key_state_visible=true
```

后镜不能只出现目标人物的任意画面，必须展示前镜正在确认的关键对象及关键状态。

## REACTION反应Gate

必须有明确`reaction_cause_id`，并证明`reaction_visible=true`和`reaction_not_completed_before=true`。普通呼吸、眨眼或无剧情作用的微表情不能单独成镜。

## CONTACT接触Gate

必须写清执行者、目标、接触点、力量或传递方向和结果状态，并证明接触与结果都可见。抓、推、踢、递交不能让模型猜接触位置。

## PROP_ACTION与MOVEMENT Gate

必须证明：

```text
action_visible=true
result_visible=true
repeats_completed_action=false
```

拿取、放置、点燃、折断、开门、下床、跌倒等动作必须展示过程和结果，不得在后镜重新从起点表演。

## DIALOGUE对白任务Gate

换说话人不自动形成独立SHOT。必须说明`dialogue_focus_reason`，证明`focus_subject_visible=true`、`new_visual_task_visible=true`和`mechanical_speaker_switch=false`。

此外，必须满足以下一项：

- 观察签名、前景关系或心理距离真实改变；
- 明确声明同机位重复的戏剧意图。

可成立的情况包括关键回答、威胁、谎言被识破、听者反应更重要、权力位置改变或对话转行动。只把画面中央人物替换为另一说话人，而摄影机XYZ、高度、背景透视和前景关系近似不变，判为`mechanical_dialogue_view_repetition`。

## ESTABLISH空间建立Gate

必须证明`spatial_relationship_visible=true`和`new_anchor_relationship_visible=true`，真实建立新空间锚点关系。所选摄影点必须能同时读出需要建立的锚点关系。

## 视角标签证据

### POV

必须提供source_character_id，并证明摄影机原点匹配人物和目标可见。

### OTS

必须看到前景人物肩部，明确聚焦主体，并证明轴线合法。仅在字段中写OTS而没有真实肩部前景不能通过。

### INSERT

必须明确insert_subject_id并证明细节主体可见。

### subjective

必须明确主观来源并证明主观几何成立。

只改viewpoint字符串不能通过。

## 状态机与重复动作

标准状态示例：

```text
区域：outside／crossing／inside
身体：standing／falling／seated
门：closed／opening／open
道具：unheld／taking／held／placing／placed
```

禁止：

- inside后再次完整ENTER。
- seated后无过程再次跌坐。
- held后再次从原处拿取。
- 前镜已发现目标，后镜重新寻找。
- MATCH-ON-ACTION后镜动作进度回退。

## 与15和13的单向关系

- 15A先完成整场摄影覆盖设计，15B再设计每个SHOT及CUT意图。
- 04B求解摄影点与轨迹空间。
- 14只回答：15设计的这个SHOT是否真的拍到了任务，而且所选摄影点是否适配任务。
- 14通过后，13审核15已经设计的CUT。
- 14不因任务失败自行新增或移动CUT；失败时返回15重做。

## 输出示例

```json
{
  "ok": true,
  "shot_id": "SHOT_B",
  "task_type": "EYELINE_REVEAL",
  "derived_independent_task": true,
  "viewpoint_evidence_passed": true,
  "viewpoint_fitness_passed": true,
  "missing_evidence": [],
  "observation_signature": {}
}
```

运行：

```bash
python3 scripts/validate_shot_task.py shot-task.json
```

## 自检

- [ ] SHOT来自15统一导演方案。
- [ ] 04B空间解已经通过。
- [ ] 当前SHOT方案锁的scope仅为shot。
- [ ] camera_station_id与15、04B一致。
- [ ] 任务必要证据真实可见。
- [ ] selected_station_serves_task=true有画面依据。
- [ ] 对话换说话人没有被误当成视角变化。
- [ ] 相同中景若连续使用，观察签名具有导演意义的变化。
- [ ] 动作状态没有回退或重复。
- [ ] 任务失败返回15，不在本文件私自改机位或CUT。
