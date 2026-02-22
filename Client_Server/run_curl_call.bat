@echo off
cd /d %~dp0
C:\Windows\System32\curl.exe -v -X POST http://127.0.0.1:8000/mcp/call -H "Content-Type: application/json" -d "{\"server\":\"bilibili\",\"tool\":\"search_videos\",\"args\":{\"keyword\":\"生化危机4\"}}"
echo EXIT_CODE %ERRORLEVEL%