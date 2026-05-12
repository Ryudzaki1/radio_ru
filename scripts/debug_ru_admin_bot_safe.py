import os

import paramiko


HOST = os.environ["RU_HOST"]
USER = os.environ.get("RU_USER", "radio")
KEY_PATH = os.environ["RU_KEY"]


def load_key(path):
    for key_cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            return key_cls.from_private_key_file(path)
        except paramiko.SSHException:
            continue
    raise RuntimeError("Could not read SSH key")


script = r"""
set -euo pipefail
cd /opt/radio_ru
set -a
. ./.env
set +a

echo "--- containers"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo "--- admin local with auth"
AUTH="$(printf '%s:%s' "$ADMIN_USERNAME" "$ADMIN_PASSWORD" | base64 -w0)"
curl -I --max-time 10 -H "Authorization: Basic $AUTH" http://127.0.0.1/admin.html || true

echo "--- env summary"
echo "PUBLIC_RADIO_URL=$PUBLIC_RADIO_URL"
echo "ADMIN_USERNAME=$ADMIN_USERNAME"
echo "TELEGRAM_BOT_TOKEN=$([ -n "${TELEGRAM_BOT_TOKEN:-}" ] && echo SET || echo EMPTY)"
echo "LISTENER_API_TOKEN=$([ -n "${LISTENER_API_TOKEN:-}" ] && echo SET || echo EMPTY)"
echo "BOT_ALLOWED_TELEGRAM_IDS=${BOT_ALLOWED_TELEGRAM_IDS:-EMPTY}"
echo "BOT_ADMIN_TELEGRAM_IDS=${BOT_ADMIN_TELEGRAM_IDS:-EMPTY}"
echo "BOT_NOTIFY_CHAT_IDS=${BOT_NOTIFY_CHAT_IDS:-EMPTY}"

echo "--- bot env summary"
docker exec ai-chill-radio-bot sh -lc 'echo PUBLIC_RADIO_URL=$PUBLIC_RADIO_URL; echo RADIO_INTERNAL_URL=$RADIO_INTERNAL_URL; echo LISTENER_API_TOKEN=$([ -n "$LISTENER_API_TOKEN" ] && echo SET || echo EMPTY); echo BOT_NOTIFY_CHAT_IDS=${BOT_NOTIFY_CHAT_IDS:-EMPTY}'

echo "--- telegram dns"
getent hosts api.telegram.org || true

echo "--- telegram getMe from host"
curl -sS --connect-timeout 8 --max-time 20 -w '\nHTTP=%{http_code}\n' "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" | head -c 1000 || true
echo

echo "--- telegram getMe from bot container"
docker exec ai-chill-radio-bot sh -lc 'curl -sS --connect-timeout 8 --max-time 20 -w "\nHTTP=%{http_code}\n" "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" | head -c 1000' || true

echo "--- bot logs"
docker logs --tail 120 ai-chill-radio-bot || true
"""


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, pkey=load_key(KEY_PATH), look_for_keys=False, allow_agent=False)
try:
    stdin, stdout, stderr = client.exec_command("sudo -n bash -s", timeout=240)
    stdin.write(script)
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(out.encode("ascii", errors="replace").decode("ascii"))
    if err:
        print(err.encode("ascii", errors="replace").decode("ascii"))
    code = stdout.channel.recv_exit_status()
    if code:
        raise SystemExit(code)
finally:
    client.close()
