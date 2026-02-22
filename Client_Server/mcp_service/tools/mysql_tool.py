from typing import Dict, Optional, Tuple, Any

from mysql.connector import connect, Error
from fastmcp import FastMCP
import json
import os

# 使用项目根的 mcp_settings.json（相对路径或可改为绝对）
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'mcp_settings.json')

def log_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as file:
            return json.load(file)

    else:
        print(f"Configuration file not found at {CONFIG_PATH}")
        return {}

def _build_db_config() -> Dict[str, Any]:
    cfg = log_config()
    mysql_env = cfg.get("mcpServers", {}).get("mysql", {}).get("env", {})

    def _pick(key: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(key) or mysql_env.get(key) or default

    host = _pick('MYSQL_HOST', 'localhost')
    port_raw = _pick('MYSQL_PORT', '3306')
    try:
        port = int(port_raw) if port_raw is not None else 3306
    except ValueError:
        port = 3306

    return {
        'host': host,
        'port': port,
        'user': _pick('MYSQL_USER', 'root'),
        'password': _pick('MYSQL_PASSWORD', ''),
        'database': _pick('MYSQL_DATABASE', 'test_db'),
    }

# 使用FastMCP创建服务器
mcp = FastMCP(name="MySQL tool")


def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}


@mcp.tool()
def execute_query(payload: Optional[Dict[str, Any]] = None, query: Optional[str] = None) -> Dict[str, Any]:
    """兼容两种调用方式：
    - 被 aggregator 以 kwargs 形式调用：execute_query(query="...")
    - 被直接以 payload 调用：execute_query(payload={"query": "..."})
    """
    if query:
        sql = query
    else:
        args, meta = _split_payload(payload)
        sql = args.get("query") or args.get("sql") or meta.get("prompt")
    if not sql:
        return {"status": "error", "message": "sql/query is required"}

    connection = None
    cursor = None
    try:
        db_config = _build_db_config()
        connection = connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql)

        if cursor.description is not None:
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()
            return {"status": "success", "data": {"columns": columns, "rows": results}, "query": sql}

        connection.commit()
        return {
            "status": "success",
            "data": {"rowcount": cursor.rowcount},
            "query": sql,
        }

    except Error as exc:
        return {"status": "error", "message": str(exc), "query": sql}
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    mcp.run(transport="stdio")
