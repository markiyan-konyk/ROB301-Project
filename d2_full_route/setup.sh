#!/usr/bin/env bash
# ROB301 Deliverable 2 setup. Run it on the REMOTE PC (not on the Pi):
#
#   bash d2_full_route/setup.sh <PI_IP>                       network + copy + build
#   bash d2_full_route/setup.sh <PI_IP> --launch              same, then open the robot terminals and the demo
#   bash d2_full_route/setup.sh <PI_IP> --launch --calibrate  same, and redo the colour calibration
#
# Steps: 1 ping, 2 ssh key, 3 ROS network in ~/.bashrc (both machines), 4 Pi: check its ROS
# environment, copy + build the camera package, 5 PC: link + build our package, 6 restart the
# ROS 2 daemon, 7 (--launch) open the terminals. Safe to run again every session.

set -e

PKG=route_follower      # our package, runs on the Remote PC
PC_WS=ros2_ws           # Remote PC workspace: ~/ros2_ws
PI_WS=turtlebot3_ws     # Pi workspace: ~/turtlebot3_ws (already has the TurtleBot3 drivers)

PI_IP="$1"
LAUNCH=0
CALIBRATE=0
for a in "${@:2}"; do
    case "$a" in
        --launch) LAUNCH=1 ;;
        --calibrate) CALIBRATE=1 ;;
        *) echo "ERROR: unknown option $a"; exit 1 ;;
    esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # this deliverable folder
PI="pi@$PI_IP"
SSH="ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5"
ROS="source /opt/ros/jazzy/setup.bash"

step() { echo; echo "=== $1 ==="; }
fail() { echo "ERROR: $1"; exit 1; }
# Run a command on the Pi through its own ~/.bashrc (TURTLEBOT3_MODEL, LDS_MODEL, ~/turtlebot3_ws),
# exactly like an ssh terminal. The grep hides bash's harmless "no job control" warnings.
pi_rc() { $SSH "$PI" "bash -ic '$1'" 2>&1 | grep -v -e 'terminal process group' -e 'no job control' || true; }

[ -n "$PI_IP" ] || fail "usage: bash $0 <PI_IP> [--launch] [--calibrate]"
[ -d "$HERE/src/camera" ] && [ -d "$HERE/src/$PKG" ] || fail "run the script from inside the repo checkout"
[ -f /opt/ros/jazzy/setup.bash ] || fail "run this on the Remote PC (Ubuntu 24.04 + ROS 2 Jazzy)"


step "1. Ping the Pi ($PI_IP)"
ping -c 2 -W 2 "$PI_IP" > /dev/null || fail "no reply from $PI_IP. Is the robot on? Is the IP right?"
PC_IP=$(ip route get "$PI_IP" | grep -oP 'src \K\S+' || true)
[ -n "$PC_IP" ] || fail "could not find this PC's IP towards the Pi"
echo "Pi: $PI_IP    this PC: $PC_IP"


step "2. ssh key (type the Pi password 'turtlebot' if asked)"
if ! $SSH -o BatchMode=yes "$PI" true 2> /dev/null; then
    [ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
    ssh-copy-id -o StrictHostKeyChecking=accept-new -i ~/.ssh/id_ed25519.pub "$PI"
fi
$SSH -o BatchMode=yes "$PI" true || fail "cannot ssh to $PI"
echo "OK"


step "3. ROS network settings in ~/.bashrc (both machines)"
# Same ROS_DOMAIN_ID on both: the Pi gets the PC's value
# (read ~/.bashrc directly: never start "bash -i" from this script, it takes over the terminal
#  and the script gets "[1]+ Stopped")
PC_DOMAIN=$(grep -oP '^\s*export\s+ROS_DOMAIN_ID=\K[0-9]+' ~/.bashrc | tail -1 || true)
[ -n "$PC_DOMAIN" ] || PC_DOMAIN=${ROS_DOMAIN_ID:-0}
# Each machine lists the OTHER machine's IP
sed -i '/ROS_STATIC_PEERS/d; /ROS_DOMAIN_ID/d' ~/.bashrc
echo "export ROS_STATIC_PEERS=$PI_IP" >> ~/.bashrc
echo "export ROS_DOMAIN_ID=$PC_DOMAIN" >> ~/.bashrc
$SSH "$PI" bash -s -- "$PC_IP" "$PC_DOMAIN" << 'EOF'
set -e
[ -f ~/.bashrc.rob301.bak ] || cp ~/.bashrc ~/.bashrc.rob301.bak
sed -i '/ROS_STATIC_PEERS/d; /ROS_DOMAIN_ID/d' ~/.bashrc
echo "export ROS_STATIC_PEERS=$1" >> ~/.bashrc
echo "export ROS_DOMAIN_ID=$2" >> ~/.bashrc
EOF
echo "PC: ROS_STATIC_PEERS=$PI_IP   Pi: ROS_STATIC_PEERS=$PC_IP   ROS_DOMAIN_ID=$PC_DOMAIN on both"


step "4. Pi: check the ROS environment, copy the camera package to ~/$PI_WS and build it (1-2 min)"
$SSH "$PI" "test -d ~/$PI_WS/src" || fail "~/$PI_WS/src not found on the Pi (the TurtleBot3 workspace). Ask the TA."
# The Pi's ~/.bashrc must source ~/turtlebot3_ws. A workspace in the Pi home folder itself
# (~/install, left by a colcon build run in ~) breaks the drivers: stop sourcing it.
$SSH "$PI" bash -s -- "$PI_WS" << 'EOF'
set -e
WS=$1
if grep -qE '^[[:space:]]*(source|\.)[[:space:]]+(~|\$HOME|/home/pi)/install/' ~/.bashrc; then
    echo "Disabling these lines in the Pi's ~/.bashrc (broken workspace in the home folder):"
    grep -nE '^[[:space:]]*(source|\.)[[:space:]]+(~|\$HOME|/home/pi)/install/' ~/.bashrc
    sed -i -E 's@^([[:space:]]*(source|\.)[[:space:]]+(~|\$HOME|/home/pi)/install/.*)@# disabled by rob301 setup: \1@' ~/.bashrc
fi
grep -qE "^[[:space:]]*source[[:space:]].*$WS/install/setup.bash" ~/.bashrc || echo "source ~/$WS/install/setup.bash" >> ~/.bashrc
if [ -d ~/install ]; then
    echo "Note: ~/install exists on the Pi (a colcon build run in the home folder). It is not used."
    echo "      To remove it: ssh pi@<PI_IP> 'rm -rf ~/build ~/install ~/log'"
fi
EOF

$SSH "$PI" "rm -rf ~/$PI_WS/src/camera"
scp -q -r -o StrictHostKeyChecking=accept-new "$HERE/src/camera" "$PI:$PI_WS/src/"
$SSH "$PI" "bash -c '$ROS && cd ~/$PI_WS && rm -rf build/camera install/camera && colcon build --symlink-install --packages-select camera'"

# Check what the bringup and camera terminals will see (same shell as an ssh terminal)
CHECK=$(pi_rc 'echo "BRINGUP=$(ros2 pkg prefix turtlebot3_bringup 2>/dev/null)"; echo "CAMERA=$(ros2 pkg prefix camera 2>/dev/null)"; echo "V4L2=$(ros2 pkg prefix v4l2_camera 2>/dev/null)"; echo "MODEL=$TURTLEBOT3_MODEL"; echo "LDS=$LDS_MODEL"')
echo "$CHECK" | grep -vE '^(BRINGUP|CAMERA|V4L2|MODEL|LDS)=' || true      # any errors printed by the Pi's ~/.bashrc
val() { echo "$CHECK" | grep -oP "^$1=\K.*" | tail -1; }
echo "turtlebot3_bringup: $(val BRINGUP)"
echo "camera:             $(val CAMERA)"
echo "v4l2_camera:        $(val V4L2)"
echo "TURTLEBOT3_MODEL=$(val MODEL)   LDS_MODEL=$(val LDS)"
if [ -z "$(val BRINGUP)" ] || [ -z "$(val V4L2)" ] || [[ "$(val CAMERA)" != *"$PI_WS/install/camera" ]] \
        || [ -z "$(val MODEL)" ] || [ -z "$(val LDS)" ]; then
    echo
    echo "The Pi's ROS environment is not right. Its ~/.bashrc ROS lines are:"
    $SSH "$PI" "grep -nE 'source|ROS|TURTLEBOT3|LDS' ~/.bashrc" || true
    fail "fix the Pi's ~/.bashrc (it must source /opt/ros/jazzy and ~/$PI_WS and export TURTLEBOT3_MODEL=waffle_pi and LDS_MODEL), or ask the TA. Backup: ~/.bashrc.rob301.bak"
fi
echo "OK"


step "5. PC: link $PKG into ~/$PC_WS and build it"
mkdir -p ~/$PC_WS/src
dest=~/$PC_WS/src/$PKG
if [ -e "$dest" ] && [ ! -L "$dest" ]; then         # an old real folder: move it out of the way
    mkdir -p ~/rob301_old
    mv "$dest" ~/rob301_old/$PKG-$(date +%s)
    echo "Moved the old $dest to ~/rob301_old/"
fi
ln -sfn "$HERE/src/$PKG" "$dest"
bash -c "$ROS && cd ~/$PC_WS && rm -rf build/$PKG install/$PKG && colcon build --symlink-install --packages-select $PKG"
grep -q "$PC_WS/install/setup.bash" ~/.bashrc || echo "source ~/$PC_WS/install/setup.bash" >> ~/.bashrc


step "6. Restart the ROS 2 daemon on both machines"
bash -c "$ROS && ros2 daemon stop" > /dev/null 2>&1 || true
$SSH "$PI" "bash -c '$ROS && ros2 daemon stop'" > /dev/null 2>&1 || true
echo "OK"


if [ "$LAUNCH" = 1 ]; then
    step "7. Open the robot terminals"
    command -v gnome-terminal > /dev/null || fail "gnome-terminal not found: open the terminals by hand (README, Manual launch)"
    gnome-terminal --tab --title="PI 1 bringup" -- bash -c "$SSH -t $PI \"bash -ic 'ros2 launch turtlebot3_bringup robot.launch.py'\"; exec bash"
    sleep 3
    gnome-terminal --tab --title="PI 2 camera" -- bash -c "$SSH -t $PI \"bash -ic 'ros2 launch camera camera.launch.py'\"; exec bash"

    # The Pi 3B needs a while to start, and the ROS 2 daemon restarted in step 6 needs a few
    # seconds of discovery: one early `ros2 topic list` misses topics that do exist. Poll instead.
    echo "Waiting for /odom, /line_idx and /mean_img_rgb from this PC (up to 90 s)..."
    # This PC's ROS environment, set here directly (no "bash -i": it would stop this script)
    set +e
    source /opt/ros/jazzy/setup.bash
    set -e
    export ROS_STATIC_PEERS="$PI_IP" ROS_DOMAIN_ID="$PC_DOMAIN"
    MISSING="/odom /line_idx /mean_img_rgb"
    for i in $(seq 1 18); do
        sleep 5
        TOPICS=$(timeout 15 ros2 topic list < /dev/null 2> /dev/null || true)
        MISSING=""
        for t in /odom /line_idx /mean_img_rgb; do
            echo "$TOPICS" | grep -qx "$t" || MISSING="$MISSING $t"
        done
        [ -z "$MISSING" ] && break
        echo "  $((i * 5)) s, still missing:$MISSING"
    done
    if [ -z "$MISSING" ]; then
        echo "  /odom /line_idx /mean_img_rgb   OK"
    else
        echo "WARNING: still missing after 90 s:$MISSING"
        echo "  /odom missing: look at the PI 1 bringup tab.  /line_idx or /mean_img_rgb missing: PI 2 camera tab."
        echo "  If they exist on the Pi but not here, it is the network: close all terminals, open new ones, rerun."
        echo "Opening the demo tab anyway: the robot waits there until both camera topics arrive."
    fi

    CAL=""
    if [ "$CALIBRATE" = 1 ] || [ ! -f ~/rob301_colors.json ]; then CAL="ros2 run $PKG calibrate_colors && "; fi
    gnome-terminal --tab --title="PC demo" -- bash -ic "${CAL}read -p 'Robot on a patch, facing the driving direction? Press Enter to start ' _ && ros2 run $PKG $PKG; exec bash"
elif [ "$CALIBRATE" = 1 ]; then
    echo "--calibrate only works together with --launch"
fi


step "Done"
echo "Open NEW terminals now (terminals that were already open still have the old settings)."
