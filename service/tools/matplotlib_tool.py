import matplotlib.pyplot as plt
from typing import Any, Dict, Optional
from fastmcp import FastMCP

mcp = FastMCP("Matplotlib Toolbox Server")

@mcp.tool()
def plot_in_2d(x_data: list, y_data: list, title: str = "2D Figure", x_label: str = "X-Axis", y_label: str = "Y-Axis", file_path: str = "2d_figure.png") -> Dict[str, Any]:
    """
    Generate a 2D plot from the provided x and y data.

    Args:
        x_data (list): The data for the x-axis.
        y_data (list): The data for the y-axis.
        title (str, optional): The title of the plot. Defaults to "2D Figure".
        x_label (str, optional): The label for the x-axis. Defaults to "X-Axis".
        y_label (str, optional): The label for the y-axis. Defaults to "Y-Axis".
        file_path (str, optional): The file path to save the plot image. Defaults to "2d_figure.png".
    Returns:
        Dict[str, Any]: A dictionary containing the file path of the saved plot image.
    """
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
    """
    Generate a 3D plot from the provided x, y, and z data.

    Args:
        x_data (list): The data for the x-axis.
        y_data (list): The data for the y-axis.
        z_data (list): The data for the z-axis.
        title (str, optional): The title of the plot. Defaults to "3D Figure".
        x_label (str, optional): The label for the x-axis. Defaults to "X-Axis".
        y_label (str, optional): The label for the y-axis. Defaults to "Y-Axis".
        z_label (str, optional): The label for the z-axis. Defaults to "Z-Axis".
        file_path (str, optional): The file path to save the plot image. Defaults to "3d_figure.png".

    Returns:
        Dict[str, Any]: A dictionary containing the file path of the saved plot image.
    """
    from mpl_toolkits.mplot3d import Axes3D  # Importing here to avoid unnecessary dependency if 3D plotting is not used

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

if __name__ == "__main__":   
    mcp.run(transport="stdio")