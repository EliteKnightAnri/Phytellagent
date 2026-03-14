import numpy as np
import sympy as sp
from scipy.optimize import leastsq
from sympy.printing.pycode import pycode
from sympy.parsing.sympy_parser import parse_expr, standard_transformations
from typing import Any, Dict, Optional, Tuple
from fastmcp import FastMCP
from data_memory import data_memory

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


def _load_dataset(args: Dict[str, Any], meta: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
    address = args.get("data_address") or meta.get("data_address")
    if not address:
        return None, None
    return data_memory.get(address), address


def _resolve_series(name: str, args: Dict[str, Any], meta: Dict[str, Any], dataset: Optional[Any]) -> Tuple[Optional[list], Optional[str]]:
    direct = _as_list(args.get(name)) or _as_list(meta.get(name))
    if direct:
        return direct, None

    address = args.get(f"{name}_address") or meta.get(f"{name}_address")
    column = args.get(f"{name}_column") or meta.get(f"{name}_column")
    if not column and name.endswith("_data"):
        alt = f"{name[:-5]}_column"
        column = args.get(alt) or meta.get(alt)

    if address:
        source = data_memory.get(address)
        if source is None:
            return None, f"{name}_address {address} not found"
        extracted = _extract_from_source(source, column)
        if extracted is None:
            if column:
                return None, f"column '{column}' not found for {name}"
            return None, f"{name}_address {address} does not contain compatible data"
        return extracted, None

    if column:
        if dataset is None:
            return None, f"data_address is required when specifying {name}_column"
        extracted = _extract_from_source(dataset, column)
        if extracted is None:
            return None, f"column '{column}' not found for {name}"
        return extracted, None

    return None, None

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
    dataset, dataset_address = _load_dataset(args, meta)
    if dataset_address and dataset is None:
        return _error(f"data_address {dataset_address} not found")

    x_data, err = _resolve_series("x_data", args, meta, dataset)
    if err:
        return _error(err)
    y_data, err = _resolve_series("y_data", args, meta, dataset)
    if err:
        return _error(err)
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
    dataset, dataset_address = _load_dataset(args, meta)
    if dataset_address and dataset is None:
        return _error(f"data_address {dataset_address} not found")

    x_data, err = _resolve_series("x_data", args, meta, dataset)
    if err:
        return _error(err)
    y_data, err = _resolve_series("y_data", args, meta, dataset)
    if err:
        return _error(err)
    z_data, err = _resolve_series("z_data", args, meta, dataset)
    if err:
        return _error(err)
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
    dataset, dataset_address = _load_dataset(args, meta)
    if dataset_address and dataset is None:
        return _error(f"data_address {dataset_address} not found")

    x_data, err = _resolve_series("x_data", args, meta, dataset)
    if err:
        return _error(err)
    model_func_str = args.get("model_func_str") or meta.get("model_func_str")
    params = _as_list(args.get("params") or meta.get("params"))

    if not x_data or not model_func_str or params is None:
        return _error("x_data, model_func_str and params are required")

    model_func = str_to_function_2d(model_func_str)
    predicted_y = model_func(params, np.array(x_data))

    result = _safe_opt_to_list(predicted_y)
    if result is None:
        return _error("model produced no predicted values")

    result_address = data_memory.store(result)
    return _success({
        "predicted_y_address": result_address,
        "predicted_y_count": len(result),
    })


@mcp.tool()
def generate_pred_values_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    dataset, dataset_address = _load_dataset(args, meta)
    if dataset_address and dataset is None:
        return _error(f"data_address {dataset_address} not found")

    x_data, err = _resolve_series("x_data", args, meta, dataset)
    if err:
        return _error(err)
    y_data, err = _resolve_series("y_data", args, meta, dataset)
    if err:
        return _error(err)
    model_func_str = args.get("model_func_str") or meta.get("model_func_str")
    params = _as_list(args.get("params") or meta.get("params"))

    if not x_data or not y_data or not model_func_str or params is None:
        return _error("x_data, y_data, model_func_str and params are required")

    model_func = str_to_function_3d(model_func_str, var_name="x,y")
    predicted_z = model_func(params, np.array(x_data), np.array(y_data))
    result = _safe_opt_to_list(predicted_z)
    if result is None:
        return _error("model produced no predicted values")

    result_address = data_memory.store(result)
    return _success({
        "predicted_z_address": result_address,
        "predicted_z_count": len(result),
    })

if __name__ == "__main__":
    mcp.run(transport="stdio")
