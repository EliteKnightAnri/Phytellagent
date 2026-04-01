import re
import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations


def _is_empty_params(value):
    """返回 True 表示该参数容器可视为“空”，可安全忽略。"""
    if value is None:
        return True
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0
    if isinstance(value, np.ndarray):
        return value.size == 0
    try:
        return len(value) == 0
    except Exception:
        return False


def str2func_2d(func_str: str = "x ** 2", var_name: str = "x"):
    """
    将字符串形式的函数转换为可调用的函数对象，支持单变量和多参数的函数
    
    Args:
    - func_str: 函数的字符串表示，例如 "x ** 2" 或 "a * x ** 2 + b * x + c"
    - var_name: 变量名，例如 "x"
    
    Returns:
    - 一个可调用的单变量函数对象，接受参数列表和变量值作为输入

    """
    func_str = func_str.replace('np.', '').replace('numpy.', '').replace('math.', '')
    transformations = standard_transformations
    func_name_map = {
        'exp': sp.exp, 'log': sp.log, 'ln': sp.log, 'sin': sp.sin, 'cos': sp.cos,
        'tan': sp.tan, 'sqrt': sp.sqrt, 'pi': sp.pi, 'E': sp.E, 'abs': sp.Abs,
        'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan, 'sinh': sp.sinh, 
        'cosh': sp.cosh, 'tanh': sp.tanh, 'floor': sp.floor, 'ceiling': sp.ceiling,
    }
    idents = re.findall(r"\b[a-zA-Z_]\w*\b", func_str) # 提取所有合法变量名/标识符
    var = sp.symbols(var_name)
    local_dict = dict(func_name_map)
    for ident in set(idents):
        # 如果标识符在函数名映射中，或者是变量名，则跳过，否则将其视为符号变量
        if ident in local_dict:
            continue
        if ident == var_name:
            continue
        local_dict[ident] = sp.symbols(ident) # 将标识符添加到局部字典中，映射到sympy的符号对象

    expr = parse_expr(func_str, local_dict=local_dict, transformations=transformations)
    symbols = list(expr.free_symbols) # 获取表达式中的所有符号变量
    param_symbols = [s for s in symbols if str(s) != var_name] # 将所有符号中除了变量名之外的符号视为参数
    param_symbols = sorted(param_symbols, key=lambda s: str(s))

    if param_symbols:
        lamb = sp.lambdify(param_symbols + [var], expr, modules=["numpy"])

        def model(params, *vars):
            return lamb(*params, *vars)

        model.param_count = len(param_symbols)
        model.param_names = [str(s) for s in param_symbols]
        return model
    else:
        lamb = sp.lambdify(var, expr, modules=["numpy"])

        def model(*call_args):
            if len(call_args) == 1:
                return lamb(call_args[0])
            if len(call_args) == 2 and _is_empty_params(call_args[0]):
                return lamb(call_args[1])
            raise TypeError("Model without parameters expects x or (empty_params, x)")

        model.param_count = 0
        model.param_names = []
        return model
    

def str2func_3d(func_str: str = "x + y", var_name: str = "x,y"):
    """
    将字符串形式的函数转换为可调用的函数对象，支持多变量和多参数的函数
    
    Args:
    - func_str: 函数的字符串表示，例如 "x + y" 或 "a * x + b * y"
    - var_name: 变量名，多个变量用逗号分隔，例如 "x,y" 或 "x,y,z"

    Returns:
    - 一个可调用的多变量函数对象，接受参数列表和变量值作为输入，返回函数值
    
    """
    func_str = func_str.replace('np.', '').replace('numpy.', '').replace('math.', '')
    transformations = standard_transformations
    func_name_map = {
        'exp': sp.exp, 'log': sp.log, 'ln': sp.log, 'sin': sp.sin, 'cos': sp.cos,
        'tan': sp.tan, 'sqrt': sp.sqrt, 'pi': sp.pi, 'E': sp.E, 'abs': sp.Abs,
        'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan, 'sinh': sp.sinh,
        'cosh': sp.cosh, 'tanh': sp.tanh, 'floor': sp.floor, 'ceiling': sp.ceiling,
    }
    idents = re.findall(r"\b[a-zA-Z_]\w*\b", func_str)
    var_names = [v.strip() for v in var_name.split(',')]
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
    param_symbols = [s for s in symbols if str(s) not in var_names]
    param_symbols = sorted(param_symbols, key=lambda s: str(s))

    if param_symbols:
        lamb = sp.lambdify(param_symbols + list(vars), expr, modules=["numpy"])

        def model(params, *vars):
            return lamb(*params, *vars)

        model.param_count = len(param_symbols)
        model.param_names = [str(s) for s in param_symbols]
        return model
    else:
        lamb = sp.lambdify(list(vars), expr, modules=["numpy"])

        def model(*call_args):
            expected = len(vars)
            if len(call_args) == expected:
                return lamb(*call_args)
            if len(call_args) == expected + 1 and _is_empty_params(call_args[0]):
                return lamb(*call_args[1:])
            raise TypeError("Model without parameters expects coordinates or (empty_params, coordinates)")

        model.param_count = 0
        model.param_names = []
        return model