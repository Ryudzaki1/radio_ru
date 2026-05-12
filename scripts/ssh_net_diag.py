import os

import paramiko


COMMANDS = [
    "journalctl -u xray --since '10 minutes ago' --no-pager",
    "ss -lntp | grep -E ':(80|443) '",
    "ufw status verbose",
    "curl -4 -I --max-time 10 https://www.google.com",
    "curl -4 --max-time 10 https://api.ipify.org; echo",
    "resolvectl status | sed -n '1,120p'",
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
        print(stdout.read().decode("utf-8", errors="replace"))
        print(stderr.read().decode("utf-8", errors="replace"))
finally:
    client.close()
