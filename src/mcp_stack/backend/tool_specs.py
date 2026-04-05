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
            "name": "SQL_query",
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
                    "diff_equation": {"type": "string", "description": "A string representation of the right side of the differential equation, e.g. 'a*x + b*y'."},
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
                    "diff_equation": {"type": "string", "description": "A string representation of the right side of the differential equation, e.g. 'a*x + b*y'."},
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
    {
        "type": "function",
        "function": {
            "name": "generate_2d_points",
            "description": "Generate 2D points only, based on a provided function string and return them as arrays or a pandas memory address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function": {"type": "string", "description": "The function string to evaluate."},
                    "variable": {"type": "string", "description": "The variable name for the function."},
                    "x_range": {"type": "array", "items": {"type": "number"}, "description": "The range of x-values."},
                    "num_points": {"type": "integer", "description": "The number of points to generate."}
                },
                "required": ["function", "variable", "x_range", "num_points"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_3d_points",
            "description": "Generate 3D points only, based on a provided function string and return them as arrays or a pandas memory address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function": {"type": "string", "description": "The function string to evaluate."},
                    "variables": {"type": "string", "description": "The variable names for the function, separated by commas."},
                    "x_range": {"type": "array", "items": {"type": "number"}, "description": "The range of x-values."},
                    "y_range": {"type": "array", "items": {"type": "number"}, "description": "The range of y-values."},
                    "num_points": {"type": "integer", "description": "The number of points to generate along each axis."}
                },
                "required": ["function", "variables", "x_range", "y_range", "num_points"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plot_2d_function",
            "description": "Generate function points, plot a 2D function based on a provided function string, and return the saved image path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function": {"type": "string", "description": "The function string to evaluate."},
                    "variable": {"type": "string", "description": "The variable name for the function."},
                    "x_range": {"type": "array", "items": {"type": "number"}, "description": "The range of x-values."},
                    "num_points": {"type": "integer", "description": "The number of points to generate."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."}
                },
                "required": ["function", "variable", "x_range", "num_points", "file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plot_3d_function",
            "description": "Generate function points, plot a 3D function based on a provided function string, and return the saved image path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function": {"type": "string", "description": "The function string to evaluate."},
                    "variables": {"type": "string", "description": "The variable names for the function, separated by commas."},
                    "x_range": {"type": "array", "items": {"type": "number"}, "description": "The range of x-values."},
                    "y_range": {"type": "array", "items": {"type": "number"}, "description": "The range of y-values."},
                    "num_points": {"type": "integer", "description": "The number of points to generate along each axis."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."}
                },
                "required": ["function", "variables", "x_range", "y_range", "num_points", "file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compute_relevancy",
            "description": "Compute the relevancy score between two pieces of text using a specified method and return a score between 0 and 1.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address that contains a DataFrame or arrays."},
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "The x-values for the relevancy computation."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "The y-values for the relevancy computation."},
                    "x_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as x-data."},
                    "y_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as y-data."},
                    "x_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for x-data."},
                    "y_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for y-data."},
                },
                "required": ["data_address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compute_variance",
            "description": "Compute the variance of a dataset provided either directly as an array or via a pandas memory address, and return the variance value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_address": {"type": "string", "description": "Memory address that contains a DataFrame or arrays."},
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "The x-values for the variance computation."},
                    "x_data_address": {"type": "string", "description": "Memory address of a preprocessed array to use as x-data."},
                    "x_data_column": {"type": "string", "description": "Column name in the referenced DataFrame to use for x-data."}
                },
                "required": ["data_address"]
            }
        }
    },
    {
        "type": "function",
        "function":{
            "name": "generate_square_signal",
            "description": "Generate a square wave signal with specified parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "frequency": {"type": "number", "description": "The frequency of the square wave (Hz)."},
                    "positive_ratio": {"type": "number", "description": "The ratio of the positive phase to the total period."},
                    "positive_amplitude": {"type": "number", "description": "The amplitude of the positive phase."},
                    "negative_amplitude": {"type": "number", "description": "The amplitude of the negative phase."},
                    "x_start": {"type": "number", "description": "The starting value of the x-axis."},
                    "x_end": {"type": "number", "description": "The ending value of the x-axis."},
                    "sampling_step": {"type": "number", "description": "The step size for sampling the signal."}
                },
                "required": ["frequency", "positive_ratio", "positive_amplitude", "negative_amplitude", "x_start", "x_end", "sampling_step"]
            }
        }
    },
    {
        "type": "function",
        "function":{
            "name": "generate_sine_signal",
            "description": "Generate a sine wave signal with specified parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "frequency": {"type": "number", "description": "The frequency of the sine wave (Hz)."},
                    "amplitude": {"type": "number", "description": "The amplitude of the sine wave."},
                    "phase": {"type": "number", "description": "The phase shift of the sine wave (radians)."},
                    "x_start": {"type": "number", "description": "The starting value of the x-axis."},
                    "x_end": {"type": "number", "description": "The ending value of the x-axis."},
                    "sampling_step": {"type": "number", "description": "The step size for sampling the signal."}
                },
                "required": ["frequency", "amplitude", "x_start", "x_end", "sampling_step"]
            }
        }
    },
    {
        "type": "function",
        "function":{
            "name": "generate_discrete_signal",
            "description": "Generate a discrete signal with specified parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_address": {"type": "string", "description": "The memory address of the source data for the discrete signal."},
                    "values": {"type": "array", "items": {"type": "number"}, "description": "Optional array of values for the discrete signal. If not provided, it will be extracted from the source data."},
                    "x_start": {"type": "number", "description": "The starting value of the x-axis."},
                    "x_end": {"type": "number", "description": "The ending value of the x-axis."},
                    "sampling_period": {"type": "number", "description": "Optional sampling period for the discrete signal. If not provided, it will be calculated based on the source data."},
                    "sampling_start": {"type": "number", "description": "Optional starting point for sampling. If not provided, it will default to x_start."},
                    "sampling_end": {"type": "number", "description": "Optional ending point for sampling. If not provided, it will default to x_end."}
                },
                "required": ["source_address"] or ["values", "x_start", "x_end"]
            }
        }
    },
    {
        "type": "function",
        "function":{
            "name": "draw_signal",
            "description": "Draw a signal based on provided signal data, which can be supplied directly or via a memory address, and return the saved image path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_address": {"type": "string", "description": "The memory address of the source data for the signal."},
                    "values": {"type": "array", "items": {"type": "number"}, "description": "Optional array of values for the signal. If not provided, it will be generated based on the frequency and x-axis parameters."},
                    "x_start": {"type": "number", "description": "The starting value of the x-axis."},
                    "x_end": {"type": "number", "description": "The ending value of the x-axis."},
                    "sampling_period": {"type": "number", "description": "Optional sampling period for the signal. If not provided, it will be calculated based on the frequency."},
                    "sampling_start": {"type": "number", "description": "Optional starting point for sampling. If not provided, it will default to x_start."},
                    "sampling_end": {"type": "number", "description": "Optional ending point for sampling. If not provided, it will default to x_end."},
                    "figsize": {"type": "array", "items": {"type": "number"},"description": "Optional figure size for the plot, e.g. [6, 4]."},
                    "title": {"type": "string", "description": "Optional title for the plot."},
                    "x_label": {"type": "string", "description": "Optional label for the x-axis. Never use Chinese characters to avoid font issues."},
                    "y_label": {"type": "string", "description": "Optional label for the y-axis. Never use Chinese characters to avoid font issues."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."}
                },
                "required": ["source_address", "file_path"] or ["values", "x_start", "x_end", "file_path"]
            }
        }
    },
    {
        "type": "function",
        "function":{
            "name": "draw_discrete_signal",
            "description": "Render a discrete pulse/stem plot for a sampled signal and return the saved image path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_address": {"type": "string", "description": "Memory address of the source data for the signal."},
                    "data_address": {"type": "string", "description": "Optional dataset address understood by the signal generator."},
                    "values": {"type": "array", "items": {"type": "number"}, "description": "Optional array of amplitudes when no address is provided."},
                    "x_start": {"type": "number", "description": "Starting value of the x-axis when values are provided."},
                    "x_end": {"type": "number", "description": "Ending value of the x-axis when values are provided."},
                    "sampling_period": {"type": "number", "description": "Optional sampling period for resampling the source signal."},
                    "sampling_start": {"type": "number", "description": "Optional starting point for sampling."},
                    "sampling_end": {"type": "number", "description": "Optional ending point for sampling."},
                    "num_samples": {"type": "integer", "description": "Optional fixed number of discrete samples to take."},
                    "figsize": {"type": "array", "items": {"type": "number"}, "description": "Figure size, e.g. [6, 4]."},
                    "title": {"type": "string", "description": "Title for the plot."},
                    "x_label": {"type": "string", "description": "Label for the x-axis."},
                    "y_label": {"type": "string", "description": "Label for the y-axis."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."},
                    "linefmt": {"type": "string", "description": "Matplotlib line format for the stem plot."},
                    "markerfmt": {"type": "string", "description": "Matplotlib marker format for the stem plot."},
                    "basefmt": {"type": "string", "description": "Matplotlib base line format for the stem plot."}
                },
                "required": [],
                "anyOf": [
                    {"required": ["source_address"]},
                    {"required": ["values"]},
                    {"required": ["data_address"]}
                ]
            }
        }
    },
    {
        "type": "function",
        "function":{
            "name": "crystal_orientation_for_cubics",
            "description": "Calculate and visualize the crystal orientation for cubic crystals based on provided Miller indices or crystallographic directions, and return the saved image path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "uvw": {"type": "array", "items": {"type": "integer"}, "description": "Crystallographic direction indices (Miller indices) for the cubic crystal, e.g. [1, 0, 0]."},
                    "hkl": {"type": "array", "items": {"type": "integer"}, "description": "Miller indices for the crystal plane, e.g. [1, 0, 0]."},
                    "input_type": {"type": "string", "enum": ["uvw", "hkl"], "description": "Specify whether the input is a crystallographic direction (uvw) or a crystal plane (hkl)."},
                    "figsize": {"type": "array", "items": {"type": "number"}, "description": "Figure size for the plot, e.g. [6, 6]."},
                    "title": {"type": "string", "description": "Title for the plot."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image. If not provided, a default path will be used."}
                },
                "required": ["input_type"],
                "anyOf": [
                    {"required": ["uvw"], "properties": {"input_type": {"const": "uvw"}}},
                    {"required": ["hkl"], "properties": {"input_type": {"const": "hkl"}}}
                ]
            }
        }
    },
]


def get_tool_schemas():
    """Return a deep copy so callers can mutate safely."""
    return deepcopy(TOOL_SCHEMAS)
