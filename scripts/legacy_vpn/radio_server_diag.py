import os

import paramiko


COMMANDS = [
    "ss -lntup | grep -E ':(80|443) ' || true",
    "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'",
    "systemctl is-active xray || true",
    "ufw status verbose",
    "curl -4 -I --max-time 10 http://127.0.0.1/ || true",
]


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    os.environ["VPS_HOST"],
    username=os.environ.get("VPS_USER", "root"),
    password=os.environ["VPS_PASS"],
    look_for_keys=False,
    allow_agent=False,
)

try:
    for command in COMMANDS:
        print("--- " + command)
        _, stdout, stderr = client.exec_command(command)
        print(stdout.read().decode("utf-8", errors="replace").encode("ascii", errors="replace").decode("ascii"))
        err = stderr.read().decode("utf-8", errors="replace")
        if err:
            print(err.encode("ascii", errors="replace").decode("ascii"))
finally:
    client.close()
