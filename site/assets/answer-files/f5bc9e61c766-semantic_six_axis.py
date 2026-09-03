"""gen_srdf() source for the six_axis_arm synthesized fixture.

生成器契约（references/generator-contract.md）：
- 顶层零参数 gen_srdf()；
- 返回 {"xml": <robot Element 或 XML 字符串>, "urdf": "相对路径.urdf"}；
- urdf 路径相对于本源文件，POSIX 分隔符，相对路径，.urdf 结尾，文件存在。

本文件为合成六轴机械臂的 SRDF 语义源，所有运动学拓扑派生自 six_axis_arm.urdf。
"""
import xml.etree.ElementTree as ET


def gen_srdf():
    robot = ET.Element("robot", {"name": "six_axis_arm"})

    # 虚拟关节：固定基座 -> world
    ET.SubElement(
        robot,
        "virtual_joint",
        {
            "name": "fixed_base",
            "type": "fixed",
            "parent_frame": "world",
            "child_link": "base_link",
        },
    )

    # 规划组 1：六轴臂（链式，base_link -> tool0）
    arm = ET.SubElement(robot, "group", {"name": "manipulator"})
    ET.SubElement(
        arm,
        "chain",
        {"base_link": "base_link", "tip_link": "tool0"},
    )

    # 规划组 2：二指夹爪（显式 link + 两个平动关节）
    gripper = ET.SubElement(robot, "group", {"name": "gripper"})
    ET.SubElement(gripper, "link", {"name": "gripper_base_link"})
    ET.SubElement(gripper, "joint", {"name": "left_finger_joint"})
    ET.SubElement(gripper, "joint", {"name": "right_finger_joint"})

    # 末端执行器：gripper 组挂在 manipulator 组的 tool0 上
    ET.SubElement(
        robot,
        "end_effector",
        {
            "name": "gripper_eef",
            "parent_link": "tool0",
            "group": "gripper",
            "parent_group": "manipulator",
        },
    )

    # 组状态：home（弧度，旋转关节零位）
    home = ET.SubElement(
        robot, "group_state", {"name": "home", "group": "manipulator"}
    )
    for jn in (
        "shoulder_pan_joint",
        "shoulder_lift_joint",
        "elbow_joint",
        "wrist_1_joint",
        "wrist_2_joint",
        "wrist_3_joint",
    ):
        ET.SubElement(home, "joint", {"name": jn, "value": "0.0"})

    # 组状态：open（米，平动关节零位 = 全开）
    opened = ET.SubElement(
        robot, "group_state", {"name": "open", "group": "gripper"}
    )
    ET.SubElement(opened, "joint", {"name": "left_finger_joint", "value": "0.0"})
    ET.SubElement(opened, "joint", {"name": "right_finger_joint", "value": "0.0"})

    # 组状态：closed（米，0.04 = 上限 = 闭合）
    closed = ET.SubElement(
        robot, "group_state", {"name": "closed", "group": "gripper"}
    )
    ET.SubElement(closed, "joint", {"name": "left_finger_joint", "value": "0.04"})
    ET.SubElement(closed, "joint", {"name": "right_finger_joint", "value": "0.04"})

    # 禁碰矩阵：仅 URDF 运动图中直接由关节连接的邻接对
    adjacent_pairs = [
        ("base_link", "shoulder_link"),
        ("shoulder_link", "upper_arm_link"),
        ("upper_arm_link", "forearm_link"),
        ("forearm_link", "wrist_1_link"),
        ("wrist_1_link", "wrist_2_link"),
        ("wrist_2_link", "wrist_3_link"),
        ("wrist_3_link", "tool0"),
        ("tool0", "gripper_base_link"),
        ("gripper_base_link", "left_finger_link"),
        ("gripper_base_link", "right_finger_link"),
    ]
    for link1, link2 in adjacent_pairs:
        ET.SubElement(
            robot,
            "disable_collisions",
            {"link1": link1, "link2": link2, "reason": "Adjacent"},
        )

    return {
        "xml": robot,
        "urdf": "six_axis_arm.urdf",
    }
