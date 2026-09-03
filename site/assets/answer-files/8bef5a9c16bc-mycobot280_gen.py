"""
myCobot 280 桌面六轴机械臂 URDF 生成器
======================================

本文件是 URDF 的唯一事实来源（source of truth）。
生成的 .urdf 文件为构建产物，不应手动编辑。

运动学参数来源：
  S1 = 大象机器人官方文档 myCobot 280 产品参数页（关节范围、DH 参数图、尺寸图）
       https://docs.elephantrobotics.com/docs/mycobot_280RDK-X5-cn/1-ProductInformation/2.ProductParameter/2-ProductParameters.html
  S2 = 官方开源 URDF（mycobot_ros2 humble 分支 mycobot_280_x3pi.urdf）
       https://github.com/elephantrobotics/mycobot_ros2/blob/humble/mycobot_description/urdf/mycobot_280_x3pi/mycobot_280_x3pi.urdf
  S3 = 官方产品参数页（自重 860 g）
       https://docs.elephantrobotics.com/docs/mycobot_280_pi_cn/1-ProductInformation/2.ProductParameter/2-ProductParameters.html

所有标记为 ASSUMED 的值为假设值，详见同目录 design_ledger.md。
"""

import math
import xml.etree.ElementTree as ET

# ============================================================================
# 常量：运动学参数（来源 S2 开源 URDF 关节原点；S1 关节范围）
# ============================================================================

# --- 关节原点（米/弧度），来源 S2 ---
J1_ORIGIN_XYZ = (0.0, 0.0, 0.13956)          # 基座底面到 J1/J2 轴线交点
J1_ORIGIN_RPY = (0.0, 0.0, 0.0)

J2_ORIGIN_XYZ = (0.0, 0.0, -0.001)           # 肩部微小偏置
J2_ORIGIN_RPY = (0.0, math.pi / 2, -math.pi / 2)

J3_ORIGIN_XYZ = (-0.1104, 0.0, 0.0)          # 大臂长度 a2=110.4mm (S1 DH 图)
J3_ORIGIN_RPY = (0.0, 0.0, 0.0)

J4_ORIGIN_XYZ = (-0.096, 0.0, 0.06462)       # 小臂 a3=96mm + d4=64.62mm (S1)
J4_ORIGIN_RPY = (0.0, 0.0, -math.pi / 2)

J5_ORIGIN_XYZ = (0.0, -0.07318, 0.0)         # d5=73.18mm (S1 DH 图)
J5_ORIGIN_RPY = (math.pi / 2, -math.pi / 2, 0.0)

J6_ORIGIN_XYZ = (0.0, 0.0456, 0.0)           # 法兰偏置 45.6mm (S2)
J6_ORIGIN_RPY = (-math.pi / 2, 0.0, 0.0)

TOOL_ORIGIN_XYZ = (0.0, 0.0, 0.0)            # ASSUMED A6: tool0 与法兰重合
TOOL_ORIGIN_RPY = (0.0, 0.0, 0.0)

# --- 关节轴（关节坐标系内），来源 S2 ---
JOINT_AXIS_Z = (0.0, 0.0, 1.0)

# --- 关节范围（弧度），来源 S1 官方关节范围表（度→弧度换算）---
J1_LIMITS = (-math.radians(168), math.radians(168))   # ±168°
J2_LIMITS = (-math.radians(135), math.radians(135))   # ±135°
J3_LIMITS = (-math.radians(150), math.radians(150))   # ±150°
J4_LIMITS = (-math.radians(145), math.radians(145))   # ±145°
J5_LIMITS = (-math.radians(165), math.radians(165))   # ±165°
J6_LIMITS = (-math.pi, math.pi)                       # ±180°

# --- 关节力矩/速度限制（ASSUMED A5：桌面小型舵机占位值）---
JOINT_EFFORT = 1.0    # N·m，占位假设
JOINT_VELOCITY = 1.0  # rad/s，占位假设

# ============================================================================
# 常量：几何参数（基本几何体近似，ASSUMED A1）
# 尺寸参考 S1 官方尺寸图：基座高 134.75mm、宽 63.4mm；大臂 110mm；小臂 96mm；
# 腕部 75.05mm；厚 45.6mm
# ============================================================================

# 基座：圆柱，直径约 110mm（近似），高 135mm
BASE_RADIUS = 0.055
BASE_HEIGHT = 0.135
BASE_VISUAL_XYZ = (0.0, 0.0, BASE_HEIGHT / 2)

# 肩部壳体：长方体
SHOULDER_BOX = (0.04, 0.04, 0.07)
SHOULDER_VISUAL_XYZ = (0.0, 0.0, -0.03)

# 大臂：长方体，长 110mm 沿 −X
UPPER_ARM_BOX = (0.11, 0.035, 0.035)
UPPER_ARM_VISUAL_XYZ = (-0.055, 0.0, 0.0)

# 小臂：长方体，长 96mm 沿 −X
FOREARM_BOX = (0.096, 0.035, 0.035)
FOREARM_VISUAL_XYZ = (-0.048, 0.0, 0.032)

# 腕部俯仰壳体：长方体
WRIST_PITCH_BOX = (0.064, 0.04, 0.05)
WRIST_PITCH_VISUAL_XYZ = (0.0, 0.0, -0.025)

# 腕部翻滚段：圆柱沿 Y 轴，长 73mm
WRIST_ROLL_RADIUS = 0.025
WRIST_ROLL_HEIGHT = 0.073
WRIST_ROLL_VISUAL_XYZ = (0.0, -0.0366, 0.0)
WRIST_ROLL_VISUAL_RPY = (math.pi / 2, 0.0, 0.0)  # 圆柱轴 Z→Y

# 法兰盘：圆柱
FLANGE_RADIUS = 0.03
FLANGE_HEIGHT = 0.012
FLANGE_VISUAL_XYZ = (0.0, 0.0, -0.006)

# ============================================================================
# 常量：质量参数（ASSUMED A2/A3/A4）
# 总质量 0.860 kg 来源 S3；各段质量按体积/元器件经验比例分配
# ============================================================================

TOTAL_MASS_KG = 0.860  # S3

BASE_MASS = 0.350
SHOULDER_MASS = 0.100
UPPER_ARM_MASS = 0.120
FOREARM_MASS = 0.100
WRIST_PITCH_MASS = 0.080
WRIST_ROLL_MASS = 0.070
FLANGE_MASS = 0.040
# 合计 = 0.860 kg

# ============================================================================
# 辅助函数
# ============================================================================


def _xyz_str(xyz):
    return f"{xyz[0]:.6f} {xyz[1]:.6f} {xyz[2]:.6f}"


def _rpy_str(rpy):
    return f"{rpy[0]:.6f} {rpy[1]:.6f} {rpy[2]:.6f}"


def _inertia_box(mass, sx, sy, sz):
    """实心长方体惯性张量（质心在几何中心，对称轴对齐坐标轴）。"""
    ixx = mass * (sy**2 + sz**2) / 12.0
    iyy = mass * (sx**2 + sz**2) / 12.0
    izz = mass * (sx**2 + sy**2) / 12.0
    return ixx, iyy, izz


def _inertia_cylinder_z(mass, radius, height):
    """实心圆柱惯性张量，圆柱轴沿 Z。"""
    ixx = mass * (3.0 * radius**2 + height**2) / 12.0
    iyy = ixx
    izz = mass * radius**2 / 2.0
    return ixx, iyy, izz


def _inertia_cylinder_y(mass, radius, height):
    """实心圆柱惯性张量，圆柱轴沿 Y（用于腕部翻滚段）。"""
    # 轴沿 Y: Iyy = mr²/2, Ixx = Izz = m(3r²+h²)/12
    ixx = mass * (3.0 * radius**2 + height**2) / 12.0
    iyy = mass * radius**2 / 2.0
    izz = ixx
    return ixx, iyy, izz


def _add_origin(parent, xyz, rpy=(0.0, 0.0, 0.0)):
    return ET.SubElement(parent, "origin", {"xyz": _xyz_str(xyz), "rpy": _rpy_str(rpy)})


def _add_box(parent, size):
    geometry = ET.SubElement(parent, "geometry")
    ET.SubElement(geometry, "box", {"size": _xyz_str(size)})


def _add_cylinder(parent, radius, length):
    geometry = ET.SubElement(parent, "geometry")
    ET.SubElement(geometry, "cylinder", {"radius": f"{radius:.6f}", "length": f"{length:.6f}"})


def _add_material(parent, name, rgba):
    material = ET.SubElement(parent, "material", {"name": name})
    ET.SubElement(material, "color", {"rgba": rgba})


def _make_visual_collision(link, vis_xyz, vis_rpy, geom_fn, material_name, material_rgba):
    visual = ET.SubElement(link, "visual")
    _add_origin(visual, vis_xyz, vis_rpy)
    geom_fn(visual)
    _add_material(visual, material_name, material_rgba)

    collision = ET.SubElement(link, "collision")
    _add_origin(collision, vis_xyz, vis_rpy)
    geom_fn(collision)


def _add_inertial(link, mass, com_xyz, ixx, iyy, izz, ixy=0.0, ixz=0.0, iyz=0.0):
    inertial = ET.SubElement(link, "inertial")
    _add_origin(inertial, com_xyz)
    ET.SubElement(inertial, "mass", {"value": f"{mass:.6f}"})
    ET.SubElement(
        inertial,
        "inertia",
        {
            "ixx": f"{ixx:.9f}",
            "ixy": f"{ixy:.9f}",
            "ixz": f"{ixz:.9f}",
            "iyy": f"{iyy:.9f}",
            "iyz": f"{iyz:.9f}",
            "izz": f"{izz:.9f}",
        },
    )


def _add_revolute_joint(robot, name, parent, child, xyz, rpy, axis, limits):
    joint = ET.SubElement(robot, "joint", {"name": name, "type": "revolute"})
    _add_origin(joint, xyz, rpy)
    ET.SubElement(joint, "parent", {"link": parent})
    ET.SubElement(joint, "child", {"link": child})
    ET.SubElement(joint, "axis", {"xyz": _xyz_str(axis)})
    ET.SubElement(
        joint,
        "limit",
        {
            "lower": f"{limits[0]:.6f}",
            "upper": f"{limits[1]:.6f}",
            "effort": f"{JOINT_EFFORT}",
            "velocity": f"{JOINT_VELOCITY}",
        },
    )
    return joint


def _add_fixed_joint(robot, name, parent, child, xyz, rpy):
    joint = ET.SubElement(robot, "joint", {"name": name, "type": "fixed"})
    _add_origin(joint, xyz, rpy)
    ET.SubElement(joint, "parent", {"link": parent})
    ET.SubElement(joint, "child", {"link": child})
    return joint


# ============================================================================
# 主生成函数
# ============================================================================


def gen_urdf():
    robot = ET.Element("robot", {"name": "mycobot280"})

    # ------------------------------------------------------------------
    # 连杆
    # ------------------------------------------------------------------

    # base_link —— 基座
    base_link = ET.SubElement(robot, "link", {"name": "base_link"})
    _make_visual_collision(
        base_link,
        BASE_VISUAL_XYZ,
        (0, 0, 0),
        lambda p: _add_cylinder(p, BASE_RADIUS, BASE_HEIGHT),
        "base_grey",
        "0.4 0.4 0.4 1.0",
    )
    ixx, iyy, izz = _inertia_cylinder_z(BASE_MASS, BASE_RADIUS, BASE_HEIGHT)
    _add_inertial(base_link, BASE_MASS, BASE_VISUAL_XYZ, ixx, iyy, izz)

    # shoulder_link —— 肩部壳体
    shoulder_link = ET.SubElement(robot, "link", {"name": "shoulder_link"})
    _make_visual_collision(
        shoulder_link,
        SHOULDER_VISUAL_XYZ,
        (0, 0, 0),
        lambda p: _add_box(p, SHOULDER_BOX),
        "arm_white",
        "0.9 0.9 0.9 1.0",
    )
    ixx, iyy, izz = _inertia_box(SHOULDER_MASS, *SHOULDER_BOX)
    _add_inertial(shoulder_link, SHOULDER_MASS, SHOULDER_VISUAL_XYZ, ixx, iyy, izz)

    # upper_arm_link —— 大臂
    upper_arm_link = ET.SubElement(robot, "link", {"name": "upper_arm_link"})
    _make_visual_collision(
        upper_arm_link,
        UPPER_ARM_VISUAL_XYZ,
        (0, 0, 0),
        lambda p: _add_box(p, UPPER_ARM_BOX),
        "arm_white",
        "0.9 0.9 0.9 1.0",
    )
    ixx, iyy, izz = _inertia_box(UPPER_ARM_MASS, *UPPER_ARM_BOX)
    _add_inertial(upper_arm_link, UPPER_ARM_MASS, UPPER_ARM_VISUAL_XYZ, ixx, iyy, izz)

    # forearm_link —— 小臂
    forearm_link = ET.SubElement(robot, "link", {"name": "forearm_link"})
    _make_visual_collision(
        forearm_link,
        FOREARM_VISUAL_XYZ,
        (0, 0, 0),
        lambda p: _add_box(p, FOREARM_BOX),
        "arm_white",
        "0.9 0.9 0.9 1.0",
    )
    ixx, iyy, izz = _inertia_box(FOREARM_MASS, *FOREARM_BOX)
    _add_inertial(forearm_link, FOREARM_MASS, FOREARM_VISUAL_XYZ, ixx, iyy, izz)

    # wrist_pitch_link —— 腕部俯仰壳体
    wrist_pitch_link = ET.SubElement(robot, "link", {"name": "wrist_pitch_link"})
    _make_visual_collision(
        wrist_pitch_link,
        WRIST_PITCH_VISUAL_XYZ,
        (0, 0, 0),
        lambda p: _add_box(p, WRIST_PITCH_BOX),
        "arm_white",
        "0.9 0.9 0.9 1.0",
    )
    ixx, iyy, izz = _inertia_box(WRIST_PITCH_MASS, *WRIST_PITCH_BOX)
    _add_inertial(wrist_pitch_link, WRIST_PITCH_MASS, WRIST_PITCH_VISUAL_XYZ, ixx, iyy, izz)

    # wrist_roll_link —— 腕部翻滚段（圆柱沿 Y）
    wrist_roll_link = ET.SubElement(robot, "link", {"name": "wrist_roll_link"})
    _make_visual_collision(
        wrist_roll_link,
        WRIST_ROLL_VISUAL_XYZ,
        WRIST_ROLL_VISUAL_RPY,
        lambda p: _add_cylinder(p, WRIST_ROLL_RADIUS, WRIST_ROLL_HEIGHT),
        "arm_white",
        "0.9 0.9 0.9 1.0",
    )
    ixx, iyy, izz = _inertia_cylinder_y(WRIST_ROLL_MASS, WRIST_ROLL_RADIUS, WRIST_ROLL_HEIGHT)
    _add_inertial(wrist_roll_link, WRIST_ROLL_MASS, WRIST_ROLL_VISUAL_XYZ, ixx, iyy, izz)

    # flange_link —— 法兰盘
    flange_link = ET.SubElement(robot, "link", {"name": "flange_link"})
    _make_visual_collision(
        flange_link,
        FLANGE_VISUAL_XYZ,
        (0, 0, 0),
        lambda p: _add_cylinder(p, FLANGE_RADIUS, FLANGE_HEIGHT),
        "flange_orange",
        "1.0 0.5 0.1 1.0",
    )
    ixx, iyy, izz = _inertia_cylinder_z(FLANGE_MASS, FLANGE_RADIUS, FLANGE_HEIGHT)
    _add_inertial(flange_link, FLANGE_MASS, FLANGE_VISUAL_XYZ, ixx, iyy, izz)

    # tool0 —— 纯坐标系（frame-only，无 inertial/visual/collision）
    ET.SubElement(robot, "link", {"name": "tool0"})

    # ------------------------------------------------------------------
    # 关节
    # ------------------------------------------------------------------

    _add_revolute_joint(
        robot, "joint1", "base_link", "shoulder_link",
        J1_ORIGIN_XYZ, J1_ORIGIN_RPY, JOINT_AXIS_Z, J1_LIMITS,
    )
    _add_revolute_joint(
        robot, "joint2", "shoulder_link", "upper_arm_link",
        J2_ORIGIN_XYZ, J2_ORIGIN_RPY, JOINT_AXIS_Z, J2_LIMITS,
    )
    _add_revolute_joint(
        robot, "joint3", "upper_arm_link", "forearm_link",
        J3_ORIGIN_XYZ, J3_ORIGIN_RPY, JOINT_AXIS_Z, J3_LIMITS,
    )
    _add_revolute_joint(
        robot, "joint4", "forearm_link", "wrist_pitch_link",
        J4_ORIGIN_XYZ, J4_ORIGIN_RPY, JOINT_AXIS_Z, J4_LIMITS,
    )
    _add_revolute_joint(
        robot, "joint5", "wrist_pitch_link", "wrist_roll_link",
        J5_ORIGIN_XYZ, J5_ORIGIN_RPY, JOINT_AXIS_Z, J5_LIMITS,
    )
    _add_revolute_joint(
        robot, "joint6", "wrist_roll_link", "flange_link",
        J6_ORIGIN_XYZ, J6_ORIGIN_RPY, JOINT_AXIS_Z, J6_LIMITS,
    )
    _add_fixed_joint(
        robot, "tool_joint", "flange_link", "tool0",
        TOOL_ORIGIN_XYZ, TOOL_ORIGIN_RPY,
    )

    return robot


if __name__ == "__main__":
    # 允许直接运行此文件进行快速检查
    ET.indent(gen_urdf(), space="  ")
    print(ET.tostring(gen_urdf(), encoding="unicode"))
