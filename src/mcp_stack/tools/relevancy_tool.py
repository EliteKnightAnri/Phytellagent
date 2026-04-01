import numpy as np
from fastmcp import FastMCP
from my_packages.data_memory import data_memory
from my_packages.status import split_payload, success, error, load_dataset
from my_packages import object_to_list
from typing import Any, Dict, Optional, Tuple, List

mcp = FastMCP("Relevancy Computation Server")


def _extract_from_source(source: Any, column: Optional[str]) -> Optional[list]:
    if source is None:
        return None
    if column is None:
        return object_to_list(source)

    if isinstance(source, dict):
        if column not in source:
            return None
        return object_to_list(source[column])

    if hasattr(source, "__getitem__"):
        try:
            selection = source[column]
        except Exception:
            return None
        return object_to_list(selection)

    return None

def _resolve_series(name: str, args: Dict[str, Any], meta: Dict[str, Any], dataset: Optional[Any]) -> Tuple[Optional[list], Optional[str]]:
    direct = object_to_list(args.get(name)) or object_to_list(meta.get(name))
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

@mcp.tool()
def compute_relevancy(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

    if x_data is None or y_data is None:
        return error("Both 'x_data' and 'y_data' data series are required")

    try:
        relevancy = np.corrcoef(x_data, y_data)[0, 1]
        return success({"relevancy": relevancy})
    except Exception as e:
        return error(f"Error computing relevancy: {str(e)}")
    

@mcp.tool()
def compute_variance(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    dataset, dataset_address = load_dataset(args, meta)
    if dataset_address and dataset is None:
        return error(f"data_address {dataset_address} not found")

    x_data, err = _resolve_series("x_data", args, meta, dataset)
    if err:
        return error(err)

    if x_data is None:
        return error("'x_data' data series is required")

    try:
        variance = np.var(x_data)
        return success({"variance": variance})
    except Exception as e:
        return error(f"Error computing variance: {str(e)}")