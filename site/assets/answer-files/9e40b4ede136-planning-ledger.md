# SRDF 规划台账 — six_axis_arm

> 本台账在编写 SRDF XML 前填写，依据 `references/planning-ledger.md` 模板。
> 资源受限说明：无真实机器人 URDF、无 MoveIt 环境、无采样碰撞分析、无 cad-viewer。
> 凡无法验证项均标注【待确认】。

## URDF 依赖

| 字段 | 值 |
|---|---|
| URDF 路径 | work/six_axis_arm.urdf |
| SRDF 输出路径 | work/six_axis_arm.srdf |
| 机器人名 | six_axis_arm |
| URDF 是否已校验 | 是；Python ElementTree 解析通过，拓扑单根 base_link，11 链接 / 10 关节 |
| 根链接 | base_link |
| 活动关节 | shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint（6 旋转）；left_finger_joint, right_finger_joint（2 平动） |
| 固定关节 | tool0_joint（wrist_3_link→tool0），gripper_base_joint（tool0→gripper_base_link） |
| 从动(mimic)关节 | 无 |
| 被动(passive)关节 | 无 |
| 用于碰撞检测的链接 | 全部 11 个链接均含 collision 几何（简化占位圆柱/盒） |
| 已知 URDF 局限 | 几何/惯量/限位为合成占位值【待确认】；未经过 URDF Skill 或真实机器人标定 |

## 规划任务

| 字段 | 值 |
|---|---|
| 主任务 | arm IK / plan-to-pose（六轴臂位姿规划）+ gripper（夹爪开合） |
| 主规划组 | manipulator |
| 预期末端执行器/TCP | gripper_eef；TCP 链接 tool0（法兰面）【待确认：真实 TCP 可能在夹爪指尖或工具尖端】 |
| 所需求解器/规划器 | 未指定；MoveIt 默认 OMPL/KDL【待确认】 |
| 仅位置 IK？ | 否；六轴臂具备完整 6DOF 位姿能力，默认带姿态约束 |
| 姿态约束？ | 是；四元数表示（xyz, quat_xyzw） |

## 虚拟关节

| 名称 | 类型 | 父坐标系 | 子链接 | 是否需要 | 理由 |
|---|---|---|---|---|---|
| fixed_base | fixed | world | base_link | 是 | 固定基座机械臂，规划需要 world→基座的固定挂载 |

## 被动关节

无。所有非固定关节均为主动驱动。

## 规划组

| 组 | 表示 | 成员 | base 链接 | tip 链接 | 活动关节 | 排除关节 | 用途 | 求解器预期 |
|---|---|---|---|---|---|---|---|---|
| manipulator | chain | base_link→tool0 | base_link | tool0 | 6 个旋转关节 | 固定关节 tool0_joint | 六轴臂 IK/位姿规划 | 6DOF 链式 IK |
| gripper | link + joints | link:gripper_base_link；joints:left_finger_joint,right_finger_joint | — | — | 2 个平动关节 | — | 夹爪开合 | 平动关节插值 |

链 base→tip 已在 URDF 图中验证存在真实路径：base_link→shoulder→upper_arm→forearm→wrist_1→wrist_2→wrist_3→tool0。

## 末端执行器

| 名称 | EE 组 | 父组 | 父链接 | 目标/TCP 链接 | 重叠已检查？ | 相邻？ | 备注 |
|---|---|---|---|---|---|---|---|
| gripper_eef | gripper | manipulator | tool0 | tool0 | 是；gripper 组链接 {gripper_base_link,left_finger_link,right_finger_link} 与 manipulator 组链接无交集 | 是；tool0 经固定关节连到 gripper_base_link | TCP=tool0 为默认法兰面【待确认】 |

## 组状态

| 状态 | 组 | 关节值 | 单位检查 | 限位检查 | 用途 |
|---|---|---|---|---|---|
| home | manipulator | 6 个旋转关节均 0.0 | 弧度（rad） | 0.0 在各关节限位内 | 零位/初始姿态 |
| open | gripper | left/right_finger_joint=0.0 | 米（m） | 0.0 在 [0,0.04] 内 | 夹爪全开 |
| closed | gripper | left/right_finger_joint=0.04 | 米（m） | 0.04 等于上限 | 夹爪闭合 |

## 禁碰矩阵

仅采用邻接策略（adjacency），来源为 URDF 运动图中直接由关节连接的链接对。无采样/Setup Assistant 数据，不臆造非邻接对。

| 链接1 | 链接2 | 原因 | 来源 | 证据 | 风险说明 |
|---|---|---|---|---|---|
| base_link | shoulder_link | Adjacent | adjacency | shoulder_pan_joint 直接连接 | 邻接链接不可能自碰 |
| shoulder_link | upper_arm_link | Adjacent | adjacency | shoulder_lift_joint | 同上 |
| upper_arm_link | forearm_link | Adjacent | adjacency | elbow_joint | 同上 |
| forearm_link | wrist_1_link | Adjacent | adjacency | wrist_1_joint | 同上 |
| wrist_1_link | wrist_2_link | Adjacent | adjacency | wrist_2_joint | 同上 |
| wrist_2_link | wrist_3_link | Adjacent | adjacency | wrist_3_joint | 同上 |
| wrist_3_link | tool0 | Adjacent | adjacency | tool0_joint(fixed) | 同上 |
| tool0 | gripper_base_link | Adjacent | adjacency | gripper_base_joint(fixed) | 同上 |
| gripper_base_link | left_finger_link | Adjacent | adjacency | left_finger_joint | 同上 |
| gripper_base_link | right_finger_link | Adjacent | adjacency | right_finger_joint | 同上 |

未禁用：left_finger_link↔right_finger_link（非邻接，闭合时可能相碰，保留碰撞检测）；跨连杆非邻接对（无采样证据，保留检测）。

## MoveIt 冒烟测试

| 测试 | 组 | 目标链接 | 目标位姿/状态 | 预期 | 实际 | 备注 |
|---|---|---|---|---|---|---|
| IK 求解 | manipulator | tool0 | — | 可解 | 跳过【待确认】 | 无 MoveIt 环境 |
| plan-to-pose | manipulator | tool0 | — | 成功 | 跳过【待确认】 | 无 MoveIt 环境 |
| 命名状态 | manipulator/gripper | — | home/open/closed | 可达 | 生成期校验通过（组成员/单位/限位） | 真实可达性未验证 |
| 碰撞检测 | all | — | — | 安全 | 跳过【待确认】 | 无采样自碰分析 |

## 需报告的假设

- 规划组成员：基于 URDF 拓扑推导，chain base_link→tool0。
- 链 base/tip：base_link 为根，tool0 为法兰末端。
- 目标/TCP 链接：默认 tool0；真实 TCP 待确认。
- 虚拟关节挂载：fixed world→base_link。
- 被动关节分类：无被动关节。
- 组状态值：home 全零；open/closed 取限位端点。
- 禁碰对：仅邻接对，无采样数据。
- 求解器/规划器设置：未指定，使用 MoveIt 默认【待确认】。
- 仅位置 IK 假设：否，默认带姿态。
- 跳过的 MoveIt 验证：IK、规划、自碰采样、控制器配置均未执行。
