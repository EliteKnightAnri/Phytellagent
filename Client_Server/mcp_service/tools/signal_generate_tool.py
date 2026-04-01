import numpy as np
import matplotlib.pyplot as plt
from fastmcp import FastMCP
from my_packages.data_memory import data_memory
from my_packages.status import success, error, split_payload, load_dataset
from typing import Any, Dict, Optional, Tuple

mcp = FastMCP("Signal Generation Server")


def _persist_signal(x_axis: np.ndarray, signal: np.ndarray, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    存储生成的信号及其相关信息，并返回包含数据地址的响应字典。
    
    Args:
        x_axis: 信号的自变量数组
        signal: 信号的采样数组
        meta: 可选的元信息字典，将与信号一起存储

    Returns:
        一个字典，包含信号数据地址、x轴数据地址、完整数据集地址以及元信息

    """
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
    """
    将输入的信号对象解析为 x 轴和 y 轴的数值数组，支持多种输入格式。
    
    Args:
        signal_obj: 可以是包含信号数据的字典、一个 (x, y) 元组，或者直接是 y 轴数据的列表/数组

    Returns:
        一个元组 (x_axis, y_axis)，其中 x_axis 和 y_axis 都是 numpy 数组。如果输入中没有明确的 x 轴数据，将自动生成一个从 0 开始的等差数列作为 x 轴。
    
    Raises:
        ValueError: 如果输入格式不正确，或者缺少必要的信号数据，将抛出异常。
    
    """
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


def _resolve_signal_samples(args: Dict[str, Any], meta: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    """Materialize sample points and amplitudes according to the provided arguments."""
    source_address = args.get("source_address")
    source_data = None
    if source_address:
        source_data = data_memory.get(source_address)
        if source_data is None:
            raise ValueError("无法根据 source_address 读取信号。")
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
                raise ValueError("未提供可采样的 source_address 或 values。")

        base_x, base_signal = _extract_axis(source_data)

        sampling_start = args.get("sampling_start")
        sampling_period = args.get("sampling_period")
        sampling_end = args.get("sampling_end")
        num_samples = args.get("num_samples")

        try:
            sampling_start = float(sampling_start) if sampling_start is not None else float(base_x[0])
            if sampling_period is None:
                if base_x.size < 2:
                    raise ValueError("请提供采样周期，或确保原信号至少有两个采样点。")
                sampling_period = float(np.median(np.diff(base_x)))
            else:
                sampling_period = float(sampling_period)

            sampling_end = float(sampling_end) if sampling_end is not None else float(base_x[-1])
            if num_samples is not None:
                num_samples = int(num_samples)
        except (TypeError, ValueError):
            raise ValueError("采样参数必须是数值。") from None

        if sampling_period <= 0:
            raise ValueError("采样周期必须为正。")
        if sampling_end < sampling_start and num_samples is None:
            raise ValueError("采样结束点需要大于或等于采样起始点。")

        if num_samples is not None:
            if num_samples <= 0:
                raise ValueError("采样点数量必须为正整数。")
            sample_points = sampling_start + sampling_period * np.arange(num_samples)
        else:
            span = sampling_end - sampling_start
            steps = int(np.floor(span / sampling_period)) + 1
            if steps <= 0:
                raise ValueError("给定的采样范围内没有有效的采样点。")
            sample_points = sampling_start + sampling_period * np.arange(steps)

        sampled_signal = _nearest_resample(base_x, base_signal, sample_points)
        return sample_points, sampled_signal

    values = args.get("values", [0.0, 1.0])
    try:
        sampled_signal = np.asarray(values, dtype=float)
        x_start = float(args.get("x_start", 0.0))
        x_end = float(args.get("x_end", x_start + sampled_signal.size - 1))
    except (TypeError, ValueError):
        raise ValueError("values、x_start 与 x_end 必须为数值。") from None

    if sampled_signal.size == 0:
        raise ValueError("values 至少需要包含一个元素。")

    sample_points = np.linspace(x_start, x_end, sampled_signal.size)
    return sample_points, sampled_signal


@mcp.tool()
def generate_square_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    生成一个方波信号

    Args:
        payload: 包含生成参数的字典，可能包含以下键：
            - frequency: 方波的频率（Hz），默认为 1.0
            - positive_ratio: 方波高电平占周期的比例，范围 (0, 1)，默认为 0.5
            - positive_amplitude: 方波高电平的幅值，默认为 1.0
            - negative_amplitude: 方波低电平的幅值，默认为 0.0
            - x_start: 信号自变量的起始值，默认为 0.0
            - x_end: 信号自变量的结束值，默认为 1.0
            - sampling_step: 采样步长，如果未提供将自动计算以确保信号质量

    Returns:
        一个字典，包含生成的方波信号的数据地址和相关元信息。如果参数无效，将返回一个错误状态字典。

    """
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
        return error("频率必须为正数。")
    if not 0 < positive_ratio < 1:
        return error("占空比需要在 0 与 1 之间。")
    if x_end <= x_start:
        return error("x_end 需要大于 x_start。")

    positive_length = positive_ratio / frequency
    negative_length = (1 - positive_ratio) / frequency
    base_step = min(positive_length, negative_length) / 10.0 # 每个高低电平至少采样10点
    if base_step <= 0: # 退化周期时兜底为默认步长
        base_step = 1.0 / (frequency * 10.0)
    sampling_step = base_step if sampling_step is None else sampling_step
    if sampling_step <= 0:
        return error("采样步长必须为正。")

    x = np.arange(x_start, x_end, sampling_step)
    if x.size == 0:
        x = np.array([x_start])
    period = positive_length + negative_length # 周期
    raw_square = np.where((x % period) < positive_length, 1.0, 0.0) # 生成基本的方波形状，其中高电平为1，低电平为0
    signal = np.where(raw_square > 0.5, positive_amplitude, negative_amplitude) # 根据占空比调整高低电平的幅值

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
def generate_sine_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    生成一个正弦波信号

    Args:
        payload: 包含生成参数的字典，可能包含以下键：
            - frequency: 正弦波的频率（Hz），默认为 1.0
            - amplitude: 正弦波的幅值，默认为 1.0
            - phase: 正弦波的相位（弧度），默认为 0.0
            - x_start: 信号自变量的起始值，默认为 0.0
            - x_end: 信号自变量的结束值，默认为 1.0
            - sampling_step: 采样步长，如果未提供将自动计算以确保信号质量

    Returns:
        一个字典，包含生成的正弦波信号的数据地址和相关元信息。如果参数无效，将返回一个错误状态字典。

    """
    args, meta = split_payload(payload)
    try:
        frequency = float(args.get("frequency", 1.0))
        amplitude = float(args.get("amplitude", 1.0))
        phase = float(args.get("phase", 0.0))
        x_start = float(args.get("x_start", 0.0))
        x_end = float(args.get("x_end", 1.0))
        sampling_step = args.get("sampling_step")
        if sampling_step is not None:
            sampling_step = float(sampling_step)
    except (TypeError, ValueError):
        return error("正弦波参数必须是数值。")

    if frequency <= 0:
        return error("频率必须为正数。")
    if x_end <= x_start:
        return error("x_end 需要大于 x_start。")

    base_step = 1.0 / (frequency * 20.0) # 每个周期至少采样20点
    if base_step <= 0: # 退化周期时兜底为默认步长
        base_step = 1.0 / (frequency * 20.0)
    sampling_step = base_step if sampling_step is None else sampling_step
    if sampling_step <= 0:
        return error("采样步长必须为正。")

    x = np.arange(x_start, x_end, sampling_step)
    if x.size == 0:
        x = np.array([x_start])
    signal = amplitude * np.sin(2 * np.pi * frequency * x + phase)

    meta_info = {
        "type": "sine",
        "frequency": frequency,
        "amplitude": amplitude,
        "phase": phase,
        "sampling_step": sampling_step,
        "x_range": [x_start, x_end],
    }

    response = _persist_signal(x, signal, meta_info)
    return success(response)


@mcp.tool()
def generate_discrete_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    生成离散的脉冲信号，可以基于提供的原始信号进行采样，或者直接使用传入的数值列表。

    Args:
        payload: 包含生成参数的字典，可能包含以下键：
            - source_address: 可选的原始信号数据地址，用于从数据内存加载信号进行采样
            - values: 可选的数值列表，直接作为信号幅值使用
            - x_start: 信号自变量的起始值，默认为 0.0（仅当 values 提供时有效）
            - x_end: 信号自变量的结束值，默认为 x_start + len(values) - 1（仅当 values 提供时有效）
            - sampling_period: 采样周期，如果提供将基于原始信号进行等间隔采样
            - sampling_start: 采样起始点，如果提供将覆盖原始信号的起始位置
            - sampling_end: 采样结束点，如果提供将覆盖原始信号的结束位置
            - num_samples: 采样点数量，如果提供将覆盖基于采样周期计算的点数

    Returns: 
        一个字典，包含生成的离散信号的数据地址和相关元信息。如果参数无效，将返回一个错误状态字典。
    """
    args, meta = split_payload(payload)
    source_address = args.get("source_address")
    source_data = None
    if source_address: # 优先从数据内存加载信号
        source_data = data_memory.get(source_address)
        if source_data is None:
            return error("无法根据 source_address 读取信号。")
    else: # 尝试从载荷中加载数据集，兼容非信号处理工具传入的参数
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
                    return error("请提供采样周期，或确保原信号至少有两个采样点。")
                sampling_period = float(np.median(np.diff(base_x)))
            else:
                sampling_period = float(sampling_period)

            sampling_end = float(sampling_end) if sampling_end is not None else float(base_x[-1])
            if num_samples is not None:
                num_samples = int(num_samples)
        except (TypeError, ValueError):
            return error("采样参数必须是数值。")

        if sampling_period <= 0:
            return error("采样周期必须为正。")
        if sampling_end < sampling_start and num_samples is None:
            return error("采样结束点需要大于或等于采样起始点。")

        if num_samples is not None:
            if num_samples <= 0:
                return error("采样点数量必须为正整数。")
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


@mcp.tool()
def draw_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    生成一个可视化的信号图像，基于提供的原始信号进行采样，或者直接使用传入的数值列表。

    Args:
        payload: 包含生成参数的字典，可能包含以下键：
            - source_address: 可选的原始信号数据地址，用于从数据内存加载信号进行采样
            - values: 可选的数值列表，直接作为信号幅值使用
            - x_start: 信号自变量的起始值，默认为 0.0（仅当 values 提供时有效）
            - x_end: 信号自变量的结束值，默认为 x_start + len(values) - 1（仅当 values 提供时有效）
            - sampling_period: 采样周期，如果提供将基于原始信号进行等间隔采样
            - sampling_start: 采样起始点，如果提供将覆盖原始信号的起始位置
            - sampling_end: 采样结束点，如果提供将覆盖原始信号的结束位置
            - num_samples: 采样点数量，如果提供将覆盖基于采样周期计算的点数
            - figsize: 图像尺寸，默认为 (6, 4)
            - title: 图像标题，默认为 "Signal Visualization"
            - x_label: x 轴标签，默认为 "X-axis"
            - y_label: y 轴标签，默认为 "Y-axis"
            - file_path: 图像保存路径，默认为 "temp_signal_plot.png"
    
    Returns:
        一个字典，包含生成的信号图像的数据地址和相关元信息。如果参数无效，将返回一个错误状态字典。

    """
    args, meta = split_payload(payload)
    try:
        sample_points, sampled_signal = _resolve_signal_samples(args, meta)
    except ValueError as exc:
        return error(str(exc))
    
    figsize = args.get("figsize", (6, 4))
    title = args.get("title", "Signal Visualization")
    x_label = args.get("x_label", "X-axis")
    y_label = args.get("y_label", "Y-axis")
    file_path = args.get("file_path", "temp_signal_plot.png")
    plt.figure(figsize=figsize)
    plt.plot(sample_points, sampled_signal, marker="o")
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True)
    
    plt.savefig(file_path)
    plt.close()
    return success(file_path)


@mcp.tool()
def draw_discrete_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """使用离散脉冲的表现方式绘制信号，适合可视化采样点。"""
    args, meta = split_payload(payload)
    try:
        sample_points, sampled_signal = _resolve_signal_samples(args, meta)
    except ValueError as exc:
        return error(str(exc))

    figsize = args.get("figsize", (6, 4))
    title = args.get("title", "Discrete Signal")
    x_label = args.get("x_label", "Sample Index")
    y_label = args.get("y_label", "Amplitude")
    file_path = args.get("file_path", "temp_discrete_signal_plot.png")
    linefmt = args.get("linefmt", "C0-")
    markerfmt = args.get("markerfmt", "C0o")
    basefmt = args.get("basefmt", "k-")

    fig, ax = plt.subplots(figsize=figsize)
    try:
        ax.stem(
            sample_points,
            sampled_signal,
            linefmt=linefmt,
            markerfmt=markerfmt,
            basefmt=basefmt,
            use_line_collection=True,
        )
    except TypeError:
        # Matplotlib < 3.3 does not accept use_line_collection; fall back gracefully.
        ax.stem(sample_points, sampled_signal, linefmt=linefmt, markerfmt=markerfmt, basefmt=basefmt)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(file_path)
    plt.close(fig)
    return success(file_path)


@mcp.tool()
def generate_sound_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """生成一个可播放的声音信号文件，基于提供的原始信号进行采样，或者直接使用传入的数值列表。"""
    args, meta = split_payload(payload)
    try:
        sample_points, sampled_signal = _resolve_signal_samples(args, meta)
    except ValueError as exc:
        return error(str(exc))

    sample_rate = args.get("sample_rate", 44100)
    file_path = args.get("file_path", "temp_sound_signal.wav")
    try:
        from scipy.io import wavfile
        wavfile.write(file_path, int(sample_rate), sampled_signal.astype(np.float32))
        return success(file_path)
    except ImportError:
        return error("需要安装 scipy 库以生成声音文件。")


if __name__ == "__main__":
    mcp.run(transport="stdio")