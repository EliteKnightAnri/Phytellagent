"""Shared DeepSeek tool schemas for MCP bridge."""
from copy import deepcopy

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_videos",
            "description": "Search Bilibili for videos that match the provided keyword and return raw API results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Chinese or English search keyword to query on Bilibili."
                    }
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Inspect the current server's OS, CPU count, memory, disk size, hostname, and Python version.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Optional field to fetch only one metric (cpu_count, memory_total_gb, disk_total_gb, etc.)."
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_environment_variables",
            "description": "Return the full environment variable dictionary for the current server.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "disk_usage",
            "description": "Report total/used/free disk space for an absolute path (defaults to root).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Optional absolute path whose disk usage should be inspected."
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_query",
            "description": "Execute a SQL query against the configured MySQL instance and stream the raw rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL statement to run. Use SELECT for read-only access."
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_csv",
            "description": "Load a CSV file with pandas on the server and return a memory address with a preview plus schema info. The file must be accessible on the server's filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the CSV file."},
                    "sep": {"type": "string", "description": "Column separator, default ','."},
                    "encoding": {"type": "string", "description": "File encoding, default utf-8."},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_excel",
            "description": "Load an Excel file with pandas on the server and return a memory address with a preview plus schema info. The file must be accessible on the server's filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to the Excel file."},
                    "sheet_name": {"type": ["string", "integer"], "description": "Sheet name or index to load, default 0."},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function":{
            "name": "least_square_fit_2d",
            "description": "Perform least squares fitting for 2D data points (x, y) based on a provided model function string and return the optimized parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address that contains a DataFrame with x and y columns or arrays."},
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data points."},
                    "x_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as x-data."},
                    "y_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as y-data."},
                    "x_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for x-data."},
                    "y_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for y-data."},
                    "model_func_str": {"type": "string", "description": "A string representation of the model function to fit, e.g. 'a*x + b'."},
                    "initial_params": {"type": "array", "items": {"type": "number"}, "description": "Optional initial parameter estimates for the optimization."}
                },
                "required": ["model_func_str"],
            },
        },
    },
    {
        "type": "function",
        "function":{
            "name": "least_square_fit_3d",
            "description": "Perform least squares fitting for 3D data points (x, y, z) based on a provided model function string and return the optimized parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address that contains a DataFrame with x, y, z columns or arrays."},
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points supplied directly."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data points supplied directly."},
                    "z_data": {"type": "array", "items": {"type": "number"}, "description": "Z-axis data points supplied directly."},
                    "x_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as x-data."},
                    "y_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as y-data."},
                    "z_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as z-data."},
                    "x_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for x-data."},
                    "y_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for y-data."},
                    "z_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for z-data."},
                    "model_func_str": {"type": "string", "description": "A string representation of the model function to fit, e.g. 'a*x + b*y + c'."},
                    "initial_params": {"type": "array", "items": {"type": "number"}, "description": "Optional initial parameter estimates for the optimization."}
                },
                "required": ["model_func_str"],
            },
        },
    },
    {
        "type": "function",
        "function":{
            "name": "generate_pred_values_2d",
            "description": "Generate predicted values for 2D data points based on a fitted model and return a reusable memory address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address that contains a DataFrame with x column or an array."},
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points."},
                    "x_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as x-data."},
                    "x_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for x-data."},
                    "model_func_str": {"type": "string", "description": "A string representation of the model function to fit, e.g. 'a*x + b'."},
                    "params": {"type": "array", "items": {"type": "number"}, "description": "Optimized parameters for the model."}
                },
                "required": ["model_func_str", "params"],
            },
        },
    },
    {
        "type": "function",
        "function":{
            "name": "generate_pred_values_3d",
            "description": "Generate predicted values for 3D data points based on a fitted model and return a reusable memory address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address that contains a DataFrame with x, y columns or arrays."},
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data points."},
                    "x_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as x-data."},
                    "y_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as y-data."},
                    "x_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for x-data."},
                    "y_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for y-data."},
                    "model_func_str": {"type": "string", "description": "A string representation of the model function to fit, e.g. 'a*x + b*y + c'."},
                    "params": {"type": "array", "items": {"type": "number"}, "description": "Optimized parameters for the model."}
                },
                "required": ["model_func_str", "params"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plot_in_2d",
            "description": "Create a 2D line plot from either raw arrays or a pandas memory address and return the saved image path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address that contains a DataFrame or arrays."},
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points supplied directly."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data points supplied directly."},
                    "x_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as x-data."},
                    "y_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as y-data."},
                    "x_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for x-data."},
                    "y_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for y-data."},
                    "title": {"type": "string", "description": "Title of the plot."},
                    "x_label": {"type": "string", "description": "Label for the X-axis. Never use Chinese characters to avoid font issues."},
                    "y_label": {"type": "string", "description": "Label for the Y-axis. Never use Chinese characters to avoid font issues."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plot_in_3d",
            "description": "Create a 3D scatter plot from either raw arrays or a pandas memory address and return the saved image path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address that contains a DataFrame or arrays."},
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points supplied directly."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data points supplied directly."},
                    "z_data": {"type": "array", "items": {"type": "number"}, "description": "Z-axis data points supplied directly."},
                    "x_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as x-data."},
                    "y_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as y-data."},
                    "z_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as z-data."},
                    "x_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for x-data."},
                    "y_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for y-data."},
                    "z_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for z-data."},
                    "title": {"type": "string", "description": "Title of the plot."},
                    "x_label": {"type": "string", "description": "Label for the X-axis. Never use Chinese characters to avoid font issues."},
                    "y_label": {"type": "string", "description": "Label for the Y-axis. Never use Chinese characters to avoid font issues."},
                    "z_label": {"type": "string", "description": "Label for the Z-axis. Never use Chinese characters to avoid font issues."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "double_plot_2d",
            "description": "Create a 2D line plot with two datasets provided either directly or via a pandas memory address, and return the saved image path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address returned by import_csv/import_excel that contains a DataFrame."},
                    "x1_data": {"type": "array", "items": {"type": "number"}, "description": "First series X data supplied directly."},
                    "y1_data": {"type": "array", "items": {"type": "number"}, "description": "First series Y data supplied directly."},
                    "x2_data": {"type": "array", "items": {"type": "number"}, "description": "Second series X data supplied directly."},
                    "y2_data": {"type": "array", "items": {"type": "number"}, "description": "Second series Y data supplied directly."},
                    "x1_data_address": {"type": "string", "description": "Memory address of a preprocessed array for x1."},
                    "y1_data_address": {"type": "string", "description": "Memory address of a preprocessed array for y1."},
                    "x2_data_address": {"type": "string", "description": "Memory address of a preprocessed array for x2."},
                    "y2_data_address": {"type": "string", "description": "Memory address of a preprocessed array for y2."},
                    "x1_data_column": {"type": "string", "description": "Column name in the referenced DataFrame for x1."},
                    "y1_data_column": {"type": "string", "description": "Column name in the referenced DataFrame for y1."},
                    "x2_data_column": {"type": "string", "description": "Column name in the referenced DataFrame for x2 (defaults to 'x' when only x2_data_address is provided)."},
                    "y2_data_column": {"type": "string", "description": "Column name in the referenced DataFrame for y2 (defaults to 'y' when only y2_data_address is provided)."},
                    "title": {"type": "string", "description": "Title of the plot."},
                    "x_label": {"type": "string", "description": "Label for the X-axis. Never use Chinese characters to avoid font issues."},
                    "y_label": {"type": "string", "description": "Label for the Y-axis. Never use Chinese characters to avoid font issues."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."}
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "double_plot_3d",
            "description": "Create a 3D scatter plot with two datasets provided either directly or via a pandas memory address, and return the saved image path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address returned by import_csv/import_excel that contains a DataFrame."},
                    "x1_data": {"type": "array", "items": {"type": "number"}, "description": "First series X data supplied directly."},
                    "y1_data": {"type": "array", "items": {"type": "number"}, "description": "First series Y data supplied directly."},
                    "z1_data": {"type": "array", "items": {"type": "number"}, "description": "First series Z data supplied directly."},
                    "x2_data": {"type": "array", "items": {"type": "number"}, "description": "Second series X data supplied directly."},
                    "y2_data": {"type": "array", "items": {"type": "number"}, "description": "Second series Y data supplied directly."},
                    "z2_data": {"type": "array", "items": {"type": "number"}, "description": "Second series Z data supplied directly."},
                    "x1_data_address": {"type": "string", "description": "Memory address of a preprocessed array for x1."},
                    "y1_data_address": {"type": "string", "description": "Memory address of a preprocessed array for y1."},
                    "z1_data_address": {"type": "string", "description": "Memory address of a preprocessed array for z1."},
                    "x2_data_address": {"type": "string", "description": "Memory address of a preprocessed array for x2."},
                    "y2_data_address": {"type": "string", "description": "Memory address of a preprocessed array for y2."},
                    "z2_data_address": {"type": "string", "description": "Memory address of a preprocessed array for z2."},
                    "x1_data_column": {"type": "string", "description": "Column name in the referenced DataFrame for x1."},
                    "y1_data_column": {"type": "string", "description": "Column name in the referenced DataFrame for y1."},
                    "z1_data_column": {"type": "string", "description": "Column name in the referenced DataFrame for z1."},
                    "x2_data_column": {"type": "string", "description": "Column name in the referenced DataFrame for x2 (defaults to 'x' when only x2_data_address is provided)."},
                    "y2_data_column": {"type": "string", "description": "Column name in the referenced DataFrame for y2 (defaults to 'y' when only y2_data_address is provided)."},
                    "z2_data_column": {"type": "string", "description": "Column name in the referenced DataFrame for z2 (defaults to 'z' when only z2_data_address is provided)."},
                    "title": {"type": "string", "description": "Title of the plot."},
                    "x_label": {"type": "string", "description": "Label for the X-axis. Never use Chinese characters to avoid font issues."},
                    "y_label": {"type": "string", "description": "Label for the Y-axis. Never use Chinese characters to avoid font issues."},
                    "z_label": {"type": "string", "description": "Label for the Z-axis. Never use Chinese characters to avoid font issues."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."}
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "euler_diff_solver",
            "description": "Solve a first-order ordinary differential equation using Euler's method based on a provided function string and initial conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "diff_equation": {"type": "string", "description": "A string representation of the differential equation, e.g. 'dy/dx = a*x + b*y'."},
                    "x0": {"type": "number", "description": "Initial value of the independent variable x, default 0."},
                    "y0": {"type": "number", "description": "Initial value of the dependent variable y, default 1."},
                    "x_end": {"type": "number", "description": "End value of x for the solution, default 10."},
                    "step": {"type": "number", "description": "Step size for Euler's method, default 0.1."}
                },
                "required": ["diff_equation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trapezoidal_diff_solver",
            "description": "Solve a first-order ordinary differential equation using the trapezoidal method based on a provided function string and initial conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "diff_equation": {"type": "string", "description": "A string representation of the differential equation, e.g. 'dy/dx = a*x + b*y'."},
                    "x0": {"type": "number", "description": "Initial value of the independent variable x, default 0."},
                    "y0": {"type": "number", "description": "Initial value of the dependent variable y, default 1."},
                    "x_end": {"type": "number", "description": "End value of x for the solution, default 10."},
                    "step": {"type": "number", "description": "Step size for the trapezoidal method, default 0.1."},
                    "eps": {"type": "number", "description": "Convergence threshold for iterative solution, default 1e-6."}
                },
                "required": ["diff_equation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fourier_transform",
            "description": "Compute the Fourier transform of a 1D signal with optional parameters for normalization, windowing, and frequency axis calculation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "signal": {"type": "array", "items": {"type": "number"}, "description": "Input 1D signal data."},
                    "sample_rate": {"type": "number", "description": "Sampling rate of the signal for accurate frequency axis calculation."},
                    "window": {"type": ["string", "array"], "description": "Optional window type (e.g. 'hann', 'hamming') or custom window array to apply to the signal."},
                    "normalize": {"type": "boolean", "description": "Whether to normalize the Fourier transform by the signal length, default false."}
                },
                "required": ["signal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inverse_fourier_transform",
            "description": "Compute the inverse Fourier transform of a spectrum with optional parameters for normalization and windowing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "real": {"type": "array", "items": {"type": "number"}, "description": "Real part of the input spectrum."},
                    "imag": {"type": "array", "items": {"type": "number"}, "description": "Imaginary part of the input spectrum."},
                    "normalize": {"type": "boolean", "description": "Whether to normalize the inverse transform by the signal length, default false."},
                },
                "required": ["real", "imag"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "power_spectrum",
            "description": "Compute the power spectrum of a 1D signal with optional parameters for windowing and frequency axis calculation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "signal": {"type": "array", "items": {"type": "number"}, "description": "Input 1D signal data."},
                    "sample_rate": {"type": "number", "description": "Sampling rate of the signal for accurate frequency axis calculation."},
                    "window": {"type": ["string", "array"], "description": "Optional window type (e.g. 'hann', 'hamming') or custom window array to apply to the signal."},
                    "only_positive": {"type": "boolean", "description": "Whether to return only positive frequencies, default true."}
                },
                "required": ["signal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "short_time_fourier_transform",
            "description": "Compute the short-time Fourier transform (STFT) of a 1D signal with parameters for window size, hop length, and windowing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "signal": {"type": "array", "items": {"type": "number"}, "description": "Input 1D signal data."},
                    "window_size": {"type": "integer", "description": "Size of the window to use for each STFT frame, default 256."},
                    "hop_length": {"type": "integer", "description": "Hop length between successive STFT frames, default window_size // 4 or 1."},
                    "window": {"type": ["string", "array"], "description": "Optional window type (e.g. 'hann', 'hamming') or custom window array to apply to each STFT frame."},
                    "sample_rate": {"type": "number", "description": "Sampling rate of the signal for accurate frequency axis calculation."}
                },
                "required": ["signal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_peaks",
            "description": "Detect peaks using the find_peaks algorithm with parameters for height and distance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address that contains a DataFrame or arrays."},
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points supplied directly."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data points supplied directly."},
                    "x_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as x-data."},
                    "y_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as y-data."},
                    "x_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for x-data."},
                    "y_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for y-data."},
                    "height": {"type": "number", "description": "Minimum height of the peaks."},
                    "distance": {"type": "integer", "description": "Minimum distance between peaks."}
                },
                "required": ["data_address", "height", "distance"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_valleys",
            "description": "Detect valleys using the find_peaks algorithm with parameters for height and distance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address that contains a DataFrame or arrays."},
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points supplied directly."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data points supplied directly."},
                    "x_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as x-data."},
                    "y_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as y-data."},
                    "x_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for x-data."},
                    "y_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for y-data."},
                    "height": {"type": "number", "description": "Maximum height of the valleys."},
                    "distance": {"type": "integer", "description": "Maximum distance between valleys."}
                },
               "required": ["data_address", "height", "distance"],
            },
        },
    },
]


def get_tool_schemas():
    """Return a deep copy so callers can mutate safely."""
    return deepcopy(TOOL_SCHEMAS)
