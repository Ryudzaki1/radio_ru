import os

import paramiko


DOMAIN = os.environ["VPN_DOMAIN"]
COMMANDS = [
    f"openssl s_client -connect {DOMAIN}:443 -servername {DOMAIN} </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates",
    "xray run -test -config /usr/local/etc/xray/config.json",
    "systemctl is-active xray",
    "journalctl -u xray -n 50 --no-pager",
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
