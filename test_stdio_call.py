# test_stdio_call.py
import subprocess, json, sys, time
p = subprocess.Popen(["python","-m","service.tools.system_info_tool"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
p.stdin.write(json.dumps({"id":1,"function":"get_system_info","params":{}}) + "\n")
p.stdin.flush()
resp = p.stdout.readline()
print("RESP:", resp)
p.kill()