import sympy as sp
import numpy as np
from typing import Any, Dict, Optional, Tuple
from sympy.parsing.sympy_parser import parse_expr, standard_transformations
from fastmcp import FastMCP

mcp = FastMCP("Differential Equations Solver Server")

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
        
def _str_to_function_2d(func_str: str = "x ** 2", var_name: str = "x"):
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
    
@mcp.tool()
def euler_diff_solver(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Solves a first-order ordinary differential equation using Euler's method.
    The function should be provided as a string in the form of "f(x, y)" where "x" is the independent variable and "y" is the dependent variable. The initial conditions and step size can also be specified.
    """
    args, meta = _split_payload(payload)
    diff_str = args.get("diff_equation", "x") or meta.get("diff_equation", "x")
    x0 = args.get("x0", 0)
    y0 = args.get("y0", 1)
    x_end = args.get("x_end", 10)
    step = args.get("step", 0.1)

    try:
        model = _str_to_function_2d(diff_str, var_name="x")
    except Exception as e:
        return _error(f"Failed to parse function: {e}")

    x_values = np.arange(x0, x_end + step, step)
    y_values = np.zeros_like(x_values)
    y_values[0] = y0

    for i in range(1, len(x_values)):
        try:
            y_values[i] = y_values[i-1] + model([], x_values[i-1]) * step
        except Exception as e:
            return _error(f"Error during Euler's method computation at step {i}: {e}")

    return {"status": "success", "x": x_values.tolist(), "y": y_values.tolist()}

@mcp.tool()
def trapezoidal_diff_solver(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Solves a first-order ordinary differential equation using the trapezoidal method.
    The function should be provided as a string in the form of "f(x, y)" where "x" is the independent variable and "y" is the dependent variable. The initial conditions and step size can also be specified.
    """
    args, meta = _split_payload(payload)
    diff_str = args.get("diff_equation", "x") or meta.get("diff_equation", "x")
    x0 = args.get("x0", 0)
    y0 = args.get("y0", 1)
    x_end = args.get("x_end", 10)
    step = args.get("step", 0.1)
    eps = args.get("eps", 1e-6)

    try:
        model = _str_to_function_2d(diff_str, var_name="x")
    except Exception as e:
        return _error(f"Failed to parse function: {e}")

    x_values = np.arange(x0, x_end + step, step)
    y_values = np.zeros_like(x_values)
    y_values[0] = y0

    for i in range(1, len(x_values)):
        try:
            f_prev = model([], x_values[i-1])
            y_predictor = y_values[i-1] + f_prev * step
            while np.fabs(y_predictor - y_values[i-1]) > eps:
                f_corrector = model([], x_values[i])
                y_values[i] = y_values[i-1] + (f_prev + f_corrector) * step / 2
        except Exception as e:
            return _error(f"Error during trapezoidal method computation at step {i}: {e}")

    return {"status": "success", "x": x_values.tolist(), "y": y_values.tolist()}

if __name__ == "__main__":
    mcp.run(transport="stdio")