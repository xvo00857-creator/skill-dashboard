# 桌面机械臂 URDF 设计台账

> 建模对象：大象机器人（Elephant Robotics）myCobot 280 系列六轴桌面协作机械臂
> 台账日期：2026-08-12
> 单位约定：米（m）、千克（kg）、秒（s）、弧度（rad），右手坐标系

---

## 1. 机器人元数据

| 项目 | 值 | 来源 |
|---|---|---|
| 机器人名称 | mycobot280 | 产品系列名 |
| 自由度 | 6 | 官方产品参数页 |
| 工作半径 | 280 mm | 官方产品参数页 |
| 自重 | 860 g（Pi/Jetson 版本约 860 g，M5 版本约 850 g） | 官方产品参数页 |
| 有效负载 | 250 g | 官方产品参数页 |
| 重复定位精度 | ±0.5 mm | 官方产品参数页 |
| 目标使用者 | RViz 可视化、robot_state_publisher TF 树、Gazebo 仿真（惯性参数为近似值） | 本任务设定 |
| 坐标系约定 | REP-103 机体约定：X 前、Y 左、Z 上；基座底面为 base_link 原点 | 本任务设定 |
| 网格单位约定 | 不使用外部网格；visual/collision 全部使用 URDF 基本几何体（box/cylinder） | 本任务设定（因无官方 DAE/STL 文件） |
| 尺寸来源 | 大象机器人官方文档 DH 参数图、尺寸图、GitHub 开源 URDF | 见下方引用 |

### 公开来源

- **S1** 官方产品参数页（关节范围、自重、工作半径）：
  https://docs.elephantrobotics.com/docs/mycobot_280RDK-X5-cn/1-ProductInformation/2.ProductParameter/2-ProductParameters.html
- **S2** 官方开源 URDF（mycobot_280_x3pi.urdf，humble 分支）：
  https://github.com/elephantrobotics/mycobot_ros2/blob/humble/mycobot_description/urdf/mycobot_280_x3pi/mycobot_280_x3pi.urdf
- **S3** 官方产品参数页（myCobot 280 Pi，自重 860 g）：
  https://docs.elephantrobotics.com/docs/mycobot_280_pi_cn/1-ProductInformation/2.ProductParameter/2-ProductParameters.html

---

## 2. 事实、假设与建议的区分

### 事实（有公开来源）

1. 六轴串联结构，6 个旋转关节。
2. 关节运动范围（官方文档 S1，单位度）：
   - J1: −168° ~ +168°
   - J2: −135° ~ +135°
   - J3: −150° ~ +150°
   - J4: −145° ~ +145°
   - J5: −165° ~ +165°
   - J6: −180° ~ +180°
3. DH 参数图（S1）标注的运动学尺寸（毫米）：
   - d1 = 131.56, a2 = 110.4, a3 = 96, d4 = 64.62, d5 = 73.18, d6 = 48.6
4. 官方开源 URDF（S2）中的关节原点（米）：
   - J1 原点: z = 0.13956
   - J2 原点: z = −0.001, rpy = (0, π/2, −π/2)
   - J3 原点: x = −0.1104
   - J4 原点: x = −0.096, z = 0.06462, rpy = (0, 0, −π/2)
   - J5 原点: y = −0.07318, rpy = (π/2, −π/2, 0)
   - J6 原点: y = 0.0456, rpy = (−π/2, 0, 0)
5. 官方尺寸图（S1）标注的分段高度（毫米）：基座 134.75、大臂段 110、小臂段 96、腕部 75.05；宽度 63.4、厚度 45.6。
6. 整机自重约 860 g（S3）。

### 假设（无公开精确数据，已命名常量标注）

1. **A1**：visual/collision 使用基本几何体（圆柱体、长方体）近似官方外壳，因为官方 DAE 网格文件未随本任务提供，且验证器会检查本地网格文件是否存在。几何体尺寸根据官方尺寸图目视估算，非 CAD 精确值。
2. **A2**：各连杆质量分配为估算值。整机 0.860 kg 按各段体积/元器件经验比例分配（基座含主控较重），非 CAD 质量属性。
3. **A3**：各连杆质心取近似几何体的几何中心，假设材料均匀分布。实际舵机、电路板偏置会导致质心偏移。
4. **A4**：惯性张量由近似几何体和均匀密度公式计算，非 CAD 实测值。
5. **A5**：关节 effort 限制取 1.0 N·m（桌面小型舵机经验值），velocity 取 1.0 rad/s，均为占位假设；官方开源 URDF 中 effort=1000、velocity=0 为占位值，不具备物理意义。
6. **A6**：tool0 法兰工具坐标系与 flange_link 原点重合（零偏移），因为未安装末端执行器。
7. **A7**：J6 按官方文档 ±180° 建模为 revolute（极限 ±π），而非 continuous，以与官方文档的有限范围一致。

### 建议（供后续完善）

1. 从官方 myCobot ROS2 仓库获取 DAE 网格文件，替换基本几何体以获得精确可视化。
2. 使用 CAD 软件或实测获取各连杆精确质量、质心和惯性张量。
3. 根据实际舵机型号（myCobot 使用 hm-06 系列舵机）设置真实 effort/velocity 限制。
4. 安装夹爪后更新 tool0 偏移和夹爪连杆。
5. 在 RViz/Gazebo 中进行消费者冒烟测试。

---

## 3. 连杆台账

| 连杆名 | 角色 | 坐标系定义 | 父关节 | visual 几何 | collision 几何 | inertial 来源 |
|---|---|---|---|---|---|---|
| base_link | 物理连杆（基座） | 原点在基座底面中心，Z 向上 | 无（根） | 圆柱 r=0.055 h=0.135 | 同 visual | 估算（A2/A3/A4） |
| shoulder_link | 物理连杆（肩部壳体） | 原点在 J1/J2 轴线交点 | joint1 | 长方体 0.04×0.04×0.07 | 同 visual | 估算 |
| upper_arm_link | 物理连杆（大臂） | 原点在 J2 轴线，沿 −X 延伸至 J3 | joint2 | 长方体 0.11×0.035×0.035 | 同 visual | 估算 |
| forearm_link | 物理连杆（小臂） | 原点在 J3 轴线 | joint3 | 长方体 0.096×0.035×0.035 | 同 visual | 估算 |
| wrist_pitch_link | 物理连杆（腕部俯仰壳体） | 原点在 J4 轴线 | joint4 | 长方体 0.064×0.04×0.05 | 同 visual | 估算 |
| wrist_roll_link | 物理连杆（腕部翻滚壳体） | 原点在 J5 轴线 | joint5 | 圆柱 r=0.025 h=0.073 | 同 visual | 估算 |
| flange_link | 物理连杆（法兰盘） | 原点在 J6 轴线 | joint6 | 圆柱 r=0.03 h=0.012 | 同 visual | 估算 |
| tool0 | 纯坐标系（TCP 标记） | 与 flange_link 原点重合 | tool_joint (fixed) | 无 | 无 | 无（frame-only） |

---

## 4. 关节台账

| 关节名 | 类型 | 父连杆 | 子连杆 | origin xyz (m) | origin rpy (rad) | axis | 下限 | 上限 | 正向运动含义 | 来源 |
|---|---|---|---|---|---|---|---|---|---|---|
| joint1 | revolute | base_link | shoulder_link | 0 0 0.13956 | 0 0 0 | 0 0 1 | −2.9321 | +2.9321 | 从上方看逆时针旋转肩部 | S2 原点；S1 范围 ±168° |
| joint2 | revolute | shoulder_link | upper_arm_link | 0 0 −0.001 | 0 π/2 −π/2 | 0 0 1 | −2.3562 | +2.3562 | 大臂前后摆动 | S2 原点；S1 范围 ±135° |
| joint3 | revolute | upper_arm_link | forearm_link | −0.1104 0 0 | 0 0 0 | 0 0 1 | −2.6180 | +2.6180 | 小臂屈伸 | S2 原点；S1 范围 ±150° |
| joint4 | revolute | forearm_link | wrist_pitch_link | −0.096 0 0.06462 | 0 0 −π/2 | 0 0 1 | −2.5307 | +2.5307 | 腕部俯仰 | S2 原点；S1 范围 ±145° |
| joint5 | revolute | wrist_pitch_link | wrist_roll_link | 0 −0.07318 0 | π/2 −π/2 0 | 0 0 1 | −2.8798 | +2.8798 | 腕部翻滚 | S2 原点；S1 范围 ±165° |
| joint6 | revolute | wrist_roll_link | flange_link | 0 0.0456 0 | −π/2 0 0 | 0 0 1 | −π | +π | 法兰旋转 | S2 原点；S1 范围 ±180° |
| tool_joint | fixed | flange_link | tool0 | 0 0 0 | 0 0 0 | — | — | — | 固定工具坐标 | A6 |

注：S2 开源 URDF 中 J2 极限为 ±2.4434 rad（≈±140°）、J4 为 ±2.6179（≈±150°）、J5 为 −2.7052~2.7925，与 S1 官方文档关节范围表存在差异。本模型采用 S1 官方文档的关节范围表作为产品规格依据，差异已记录。

---

## 5. 几何台账

| 连杆 | 类别 | 类型 | 尺寸 (m) | origin xyz (m) | origin rpy | 说明 |
|---|---|---|---|---|---|---|
| base_link | visual/collision | cylinder | r=0.055, h=0.135 | 0 0 0.0675 | 0 0 0 | 基座近似圆柱（A1）；尺寸图基座高 134.75mm、宽约 63.4mm |
| shoulder_link | visual/collision | box | 0.04×0.04×0.07 | 0 0 −0.03 | 0 0 0 | 肩部壳体近似（A1） |
| upper_arm_link | visual/collision | box | 0.11×0.035×0.035 | −0.055 0 0 | 0 0 0 | 大臂段，长度 110mm（S1 尺寸图） |
| forearm_link | visual/collision | box | 0.096×0.035×0.035 | −0.048 0 0 | 0 0 0 | 小臂段，长度 96mm（S1 尺寸图） |
| wrist_pitch_link | visual/collision | box | 0.064×0.04×0.05 | 0 0 0 | 0 0 0 | 腕部壳体，d4=64.62mm（S1 DH 图） |
| wrist_roll_link | visual/collision | cylinder | r=0.025, h=0.073 | 0 −0.0366 0 | 0 0 π/2 | 腕部翻滚段，d5=73.18mm（S1 DH 图） |
| flange_link | visual/collision | cylinder | r=0.03, h=0.012 | 0 0 −0.006 | 0 0 0 | 法兰盘，参考 S2 中 joint7 网格偏移 −0.012 |

---

## 6. 惯性台账

所有惯性参数为**估算值**（A2/A3/A4），计算口径：

- 质量分配：整机 0.860 kg（S3），按各段体积/元器件经验比例分配
- 质心：取近似几何体几何中心
- 惯性张量：按标准刚体公式计算
  - 实心圆柱（中心轴沿 Z）：Ixx = Iyy = m(3r²+h²)/12, Izz = mr²/2
  - 实心长方体：Ixx = m(y²+z²)/12, Iyy = m(x²+z²)/12, Izz = m(x²+y²)/12
- 交叉惯性积（ixy, ixz, iyz）取 0（对称性假设）

| 连杆 | 质量 (kg) | 质心 xyz (m，连杆坐标系) | 惯性张量来源 | 置信度 |
|---|---|---|---|---|
| base_link | 0.350 | 0 0 0.0675 | 圆柱公式 | 占位/估算 |
| shoulder_link | 0.100 | 0 0 −0.03 | 长方体公式 | 占位/估算 |
| upper_arm_link | 0.120 | −0.055 0 0 | 长方体公式 | 占位/估算 |
| forearm_link | 0.100 | −0.048 0 0 | 长方体公式 | 占位/估算 |
| wrist_pitch_link | 0.080 | 0 0 0 | 长方体公式 | 占位/估算 |
| wrist_roll_link | 0.070 | 0 −0.0366 0 | 圆柱公式（轴沿 Y） | 占位/估算 |
| flange_link | 0.040 | 0 0 −0.006 | 圆柱公式 | 占位/估算 |
| tool0 | — | — | 无（frame-only） | 不适用 |

质量合计：0.350+0.100+0.120+0.100+0.080+0.070+0.040 = 0.860 kg（与 S3 一致）

---

## 7. 假设台账

| 编号 | 假设内容 | 影响 | 替换方式 |
|---|---|---|---|
| A1 | 基本几何体近似外壳 | 可视化精度 | 获取官方 DAE/STL 网格 |
| A2 | 质量按经验比例分配 | 动力学精度 | CAD 质量属性或实测 |
| A3 | 质心在几何中心 | 动力学精度 | CAD 质心或实测 |
| A4 | 惯性张量由均匀几何体公式计算 | 动力学精度 | CAD 惯性属性或实测 |
| A5 | effort=1.0 N·m, velocity=1.0 rad/s | 仿真限制 | 舵机规格书 |
| A6 | tool0 与法兰重合 | 无工具时正确 | 安装夹爪后更新 |
| A7 | J6 用 revolute ±π | 与文档一致 | 如需连续旋转改为 continuous |
