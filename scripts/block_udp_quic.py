import json
import os

import paramiko


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
client.connect(
    os.environ["VPS_HOST"],
    username=os.environ.get("VPS_USER", "root"),
    password=os.environ["VPS_PASS"],
    look_for_keys=False,
    allow_agent=False,
)

try:
    sftp = client.open_sftp()
    with sftp.file(CONFIG_PATH, "r") as fh:
        config = json.loads(fh.read().decode("utf-8"))

    outbounds = config.setdefault("outbounds", [])
    if not any(o.get("tag") == "blocked" for o in outbounds):
        outbounds.append({"protocol": "blackhole", "tag": "blocked"})

    config["routing"] = {
        "domainStrategy": "AsIs",
        "rules": [
            {
                "type": "field",
                "network": "udp",
                "port": "443",
                "outboundTag": "blocked",
            }
        ],
    }

    with sftp.file(CONFIG_PATH, "w") as fh:
        fh.write(json.dumps(config, indent=2))
    sftp.close()

    test = run(client, "xray run -test -config /usr/local/etc/xray/config.json")
    run(client, "systemctl restart xray")
    status = run(client, "systemctl is-active xray")
    print("TEST=" + test.splitlines()[-1])
    print("XRAY_STATUS=" + status)
finally:
    client.close()
