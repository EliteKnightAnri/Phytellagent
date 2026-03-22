"""
这是一个由MCP tools构成的包
"""

__version__ = "1.0.0"
__author__ = "Anri"
__email__ = "jinkelamaster@gmail.com"

__all__ = [
    'search_videos',
    'execute_query',
    'get_system_info',
    'get_environment_variables',
    'disk_usage',
    'read_csv',
    'read_excel',
    'least_square_fit_2d',
    'least_square_fit_3d',
    'generate_pred_values_2d',
    'generate_pred_values_3d',
    'euler_diff_solver',
    'trapezoidal_diff_solver',
    'plot_in_2d',
    'plot_in_3d',
    'double_plot_2d',
    'double_plot_3d',
    'detect_peaks',
    'detect_valleys',
]

from .bilibili_tool import search_videos
from .mysql_tool import execute_query
from .system_info_tool import get_system_info, get_environment_variables, disk_usage
from .pandas_tool import read_csv, read_excel
from .least_square_tool import least_square_fit_2d, least_square_fit_3d, generate_pred_values_2d, generate_pred_values_3d
from .differential_equations_tool import euler_diff_solver, trapezoidal_diff_solver
from .matplotlib_tool import plot_in_2d, plot_in_3d, double_plot_2d, double_plot_3d
from .peak_tool import detect_peaks, detect_valleys
