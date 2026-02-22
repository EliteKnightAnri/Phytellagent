import matplotlib.pyplot as plt
from typing import Any, Dict, List, Optional, Tuple
from fastmcp import FastMCP

mcp = FastMCP("Matplotlib Toolbox Server")


def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}


def _ensure_list(value: Optional[Any]) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _maybe_error(*lists: List[Any]) -> Optional[str]:
    lengths = [len(lst) for lst in lists]
    filtered = [l for l in lengths if l]
    if not filtered:
        return "input data is empty"
    if len(set(filtered)) > 1:
        return f"data length mismatch: {filtered}"
    return None


def _success(file_path: str) -> Dict[str, Any]:
    return {"status": "success", "file_path": file_path}


@mcp.tool()
def plot_in_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    x_data = _ensure_list(args.get("x_data"))
    y_data = _ensure_list(args.get("y_data"))
    err = _maybe_error(x_data, y_data)
    if err:
        return {"status": "error", "message": err}

    title = args.get("title") or meta.get("title") or "2D Figure"
    x_label = args.get("x_label", "X-Axis")
    y_label = args.get("y_label", "Y-Axis")
    file_path = args.get("file_path", "2d_figure.png")

    plt.figure()
    plt.plot(x_data, y_data, marker='o')
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True)

    plt.savefig(file_path)
    plt.close()
    return _success(file_path)


@mcp.tool()
def plot_in_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    x_data = _ensure_list(args.get("x_data"))
    y_data = _ensure_list(args.get("y_data"))
    z_data = _ensure_list(args.get("z_data"))
    err = _maybe_error(x_data, y_data, z_data)
    if err:
        return {"status": "error", "message": err}

    title = args.get("title") or meta.get("title") or "3D Figure"
    x_label = args.get("x_label", "X-Axis")
    y_label = args.get("y_label", "Y-Axis")
    z_label = args.get("z_label", "Z-Axis")
    file_path = args.get("file_path", "3d_figure.png")

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(x_data, y_data, z_data, marker='o')
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_zlabel(z_label)

    plt.savefig(file_path)
    plt.close()
    return _success(file_path)


@mcp.tool()
def double_plot_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    x1_data = _ensure_list(args.get("x1_data"))
    y1_data = _ensure_list(args.get("y1_data"))
    x2_data = _ensure_list(args.get("x2_data"))
    y2_data = _ensure_list(args.get("y2_data"))
    err = _maybe_error(x1_data, y1_data, x2_data, y2_data)
    if err:
        return {"status": "error", "message": err}

    title = args.get("title") or meta.get("title") or "Double 2D Figure"
    x_label = args.get("x_label", "X-Axis")
    y_label = args.get("y_label", "Y-Axis")
    file_path = args.get("file_path", "double_2d_figure.png")

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
    return _success(file_path)


@mcp.tool()
def double_plot_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - ensures 3d projection registered

    args, meta = _split_payload(payload)
    x1_data = _ensure_list(args.get("x1_data"))
    y1_data = _ensure_list(args.get("y1_data"))
    z1_data = _ensure_list(args.get("z1_data"))
    x2_data = _ensure_list(args.get("x2_data"))
    y2_data = _ensure_list(args.get("y2_data"))
    z2_data = _ensure_list(args.get("z2_data"))
    err = _maybe_error(x1_data, y1_data, z1_data, x2_data, y2_data, z2_data)
    if err:
        return {"status": "error", "message": err}

    title = args.get("title") or meta.get("title") or "Double 3D Figure"
    x_label = args.get("x_label", "X-Axis")
    y_label = args.get("y_label", "Y-Axis")
    z_label = args.get("z_label", "Z-Axis")
    file_path = args.get("file_path", "double_3d_figure.png")

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
    return _success(file_path)


if __name__ == "__main__":
    mcp.run(transport="stdio")
