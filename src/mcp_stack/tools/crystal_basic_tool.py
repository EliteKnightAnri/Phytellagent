"""
This module provides basic tools for working with crystals in the MCP stack. 
It includes functions for creating, manipulating, and analyzing crystal structures, as well as utilities for visualizing and exporting crystal data.
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
from pathlib import Path
from fastmcp import FastMCP
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = BASE_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from mcp_stack.local_packages.data_memory import data_memory
from mcp_stack.local_packages.status import success, error, split_payload, load_dataset

mcp = FastMCP("Basic Crystal Computation Server")

@mcp.tool()
def crystal_orientation_for_cubics(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    根据传入的晶向指数[uvw]或晶面指数(hkl)，对立方晶系计算晶向。

    Args:
        payload: 包含该立方晶体的晶向指数[uvw]或晶面指数(hkl]的字典。可能包含以下键：
            - uvw: List[int] - 晶向指数，表示晶体的取向，默认值为[1, 0, 0]。
            - hkl: List[int] - 晶面指数，表示晶体的取向，默认值为[1, 0, 0]。
            - input_type: str - 指定输入的类型，可能是"uvw"或"hkl"，默认值为"uvw"。
            - figsize: Tuple[int, int] - 绘图的尺寸，默认值为(6, 6)。
            - title: str - 绘图的标题，默认值为"Crystal Orientation for Cubics"。
            - file_path: str - 笛卡尔坐标系中的晶向绘制图片的文件路径，默认值为"docs/generated_images/crystal_orientation.png"。

    Returns:
        Dict[str, Any]: 一个包含晶向信息的字典，可能包含以下键：
            - orientation: List[float] - 晶向在笛卡尔坐标系中的表示。
            - angle: List[float] - 晶向与坐标轴的夹角。
            - file_path: str - 笛卡尔坐标系中的晶向绘制图片的文件路径。

    """
    args, meta = split_payload(payload)
    input_type = args.get("input_type", "uvw")

    if input_type == "uvw":
        uvw = args.get("uvw", [1, 0, 0])
        max_value = abs(max(abs(uvw[0]), abs(uvw[1]), abs(uvw[2])))
        if max_value == 0:
            return error("Invalid uvw indices. At least one index must be non-zero.")
        # 计算晶向的笛卡尔坐标表示
        orientation_int = [uvw[0], uvw[1], uvw[2]]
        orientation = [uvw[0]/max_value, uvw[1]/max_value, uvw[2]/max_value]
        angle = np.arccos(orientation[0] / np.linalg.norm(orientation)) * 180 / np.pi
    elif input_type == "hkl":
        hkl = args.get("hkl", [1, 0, 0])
        # 计算晶面的法向量作为晶向
        max_value = abs(max(abs(hkl[0]), abs(hkl[1]), abs(hkl[2])))
        if max_value == 0:
            return error("Invalid hkl indices. At least one index must be non-zero.")
        orientation_int = [hkl[0], hkl[1], hkl[2]]
        orientation = [hkl[0]/max_value, hkl[1]/max_value, hkl[2]/max_value]
        angle = np.arccos(orientation[0] / np.linalg.norm(orientation)) * 180 / np.pi
    else:
        return error("Invalid input type. Must be 'uvw' or 'hkl'.")
    
    # 在三维笛卡尔坐标系中绘制一个包含晶面和晶向的图像
    fig = plt.figure(figsize=args.get("figsize", (6, 6)))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_title(args.get("title", "Crystal Orientation for Cubics"))
    ax.set_xlabel('X-axis')
    ax.set_ylabel('Y-axis')
    ax.set_zlabel('Z-axis')
    # 绘制晶向
    ax.quiver(0, 0, 0, orientation[0], orientation[1], orientation[2], color='r', label=f'Orientation: {orientation}')
    # 绘制晶面：自动选择非零法向分量来求解，避免固定除以 z 分量
    def _plot_plane(ax, normal_vector, point_on_plane, label):
        plane_size = 1.5
        nx, ny, nz = normal_vector

        if not np.isclose(nz, 0.0):
            xx, yy = np.meshgrid(
                np.linspace(-plane_size, plane_size, 10),
                np.linspace(-plane_size, plane_size, 10),
            )
            zz = (-nx * (xx - point_on_plane[0]) - ny * (yy - point_on_plane[1])) / nz + point_on_plane[2]
            ax.plot_surface(xx, yy, zz, alpha=0.5, color='b', label=label)
        elif not np.isclose(ny, 0.0):
            xx, zz = np.meshgrid(
                np.linspace(-plane_size, plane_size, 10),
                np.linspace(-plane_size, plane_size, 10),
            )
            yy = (-nx * (xx - point_on_plane[0]) - nz * (zz - point_on_plane[2])) / ny + point_on_plane[1]
            ax.plot_surface(xx, yy, zz, alpha=0.5, color='b', label=label)
        else:
            yy, zz = np.meshgrid(
                np.linspace(-plane_size, plane_size, 10),
                np.linspace(-plane_size, plane_size, 10),
            )
            xx = (-ny * (yy - point_on_plane[1]) - nz * (zz - point_on_plane[2])) / nx + point_on_plane[0]
            ax.plot_surface(xx, yy, zz, alpha=0.5, color='b', label=label)

    normal_vector = np.array(orientation)
    d = 1 / np.linalg.norm(normal_vector)  # 晶面到原点的距离
    point_on_plane = normal_vector * d  # 晶面上的一个点
    _plot_plane(ax, normal_vector, point_on_plane, f'Plane: {orientation_int}')
    ax.legend()
    # 保存图像到文件
    file_path = args.get("file_path", BASE_DIR / "docs" / "generated_images" / "crystal_orientation.png")
    plt.savefig(file_path)
    plt.close(fig)

    result = {
        "orientation": orientation,
        "angle": angle,
        "file_path": file_path
    }
    return success(result)


if __name__ == "__main__":
    mcp.run(transport="stdio")