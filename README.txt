针对mcp_settings.json，约定俗成的写法如下：
{
  "mcpServers": {
    "server_name_1": {
      "...": "..."
    },
    "server_name_2": {
      "...": "..."
    }
  }
}

stdio通信使用写法如下：
{
  "mcpServers": {
    "local_tools": {
      "command": "python",
      "args": ["-m", "my_mcp_server"],
      "env": {
        "PYTHONPATH": "/home/user/projects",
        "MY_TOOL_MODE": "production"
      }
    }
  }
}

http通信使用写法如下：
{
  "mcpServers": {
    "secure_server": {
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY",
        "X-Client": "chatgpt"
      }
    }
  }
}
