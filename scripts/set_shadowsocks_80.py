import base64
import json
import os

import paramiko


HOST = os.environ["VPS_HOST"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]
CONFIG_PATH = "/usr/local/etc/xray/config.json"
METHOD = "chacha20-ietf-poly1305"
SS_TAG = "ss-80"


def run(client, command):
    _, stdout, stderr = client.exec_command(command)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if code:
        raise RuntimeError(f"{command}\n{out}\n{err}")
    return out.strip()


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, allow_agent=False)

try:
    sftp = client.open_sftp()
    with sftp.file(CONFIG_PATH, "r") as fh:
        config = json.loads(fh.read().decode("utf-8"))

    password = run(client, "openssl rand -base64 24 | tr -d '\\n'")
    config["inbounds"] = [i for i in config["inbounds"] if i.get("port") != 80]
    config["inbounds"].append(
        {
            "tag": SS_TAG,
            "listen": "0.0.0.0",
            "port": 80,
            "protocol": "shadowsocks",
            "settings": {
                "method": METHOD,
                "password": password,
                "network": "tcp,udp",
            },
        }
    )

    with sftp.file(CONFIG_PATH, "w") as fh:
        fh.write(json.dumps(config, indent=2))
    sftp.close()

    run(client, "ufw allow 80/tcp")
    run(client, "ufw allow 80/udp")
    test = run(client, "xray run -test -config /usr/local/etc/xray/config.json")
    run(client, "systemctl restart xray")
    status = run(client, "systemctl is-active xray")
    listen = run(client, "ss -lntup | grep ':80 ' || true")

    userinfo = base64.urlsafe_b64encode(f"{METHOD}:{password}".encode()).decode().rstrip("=")
    link = f"ss://{userinfo}@{HOST}:80#{HOST}-ss-80"

    print("TEST=" + test.splitlines()[-1])
    print("XRAY_STATUS=" + status)
    print("LISTEN=" + listen.replace("\n", " | "))
    print("SS_LINK=" + link)
finally:
    client.close()
