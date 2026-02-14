import matplotlib.pyplot as plt
from typing import Any, Dict, Optional
from fastmcp import FastMCP

mcp = FastMCP("Matplotlib Toolbox Server")

@mcp.tool()
def plot_in_2d(x_data: list, y_data: list, title: str = "2D Figure", x_label: str = "X-Axis", y_label: str = "Y-Axis", file_path: str = "2d_figure.png") -> Dict[str, Any]:
    plt.figure()
    plt.plot(x_data, y_data, marker='o')
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True)

    plt.savefig(file_path)
    plt.close()
    return {"file_path": file_path}

@mcp.tool()
def plot_in_3d(x_data: list, y_data: list, z_data: list, title: str = "3D Figure", x_label: str = "X-Axis", y_label: str = "Y-Axis", z_label: str = "Z-Axis", file_path: str = "3d_figure.png") -> Dict[str, Any]:
    from mpl_toolkits.mplot3d import Axes3D

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(x_data, y_data, z_data, marker='o')
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_zlabel(z_label)

    plt.savefig(file_path)
    plt.close()
    return {"file_path": file_path}

@mcp.tool()
def double_plot_2d(x1_data: list, y1_data: list, x2_data: list, y2_data: list, title: str = "Double 2D Figure", x_label: str = "X-Axis", y_label: str = "Y-Axis", file_path: str = "double_2d_figure.png") -> Dict[str, Any]:
    plt.figure()
    plt.plot(x1_data, y1_data, marker='o', label='Set 1')
    plt.plot(x2_data, y2_data, marker='x', label='Set 2')
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True)
    plt.legend()

    plt.savefig(file_path)
    plt.close()
    return {"file_path": file_path}

@mcp.tool()
def double_plot_3d(x1_data: list, y1_data: list, z1_data: list, x2_data: list, y2_data: list, z2_data: list, title: str = "Double 3D Figure", x_label: str = "X-Axis", y_label: str = "Y-Axis", z_label: str = "Z-Axis", file_path: str = "double_3d_figure.png") -> Dict[str, Any]:
    from mpl_toolkits.mplot3d import Axes3D

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(x1_data, y1_data, z1_data, marker='o', label='Set 1')
    ax.scatter(x2_data, y2_data, z2_data, marker='x', label='Set 2')
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_zlabel(z_label)
    plt.legend()

    plt.savefig(file_path)
    plt.close()
    return {"file_path": file_path}

if __name__ == "__main__":   
    mcp.run(transport="stdio")
