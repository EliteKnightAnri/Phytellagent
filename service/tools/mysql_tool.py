from mysql.connector import connect, Error
from fastmcp import FastMCP
import json
import os

# 如果不希望密码泄露，可以给这个文件加上权限
CONFIG_PATH = "E:\local_mcp\mcp_settings.json"

# 读取配置文件
def log_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as file:
            return json.load(file)

    else:
        print(f"Configuration file not found at {CONFIG_PATH}")
        return {}

config = log_config()

# 这个配置包含了host, port, user, password和database
mysql_env = config.get("mcpServers", {}).get("mysql", {}).get("env", {})

DB_CONFIG = {
    'host': mysql_env.get('MYSQL_HOST', 'localhost'),
    # port要求必须是整数，所以要做强转
    'port': int(mysql_env.get('MYSQL_PORT', 3306)),
    'user': mysql_env.get('MYSQL_USER', 'root'),
    'password': mysql_env.get('MYSQL_PASSWORD', ''),
    'database': mysql_env.get('MYSQL_DATABASE', 'test_db')
}

# 使用FastMCP创建服务器
mcp = FastMCP(name="MySQL tool")

@mcp.tool()
def execute_query(query: str) -> dict:
    """
    Execute a SQL query on the MySQL database and return the results.

    Args:
        query (str): The SQL query to execute.

    Returns:
        dict: A dictionary containing the query results.

    Raises:
        mysql.connector.Error: If there is an error executing the query.
    """
    connection = None

    try:
        connection = connect(**DB_CONFIG)
        
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            
            # 检查是否有结果集
            if cursor.description is not None:
                # 有结果集的情况（SELECT, SHOW, DESCRIBE等）
                # 返回规范格式后的结果
                columns = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()
                return {"columns": columns, "results": results}
            else:
                # 没有结果集的情况（INSERT, UPDATE, DELETE等）
                # 需要返回受影响的行数
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