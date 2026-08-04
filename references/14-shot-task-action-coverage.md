# SHOT任务与动作覆盖规则

## 唯一职责

本文件是以下内容的唯一规则真源：

- 验证`15-directorial-camera-plan.md`设计的这个SHOT是否真的拍到了任务。
- 从画面证据推导下一SHOT是否具有独立导演任务。
- 验证同一SHOT的连续摄影机轨迹阶段是否完成阶段任务，且没有被误报为独立SHOT。
- 验证ENTER、EXIT、EYELINE_REVEAL、REACTION、CONTACT、PROP_ACTION、MOVEMENT、DIALOGUE、ESTABLISH等任务。
- 验证人物／道具动作状态机，防止重复进入、重复跌倒、重复拿取或动作重置。
- 验证POV、OTS、INSERT和subjective标签具有真实画面证据。

本文件读取`04-blocking-continuity.md`的XYZ空间解和场景观察签名，也读取15的SHOT任务和摄影机轨迹意图。本文件不重新设计怎么拍、怎么运或怎么切；这些只由15决定。本文件不计算人物正面、关系轴或摄影机允许区；这些只由04决定。本文件不审核CUT类型、30度和相邻视觉差异；这些只由`13-cut-shot-geometry.md`完成。

任何CUT必须先通过04空间求解，再通过本文件任务覆盖，最后交给13审核。

## 核心原则

> 写了“镜头任务”不等于完成镜头任务。只有当前构图真正展示了任务要求的主体、空间锚点、动作过程和结果，下一SHOT才成立。

禁止自我证明：

```text
independent_task: true
主体改变了，所以镜头成立
viewpoint写成OTS，所以已经形成过肩
自然语言场景名称不同，所以已经换场
```

必须推导：

```text
任务类型
→ 必要画面证据
→ 04B机位和XYZ轨迹能否看见
→ 动作起点、经过节点与终点是否连续
→ 状态机是否允许
→ derived_independent_task=true／false
```

`derived_independent_task`只用于验证显式新SHOT。一个SHOT内的推、拉、摇、移、跟、升降、环绕、景别自然变化或移动后锁定使用`motion_phase_task`，不得因为阶段变化自动新增SHOT。

## 场景世界机位合同

涉及人物移动、空间边界、视线揭示、关系镜头或主体切换的SHOT必须引用04B：

```text
scene_id
time_id
zone_id
camera_position_world
camera_forward_world
primary_scene_anchor_id
visible_anchor_ids
```

这些字段形成场景观察签名：摄影机区域、世界朝向、主要锚点和可见锚点集合。近似签名是风险信号，不是自动错误；继续检查任务证据。

## SHOT任务合同

```yaml
shot_id:
task_type:
scene_id:
time_id:
primary_subject_id:
viewpoint: objective | POV | OTS | INSERT | subjective
camera:
  zone_id:
  position_world:
  forward_world:
  primary_scene_anchor_id:
  visible_anchor_ids: []
required_evidence: []
visible_evidence: []
action: {}
```

验证器输出：

```text
derived_independent_task
viewpoint_evidence_passed
missing_evidence
observation_signature
```

模型、用户或下游提示词不得直接指定`derived_independent_task=true`。task_contract必须与实际SHOT的摄影机、场景、主体和状态一致。

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

可成立的情况包括关键回答、威胁、谎言被识破、听者反应更重要或对话转行动。

## ESTABLISH空间建立Gate

必须证明`spatial_relationship_visible=true`和`new_anchor_relationship_visible=true`，真实建立新空间锚点关系。

## 视角标签证据

### POV

必须提供source_character_id，并证明摄影机原点匹配人物和目标可见。

### OTS

必须看到前景人物肩部，明确聚焦主体，并证明轴线合法。

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

- 15先设计SHOT及CUT意图。
- 04B求解空间。
- 14只回答：15设计的这个SHOT是否真的拍到了任务。
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
- [ ] required_evidence全部真实可见。
- [ ] 任务合同与实际机位、场景、主体和状态一致。
- [ ] ENTER／EXIT边界、路径和落点可见。
- [ ] POV／OTS／INSERT具有真实证据。
- [ ] 动作状态机没有重复或重置。
- [ ] 连续轨迹阶段没有被误报为新SHOT。
- [ ] derived_independent_task由验证器推导，不是自报。
- [ ] 通过后才交给13审核CUT。
