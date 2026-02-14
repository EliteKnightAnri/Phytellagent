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

config = log_config()

mysql_env = config.get("mcpServers", {}).get("mysql", {}).get("env", {})

DB_CONFIG = {
    'host': mysql_env.get('MYSQL_HOST', 'localhost'),
    'port': int(mysql_env.get('MYSQL_PORT', 3306)),
    'user': mysql_env.get('MYSQL_USER', 'root'),
    'password': mysql_env.get('MYSQL_PASSWORD', ''),
    'database': mysql_env.get('MYSQL_DATABASE', 'test_db')
}

# 使用FastMCP创建服务器
mcp = FastMCP(name="MySQL tool")

@mcp.tool()
def execute_query(query: str) -> dict:
    connection = None

    try:
        connection = connect(**DB_CONFIG)
        
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            
            if cursor.description is not None:
                columns = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()
                return {"columns": columns, "results": results}
            else:
                connection.commit()
                return {"rowcount": cursor.rowcount, "message": f"Query affected {cursor.rowcount} rows"}
                
    except Error as e:
        return {"error": str(e)}
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    mcp.run(transport="stdio")
