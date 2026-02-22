import asyncio, importlib.util, pathlib, sys
service_path = pathlib.Path('Client_Server') / 'mcp_service' / 'service.py'
spec = importlib.util.spec_from_file_location('mcp_service_module', str(service_path))
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
except Exception as e:
    import traceback; traceback.print_exc(); raise SystemExit(1)

async def main():
    try:
        print('Calling mysql.execute_query...')
        r = await mod.manager.call_tool('mysql','execute_query', {'args':{'query':'SELECT 1'}})
        print('RESULT:', r)
    except Exception as e:
        import traceback; traceback.print_exc()

asyncio.run(main())
