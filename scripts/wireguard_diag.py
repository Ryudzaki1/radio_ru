import os

import paramiko


COMMANDS = [
    "date -u",
    "systemctl is-active wg-quick@wg0 || true",
    "wg show",
    "ss -lunp | grep -E ':(51820|443) ' || true",
    "sysctl net.ipv4.ip_forward",
    "ufw status verbose",
    "iptables -S FORWARD",
    "iptables -t nat -S POSTROUTING",
    "ip route",
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
        err = stderr.read().decode("utf-8", errors="replace")
        if err:
            print(err.encode("ascii", errors="replace").decode("ascii"))
finally:
    client.close()
