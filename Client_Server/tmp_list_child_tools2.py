import requests
import json
import sys

payload = {'server': 'aggregator', 'tool': 'list_child_tools', 'args': {}}

try:
    r = requests.post('http://127.0.0.1:8000/mcp/call', json=payload, timeout=60)
    print('STATUS', r.status_code)
    print(r.text)
except Exception as e:
    print('ERROR', e)
    sys.exit(2)
