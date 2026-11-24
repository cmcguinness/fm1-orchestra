#!/bin/sh
# Copy the FM-1 keyboard bridge to a Raspberry Pi and (re)start its service.
# Usage: pi/deploy.sh [HOST]   (default pizerow01; run from fm1-orchestra/)
set -e
case "$1" in
  -h|--help) sed -n '2,3p' "$0" | sed 's/^# //'; exit 0 ;;
  -*) echo "unknown option: $1" >&2; exit 2 ;;
esac
[ $# -le 1 ] || { echo "too many arguments" >&2; exit 2; }
HOST=${1:-pizerow01}
cd "$(dirname "$0")/.."
RSYNC=/opt/homebrew/bin/rsync
[ -x "$RSYNC" ] || RSYNC=rsync
ssh "$HOST" 'mkdir -p ~/fm1-bridge/fm1 ~/fm1-bridge/pi
  dpkg -s python3-mido python3-rtmidi >/dev/null 2>&1 ||
    sudo apt-get install -y -q python3-mido python3-rtmidi'
"$RSYNC" -a -e ssh fm1/__init__.py fm1/keys.py fm1/port.py "$HOST":fm1-bridge/fm1/
"$RSYNC" -a -e ssh pi/ "$HOST":fm1-bridge/pi/
ssh "$HOST" 'sudo cp ~/fm1-bridge/pi/fm1-bridge.service /etc/systemd/system/ &&
  sudo systemctl daemon-reload && sudo systemctl enable fm1-bridge &&
  sudo systemctl restart fm1-bridge && sleep 3 &&
  journalctl -u fm1-bridge -n 3 --no-pager'
