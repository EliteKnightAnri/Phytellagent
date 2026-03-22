import numpy as np
from fastmcp import FastMCP
from my_packages.data_memory import data_memory
from my_packages.status import success, error, split_payload, load_dataset
from typing import Any, Dict, Optional, Tuple

mcp = FastMCP("Signal Generation Server")


def _persist_signal(x_axis: np.ndarray, signal: np.ndarray, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """存储生成的信号及其相关信息，并返回包含数据地址的响应字典。"""
    meta = meta or {}
    dataset = {"x": x_axis, "y": signal, "meta": meta}
    dataset_address = data_memory.store(dataset)
    signal_address = data_memory.store(signal)
    x_address = data_memory.store(x_axis)
    return {
        "data_address": signal_address,
        "x_address": x_address,
        "dataset_address": dataset_address,
        "meta": meta,
    }


def _extract_axis(signal_obj: Any) -> Tuple[np.ndarray, np.ndarray]:
    """Normalize different source signal formats into aligned x/y arrays."""
    if signal_obj is None:
        raise ValueError("未提供可用于采样的原始信号。")

    x_axis = None
    y_axis = None

    if isinstance(signal_obj, dict):
        for key in ("signal", "y", "values", "data"):
            if key in signal_obj:
                y_axis = signal_obj[key]
                break
        for key in ("x", "t", "time", "domain"):
            if key in signal_obj:
                x_axis = signal_obj[key]
                break
    elif isinstance(signal_obj, tuple) and len(signal_obj) == 2:
        x_axis, y_axis = signal_obj
    else:
        y_axis = signal_obj

    if y_axis is None:
        raise ValueError("原始信号中缺少幅值数据。")

    y_arr = np.asarray(y_axis, dtype=float)
    if y_arr.ndim == 0:
        y_arr = y_arr.reshape(1)

    if x_axis is None:
        x_arr = np.arange(y_arr.size, dtype=float)
    else:
        x_arr = np.asarray(x_axis, dtype=float)
        if x_arr.ndim == 0:
            x_arr = x_arr.reshape(1)

    if x_arr.shape[0] != y_arr.shape[0]:
        raise ValueError("原始信号的自变量与幅值数量不一致。")

    if x_arr.size < 1:
        raise ValueError("原始信号为空。")

    order = np.argsort(x_arr)
    x_arr = x_arr[order]
    y_arr = y_arr[order]

    if x_arr.size > 1:
        unique_mask = np.concatenate(([True], np.diff(x_arr) != 0.0))
        x_arr = x_arr[unique_mask]
        y_arr = y_arr[unique_mask]

    return x_arr, y_arr


def _nearest_resample(x_axis: np.ndarray, signal: np.ndarray, sample_points: np.ndarray) -> np.ndarray:
    """Sample signal using nearest-neighbour strategy to keep rectangular levels."""
    if x_axis.size == 0:
        raise ValueError("无法在空轴上执行采样。")
    indices = np.searchsorted(x_axis, sample_points, side="left")
    indices = np.clip(indices, 0, x_axis.size - 1)
    left_indices = np.clip(indices - 1, 0, x_axis.size - 1)
    right_indices = indices
    left_dist = np.abs(sample_points - x_axis[left_indices])
    right_dist = np.abs(x_axis[right_indices] - sample_points)
    use_left = left_dist <= right_dist
    chosen = np.where(use_left, left_indices, right_indices)
    return signal[chosen]


@mcp.tool()
def generate_square_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    try:
        frequency = float(args.get("frequency", 1.0))
        positive_ratio = float(args.get("positive_ratio", 0.5))
        positive_amplitude = float(args.get("positive_amplitude", 1.0))
        negative_amplitude = float(args.get("negative_amplitude", 0.0))
        x_start = float(args.get("x_start", 0.0))
        x_end = float(args.get("x_end", 1.0))
        sampling_step = args.get("sampling_step")
        if sampling_step is not None:
            sampling_step = float(sampling_step)
    except (TypeError, ValueError):
        return error("方波参数必须是数值。")

    if frequency <= 0:
        return error("frequency 必须为正数。")
    if not 0 < positive_ratio < 1:
        return error("positive_ratio 需要在 0 与 1 之间。")
    if x_end <= x_start:
        return error("x_end 需要大于 x_start。")

    positive_length = positive_ratio / frequency
    negative_length = (1 - positive_ratio) / frequency
    base_step = min(positive_length, negative_length) / 10.0
    if base_step <= 0:
        base_step = 1.0 / (frequency * 10.0)
    sampling_step = sampling_step or base_step
    if sampling_step <= 0:
        return error("sampling_step 必须为正。")

    x = np.arange(x_start, x_end, sampling_step)
    if x.size == 0:
        x = np.array([x_start])
    period = positive_length + negative_length
    raw_square = np.where((x % period) < positive_length, 1.0, 0.0)
    signal = np.where(raw_square > 0.5, positive_amplitude, negative_amplitude)

    meta_info = {
        "type": "square",
        "frequency": frequency,
        "positive_ratio": positive_ratio,
        "positive_amplitude": positive_amplitude,
        "negative_amplitude": negative_amplitude,
        "sampling_step": sampling_step,
        "x_range": [x_start, x_end],
    }

    response = _persist_signal(x, signal, meta_info)
    return success(response)


@mcp.tool()
def generate_discrete_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    source_address = args.get("source_address")
    source_data = None
    if source_address:
        source_data = data_memory.get(source_address)
        if source_data is None:
            return error("无法根据 source_address 读取信号。")
    else:
        loaded_data, loaded_address = load_dataset(args, meta)
        if loaded_address:
            source_address = loaded_address
            source_data = loaded_data

    sampling_keys = {"sampling_period", "sampling_start", "sampling_end", "num_samples"}
    wants_sampling = bool(source_data is not None) or any(key in args for key in sampling_keys)

    if wants_sampling:
        if source_data is None:
            source_data = args.get("values")
            if source_data is None:
                return error("未提供可采样的 source_address 或 values。")

        try:
            base_x, base_signal = _extract_axis(source_data)
        except ValueError as exc:
            return error(str(exc))

        sampling_start = args.get("sampling_start")
        sampling_period = args.get("sampling_period")
        sampling_end = args.get("sampling_end")
        num_samples = args.get("num_samples")

        try:
            sampling_start = float(sampling_start) if sampling_start is not None else float(base_x[0])
            if sampling_period is None:
                if base_x.size < 2:
                    return error("请提供 sampling_period，或确保原信号至少有两个采样点。")
                sampling_period = float(np.median(np.diff(base_x)))
            else:
                sampling_period = float(sampling_period)

            sampling_end = float(sampling_end) if sampling_end is not None else float(base_x[-1])
            if num_samples is not None:
                num_samples = int(num_samples)
        except (TypeError, ValueError):
            return error("采样参数必须是数值。")

        if sampling_period <= 0:
            return error("sampling_period 必须为正。")
        if sampling_end < sampling_start and num_samples is None:
            return error("sampling_end 需要大于或等于 sampling_start。")

        if num_samples is not None:
            if num_samples <= 0:
                return error("num_samples 必须为正整数。")
            sample_points = sampling_start + sampling_period * np.arange(num_samples)
        else:
            span = sampling_end - sampling_start
            steps = int(np.floor(span / sampling_period)) + 1
            if steps <= 0:
                return error("给定的采样范围内没有有效的采样点。")
            sample_points = sampling_start + sampling_period * np.arange(steps)

        sampled_signal = _nearest_resample(base_x, base_signal, sample_points)

        meta_info = {
            "mode": "external_sampling",
            "source_address": source_address,
            "sampling_start": sampling_start,
            "sampling_period": sampling_period,
            "num_samples": int(sample_points.size),
        }

        response = _persist_signal(sample_points, sampled_signal, meta_info)
        return success(response)

    values = args.get("values", [0.0, 1.0])
    try:
        signal = np.asarray(values, dtype=float)
        x_start = float(args.get("x_start", 0.0))
        x_end = float(args.get("x_end", x_start + signal.size - 1))
    except (TypeError, ValueError):
        return error("values、x_start 与 x_end 必须为数值。")

    if signal.size == 0:
        return error("values 至少需要包含一个元素。")

    x = np.linspace(x_start, x_end, signal.size)
    meta_info = {
        "mode": "manual_values",
        "num_points": int(signal.size),
    }
    response = _persist_signal(x, signal, meta_info)
    return success(response)