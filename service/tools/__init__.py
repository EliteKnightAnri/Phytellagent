"""
这是一个由MCP tools构成的包
"""

__version__ = "1.0.0"
__author__ = "Anri"
__email__ = "jinkelamaster@gmail.com"

__all__ = [
    'search_videos',
    'execute_query'
]

from .bilibili_tool import search_videos
from .mysql_tool import execute_query