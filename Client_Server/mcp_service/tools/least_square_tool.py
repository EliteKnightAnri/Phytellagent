import pandas as pd
import numpy as np
import sympy as sp
from scipy.optimize import leastsq
from sympy.printing.pycode import pycode
from sympy.parsing.sympy_parser import parse_expr, standard_transformations
from typing import Any, Dict, Optional
from fastmcp import FastMCP

mcp = FastMCP("Least Square Method Server")

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
def least_square_fit_2d(x_data: list, y_data: list, model_func_str: str, initial_params: Optional[list] = None) -> Dict[str, Any]:
    if model_func_str:
        model_func = str_to_function_2d(model_func_str)
    else:
        func_str = input("Enter the model function in terms of x (e.g., 'sin(x) + cos(x)'):")
        model_func = str_to_function_2d(func_str)

    if initial_params is None:
        try:
            param_count = int(getattr(model_func, 'param_count', None))
        except Exception:
            param_count = None
        if param_count is None:
            try:
                param_count = max(1, model_func.__code__.co_argcount - 1)
            except Exception:
                param_count = 1
        initial_params = np.ones(param_count)

    def error_func(params, x, y):
        return y - model_func(params, x)

    optimized_params, covariance = leastsq(error_func, initial_params, args=(np.array(x_data), np.array(y_data)))

    return {
        "optimized_params": _safe_opt_to_list(optimized_params),
        "covariance": _safe_cov_to_serializable(covariance),
        "param_names": getattr(model_func, 'param_names', None)
    }

@mcp.tool()
def least_square_fit_3d(x_data: list, y_data: list, z_data: list, model_func_str: str, initial_params: Optional[list] = None) -> Dict[str, Any]:
    if model_func_str:
        model_func = str_to_function_3d(model_func_str, var_name="x,y")
    else:
        func_str = input("Enter the model function in terms of x and y (e.g., 'sin(x) + cos(y)'):")
        model_func = str_to_function_3d(func_str, var_name="x,y")

    if initial_params is None:
        try:
            param_count = int(getattr(model_func, 'param_count', None))
        except Exception:
            param_count = None
        if param_count is None:
            try:
                param_count = max(1, model_func.__code__.co_argcount - 2)
            except Exception:
                param_count = 1
        initial_params = np.ones(param_count)

    def error_func(params, x, y, z):
        return z - model_func(params, x, y)

    optimized_params, covariance = leastsq(error_func, initial_params, args=(np.array(x_data), np.array(y_data), np.array(z_data)))

    return {
        "optimized_params": _safe_opt_to_list(optimized_params),
        "covariance": _safe_cov_to_serializable(covariance),
        "param_names": getattr(model_func, 'param_names', None)
    }

@mcp.tool()
def generate_pred_values_2d(x_data: list, model_func_str: str, params: list) -> Dict[str, Any]:
    model_func = str_to_function_2d(model_func_str)
    predicted_y = model_func(params, np.array(x_data))
    return {"predicted_y": _safe_opt_to_list(predicted_y)}

@mcp.tool()
def generate_pred_values_3d(x_data: list, y_data: list, model_func_str: str, params: list) -> Dict[str, Any]:
    model_func = str_to_function_3d(model_func_str, var_name="x,y")
    predicted_z = model_func(params, np.array(x_data), np.array(y_data))
    return {"predicted_z": _safe_opt_to_list(predicted_z)}

if __name__ == "__main__":
    mcp.run(transport="stdio")
