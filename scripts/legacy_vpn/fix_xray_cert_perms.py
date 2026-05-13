import os

import paramiko


DOMAIN = os.environ["VPN_DOMAIN"]
CERT_DIR = f"/etc/ssl/xray/{DOMAIN}"

COMMANDS = [
    "id nobody",
    f"chown -R nobody:nogroup {CERT_DIR}",
    "chmod 755 /etc/ssl/xray",
    f"chmod 750 {CERT_DIR}",
    f"chmod 640 {CERT_DIR}/privkey.pem",
    f"chmod 644 {CERT_DIR}/fullchain.pem",
    "systemctl restart xray",
    "systemctl is-active xray",
    "ss -lntp | grep ':443 '",
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
