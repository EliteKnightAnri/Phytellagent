import importlib
try:
    importlib.import_module('mcp_service.tools.bilibili_tool')
    print('IMPORT_OK')
except Exception as e:
    print('IMPORT_ERR', e)
    raise
