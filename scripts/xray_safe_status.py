import os

import paramiko


COMMANDS = [
    "date -u",
    "systemctl is-active xray",
    "xray run -test -config /usr/local/etc/xray/config.json",
    "ss -lntp | grep -E ':(80|443) '",
    "ufw status verbose",
    "journalctl -u xray --since '15 minutes ago' --no-pager | tail -180",
    "curl -4 --max-time 8 https://api.ipify.org; echo",
    "curl -4 -I --max-time 8 https://2ip.ru",
    "curl -4 -I --max-time 8 https://www.google.com",
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
