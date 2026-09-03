#!/usr/bin/env python3
"""
myCobot 280 URDF 零位构型可视化（替代 cad-viewer 的 2D 预览）

由于 cad-viewer 技能未安装，本脚本使用 matplotlib 绘制零位构型下的
连杆轮廓、关节坐标系和关节轴，作为可视化预览替代方案。

正运动学直接从生成的 URDF 解析关节原点和 RPY，不依赖外部库。
几何体顶点经完整 3D 变换后投影到 2D 平面。
"""

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
import numpy as np


URDF_PATH = Path(__file__).parent / "mycobot280.urdf"
OUTPUT_PATH = Path(__file__).parent / "preview_zero_config.png"


def rpy_to_rotation(roll, pitch, yaw):
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return rz @ ry @ rx


def parse_urdf(urdf_path):
    tree = ET.parse(urdf_path)
    root = tree.getroot()

    links = {}
    for link_elem in root.findall("link"):
        name = link_elem.get("name")
        links[name] = {"visuals": []}
        for vis in link_elem.findall("visual"):
            origin = vis.find("origin")
            xyz = [float(v) for v in origin.get("xyz").split()] if origin is not None else [0, 0, 0]
            rpy = [float(v) for v in origin.get("rpy").split()] if origin is not None else [0, 0, 0]
            geom = vis.find("geometry")
            if geom is not None:
                box = geom.find("box")
                cyl = geom.find("cylinder")
                if box is not None:
                    size = [float(v) for v in box.get("size").split()]
                    links[name]["visuals"].append({"type": "box", "xyz": xyz, "rpy": rpy, "size": size})
                elif cyl is not None:
                    r = float(cyl.get("radius"))
                    h = float(cyl.get("length"))
                    links[name]["visuals"].append({"type": "cylinder", "xyz": xyz, "rpy": rpy, "radius": r, "length": h})

    joints = []
    for joint_elem in root.findall("joint"):
        j = {
            "name": joint_elem.get("name"),
            "type": joint_elem.get("type"),
            "parent": joint_elem.find("parent").get("link"),
            "child": joint_elem.find("child").get("link"),
        }
        origin = joint_elem.find("origin")
        j["xyz"] = [float(v) for v in origin.get("xyz").split()] if origin is not None else [0, 0, 0]
        j["rpy"] = [float(v) for v in origin.get("rpy").split()] if origin is not None else [0, 0, 0]
        axis_elem = joint_elem.find("axis")
        j["axis"] = [float(v) for v in axis_elem.get("xyz").split()] if axis_elem is not None else [0, 0, 1]
        limit = joint_elem.find("limit")
        if limit is not None:
            j["lower"] = math.degrees(float(limit.get("lower", 0)))
            j["upper"] = math.degrees(float(limit.get("upper", 0)))
        else:
            j["lower"] = j["upper"] = 0.0
        joints.append(j)

    return links, joints


def compute_fk(joints):
    transforms = {"base_link": (np.eye(3), np.zeros(3))}
    queue = ["base_link"]
    while queue:
        parent = queue.pop(0)
        for j in joints:
            if j["parent"] == parent:
                child = j["child"]
                r_parent, t_parent = transforms[parent]
                r_joint = rpy_to_rotation(*j["rpy"])
                t_joint = np.array(j["xyz"])
                transforms[child] = (r_parent @ r_joint, r_parent @ t_joint + t_parent)
                queue.append(child)
    return transforms


def box_corners(size):
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    return np.array([
        [-sx, -sy, -sz], [sx, -sy, -sz], [sx, sy, -sz], [-sx, sy, -sz],
        [-sx, -sy, sz], [sx, -sy, sz], [sx, sy, sz], [-sx, sy, sz],
    ])


def cylinder_corners(radius, length, n=16):
    """用多边形近似圆柱的端面顶点。"""
    pts = []
    for z in (-length / 2, length / 2):
        for i in range(n):
            a = 2 * math.pi * i / n
            pts.append([radius * math.cos(a), radius * math.sin(a), z])
    return np.array(pts)


def draw_geometry(ax, vis, r_link, t_link, plane, color, alpha=0.35):
    """将几何体顶点变换到世界坐标后投影到 2D 平面并绘制凸包。"""
    r_vis = rpy_to_rotation(*vis["rpy"])
    t_vis = np.array(vis["xyz"])
    r_world = r_link @ r_vis
    t_world = r_link @ t_vis + t_link

    if vis["type"] == "box":
        corners = box_corners(vis["size"])
    elif vis["type"] == "cylinder":
        corners = cylinder_corners(vis["radius"], vis["length"])
    else:
        return

    world_pts = (r_world @ corners.T).T + t_world

    if plane == "xz":
        pts2d = world_pts[:, [0, 2]]
    else:
        pts2d = world_pts[:, [0, 1]]

    # 简单凸包
    from scipy.spatial import ConvexHull
    try:
        hull = ConvexHull(pts2d)
        poly = Polygon(pts2d[hull.vertices], closed=True, linewidth=1.2,
                       edgecolor=color, facecolor=color, alpha=alpha)
        ax.add_patch(poly)
    except Exception:
        ax.plot(pts2d[:, 0], pts2d[:, 1], "o", color=color, markersize=2)


def draw_frame(ax, origin, rotation, plane, scale=0.025, label=""):
    colors = {"x": "red", "y": "green", "z": "blue"}
    if plane == "xz":
        ax_map = {"x": (0, 2), "z": (2, 2)}
        draw_axes = ["x", "z"]
    else:
        ax_map = {"x": (0, 0), "y": (1, 1)}
        draw_axes = ["x", "y"]

    for ax_name in draw_axes:
        idx = {"x": 0, "y": 1, "z": 2}[ax_name]
        direction = rotation[:, idx]
        end = origin + direction * scale
        if plane == "xz":
            ax.plot([origin[0], end[0]], [origin[2], end[2]],
                    color=colors[ax_name], linewidth=1.5)
        else:
            ax.plot([origin[0], end[0]], [origin[1], end[1]],
                    color=colors[ax_name], linewidth=1.5)
    if label:
        if plane == "xz":
            ax.plot(origin[0], origin[2], "k.", markersize=3)
            ax.annotate(label, (origin[0], origin[2]),
                        textcoords="offset points", xytext=(5, 5), fontsize=6, color="black")
        else:
            ax.plot(origin[0], origin[1], "k.", markersize=3)
            ax.annotate(label, (origin[0], origin[1]),
                        textcoords="offset points", xytext=(5, 5), fontsize=6, color="black")


def main():
    links, joints = parse_urdf(URDF_PATH)
    transforms = compute_fk(joints)

    joint_positions = {}
    for j in joints:
        r_parent, t_parent = transforms[j["parent"]]
        r_joint = rpy_to_rotation(*j["rpy"])
        t_joint = np.array(j["xyz"])
        joint_pos_world = r_parent @ t_joint + t_parent
        joint_axis_world = r_parent @ r_joint @ np.array(j["axis"])
        joint_positions[j["name"]] = (joint_pos_world, joint_axis_world)

    fig, axes = plt.subplots(1, 2, figsize=(14, 8))

    link_colors = {
        "base_link": "#555555",
        "shoulder_link": "#3377bb",
        "upper_arm_link": "#3377bb",
        "forearm_link": "#3377bb",
        "wrist_pitch_link": "#33aa55",
        "wrist_roll_link": "#33aa55",
        "flange_link": "#ee7722",
    }

    for ax_idx, (plane, title) in enumerate([("xz", "Side View (X-Z plane, zero config)"),
                                              ("xy", "Top View (X-Y plane, zero config)")]):
        ax = axes[ax_idx]

        for link_name, link_data in links.items():
            if link_name not in transforms:
                continue
            r_link, t_link = transforms[link_name]
            color = link_colors.get(link_name, "#888888")
            for vis in link_data["visuals"]:
                draw_geometry(ax, vis, r_link, t_link, plane, color)

        for link_name, (r, t) in transforms.items():
            draw_frame(ax, t, r, plane, label=link_name)

        for j in joints:
            if j["name"] not in joint_positions:
                continue
            jpos, jaxis = joint_positions[j["name"]]
            if plane == "xz":
                ax.plot(jpos[0], jpos[2], "ko", markersize=6, zorder=5)
                ax.annotate(f"{j['name']}  [{j['lower']:.0f}, {j['upper']:.0f}] deg",
                            (jpos[0], jpos[2]), textcoords="offset points",
                            xytext=(8, -12), fontsize=6.5, color="darkred", fontweight="bold")
            else:
                ax.plot(jpos[0], jpos[1], "ko", markersize=6, zorder=5)
                ax.annotate(j["name"], (jpos[0], jpos[1]),
                            textcoords="offset points", xytext=(8, -8),
                            fontsize=6.5, color="darkred", fontweight="bold")

        for j in joints:
            if j["name"] not in joint_positions:
                continue
            jpos, _ = joint_positions[j["name"]]
            _, t_parent = transforms[j["parent"]]
            if plane == "xz":
                ax.plot([t_parent[0], jpos[0]], [t_parent[2], jpos[2]],
                        "k--", linewidth=1.0, alpha=0.6, zorder=3)
            else:
                ax.plot([t_parent[0], jpos[0]], [t_parent[1], jpos[1]],
                        "k--", linewidth=1.0, alpha=0.6, zorder=3)

        ax.set_xlabel("X (m)")
        ax.set_ylabel("Z (m)" if plane == "xz" else "Y (m)")
        ax.set_title(title)
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color="k", linewidth=0.5)
        ax.axvline(x=0, color="k", linewidth=0.5)

    fig.suptitle("myCobot 280 URDF Zero Configuration Preview (all joint angles = 0)\n"
                 "Red=X  Green=Y  Blue=Z  Black dots=joint origins  Dashed=kinematic chain",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight")
    print(f"Preview saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
