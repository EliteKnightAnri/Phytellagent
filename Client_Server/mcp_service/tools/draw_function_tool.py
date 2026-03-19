import matplotlib.pyplot as plt
import numpy as np
import sympy as sp
from fastmcp import FastMCP
from sympy import symbols, lambdify, sympify
from sympy.parsing.sympy_parser import parse_expr, standard_transformations
from typing import Any, Dict, Optional, Tuple

mcp = FastMCP("FunctionDrawer")


def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}


def _as_list(value: Optional[Any]) -> Optional[list]:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _error(message: str) -> Dict[str, Any]:
    return {"status": "error", "message": message}


def _success(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "data": data}


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
            

def str_to_function_2d(func_str: str = "x ** 2", var_name: str = "x"):
    func_str = func_str.replace('np.', '').replace('numpy.', '').replace('math.', '')
    transformations = standard_transformations
    func_name_map = {
        'exp': sp.exp, 'log': sp.log, 'ln': sp.log, 'sin': sp.sin, 'cos': sp.cos,
        'tan': sp.tan, 'sqrt': sp.sqrt, 'pi': sp.pi, 'E': sp.E, 'abs': sp.Abs,
        'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan, 'sinh': sp.sinh,
        'cosh': sp.cosh, 'tanh': sp.tanh, 'floor': sp.floor, 'ceiling': sp.ceiling,
    }

    import re
    idents = re.findall(r"\b[a-zA-Z_]\w*\b", func_str)
    var = sp.symbols(var_name)
    local_dict = dict(func_name_map)
    for ident in set(idents):
        if ident in local_dict:
            continue
        if ident == var_name:
            continue
        local_dict[ident] = sp.symbols(ident)

    expr = parse_expr(func_str, local_dict=local_dict, transformations=transformations)
    symbols = list(expr.free_symbols)
    param_symbols = [s for s in symbols if str(s) != var_name]
    param_symbols = sorted(param_symbols, key=lambda s: str(s))

    if param_symbols:
        lamb = sp.lambdify(param_symbols + [var], expr, modules=["numpy"]) 

        def model(params, x):
            return lamb(*params, x)

        model.param_count = len(param_symbols)
        model.param_names = [str(s) for s in param_symbols]
        return model
    else:
        lamb = sp.lambdify(var, expr, modules=["numpy"]) 

        def model(params, x):
            return lamb(x)

        model.param_count = 0
        model.param_names = []
        return model


def str_to_function_3d(func_str: str = "x + y", var_name: str = "x,y"):
    func_str = func_str.replace('np.', '').replace('numpy.', '').replace('math.', '')
    transformations = standard_transformations
    func_name_map = {
        'exp': sp.exp, 'log': sp.log, 'ln': sp.log, 'sin': sp.sin, 'cos': sp.cos,
        'tan': sp.tan, 'sqrt': sp.sqrt, 'pi': sp.pi, 'E': sp.E, 'abs': sp.Abs,
        'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan, 'sinh': sp.sinh,
        'cosh': sp.cosh, 'tanh': sp.tanh, 'floor': sp.floor, 'ceiling': sp.ceiling,
    }

    import re
    idents = re.findall(r"\b[a-zA-Z_]\w*\b", func_str)
    var_names = [name.strip() for name in var_name.split(",")]
    vars = sp.symbols(var_names)
    local_dict = dict(func_name_map)
    for ident in set(idents):
        if ident in local_dict:
            continue
        if ident in var_names:
            continue
        local_dict[ident] = sp.symbols(ident)

    expr = parse_expr(func_str, local_dict=local_dict, transformations=transformations)
    symbols = list(expr.free_symbols)
    var_name_set = set(var_names)
    param_symbols = [s for s in symbols if str(s) not in var_name_set]
    param_symbols = sorted(param_symbols, key=lambda s: str(s))

    if param_symbols:
        lamb = sp.lambdify(param_symbols + list(vars), expr, modules=["numpy"]) 

        def model(params, x, y):
            return lamb(*params, x, y)

        model.param_count = len(param_symbols)
        model.param_names = [str(s) for s in param_symbols]
        return model
    else:
        lamb = sp.lambdify(list(vars), expr, modules=["numpy"]) 

        def model(params, x, y):
            return lamb(x, y)

        model.param_count = 0
        model.param_names = []
        return model


@mcp.tool()
def generate_2d_points(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    func_str = args.get("function", "x ** 2")
    var_name = args.get("variable", "x")
    x_range = args.get("x_range", [-10, 10])
    num_points = args.get("num_points", 100)

    try:
        model = str_to_function_2d(func_str, var_name)
        x_values = np.linspace(x_range[0], x_range[1], num_points)
        y_values = model([], x_values)
        return _success({"x": x_values.tolist(), "y": y_values.tolist()})
    except Exception as e:
        return _error(f"Error generating points: {str(e)}")
    

@mcp.tool()
def generate_3d_points(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    func_str = args.get("function", "x + y")
    var_name = args.get("variables", "x,y")
    x_range = args.get("x_range", [-10, 10])
    y_range = args.get("y_range", [-10, 10])
    num_points = args.get("num_points", 100)

    try:
        model = str_to_function_3d(func_str, var_name)
        x_values = np.linspace(x_range[0], x_range[1], num_points)
        y_values = np.linspace(y_range[0], y_range[1], num_points)
        X, Y = np.meshgrid(x_values, y_values)
        Z = model([], X, Y)
        return _success({"x": X.tolist(), "y": Y.tolist(), "z": Z.tolist()})
    except Exception as e:
        return _error(f"Error generating points: {str(e)}")
    

@mcp.tool()
def plot_2d_function(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    func_str = args.get("function", "x ** 2") or meta.get("function", "x ** 2")
    var_name = args.get("variable", "x")
    x_range = args.get("x_range", [-10, 10])
    num_points = args.get("num_points", 100)
    file_path = args.get("file_path", "function_plot.png") or meta.get("file_path", "function_plot.png")

    try:
        model = str_to_function_2d(func_str, var_name)
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

        return _success({"message": f"Plot saved as {file_path}"})
    except Exception as e:
        return _error(f"Error plotting function: {str(e)}")
    

@mcp.tool()
def plot_3d_function(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    func_str = args.get("function", "x + y") or meta.get("function", "x + y")
    var_name = args.get("variables", "x,y")
    x_range = args.get("x_range", [-10, 10])
    y_range = args.get("y_range", [-10, 10])
    num_points = args.get("num_points", 100)
    file_path = args.get("file_path", "function_plot_3d.png") or meta.get("file_path", "function_plot_3d.png")

    try:
        model = str_to_function_3d(func_str, var_name)
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

        return _success({"message": f"3D plot saved as {file_path}"})
    except Exception as e:
        return _error(f"Error plotting 3D function: {str(e)}")
    

if __name__ == "__main__":
    mcp.run(transport="stdio")