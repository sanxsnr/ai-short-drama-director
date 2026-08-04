# 灵感、小说改编、剧本与视听切片

## 唯一职责

本文件只负责：

- 灵感发展、小说改编和短剧结构。
- 可拍摄剧本、动作链、对白和OS／画外音。
- 台词与动作读秒。
- 10秒／15秒SEG规格选择。
- SEG、SHOT、CUT与连续运镜的边界定义。
- AI直接成片SEG的内容类型、SHOT数量上限与高速动作例外。
- 将已经通过导演方案、空间求解、SHOT任务覆盖与CUT审核的SHOT封装成SEG。

本文件不负责：

- 场景基础空间模型、人物／摄影机XYZ轨迹、朝向、轴线、状态继承、场景世界机位或信息可见性；这些只由`04-blocking-continuity.md`定义。
- 场景怎么拍、每个SHOT内摄影机怎么走、在哪里CUT；这些只由`15-directorial-camera-plan.md`统一设计。
- SHOT任务证据、动作覆盖、进出场Gate、视角证据和动作状态机；这些只由`14-shot-task-action-coverage.md`定义。
- CUT类型的导演意图与连接方式由`15-directorial-camera-plan.md`提出；CUT是否真正成立、30度适用性、同轴景别路径和相邻SHOT视觉差异只由`13-cut-shot-geometry.md`审核。

涉及完整分镜、段内SHOT、故事板格序或机位变化时，必须先确认`02／03`的视觉与场景布局资产已经锁定，再按`04A → 15 → 04B → 14 → 13`读取。本文件不得改写或覆盖它们。

## 创作授权模式

先判断用户授权范围：

- **忠实整理**：保留原剧情和对白，只整理格式、逻辑和时长。
- **完善模式**：保留核心剧情，允许补足动机、动作、对白和转折。
- **改编模式**：重组为短剧结构，可合并事件、调整顺序和设计钩子。
- **原创模式**：从灵感建立完整故事。

用户明确“按原文”“台词不改”或指定最终版时，不得擅自改变核心人物、主线结果、锁定动作或对白。

## 从灵感到故事

整理为：

1. 类型与目标观众。
2. 一句话梗概。
3. 主角目标、阻力和代价。
4. 独特卖点与开场视觉钩子。
5. 情绪曲线与结尾体验。
6. 适合片段、单集或连续剧的体量。

先确保“谁想做什么、谁阻止、为什么现在行动”清楚，再扩展世界观。

## 小说改编

提取并锁定：

- 主线与必要支线。
- 人物关系、秘密和利益冲突。
- 世界规则、时代、地域与不可改变事实。
- 可视觉化的动作、场景和道具。
- 需要从内心叙述转为画面、行为、对白或OS的信息。

再建立每集的核心事件、开场钩子、升级、转折、结尾悬念与新增资产。

## 可拍摄剧本格式

```text
第X集

场景X  内／外  场景名  时间
出场人物：
剧情目的：

△ 可见、可表演、可生成的动作。
角色A（语气／状态）：“完整对白。”
△ 对方直接反应或动作结果。
```

每场至少改变一项：事件、关系、信息、目标或人物状态。动作写可见事实，不用抽象情绪替代画面。

## 动作链

正式分镜前先拆成：

```text
起始状态 → 动作发生 → 动作结果 → 反应／新信息 → 下一动作阶段
```

动作链只描述剧情和表演进度，不在本文件决定机位、运镜或CUT；完整拍法由`15-directorial-camera-plan.md`设计。

必须标明：

- 谁执行动作。
- 动作目标。
- 动作开始、发展和结果。
- 谁看到、听到或受到影响。
- 下一阶段因何成立。

若动作依赖具体站位、接触点、遮挡或方向，交由`04-blocking-continuity.md`锁定。

## 对白、OS与读秒

每句对白至少承担一项功能：推进事件、暴露关系、提供必要信息、制造冲突／笑点／威胁或形成行动节奏。

- 正常中文语速约每秒4—5字。
- 对话主导的10秒SEG，20—35字通常较舒适；超过40字属于高密度。
- 对话主导的15秒SEG，30—52字通常较舒适；超过约60字应压缩、延长或跨SHOT持续。
- 停顿、喘息、抢话、转身、移动和复杂动作单独占时。
- 对白过长时先删除重复信息，不靠异常加速解决。

必须区分：

- **对白**：同场人物真实可听见。
- **OS**：人物内心声音，同场人物不能因OS产生反应，除非剧情明确存在特殊机制。
- **画外音**：来自画外或其他时空，需写明声源与作用。

## SEG规格选择

正式拆完整剧本前确认：

```text
A（推荐）：使用 $ai-short-drama-director，选择A：按10秒SEG制作。
B：使用 $ai-short-drama-director，选择B：按15秒SEG制作。
C：使用 $ai-short-drama-director，选择C：先输出同一片段的10秒／15秒对照样例。
```

用户已明确“每段10秒”“每镜10秒”或“按15秒切”时，直接继承，不重复询问。

记录：

```text
分镜切片规格：10秒版／15秒版
当前SEG类型：normal／high_speed_action／fixed_camera_time_passage
SHOT计数来源：仅显式SHOT边界
```

定义：

- `SEG`：一次交给视频模型直接生成的固定时长编号单元，通常为10秒或15秒；SEG可以包含一个连续SHOT，也可以包含多个由显式CUT连接的SHOT。
- `SHOT`：两次CUT之间持续生成的连续观察。摄影机推近、后退、横移、跟拍、摇摄、升降、环绕，人物靠近／远离摄影机，景别自然改变，以及摄影机移动后锁定，都可以发生在同一SHOT内。
- `CUT`：画面从一个连续观察切换到另一个连续观察。硬切、动作切、视线切、同侧反打、主观切以及完成遮挡后的真实镜头切换都属于CUT。
- `运镜`：同一SHOT内摄影机位置、朝向或运动状态的连续变化。运镜本身不增加SHOT或CUT数量。

本文件只负责SEG；15先设计统一SHOT序列、摄影机轨迹和CUT意图，04把方案求解为空间事实，14验证任务覆盖，13审核CUT几何。

不得根据编号时长、景别变化、焦段数值或运镜阶段自动推导SHOT边界。只有显式CUT或显式SHOT边界才增加数量。

| 规格 | 常用范围 | 绝对上限 |
|---|---:|---:|
| 10秒版 | 8—12秒 | 13秒 |
| 15秒版 | 13—17秒 | 18秒 |

大场景变化、时间跳跃、完整动作保护或最后尾段可以短于目标时长，不为凑满塞入无关剧情。

## AI直接成片SEG数量规则｜SEG_SHOT_COUNT_POLICY_V1

本节是文档中唯一维护SEG数量上限的规则真源；其他文件只能引用，不得抄写另一套数值。

### segment_content_type=normal｜普通剧情

适用于普通对话、反应、起身、转身、进门、拿取道具等常规表演：

```text
shot_count <= 2
cut_count <= 1
```

- 默认使用一个连续SHOT。
- 只有两个确实独立的画面任务都通过`14`，且CUT通过`13`时，才使用两个SHOT和一次CUT。
- 超出上限输出错误码`too_many_shots_for_normal_segment`。
- 可以通过合法运镜完成的自然景别变化，优先保留在同一SHOT内；“优先”不等于强制，两个任务明显不同时CUT仍然合法。

### segment_content_type=high_speed_action｜高速动作例外

适用于打斗、追逐、高速奔跑、快速逃脱、连续闪避、灾难冲击和其他高速动作链。允许超过普通剧情的SHOT数量，但必须同时满足：

1. 每个短SHOT推进不同动作阶段，并具有不同`action_signature`。
2. 每次CUT落在刀锋、拳脚、身体运动、烟雾、遮挡或可见方向变化节点。
3. 动作速度、进度与人物屏幕方向连续。
4. 人物换位在画面中真实发生。
5. 保持同一轴线侧；若改变轴线，必须在画面中重新建立空间。
6. 相邻SHOT不得同时使用近似景别、近似角度和近似构图。
7. 不重复同一攻防动作。
8. 多SHOT确实提高动作节奏，而不是只为了展示更多景别。

高速动作例外不得扩展到普通对话、普通进门或普通道具动作。

### segment_content_type=fixed_camera_time_passage｜固定机位时间流逝

标记`FIXED_CAMERA_TIME_PASSAGE`。适用于日夜交替、多日流逝、人物逐渐衰弱、光线与环境状态变化，以及固定构图内的时间压缩。

```text
shot_count = 1
cut_count = 0
```

允许摄影机从开始即固定；也允许前段连续移动到目标构图后锁定。后续日夜、灯光与人物状态可以依次变化，但必须证明：

```text
camera_locked_after_move=true
scene_geometry_unchanged=true
character_screen_positions_stable=true
time_transition_visible=true
```

可见的时间变化不是CUT、换机位或多SHOT蒙太奇。若确实切换连续观察，则不再属于本类型。

## 完整分镜生产顺序

```text
1. 本文件：灵感／小说 → 改编方案 → 可拍摄剧本 → 对白、动作链、视听节拍与SEG规格
2. 02／03：锁定视觉风格、人物／服装／道具资产和场景布局资产；已有锁定版时直接继承
3. 04A：根据锁定场景资产建立基础空间模型，只锁尺寸、锚点、可通行区、人物初始区和不可穿越物
4. 15：导演思维一次性决定怎么拍、每个SHOT内摄影机怎么走、在哪里停、在哪里CUT
5. 04B：把15的方案求解为人物与摄影机XYZ、世界朝向和连续关键帧轨迹
6. 若04B不可执行：返回15重做方案，再交04B求解；不把选择推给用户
7. 14：验证每个SHOT和轨迹阶段的导演任务、动作覆盖、场景锚点与状态机
8. 13：审核每个已设计CUT的切点、类型、动作连续、轴线与相邻SHOT视觉差异
9. 本文件：把全部通过的SHOT封装成SEG并读秒
10. 下游模块：生成故事板与视频提示词
```

统一原则：固定机位、连续运镜和CUT不分别计算。15先形成一份按时间排列的导演镜头方案；04B再对每个SHOT的连续摄影机状态`C(t)`求解。`C(t)`不变时自然得到固定机位，连续变化时自然得到运镜；两个连续SHOT区间之间自然形成CUT。

禁止先凑满10秒或15秒，再临时编镜头；也禁止先让用户选择“固定／运镜／CUT”，再反向拼装方案。

## SEG封装规则

先按本文件确定`segment_content_type`，再把已经通过`15`导演方案、`04`空间求解、`14`任务覆盖与`13`CUT审核且未违反本节数量规则的SHOT装进同一SEG。必须完整保留：

- 每个SHOT编号和起止时间。
- 每个CUT点和CUT类型。
- 每个SHOT的空间／状态引用。
- 前一SHOT结束状态和下一SHOT起始状态。
- 台词、OS、画外音、环境声和音效的时间位置。

模型负载过高时，把SHOT拆入更多SEG；不得删除、合并或重写已通过审核的CUT。

“每个编号段为10秒”只锁定SEG时长，不自动锁定SHOT数量。用户若另行明确要求单SHOT长镜头，才把单SHOT作为创作约束；该约束不得由“10秒一段”等表述自行推导。

## SEG结构字段

结构化SEG至少记录：

```yaml
segment_id:
duration_seconds: 10
segment_content_type: normal | high_speed_action | fixed_camera_time_passage
shots:
  - shot_id:
    shot_task:
    camera_zone:
    camera_direction:
    shot_size:
    camera_motion:
    cut_in:
    cut_out:
    focal_feel:
    action_stage:
shot_count:
cut_count:
directorial_camera_plan_ref:
spatial_solution_ref:
camera_motion_phases:
  - start_state:
    movement:
    end_state:
    lock_after_move:
time_passage:
  enabled:
  method:
  camera_locked: # camera_locked_after_move的兼容别名
  geometry_unchanged: # scene_geometry_unchanged的兼容别名
  camera_locked_after_move:
  scene_geometry_unchanged:
  character_screen_positions_stable:
  time_transition_visible:
```

`focal_feel`只保存广角空间感、标准透视、轻长焦压缩感或浅景深特写感等辅助视觉提示，不参与CUT、越轴、人物换位、动作可见性或SHOT数量硬判定。

`shots`中的以下字段名必须原样存在，不能只用其他模块字段替代：

- `shot_task`：当前SHOT的导演目标；`task_type`是14的任务分类，二者可以并存但不能互相省略。
- `camera_zone`：可与04的`camera_zone_id`取相同值，但结构字段仍须保留。
- `camera_direction`：可直接复制04的`camera_forward_world`，不能只提供后者。
- `action_stage`：当前SHOT在动作链中的阶段；`phase_task`只描述运镜阶段任务，不能代替。
- `shot_size`、`camera_motion`、`cut_in`、`cut_out`与`focal_feel`同样必须显式填写；无内部CUT时使用`null`，不得省略字段。

输出“验证通过”前必须把实际结构原样输入`scripts/validate_segment_structure.py`，不能只凭人工判断宣称通过。

## SEG时间轴格式

```markdown
### EPXX｜SEGXXX｜10秒版／15秒版

#### 基础信息
- 剧情功能：
- 场景：
- segment_content_type：normal／high_speed_action／fixed_camera_time_passage
- shot_count／cut_count：
- 导演镜头方案引用：15中的plan_id
- 空间状态引用：04中的scene_space_basis／spatial_solution编号
- CUT审核引用：13中的SHOT／CUT编号

#### 资产与状态
- 人物、服装、道具：
- 上一SEG结束状态：
- 本SEG起始状态：
- 本SEG结束状态：
- 下一SEG继承：

#### 时间轴
| 时间码 | SHOT | 画面与动作 | CUT点／类型 | 表演／台词／声音 | 空间／状态引用 |
|---|---:|---|---|---|---|

#### 自检
- 剧情与授权：
- 时长与对白容量：
- SHOT／CUT是否完整保留：
- 导演镜头方案是否已通过15：
- 空间与连续性是否已通过04：
- 结论：已通过／需返工／被阻塞
```

完整SHOT任务合同以`14-shot-task-action-coverage.md`为准，CUT检查格式以`13-cut-shot-geometry.md`为准；空间表和跨镜状态格式以`04-blocking-continuity.md`为准，不在本文件重复定义。

## 本文件自检

### 剧情与授权

- 主线、动机、因果和情绪递进成立。
- 原动作和对白按用户授权范围保留。
- OS、画外音和实际对白区分正确。

### 读秒

- 台词、停顿和动作在目标时长内可实现。
- 没有为凑时长塞入无关动作。
- 没有靠异常语速解决过载。

### SEG封装

- SEG与SHOT没有混淆。
- SEG类型与显式SHOT／CUT计数已经通过`scripts/validate_segment_structure.py`。
- 运镜、景别与焦段提示没有被误计为SHOT边界。
- 所有已审核CUT均被完整保留。
- 每个SHOT的时间码连续且无重叠冲突。
- 每个SEG明确是否为终点。
- `fixed_camera_time_passage`保持场景几何和屏幕位置稳定，摄影机前段移动后已经锁定。

怎么拍、怎么运、怎么切不在本文件自判，必须引用`15`；空间、轴线、状态继承和信息可见性必须引用`04`；SHOT任务与动作覆盖必须引用`14`；CUT合法性必须引用`13`。
