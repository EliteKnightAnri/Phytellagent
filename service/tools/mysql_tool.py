from mysql.connector import connect, Error
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any
import uvicorn
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

app = FastAPI(title="MySQL tool", version="1.0")

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

async def process_request(request: Request) -> Dict[str, Any]:
    try:
        body = await request.json()
        # 打印调试信息
        print(f"Request received: {body}")
        
        # 支持多种可能的字段名
        method = body.get("method") or body.get("function") or body.get("action")
        params = body.get("params") or body.get("arguments") or body.get("parameters") or {}
        
        query = params.get("query", "") or params.get("sql", "")
        return {"method": method, "query": query}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    
@app.post("/query")
async def mcp_call_endpoint(request: dict):
    function_name = request.get("function")
    params = request.get("params", {})
    query = params.get("query", "") or params.get("sql", "")

    print(f"Received SQL request - function: {function_name}, query: {query}")
    
    if not query:
        return {"error": "SQL query is required"}
    
    try:
        results = execute_query(query)
        return {"results": results}
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    uvicorn.run(
        app="service.tools.mysql_tool:app",
        host="0.0.0.0",
        port=8081,
        reload=True
    )