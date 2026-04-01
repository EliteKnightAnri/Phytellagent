import matplotlib.pyplot as plt
import numpy as np
import sympy as sp
from fastmcp import FastMCP
from typing import Any, Dict, Optional, Tuple
from my_packages.status import split_payload, success, error
from my_packages.str2func import str2func_2d, str2func_3d

mcp = FastMCP("FunctionDrawer")


def _object_to_list(obj: Optional[Any]) -> Optional[list]:
    if obj is None:
        return None
    try:
        if hasattr(obj, "tolist"):
            candidate = obj.tolist()
        else:
            candidate = obj
    except Exception:
        candidate = obj
    return _safe_opt_to_list(candidate)


def _extract_from_source(source: Any, column: Optional[str]) -> Optional[list]:
    if source is None:
        return None
    if column is None:
        return _object_to_list(source)

    if isinstance(source, dict):
        if column not in source:
            return None
        return _object_to_list(source[column])

    if hasattr(source, "__getitem__"):
        try:
            selection = source[column]
        except Exception:
            return None
        return _object_to_list(selection)

    return None


def _safe_opt_to_list(obj):
    if obj is None:
        return None
    try:
        res = obj.tolist()
    except Exception:
        res = obj

    if isinstance(res, (list, tuple)):
        return list(res)
    return [res]

def _safe_cov_to_serializable(obj):
    if obj is None:
        return None
    try:
        return obj.tolist()
    except Exception:
        try:
            return float(obj)
        except Exception:
            return obj


@mcp.tool()
def generate_2d_points(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    func_str = args.get("function", "x ** 2")
    var_name = args.get("variable", "x")
    x_range = args.get("x_range", [-10, 10])
    num_points = args.get("num_points", 100)

    try:
        model = str2func_2d(func_str, var_name)
        x_values = np.linspace(x_range[0], x_range[1], num_points)
        y_values = model([], x_values)
        return success({"x": x_values.tolist(), "y": y_values.tolist()})
    except Exception as e:
        return error(f"Error generating points: {str(e)}")
    

@mcp.tool()
def generate_3d_points(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    func_str = args.get("function", "x + y")
    var_name = args.get("variables", "x,y")
    x_range = args.get("x_range", [-10, 10])
    y_range = args.get("y_range", [-10, 10])
    num_points = args.get("num_points", 100)

    try:
        model = str2func_3d(func_str, var_name)
        x_values = np.linspace(x_range[0], x_range[1], num_points)
        y_values = np.linspace(y_range[0], y_range[1], num_points)
        X, Y = np.meshgrid(x_values, y_values)
        Z = model([], X, Y)
        return success({"x": X.tolist(), "y": Y.tolist(), "z": Z.tolist()})
    except Exception as e:
        return error(f"Error generating points: {str(e)}")
    

@mcp.tool()
def plot_2d_function(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    func_str = args.get("function", "x ** 2") or meta.get("function", "x ** 2")
    var_name = args.get("variable", "x")
    x_range = args.get("x_range", [-10, 10])
    num_points = args.get("num_points", 100)
    file_path = args.get("file_path", "function_plot.png") or meta.get("file_path", "function_plot.png")

    try:
        model = str2func_2d(func_str, var_name)
        x_values = np.linspace(x_range[0], x_range[1], num_points)
        y_values = model([], x_values)

        plt.figure()
        plt.plot(x_values, y_values)
        plt.title(f"Plot of {func_str}")
        plt.xlabel(var_name)
        plt.ylabel("f({})".format(var_name))
        plt.grid()
        plt.savefig(file_path)
        plt.close()

        return success({"message": f"Plot saved as {file_path}"})
    except Exception as e:
        return error(f"Error plotting function: {str(e)}")
    

@mcp.tool()
def plot_3d_function(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    func_str = args.get("function", "x + y") or meta.get("function", "x + y")
    var_name = args.get("variables", "x,y")
    x_range = args.get("x_range", [-10, 10])
    y_range = args.get("y_range", [-10, 10])
    num_points = args.get("num_points", 100)
    file_path = args.get("file_path", "function_plot_3d.png") or meta.get("file_path", "function_plot_3d.png")

    try:
        model = str2func_3d(func_str, var_name)
        x_values = np.linspace(x_range[0], x_range[1], num_points)
        y_values = np.linspace(y_range[0], y_range[1], num_points)
        X, Y = np.meshgrid(x_values, y_values)
        Z = model([], X, Y)

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.plot_surface(X, Y, Z, cmap='viridis')
        ax.set_title(f"Plot of {func_str}")
        ax.set_xlabel(var_name.split(",")[0])
        ax.set_ylabel(var_name.split(",")[1])
        ax.set_zlabel("f({}, {})".format(var_name.split(",")[0], var_name.split(",")[1]))
        plt.savefig(file_path)
        plt.close()

        return success({"message": f"3D plot saved as {file_path}"})
    except Exception as e:
        return error(f"Error plotting 3D function: {str(e)}")
    

if __name__ == "__main__":
    mcp.run(transport="stdio")