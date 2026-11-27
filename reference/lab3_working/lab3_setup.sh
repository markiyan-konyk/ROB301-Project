#!/usr/bin/env bash
# ROB301 Lab 3: setup in one go. Run it on the REMOTE PC (not on the Pi):
#
#   bash ~/lab3/lab3_setup.sh <PI_IP>            network config + copy + build
#   bash ~/lab3/lab3_setup.sh <PI_IP> --launch   same, then open the robot terminals
#
# It does steps 2 and 3 of TUTORIAL.md:
#   1. ping the Pi
#   2. ssh key, so the Pi password (turtlebot) is typed only once, ever
#   3. ~/.bashrc on both machines: ROS_STATIC_PEERS = the other machine's IP,
#      same ROS_DOMAIN_ID on both
#   4. copy src/camera to the Pi and build it there
#   5. link src/lab_2 and src/lab_3 into ~/turtlebot3_ws on this PC and build them
#   6. restart the ROS 2 daemon on both machines
# Safe to run again every session (your code in ~/lab3/src is never overwritten).

set -e

PI_IP="$1"
WS=turtlebot3_ws                          # workspace folder in the home directory, both machines
HERE="$(cd "$(dirname "$0")" && pwd)"     # this lab3 folder (contains src/)
PI="pi@$PI_IP"
SSH="ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5"
ROS="source /opt/ros/jazzy/setup.bash"

step() { echo; echo "=== $1 ==="; }
fail() { echo "ERROR: $1"; exit 1; }

[ -n "$PI_IP" ] || fail "usage: bash $0 <PI_IP> [--launch]"
[ -d "$HERE/src/camera" ] || fail "$HERE/src/camera not found (keep this script next to src/)"


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
$SSH "$PI" true || fail "cannot ssh to $PI"
echo "OK"


step "3. ROS network settings in ~/.bashrc"
# Each machine must list the OTHER machine's IP
sed -i '/ROS_STATIC_PEERS/d' ~/.bashrc
echo "export ROS_STATIC_PEERS=$PI_IP" >> ~/.bashrc
$SSH "$PI" "sed -i '/ROS_STATIC_PEERS/d' ~/.bashrc && echo 'export ROS_STATIC_PEERS=$PC_IP' >> ~/.bashrc"
echo "PC: ROS_STATIC_PEERS=$PI_IP"
echo "Pi: ROS_STATIC_PEERS=$PC_IP"

# Both machines must use the same ROS_DOMAIN_ID: give the Pi the PC's value
PC_DOMAIN=$(bash -ic 'echo "DOMAIN=${ROS_DOMAIN_ID:-0}"' 2> /dev/null | grep -oP 'DOMAIN=\K.*' | tail -1)
PI_DOMAIN=$($SSH "$PI" "bash -ic 'echo DOMAIN=\${ROS_DOMAIN_ID:-0}'" 2> /dev/null | grep -oP 'DOMAIN=\K.*' | tail -1)
[ -n "$PC_DOMAIN" ] || PC_DOMAIN=0
if [ "$PC_DOMAIN" != "$PI_DOMAIN" ]; then
    echo "ROS_DOMAIN_ID differs (PC: $PC_DOMAIN, Pi: $PI_DOMAIN), setting the Pi to $PC_DOMAIN"
    $SSH "$PI" "sed -i '/ROS_DOMAIN_ID/d' ~/.bashrc && echo 'export ROS_DOMAIN_ID=$PC_DOMAIN' >> ~/.bashrc"
fi
echo "ROS_DOMAIN_ID=$PC_DOMAIN on both"


step "4. Copy the camera package to the Pi and build it (1-2 min)"
$SSH "$PI" "mkdir -p ~/$WS/src && rm -rf ~/$WS/src/camera"
scp -q -r -o StrictHostKeyChecking=accept-new "$HERE/src/camera" "$PI:$WS/src/"
$SSH "$PI" "bash -c '$ROS && cd ~/$WS && rm -rf build/camera install/camera && colcon build --symlink-install --packages-select camera'"
$SSH "$PI" "grep -q '$WS/install/setup.bash' ~/.bashrc || echo 'source ~/$WS/install/setup.bash' >> ~/.bashrc"


step "5. Link lab_2 and lab_3 into ~/$WS on this PC and build them"
mkdir -p ~/$WS/src
for p in lab_2 lab_3; do
    dest=~/$WS/src/$p
    if [ -e "$dest" ] && [ ! -L "$dest" ]; then      # an old real folder: move it out of the way
        mkdir -p ~/lab3_old
        mv "$dest" ~/lab3_old/$p-$(date +%s)
        echo "Moved the old $dest to ~/lab3_old/"
    fi
    ln -sfn "$HERE/src/$p" "$dest"
done
bash -c "$ROS && cd ~/$WS && rm -rf build/lab_2 build/lab_3 install/lab_2 install/lab_3 && colcon build --symlink-install --packages-select lab_2 lab_3"
grep -q "$WS/install/setup.bash" ~/.bashrc || echo "source ~/$WS/install/setup.bash" >> ~/.bashrc


step "6. Restart the ROS 2 daemon on both machines"
bash -c "$ROS && ros2 daemon stop" > /dev/null 2>&1 || true
$SSH "$PI" "bash -c '$ROS && ros2 daemon stop'" > /dev/null 2>&1 || true
echo "OK"


if [ "$2" = "--launch" ]; then
    step "7. Open the robot terminals"
    command -v gnome-terminal > /dev/null || fail "gnome-terminal not found: open them by hand (TUTORIAL.md step 4)"
    gnome-terminal --tab --title="PI 1 bringup" -- bash -c "$SSH -t $PI \"bash -ic 'ros2 launch turtlebot3_bringup robot.launch.py'\"; exec bash"
    sleep 3
    gnome-terminal --tab --title="PI 2 camera" -- bash -c "$SSH -t $PI \"bash -ic 'ros2 launch camera camera.launch.py'\"; exec bash"
    gnome-terminal --tab --title="PC 1 lab3" -- bash -ic "ros2 launch lab_3 lab3.launch.py; exec bash"

    echo "Waiting 25 s for the robot to start, then checking the topics from this PC..."
    sleep 25
    TOPICS=$(bash -ic 'ros2 topic list' 2> /dev/null || true)
    for t in /scan /line_idx /scan_angle /cmd_vel_noisy; do
        if echo "$TOPICS" | grep -qx "$t"; then
            echo "  $t   OK"
        else
            echo "  $t   MISSING (see TUTORIAL.md step 6)"
        fi
    done
fi


step "Done"
echo "Open NEW terminals now (terminals that were already open still have the old settings)."
echo "Next: TUTORIAL.md step 4 (start the robot, check /line_idx), then step 5 (demos)."
