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
    # 优先使用 numpy 的 tolist
    try:
        res = obj.tolist()
    except Exception:
        res = obj

    # 如果得到的是标量，包装为单元素列表；如果是列表/元组，转为 list
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
    """
    Convert a string representation of a mathematical function into a callable function.

    Args:
        func_str (str): The mathematical expression as a string (e.g., "sin(x) + cos(x)").
        var_name (str, optional): The variable name to use as the function argument. Defaults to "x".
        str: The source code of a Python function that computes the given expression.

    Returns:
        callable: A function that takes a numpy array as input and returns the computed values.
    """

    # 允许用户使用 `np.` / `numpy.` / `math.` 前缀的写法，先移除前缀
    func_str = func_str.replace('np.', '').replace('numpy.', '').replace('math.', '')

    # 映射常用数学函数到 sympy 实现，避免把函数名当作符号
    transformations = standard_transformations
    func_name_map = {
        'exp': sp.exp, 'log': sp.log, 'ln': sp.log, 'sin': sp.sin, 'cos': sp.cos,
        'tan': sp.tan, 'sqrt': sp.sqrt, 'pi': sp.pi, 'E': sp.E, 'abs': sp.Abs,
        'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan, 'sinh': sp.sinh,
        'cosh': sp.cosh, 'tanh': sp.tanh, 'floor': sp.floor, 'ceiling': sp.ceiling,
    }

    # 先扫描所有标识符，预声明除自变量与已知函数外的名字为 Symbol，避免 parse_expr 在 eval 阶段把它们解析成未定义函数
    import re
    idents = re.findall(r"\b[a-zA-Z_]\w*\b", func_str)
    idents = [i for i in idents]
    # 自变量集合
    var = sp.symbols(var_name)
    var_name_str = str(var)
    var_names_set = {var_name}

    # 构建 local_dict：函数名映射 + 预定义的参数符号
    local_dict = dict(func_name_map)
    for ident in set(idents):
        if ident in local_dict:
            continue
        if ident == var_name:
            # 自变量，已由 parse_expr 自动处理
            continue
        # 预声明为 Symbol（例如 h0, x0 等）
        local_dict[ident] = sp.symbols(ident)

    expr = parse_expr(func_str, local_dict=local_dict, transformations=transformations)

    # 找出参数符号（所有自由符号中去掉自变量）
    symbols = list(expr.free_symbols)
    param_symbols = [s for s in symbols if str(s) != var_name]
    # 确定参数顺序：按名称排序以保证可重现性
    param_symbols = sorted(param_symbols, key=lambda s: str(s))

    if param_symbols:
        # lambdify 接受的参数顺序：参数符号..., 自变量
        lamb = sp.lambdify(param_symbols + [var], expr, modules=["numpy"]) 

        def model(params, x):
            return lamb(*params, x)

        model.param_count = len(param_symbols)
        model.param_names = [str(s) for s in param_symbols]
        return model
    else:
        # 无参数，仅关于 x
        lamb = sp.lambdify(var, expr, modules=["numpy"]) 

        def model(params, x):
            # params 被忽略
            return lamb(x)

        model.param_count = 0
        model.param_names = []
        return model


def str_to_function_3d(func_str: str = "x + y", var_name: str = "x,y"):
    """
    Convert a string representation of a mathematical function into a callable function.

    Args:
        func_str (str): The mathematical expression as a string (e.g., "sin(x) + cos(y)").
        var_name (str, optional): The variable names to use as the function arguments, separated by commas. Defaults to "x,y".
        str: The source code of a Python function that computes the given expression.

    Returns:
        callable: A function that takes two numpy arrays as input and returns the computed values.
    """
    # 允许带前缀的 numpy/math 写法
    func_str = func_str.replace('np.', '').replace('numpy.', '').replace('math.', '')

    transformations = standard_transformations
    func_name_map = {
        'exp': sp.exp, 'log': sp.log, 'ln': sp.log, 'sin': sp.sin, 'cos': sp.cos,
        'tan': sp.tan, 'sqrt': sp.sqrt, 'pi': sp.pi, 'E': sp.E, 'abs': sp.Abs,
        'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan, 'sinh': sp.sinh,
        'cosh': sp.cosh, 'tanh': sp.tanh, 'floor': sp.floor, 'ceiling': sp.ceiling,
    }

    # 预声明标识符为 Symbol（排除自变量和已知函数），避免 parse 时将其作为未定义函数
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

    # 找出参数符号（去掉自变量 x,y）
    symbols = list(expr.free_symbols)
    var_name_set = set(var_names)
    param_symbols = [s for s in symbols if str(s) not in var_name_set]
    param_symbols = sorted(param_symbols, key=lambda s: str(s))

    if param_symbols:
        # lambdify 参数顺序：参数符号..., 自变量 x,y
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
    """
    Perform least squares fitting on the provided data using the specified model function.

    Args:
        x_data (list): The independent variable data points.
        y_data (list): The dependent variable data points.
        model_func (callable): The model function to fit, should take parameters and x_data as input.

    Returns:
        Dict[str, Any]: A dictionary containing the optimized parameters and the covariance matrix.
    """
    # 获取模型函数：优先使用传入的 model_func_str，否则回退到交互输入
    if model_func_str:
        model_func = str_to_function_2d(model_func_str)
    else:
        func_str = input("Enter the model function in terms of x (e.g., 'sin(x) + cos(x)'): ")
        model_func = str_to_function_2d(func_str)

    # 初始参数猜测：优先使用传入的 initial_params，否则尝试根据模型函数推断长度
    if initial_params is None:
        # 优先使用 model_func 提供的 param_count
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

    # 误差函数
    def error_func(params, x, y):
        return y - model_func(params, x)

    # 最小二乘法拟合
    optimized_params, covariance = leastsq(error_func, initial_params, args=(np.array(x_data), np.array(y_data)))

    return {
        "optimized_params": _safe_opt_to_list(optimized_params),
        "covariance": _safe_cov_to_serializable(covariance),
        "param_names": getattr(model_func, 'param_names', None)
    }

@mcp.tool()
def least_square_fit_3d(x_data: list, y_data: list, z_data: list, model_func_str: str, initial_params: Optional[list] = None) -> Dict[str, Any]:
    """
    Perform least squares fitting on the provided 3D data using the specified model function.

    Args:
        x_data (list): The independent variable data points for x-axis.
        y_data (list): The independent variable data points for y-axis.
        z_data (list): The dependent variable data points.
        model_func (callable): The model function to fit, should take parameters, x_data, and y_data as input.

    Returns:
        Dict[str, Any]: A dictionary containing the optimized parameters and the covariance matrix.
    """
    # 获取模型函数：优先使用传入的 model_func_str，否则回退到交互输入
    if model_func_str:
        model_func = str_to_function_3d(model_func_str, var_name="x,y")
    else:
        func_str = input("Enter the model function in terms of x and y (e.g., 'sin(x) + cos(y)'): ")
        model_func = str_to_function_3d(func_str, var_name="x,y")

    # 初始参数猜测：优先使用传入的 initial_params，否则尝试根据模型函数推断长度
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

    # 误差函数
    def error_func(params, x, y, z):
        return z - model_func(params, x, y)

    # 最小二乘法拟合
    optimized_params, covariance = leastsq(error_func, initial_params, args=(np.array(x_data), np.array(y_data), np.array(z_data)))

    return {
        "optimized_params": _safe_opt_to_list(optimized_params),
        "covariance": _safe_cov_to_serializable(covariance),
        "param_names": getattr(model_func, 'param_names', None)
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")