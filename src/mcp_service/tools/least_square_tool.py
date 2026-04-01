import numpy as np
import sympy as sp
from scipy.optimize import leastsq
from sympy.printing.pycode import pycode
from sympy.parsing.sympy_parser import parse_expr, standard_transformations
from typing import Any, Dict, Optional, Tuple
from fastmcp import FastMCP
from my_packages.status import split_payload, success, error, load_dataset
from my_packages.data_memory import data_memory
from my_packages.str2func import str2func_2d, str2func_3d

mcp = FastMCP("Least Square Method Server")


def _as_list(value: Optional[Any]) -> Optional[list]:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


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


@mcp.tool()
def least_square_fit_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    dataset, dataset_address = load_dataset(args, meta)
    if dataset_address and dataset is None:
        return error(f"data_address {dataset_address} not found")

    x_data, err = _resolve_series("x_data", args, meta, dataset)
    if err:
        return error(err)
    y_data, err = _resolve_series("y_data", args, meta, dataset)
    if err:
        return error(err)
    model_func_str = args.get("model_func_str") or meta.get("model_func_str")

    if not x_data or not y_data:
        return error("x_data and y_data are required")
    if not model_func_str:
        return error("model_func_str is required")

    model_func = str2func_2d(model_func_str)
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

    return success({
        "optimized_params": _safe_opt_to_list(optimized_params),
        "covariance": _safe_cov_to_serializable(covariance),
        "param_names": getattr(model_func, 'param_names', None),
    })


@mcp.tool()
def least_square_fit_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    dataset, dataset_address = load_dataset(args, meta)
    if dataset_address and dataset is None:
        return error(f"data_address {dataset_address} not found")

    x_data, err = _resolve_series("x_data", args, meta, dataset)
    if err:
        return error(err)
    y_data, err = _resolve_series("y_data", args, meta, dataset)
    if err:
        return error(err)
    z_data, err = _resolve_series("z_data", args, meta, dataset)
    if err:
        return error(err)
    model_func_str = args.get("model_func_str") or meta.get("model_func_str")

    if not x_data or not y_data or not z_data:
        return error("x_data, y_data and z_data are required")
    if not model_func_str:
        return error("model_func_str is required")

    model_func = str2func_3d(model_func_str, var_name="x,y")
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

    return success({
        "optimized_params": _safe_opt_to_list(optimized_params),
        "covariance": _safe_cov_to_serializable(covariance),
        "param_names": getattr(model_func, 'param_names', None),
    })


@mcp.tool()
def generate_pred_values_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    dataset, dataset_address = load_dataset(args, meta)
    if dataset_address and dataset is None:
        return error(f"data_address {dataset_address} not found")

    x_data, err = _resolve_series("x_data", args, meta, dataset)
    if err:
        return error(err)
    model_func_str = args.get("model_func_str") or meta.get("model_func_str")
    params = _as_list(args.get("params") or meta.get("params"))

    if not x_data or not model_func_str or params is None:
        return error("x_data, model_func_str and params are required")

    model_func = str2func_2d(model_func_str)
    predicted_y = model_func(params, np.array(x_data))

    result = _safe_opt_to_list(predicted_y)
    if result is None:
        return error("model produced no predicted values")

    result_address = data_memory.store(result)
    return success({
        "predicted_y_address": result_address,
        "predicted_y_count": len(result),
    })


@mcp.tool()
def generate_pred_values_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    dataset, dataset_address = load_dataset(args, meta)
    if dataset_address and dataset is None:
        return error(f"data_address {dataset_address} not found")

    x_data, err = _resolve_series("x_data", args, meta, dataset)
    if err:
        return error(err)
    y_data, err = _resolve_series("y_data", args, meta, dataset)
    if err:
        return error(err)
    model_func_str = args.get("model_func_str") or meta.get("model_func_str")
    params = _as_list(args.get("params") or meta.get("params"))

    if not x_data or not y_data or not model_func_str or params is None:
        return error("x_data, y_data, model_func_str and params are required")

    model_func = str2func_3d(model_func_str, var_name="x,y")
    predicted_z = model_func(params, np.array(x_data), np.array(y_data))
    result = _safe_opt_to_list(predicted_z)
    if result is None:
        return error("model produced no predicted values")

    result_address = data_memory.store(result)
    return success({
        "predicted_z_address": result_address,
        "predicted_z_count": len(result),
    })

if __name__ == "__main__":
    mcp.run(transport="stdio")
