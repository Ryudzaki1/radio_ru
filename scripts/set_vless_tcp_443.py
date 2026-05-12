import json
import os

import paramiko


HOST = os.environ["VPS_HOST"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]
CONFIG_PATH = "/usr/local/etc/xray/config.json"


def run(client, command):
    _, stdout, stderr = client.exec_command(command)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if code:
        raise RuntimeError(f"{command}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
    return out.strip()


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, allow_agent=False)

try:
    uuid = run(client, "xray uuid")
    config = {
        "log": {"loglevel": "info"},
        "inbounds": [
            {
                "tag": "vless-tcp-443",
                "listen": "0.0.0.0",
                "port": 443,
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": uuid, "email": "phone-vless-tcp-443"}],
                    "decryption": "none",
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "none",
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"],
                },
            }
        ],
        "outbounds": [
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "blocked"},
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {
                    "type": "field",
                    "network": "udp",
                    "port": "443",
                    "outboundTag": "blocked",
                }
            ],
        },
    }

    sftp = client.open_sftp()
    with sftp.file(CONFIG_PATH, "w") as fh:
        fh.write(json.dumps(config, indent=2))
    sftp.close()

    run(client, "ufw allow 443/tcp")
    test = run(client, "xray run -test -config /usr/local/etc/xray/config.json")
    run(client, "systemctl restart xray")
    status = run(client, "systemctl is-active xray")
    listen = run(client, "ss -lntp | grep ':443 ' || true")
    link = f"vless://{uuid}@{HOST}:443?encryption=none&type=tcp&security=none#{HOST}-vless-tcp-443"

    print("TEST=" + test.splitlines()[-1])
    print("XRAY_STATUS=" + status)
    print("LISTEN=" + listen.replace("\n", " | "))
    print("VLESS_LINK=" + link)
finally:
    client.close()
