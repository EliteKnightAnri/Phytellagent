import numpy as np
from fastmcp import FastMCP
from typing import Any, Dict, Optional, Tuple

mcp = FastMCP("Fourier Transform Server")


def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}


def _ensure_1d_numeric(data: Any, field_name: str) -> np.ndarray:
    if data is None:
        raise ValueError(f"Missing '{field_name}' in arguments.")
    arr = np.asarray(data, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"'{field_name}' must be a 1D sequence.")
    if arr.size == 0:
        raise ValueError(f"'{field_name}' cannot be empty.")
    return arr


def _build_complex(real: Any, imag: Any) -> np.ndarray:
    if real is None or imag is None:
        raise ValueError("Both 'real' and 'imag' must be provided.")
    real_arr = np.asarray(real, dtype=float)
    imag_arr = np.asarray(imag, dtype=float)
    if real_arr.shape != imag_arr.shape:
        raise ValueError("'real' and 'imag' must have the same length.")
    if real_arr.ndim != 1:
        raise ValueError("'real' and 'imag' must be 1D sequences.")
    return real_arr + 1j * imag_arr


def _serialize_complex(arr: np.ndarray) -> Dict[str, Any]:
    return {"real": arr.real.tolist(), "imag": arr.imag.tolist()}


def _frequency_axis(length: int, sample_rate: Optional[float]) -> Optional[np.ndarray]:
    if sample_rate is None:
        return None
    sr = float(sample_rate)
    if sr <= 0:
        raise ValueError("'sample_rate' must be positive if provided.")
    return np.fft.fftfreq(length, d=1.0 / sr)


def _window_array(window: Optional[Any], size: int) -> np.ndarray:
    if window is None or str(window).lower() in {"rect", "rectangular", "boxcar"}:
        return np.ones(size)
    if isinstance(window, (list, tuple)):
        win = np.asarray(window, dtype=float)
        if win.size != size:
            raise ValueError("Custom window length must match data length.")
        return win

    name = str(window).lower()
    if name == "hann":
        return np.hanning(size)
    if name == "hamming":
        return np.hamming(size)
    if name == "blackman":
        return np.blackman(size)
    if name == "bartlett":
        return np.bartlett(size)
    raise ValueError(f"Unsupported window '{window}'.")


def _success(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "data": data}


@mcp.tool()
def fourier_transform(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, _ = _split_payload(payload)
    sample_rate = args.get("sample_rate")
    normalize = bool(args.get("normalize", False))
    window = args.get("window")

    try:
        signal = _ensure_1d_numeric(args.get("signal"), "signal")
        win = _window_array(window, signal.size)
        windowed = signal * win
        spectrum = np.fft.fft(windowed)
        if normalize:
            spectrum /= signal.size

        freq_axis = _frequency_axis(signal.size, sample_rate)
        payload = {
            "length": int(signal.size),
            "complex": _serialize_complex(spectrum),
            "magnitude": np.abs(spectrum).tolist(),
            "phase": np.angle(spectrum).tolist(),
        }
        if freq_axis is not None:
            payload["frequencies"] = freq_axis.tolist()
        payload["window"] = window or "rect"
        payload["normalized"] = normalize
        return _success(payload)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@mcp.tool()
def inverse_fourier_transform(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, _ = _split_payload(payload)
    normalize = bool(args.get("normalize", False))

    try:
        spectrum = _build_complex(args.get("real"), args.get("imag"))
        signal = np.fft.ifft(spectrum)
        if normalize:
            signal /= spectrum.size

        reconstructed = np.real_if_close(signal, tol=1e5)
        signal_real = reconstructed.real.tolist()
        signal_imag = reconstructed.imag.tolist() if np.iscomplexobj(reconstructed) else [0.0] * signal.size
        response = {
            "complex": _serialize_complex(signal),
            "signal_real": signal_real,
            "signal_imag": signal_imag,
        }
        response["length"] = int(signal.size)
        response["normalized"] = normalize
        return _success(response)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@mcp.tool()
def power_spectrum(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, _ = _split_payload(payload)
    sample_rate = args.get("sample_rate")
    window = args.get("window")
    only_positive = bool(args.get("only_positive", True))

    try:
        signal = _ensure_1d_numeric(args.get("signal"), "signal")
        win = _window_array(window, signal.size)
        windowed = signal * win
        spectrum = np.fft.fft(windowed)
        n = windowed.size
        power = (np.abs(spectrum) ** 2) / n
        freqs = _frequency_axis(n, sample_rate)
        if freqs is None:
            freqs = np.fft.fftfreq(n)

        if only_positive:
            mask = freqs >= 0
            freqs = freqs[mask]
            power = power[mask]

        payload = {
            "power": power.tolist(),
            "frequencies": freqs.tolist(),
            "length": int(n),
            "window": window or "rect",
        }
        if sample_rate is not None:
            payload["sample_rate"] = float(sample_rate)
        payload["only_positive"] = only_positive
        return _success(payload)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@mcp.tool()
def short_time_fourier_transform(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, _ = _split_payload(payload)
    sample_rate = args.get("sample_rate")
    window_size = int(args.get("window_size", 256))
    hop_length = int(args.get("hop_length", window_size // 4 or 1))
    window = args.get("window", "hann")

    try:
        signal = _ensure_1d_numeric(args.get("signal"), "signal")
        if window_size <= 0 or hop_length <= 0:
            raise ValueError("'window_size' and 'hop_length' must be positive integers.")
        if window_size > signal.size:
            raise ValueError("'window_size' cannot exceed signal length.")

        win = _window_array(window, window_size)
        frames = []
        indices = []
        for start in range(0, signal.size - window_size + 1, hop_length):
            frame = signal[start:start + window_size] * win
            frames.append(np.fft.fft(frame))
            indices.append(start)

        if not frames:
            raise ValueError("Signal is too short for the requested STFT parameters.")

        matrix = np.vstack(frames)
        freq_axis = _frequency_axis(window_size, sample_rate)
        if freq_axis is None:
            freq_axis = np.fft.fftfreq(window_size)

        payload = {
            "magnitude": np.abs(matrix).tolist(),
            "phase": np.angle(matrix).tolist(),
            "frequencies": freq_axis.tolist(),
            "frame_indices": indices,
            "window_size": window_size,
            "hop_length": hop_length,
            "window": window,
        }
        if sample_rate is not None:
            payload["sample_rate"] = float(sample_rate)
        return _success(payload)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


if __name__ == "__main__":
    mcp.run(transport="stdio")