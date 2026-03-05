import numpy as np
import sympy as sp
from scipy.optimize import leastsq
from sympy.printing.pycode import pycode
from sympy.parsing.sympy_parser import parse_expr, standard_transformations
from typing import Any, Dict, Optional, Tuple
from fastmcp import FastMCP

mcp = FastMCP("Least Square Method Server")


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
def least_square_fit_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    x_data = _as_list(args.get("x_data"))
    y_data = _as_list(args.get("y_data"))
    model_func_str = args.get("model_func_str") or meta.get("model_func_str")

    if not x_data or not y_data:
        return _error("x_data and y_data are required")
    if not model_func_str:
        return _error("model_func_str is required")

    model_func = str_to_function_2d(model_func_str)
    initial_params = args.get("initial_params")
    if initial_params is None:
        param_count = int(getattr(model_func, 'param_count', 0) or 0)
        initial_params = np.ones(max(param_count, 1))

    def error_func(params, x, y):
        return y - model_func(params, x)

    optimized_params, covariance = leastsq(
        error_func,
        initial_params,
        args=(np.array(x_data), np.array(y_data)),
    )

    return _success({
        "optimized_params": _safe_opt_to_list(optimized_params),
        "covariance": _safe_cov_to_serializable(covariance),
        "param_names": getattr(model_func, 'param_names', None),
    })


@mcp.tool()
def least_square_fit_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    x_data = _as_list(args.get("x_data"))
    y_data = _as_list(args.get("y_data"))
    z_data = _as_list(args.get("z_data"))
    model_func_str = args.get("model_func_str") or meta.get("model_func_str")

    if not x_data or not y_data or not z_data:
        return _error("x_data, y_data and z_data are required")
    if not model_func_str:
        return _error("model_func_str is required")

    model_func = str_to_function_3d(model_func_str, var_name="x,y")
    initial_params = args.get("initial_params")
    if initial_params is None:
        param_count = int(getattr(model_func, 'param_count', 0) or 0)
        initial_params = np.ones(max(param_count, 1))

    def error_func(params, x, y, z):
        return z - model_func(params, x, y)

    optimized_params, covariance = leastsq(
        error_func,
        initial_params,
        args=(np.array(x_data), np.array(y_data), np.array(z_data)),
    )

    return _success({
        "optimized_params": _safe_opt_to_list(optimized_params),
        "covariance": _safe_cov_to_serializable(covariance),
        "param_names": getattr(model_func, 'param_names', None),
    })


@mcp.tool()
def generate_pred_values_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    x_data = _as_list(args.get("x_data"))
    model_func_str = args.get("model_func_str") or meta.get("model_func_str")
    params = _as_list(args.get("params"))

    if not x_data or not model_func_str or params is None:
        return _error("x_data, model_func_str and params are required")

    model_func = str_to_function_2d(model_func_str)
    predicted_y = model_func(params, np.array(x_data))
    return _success({"predicted_y": _safe_opt_to_list(predicted_y)})


@mcp.tool()
def generate_pred_values_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    x_data = _as_list(args.get("x_data"))
    y_data = _as_list(args.get("y_data"))
    model_func_str = args.get("model_func_str") or meta.get("model_func_str")
    params = _as_list(args.get("params"))

    if not x_data or not y_data or not model_func_str or params is None:
        return _error("x_data, y_data, model_func_str and params are required")

    model_func = str_to_function_3d(model_func_str, var_name="x,y")
    predicted_z = model_func(params, np.array(x_data), np.array(y_data))
    return _success({"predicted_z": _safe_opt_to_list(predicted_z)})

if __name__ == "__main__":
    mcp.run(transport="stdio")
