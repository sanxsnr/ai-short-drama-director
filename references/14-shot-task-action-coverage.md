# SHOT任务与动作覆盖规则

## 唯一职责

本文件是以下内容的唯一规则真源：

- 下一SHOT是否真正具有独立导演任务。
- 镜头任务是否由画面证据完成，而不是由模型自行声明。
- 摄影机在统一场景世界坐标中的区域、朝向、主要场景锚点和可见锚点。
- ENTER、EXIT、EYELINE_REVEAL、REACTION、CONTACT、PROP_ACTION、MOVEMENT、DIALOGUE、ESTABLISH等动作的覆盖Gate。
- 人物或道具动作状态机，以及是否重复已经完成的动作。
- 构图类型、主体名称或视角标签是否有真实几何和画面证据。

本文件不负责定义人物正面、移动向量、轴线和摄影机可见面；这些由`04-blocking-continuity.md`定义。本文件不负责决定CUT类型、30度适用性和相邻SHOT视觉差异；这些由`13-cut-shot-geometry.md`定义。

任何CUT候选必须先通过`04`空间几何，再通过本文件的任务与动作覆盖Gate，最后才能交给`13`。

## 核心原则

> 写了“镜头任务”不等于完成了镜头任务。只有当前构图真正展示了任务所要求的主体、空间锚点、动作过程和结果，下一SHOT才具有独立任务。

禁止使用以下自我证明：

```text
independent_task: true
主体改变了，所以镜头成立
viewpoint写成OTS，所以已经形成过肩
space文字不同，所以已经换了场景
```

必须由结构化证据推导：

```text
任务类型
→ 必要画面证据
→ 当前机位能否看到
→ 动作起点、经过节点与终点是否连续
→ 状态机是否允许
→ derived_independent_task=true／false
```

模型、用户或下游提示词不得直接指定`derived_independent_task=true`。task_contract也不得描述与实际SHOT不同的摄影机、场景锚点、主体、视角或状态；`13`必须交叉核对。

## 场景世界机位合同

每个涉及人物移动、空间边界、视线揭示、关系镜头或主体切换的SHOT，必须引用`04`并填写：

```text
scene_id：标准场景ID
zone_id：摄影机所在功能区ID
camera_position_world：摄影机世界坐标
camera_forward_world：摄影机在场景中的真实朝向
primary_scene_anchor_id：本镜主要空间锚点
visible_anchor_ids：画面真实可见的固定锚点
```

自然语言标签只用于显示，不用于判断是否换场：

```text
scene_id: torture_room
scene_label: 破旧刑房
zone_id: east_door_inside
zone_label: 东侧门槛内
```

禁止通过“刑房”与“刑房内”、“夜”与“夜晚”等文字差异伪造场景或时间变化。

## 场景观察签名

每个SHOT生成以下签名：

```text
摄影机区域
摄影机世界朝向
主要场景锚点
可见固定锚点集合
```

该签名用于判断相邻SHOT是否仍然从近似区域、近似方向观察同一空间关系。

场景观察签名近似本身不是绝对错误。例如合法EYELINE CUT可能沿相同方向切到目标。它是风险信号，必须继续检查本文件的任务证据；不能仅因主体名称改变就自动通过。

## SHOT任务合同

每个非终点SHOT至少填写：

```text
shot_id：
task_type：
scene_id：
time_id：
primary_subject_id：
viewpoint：objective／POV／OTS／INSERT／subjective
camera：
  zone_id：
  position_world：
  forward_world：
  primary_scene_anchor_id：
  visible_anchor_ids：
required_evidence：
visible_evidence：
action：
```

验证器输出：

```text
derived_independent_task：true／false
viewpoint_evidence_passed：true／false
missing_evidence：[]
observation_signature：{}
```

只有`derived_independent_task=true`，`13`才允许继续判断CUT。

## 通用任务证据Gate

所有任务必须满足：

1. `required_evidence`中的每项都存在于`visible_evidence`。
2. 主要场景锚点必须真实进入`visible_anchor_ids`。
3. 当前景别、遮挡、焦点和光线能够展示所声明证据。
4. 动作结果没有在上一SHOT已经完成。
5. 人物位置、道具归属和动作状态符合`04`继承状态。
6. 任务证据必须是画面事实，不能只写情绪名称、台词意义或导演解释。

## ENTER／EXIT进出场Gate

完整进场必须形成：

```text
outside → crossing boundary → inside
```

完整离场必须形成：

```text
inside → crossing boundary → outside
```

必须同时锁定：

- actor_id；
- start_zone_id；
- boundary_id；
- end_zone_id；
- movement_world；
- state_before；
- state_after；
- state_path：指向SHOT start_state／end_state中的标准状态路径；
- crossing_visible=true；
- path_visible=true；
- movement_crosses_boundary=true。

硬要求：

- 起点与终点必须位于边界两侧。
- 边界锚点必须进入画面。
- `primary_scene_anchor_id`必须是该门框、门槛、窗、屏风口或其他边界，而不能只写进入的人物。
- 景别与构图必须能展示起点、跨越方向和进入后的落点；不要求固定使用某一种景别。
- 摄影机不得位于会遮挡或阻断进场路线的位置。
- 人物已经处于inside状态时，不得再次执行完整ENTER；已经outside时不得重复EXIT。
- task_contract中的state_before／state_after必须与实际SHOT的start_state／end_state一致，不能让合同描述一个不存在的理想状态。

错误示例：

```text
任务写“苏清月从门外进入刑房”
但画面只有苏清月侧面中景
门框、门槛和跨越过程全部不可见
```

该镜头即使主体改变、角度达到30度，也必须判定任务覆盖失败。

## EYELINE_REVEAL视线揭示Gate

必须证明：

- previous_eyeline_locked=true；
- target_id明确；
- target_visible=true；
- target_direction_matches=true；
- target_key_state_visible=true。

后镜不能只出现目标人物的任意画面，必须展示前镜正在寻找或确认的关键对象及其关键状态。

若目标正在跨越门槛、拿取道具或完成其他关键动作，应继续调用对应动作Gate，不能只以“视线目标已出现”代替动作覆盖。

## REACTION反应Gate

必须证明：

- reaction_cause_id明确；
- reaction_visible=true；
- reaction_not_completed_before=true。

普通眨眼、呼吸或已经在上一SHOT完成的惊讶不能重复切镜。

## CONTACT接触Gate

必须明确：

- actor_id；
- target_id；
- contact_point；
- force_or_transfer_direction；
- result_state；
- contact_visible=true；
- result_visible=true。

不能只写“发生接触”，却看不到执行者、接触部位、方向和结果。

## PROP_ACTION／MOVEMENT动作Gate

必须证明：

- action_visible=true；
- result_visible=true；
- repeats_completed_action=false。

拿取、放下、开门、关门、转身、跌倒、坐下、站起等动作必须继承上一SHOT的真实进度。已完成动作不得重新从起点表演。

## DIALOGUE对白任务Gate

说话人改变不自动形成独立镜头。必须证明：

- dialogue_focus_reason明确；
- focus_subject_visible=true；
- new_visual_task_visible=true；
- mechanical_speaker_switch=false。

合法理由可以是关键回答、谎言被识破、听者反应、权力关系变化或由对白转入行动。禁止“谁说话就切谁”。

## ESTABLISH空间建立Gate

必须证明：

- spatial_relationship_visible=true；
- new_anchor_relationship_visible=true。

仅换成更广景别但没有建立新的空间、人物或锚点关系，不构成独立建立镜头。

## 视角标签证据

### POV

必须提供：

- source_character_id；
- camera_origin_matches_character=true；
- target_visible=true。

### OTS

必须提供：

- foreground_character_id；
- foreground_shoulder_visible=true；
- focus_subject_id；
- axis_valid=true。

### INSERT

必须提供：

- insert_subject_id；
- insert_subject_visible=true。

只改变`viewpoint`字符串，不提供以上证据，不能视为真正的视角变化。

## 状态机与重复动作

状态必须使用标准ID，不只写自然语言：

```text
人物区域：outside／crossing／inside
头部：lowered／raising／raised
身体：standing／falling／seated
门：closed／opening／open
道具：unheld／taking／held／placing／placed
```

只有合法转换才能通过。例如：

```text
outside → crossing → inside
lowered → raising → raised
standing → falling → seated
```

禁止：

```text
inside → ENTER → inside
raised → 再次抬头
held → 再次从原处拿取
seated → 无过程重新跌坐
```

## 主体改变的正确判断

主体改变只表示“可能需要新镜头”，不能自动证明视觉差异或任务成立。

正确流程：

```text
主体改变
→ 本文件验证新主体的关键状态／动作是否可见
→ 验证场景锚点和动作覆盖
→ derived_independent_task=true
→ 交给13判断相邻SHOT视觉差异
```

没有任务覆盖证据时，主体改变不能挽救错误机位。

## 与04和13的固定顺序

```text
01：拆剧情、动作链、对白和时长
→ 04：锁场景世界坐标、人物朝向、摄影机允许区和状态继承
→ 14：验证SHOT任务、动作覆盖、视角证据和状态机
→ 13：决定CUT类型、30度适用性和相邻SHOT视觉差异
→ 01：封装SEG
```

任一上游失败，不能进入下一层。

## 输出格式

```text
## SHOT任务覆盖｜SHOT XX
- task_type：
- primary_subject_id：
- scene_id／time_id：
- camera_zone_id：
- camera_forward_world：
- primary_scene_anchor_id：
- visible_anchor_ids：
- required_evidence：
- visible_evidence：
- 动作状态转换：
- 视角证据：
- derived_independent_task：通过／失败
- 失败原因：
```

## 本文件自检

- [ ] 未直接相信`independent_task=true`。
- [ ] 使用标准scene_id、time_id、zone_id和anchor_id。
- [ ] 摄影机世界坐标、朝向和场景锚点明确。
- [ ] 任务要求的全部画面证据真实可见。
- [ ] ENTER／EXIT显示边界、路径与跨越结果。
- [ ] POV／OTS／INSERT有真实几何证据。
- [ ] 人物和道具状态机转换合法，没有重复动作。
- [ ] 主体改变没有被自动当作强通过。
- [ ] 只有本文件通过后才交给13。
