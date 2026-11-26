#!/usr/bin/env bash
PKG=route_follower
PC_WS=ros2_ws
set -eEo pipefail
trap 'echo "ERROR: setup failed at line $LINENO. Fix the reported problem and rerun." >&2' ERR
fail() { echo "ERROR: $*" >&2; exit 1; }
step() { echo "=== $* ==="; }
[[ $# -ge 1 ]] || fail "Usage: bash setup.sh <PI_IP> [--launch] [--calibrate]"
PI_IP=$1
shift
LAUNCH=0
CALIBRATE=0
for option in "$@"; do
    case "$option" in
        --launch) LAUNCH=1 ;;
        --calibrate) CALIBRATE=1 ;;
        *) fail "Unknown option: $option" ;;
    esac
done
python3 - "$PI_IP" <<'PY'
import ipaddress, sys
ipaddress.IPv4Address(sys.argv[1])
PY
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
WS="$HOME/$PC_WS"
[[ -f /opt/ros/jazzy/setup.bash ]] || fail 'Run on the Ubuntu 24.04 Remote PC with ROS 2 Jazzy.'
source /opt/ros/jazzy/setup.bash
for tool in ping ip ssh ssh-keygen ssh-copy-id tar colcon; do
    command -v "$tool" >/dev/null || fail "Missing required command: $tool"
done
if (( LAUNCH )); then
    command -v gnome-terminal >/dev/null || fail 'gnome-terminal is required for --launch.'
fi
step '1: Check Pi and find PC address'
ping -c 1 -W 3 "$PI_IP" >/dev/null || fail "Pi $PI_IP is unreachable."
PC_IP=$(ip route get "$PI_IP" | awk '{for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}')
[[ -n "$PC_IP" ]] || fail 'Could not find PC source IP.'
echo "PC: $PC_IP; Pi: $PI_IP"
step '2: Set up SSH key (Pi password: turtlebot)'
mkdir -p "$HOME/.ssh"
KEY="$HOME/.ssh/rob301_ed25519"
[[ -f "$KEY" ]] || ssh-keygen -t ed25519 -N '' -f "$KEY"
SSH=(ssh -i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o BatchMode=yes "pi@$PI_IP")
if ! "${SSH[@]}" 'source /opt/ros/jazzy/setup.bash; true' 2>/dev/null; then
    ssh-copy-id -i "$KEY.pub" -o StrictHostKeyChecking=accept-new -o NumberOfPasswordPrompts=1 "pi@$PI_IP"
fi
"${SSH[@]}" 'source /opt/ros/jazzy/setup.bash; true'
# Quote every remote argument for the remote shell.
remote() {
    local command='source /opt/ros/jazzy/setup.bash && ' quoted
    printf -v quoted '%q ' "$@"
    "${SSH[@]}" "$command$quoted"
}
step '3: Configure ROS peers and domain on both machines'
DOMAIN=${ROS_DOMAIN_ID:-0}
[[ "$DOMAIN" =~ ^[0-9]+$ ]] || fail 'ROS_DOMAIN_ID must be an integer.'
(( 10#$DOMAIN <= 232 )) || fail 'ROS_DOMAIN_ID must be between 0 and 232.'
# This helper edits only ROS assignments; a backup preserves the original bashrc.
UPDATE_RC=$(cat <<'PY'
import pathlib, re, sys
peer, domain, workspace = sys.argv[1:]
p = pathlib.Path.home()/'.bashrc'
text = p.read_text() if p.exists() else ''
backup = p.with_name('.bashrc.rob301.bak')
if not backup.exists():
    backup.write_text(text)
lines = [line for line in text.splitlines() if not re.match(r'^\s*(?:export\s+)?ROS_(?:STATIC_PEERS|DOMAIN_ID)\s*=', line)]
lines += [f'export ROS_STATIC_PEERS="{peer}"', f'export ROS_DOMAIN_ID="{domain}"']
if workspace:
    import shlex
    source = 'source ' + shlex.quote(str(pathlib.Path(workspace)/'install/setup.bash'))
    if source not in lines:
        lines.append(source)
p.write_text('\n'.join(lines)+'\n')
PY
)
python3 -c "$UPDATE_RC" "$PI_IP" "$DOMAIN" ''
remote python3 -c "$UPDATE_RC" "$PC_IP" "$DOMAIN" ''
export ROS_STATIC_PEERS="$PI_IP" ROS_DOMAIN_ID="$DOMAIN"
step '4: Find Pi camera workspace, replace camera source, build'
# Interactive bash loads the Pi's existing overlay from .bashrc.
PI_WS=$(remote bash -ic 'source /opt/ros/jazzy/setup.bash; prefix=$(ros2 pkg prefix camera 2>/dev/null) || prefix=""; if [[ -n "$prefix" ]]; then case "$prefix" in */install/camera) printf "ROB301_WS=%s\n" "${prefix%/install/camera}" ;; *) echo "Unsupported camera prefix: $prefix" >&2; exit 1 ;; esac; else printf "ROB301_WS=%s/ros2_ws\n" "$HOME"; fi' | sed -n 's/^ROB301_WS=//p')
[[ "$PI_WS" == /* && "$PI_WS" != / && "$PI_WS" != *$'\n'* ]] || fail 'Could not determine a safe Pi workspace path.'
echo "Pi workspace: $PI_WS"
remote bash -c 'set -e; ws=$1; mkdir -p "$ws/src"; rm -rf -- "$ws/src/camera"; mkdir -p "$ws/src/camera"' bash "$PI_WS"
tar -C "$HERE/src/camera" -cf - . | remote tar -C "$PI_WS/src/camera" -xf -
remote bash -c 'set -e; source /opt/ros/jazzy/setup.bash; cd "$1"; colcon build --symlink-install --packages-select camera' bash "$PI_WS"
remote python3 -c "$UPDATE_RC" "$PC_IP" "$DOMAIN" "$PI_WS"
step '5: Link and build Remote PC package'
mkdir -p "$WS/src"
DEST="$WS/src/$PKG"
if [[ -L "$DEST" ]]; then
    [[ "$(readlink "$DEST")" == "$HERE/src/$PKG" ]] || fail "$DEST points elsewhere; resolve it before rerunning."
elif [[ -e "$DEST" ]]; then
    fail "$DEST already exists and is not our symlink; move it aside before rerunning."
else
    ln -s "$HERE/src/$PKG" "$DEST"
fi
cd "$WS"
rm -rf -- "build/$PKG" "install/$PKG"
colcon build --symlink-install --packages-select "$PKG"
python3 -c "$UPDATE_RC" "$PI_IP" "$DOMAIN" "$WS"
source "$WS/install/setup.bash"
step '6: Restart ROS discovery on both machines'
ros2 daemon stop
remote env ROS_STATIC_PEERS="$PC_IP" ROS_DOMAIN_ID="$DOMAIN" ros2 daemon stop
if (( LAUNCH )); then
    step '7: Launch Pi drivers and camera'
    printf -v REMOTE_ENV 'source /opt/ros/jazzy/setup.bash && source %q && export ROS_STATIC_PEERS=%q ROS_DOMAIN_ID=%q TURTLEBOT3_MODEL=waffle_pi && ' "$PI_WS/install/setup.bash" "$PC_IP" "$DOMAIN"
    gnome-terminal --tab --title='[PI] Bringup' -- "${SSH[@]:0:${#SSH[@]}-1}" -t "pi@$PI_IP" "${REMOTE_ENV}ros2 launch turtlebot3_bringup robot.launch.py"
    gnome-terminal --tab --title='[PI] Camera' -- "${SSH[@]:0:${#SSH[@]}-1}" -t "pi@$PI_IP" "${REMOTE_ENV}ros2 launch camera camera.launch.py"
    echo 'Waiting 25 seconds for Pi startup...'
    sleep 25
    TOPICS=$(ros2 topic list)
    MISSING=0
    for topic in /line_idx /mean_img_rgb /odom; do
        if grep -Fxq "$topic" <<< "$TOPICS"; then
            echo "OK: $topic"
        else
            echo "MISSING: $topic"
            MISSING=1
        fi
    done
    (( MISSING == 0 )) || fail 'Topics missing. Check Pi tabs and step 3 network settings; open new terminals.'
    gnome-terminal --tab --title='[PC] Route follower' -- bash -c '
        set -e
        trap '\''echo "ERROR: demo command failed; inspect output above."; read -r -p "Press Enter to close"'\'' ERR
        source /opt/ros/jazzy/setup.bash
        source "$1/install/setup.bash"
        export ROS_STATIC_PEERS="$2" ROS_DOMAIN_ID="$3"
        if [[ ! -f "$HOME/rob301_colors.json" || "$4" == 1 ]]; then
            ros2 run route_follower calibrate_colors
        fi
        read -r -p "Robot in place? Press Enter to start"
        ros2 run route_follower route_follower
    ' bash "$WS" "$PI_IP" "$DOMAIN" "$CALIBRATE"
fi
step 'Setup complete: open new terminals to load the updated ROS environment'
if (( CALIBRATE && ! LAUNCH )); then
    echo '--calibrate takes effect with --launch; nothing was launched.'
fi
