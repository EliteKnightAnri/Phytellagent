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
            "description": "Load a CSV file with pandas on the server and return a preview plus schema info.",
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
            "description": "Load an Excel file with pandas on the server and return a preview plus schema info.",
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
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data points."},
                    "model_func_str": {"type": "string", "description": "A string representation of the model function to fit, e.g. 'a*x + b'."},
                    "initial_params": {"type": "array", "items": {"type": "number"}, "description": "Optional initial parameter estimates for the optimization."}
                },
                "required": ["x_data", "y_data", "model_func_str"],
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
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data points."},
                    "z_data": {"type": "array", "items": {"type": "number"}, "description": "Z-axis data points."},
                    "model_func_str": {"type": "string", "description": "A string representation of the model function to fit, e.g. 'a*x + b*y + c'."},
                    "initial_params": {"type": "array", "items": {"type": "number"}, "description": "Optional initial parameter estimates for the optimization."}
                },
                "required": ["x_data", "y_data", "z_data", "model_func_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plot_in_2d",
            "description": "Create a 2D line plot with one set of (x, y) data points and return the file path to the saved image.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data points."},
                    "title": {"type": "string", "description": "Title of the plot."},
                    "x_label": {"type": "string", "description": "Label for the X-axis."},
                    "y_label": {"type": "string", "description": "Label for the Y-axis."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."},
                },
                "required": ["x_data", "y_data", "file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plot_in_3d",
            "description": "Create a 3D scatter plot with one set of (x, y, z) data points and return the file path to the saved image.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data points."},
                    "y_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data points."},
                    "z_data": {"type": "array", "items": {"type": "number"}, "description": "Z-axis data points."},
                    "title": {"type": "string", "description": "Title of the plot."},
                    "x_label": {"type": "string", "description": "Label for the X-axis."},
                    "y_label": {"type": "string", "description": "Label for the Y-axis."},
                    "z_label": {"type": "string", "description": "Label for the Z-axis."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."},
                },
                "required": ["x_data", "y_data", "z_data", "file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "double_plot_2d",
            "description": "Create a 2D line plot with two sets of (x, y) data points and return the file path to the saved image.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data for the first set."},
                    "y1_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data for the first set."},
                    "x2_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data for the second set."},
                    "y2_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data for the second set."},
                    "title": {"type": "string", "description": "Title of the plot."},
                    "x_label": {"type": "string", "description": "Label for the X-axis."},
                    "y_label": {"type": "string", "description": "Label for the Y-axis."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."}
                },
                "required": ["x1_data", "y1_data", "x2_data", "y2_data", "file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "double_plot_3d",
            "description": "Create a 3D scatter plot with two sets of (x, y, z) data points and return the file path to the saved image.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data for the first set."},
                    "y1_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data for the first set."},
                    "z1_data": {"type": "array", "items": {"type": "number"}, "description": "Z-axis data for the first set."},
                    "x2_data": {"type": "array", "items": {"type": "number"}, "description": "X-axis data for the second set."},
                    "y2_data": {"type": "array", "items": {"type": "number"}, "description": "Y-axis data for the second set."},
                    "z2_data": {"type": "array", "items": {"type": "number"}, "description": "Z-axis data for the second set."},
                    "title": {"type": "string", "description": "Title of the plot."},
                    "x_label": {"type": "string", "description": "Label for the X-axis."},
                    "y_label": {"type": "string", "description": "Label for the Y-axis."},
                    "z_label": {"type": "string", "description": "Label for the Z-axis."},
                    "file_path": {"type": "string", "description": "File path to save the generated plot image."}
                },
                "required": ["x1_data", "y1_data", 	"z1_data", 	"x2_data", 	"y2_data", 	"z2_data", 	"file_path"],
            },
        },
    },
]


def get_tool_schemas():
    """Return a deep copy so callers can mutate safely."""
    return deepcopy(TOOL_SCHEMAS)
