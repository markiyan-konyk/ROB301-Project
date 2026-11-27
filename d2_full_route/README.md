# Deliverable 2: full route execution

The robot starts on any office patch, drives straight until it detects the white
line, then follows the line from patch to patch. After 11 arrivals it stops at the
starting office and prints `Full route done`. This counts arrivals, not map office
numbers: `Office #1 reached: blue` means the first patch after the starting patch.
There is no localization in D2.

This folder is self-contained. `src/camera` is the teammate's camera package for the
Pi, with one change: both nodes subscribe to the camera with sensor-data QoS (with the
default reliable QoS a best-effort camera driver delivers no images, so no `/line_idx`). `src/route_follower` runs on the Remote PC, using ROS 2
Jazzy / Ubuntu 24.04 / Python 3.12. The camera and robot dependencies supplied in the
lab must already be installed; setup does not install software.

## One-shot setup

[PC] Clone on the Remote PC (skip cloning if you already have this checkout):

```bash
git clone https://github.com/markiyan-konyk/ROB301-Project.git
cd ROB301-Project
bash d2_full_route/setup.sh <PI_IP> --launch
```

### Start the robot by hand

Once bringup and the camera are running (`ros2 topic list` on the PC shows `/odom`,
`/line_idx` and `/mean_img_rgb`), open a **new** [PC] terminal:

```bash
ros2 run route_follower calibrate_colors     # once per session / lighting (robot does not move)
ros2 run route_follower route_follower       # place the robot on a patch first: it starts driving
```

Ctrl+C stops the robot. `ros2 run route_follower route_follower 1` stops after one office.

Replace `<PI_IP>` with the robot's IPv4 address. The Pi password is `turtlebot`;
setup asks for it at most once (it installs your `~/.ssh/id_ed25519` key, so plain
`ssh pi@<PI_IP>` needs no password afterwards). Keep the checkout in place: the PC
package is symlinked from it. Setup is safe to rerun; close the old robot tabs first.

What it does:

1. Pings the Pi and finds this PC's IP towards it.
2. Sets up the ssh key.
3. Writes `ROS_STATIC_PEERS` (the other machine's IP) and the same `ROS_DOMAIN_ID` into
   `~/.bashrc` on both machines (the Pi's original is kept as `~/.bashrc.rob301.bak`).
4. Pi: makes sure its `~/.bashrc` sources `~/turtlebot3_ws` and stops sourcing any
   broken workspace in the Pi home folder (`~/install`); copies `src/camera` to
   `~/turtlebot3_ws/src/camera` and builds it; then checks, in the same shell an ssh
   terminal gets, that `turtlebot3_bringup`, `camera` and `v4l2_camera` are found and
   `TURTLEBOT3_MODEL` / `LDS_MODEL` are set. If not, it prints the Pi's `~/.bashrc` ROS
   lines and stops.
5. PC: links `src/route_follower` into `~/ros2_ws/src` and builds it.
6. Restarts the ROS 2 daemon on both machines.
7. With `--launch`: opens the [PI] bringup and camera tabs (through the Pi's own
   `~/.bashrc`, like a normal ssh terminal), waits up to 90 s for `/odom`, `/line_idx`,
   `/mean_img_rgb` to appear on the PC, then opens the demo tab. If a topic is still
   missing it prints a warning and opens the demo tab anyway: the robot waits there until
   both camera topics arrive.

The PC demo tab calibrates if `~/rob301_colors.json` is absent. For each of blue,
green, yellow, orange, and line, place the robot on that surface, press Enter,
and hold it still while 30 new readings are averaged. For `line`, use the actual
white tape and surrounding floor between offices. After saving, move it between
surfaces during the 10-second live classification check. These tools do not move
the robot. Place the robot back on a patch before accepting the start prompt.

Open **new terminals afterwards** so they inherit the updated networking and
workspace environment. Setup cannot change the environment of your existing shell.
Without `--launch`, setup only configures/builds; `--calibrate` applies when launching.

[PC] Force recalibration on the next launch:

```bash
bash d2_full_route/setup.sh <PI_IP> --launch --calibrate
```

## Manual launch

[PC] Configure and build once, without launching:

```bash
bash d2_full_route/setup.sh <PI_IP>
```

Open **new** terminals (they load the updated `~/.bashrc`, nothing else needs
sourcing). A [PI] terminal is a PC terminal in which you first ran `ssh pi@<PI_IP>`.
Run these in order, keeping the driver terminals open:

| Terminal | Exact commands |
| --- | --- |
| [PI] 1: motors, lidar, odometry | `ssh pi@<PI_IP>`<br>`ros2 launch turtlebot3_bringup robot.launch.py` |
| [PI] 2: camera | `ssh pi@<PI_IP>`<br>`ros2 launch camera camera.launch.py` |
| [PC] 3: check topics, then calibrate | `ros2 topic list` (must include `/odom /line_idx /mean_img_rgb`)<br>`ros2 run route_follower calibrate_colors` |
| [PC] 4: optional stationary sensor check | `ros2 run route_follower color_monitor` |
| [PC] 3: start when robot is in place | `ros2 run route_follower route_follower` |

Do not add `source` / `export` lines in the [PI] terminals: the Pi's `~/.bashrc`
already sets the workspace, `TURTLEBOT3_MODEL` and `LDS_MODEL`, and bringup needs all
of them.

The camera launch already starts the camera driver. `/odom` is checked as evidence
that bringup is running; D2 itself needs only the two camera topics.

[PC] For a short test, stop after one arrival:

```bash
ros2 run route_follower route_follower 1
```

Any positive integer `N` may replace `1`. Omit it for 11 arrivals. Ctrl+C in the
demo terminal sends five zero velocity messages before shutdown. On completion,
the node keeps publishing zero velocity until you exit.

## TA demonstration

1. Start bringup/camera, calibrate, and check classifications under the demo lighting.
2. Place the robot on any patch, facing increasing office numbers, with the offices
   on its left (counter-clockwise on the course map).
3. Run the default demo or press Enter at the setup start prompt. It waits for both
   camera topics before moving, leaves the starting patch straight, and follows
   the tape between offices.
4. Show the TA the numbered arrival/color logs. The starting patch is not counted
   until the robot returns. After arrival 11 it prints `Full route done` and stops.
   Detection is based on the camera's view, so the stopping pose needs verification
   on the physical course.
5. End the demo with Ctrl+C. For the patch detector demonstration, use the stationary
   color monitor in terminal [PC] 4; it prints RGB and class twice per second.

## Tuning and troubleshooting

Edit the marked constants at the top of
`src/route_follower/route_follower/route_follower.py`, then restart the node. With
the symlink install, Python edits need no rebuild.

| Knob | Default | Purpose |
| --- | --- | --- |
| `SPEED` | 0.05 m/s | Forward speed, including patch crossing |
| `KP`, `KI`, `KD` | 0.002, 0, 0 | PID gains for `CENTER - line_idx`; begin with P only |
| `MAX_TURN` | 0.5 rad/s | Absolute turn-rate limit |
| `CENTER` | 320 | Center of the 640-pixel camera image |
| `DEBOUNCE` | 3 frames | Consecutive patch-vs-line readings required to switch state |
| `NUM_OFFICES` | 11 | Default arrival count; overridden by positional `N` |
| `MAP` | Offices 2..12 | Editable course map for reference; not used for localization |
| `CONTROL_HZ`, `STALE_SECONDS` | 20 Hz, 1 s | Control frequency and sensor timeout |

On a confirmed patch the turn rate is zero. A patch hue changing to another patch
hue does not count another office. Both transitions require three frames agreeing
on patch versus line. If either sensor stops arriving for over one second, the
controller stops and warns; it resumes when both are fresh. Pending debounce and
PID history reset during a stale-data stop.

- **Robot does not move.** Check in this order, in a new [PC] terminal:
  1. `ros2 node list` must show `/route_follower` (our node; if missing, no demo tab is
     running: start it with `ros2 run route_follower route_follower`) and `/turtlebot3_node`
     (bringup; if missing, look at the PI 1 tab).
  2. The demo tab must not be printing `STOPPED: waiting for fresh /line_idx AND /mean_img_rgb`.
     If it is: `ros2 topic hz /line_idx` and `ros2 topic hz /mean_img_rgb` must both show a
     rate (several Hz). No rate means look at the PI 2 camera tab.
  3. `ros2 topic echo /cmd_vel --once` must show `linear.x: 0.05`. If it does and the robot
     still does not move, bringup is not receiving it: restart the PI 1 tab.
- `Package 'turtlebot3_bringup' not found` or `not found: .../install/...local_setup.bash`
  on the Pi: its `~/.bashrc` sources a wrong or broken workspace. Rerun setup: step 4
  repairs the usual case and otherwise prints the Pi's `~/.bashrc` ROS lines. It must
  source `/opt/ros/jazzy/setup.bash` and `~/turtlebot3_ws/install/setup.bash` and export
  `TURTLEBOT3_MODEL=waffle_pi` and `LDS_MODEL`; ask the TA if those are missing.
- `bash: cannot set terminal process group` / `no job control`: harmless (a Pi shell
  started without a terminal), ignore it.
- Topics missing on the PC: rerun setup's network configuration (step 3), check both
  machines point `ROS_STATIC_PEERS` at each other and share `ROS_DOMAIN_ID`, and open
  new terminals. Look at the Pi tabs for bringup/camera failures.
- Robot turns away from the tape: flip the sign of `KP`.
- Wobbling: lower `KP` and/or `SPEED` before adding integral/derivative gains.
- Missed patches: recalibrate with the command above or inspect
  [PC] `ros2 run route_follower color_monitor`. Missing or invalid calibration gives
  a loud warning and uses rough defaults; calibrate before the TA demonstration.
- Line index does not track the tape: run [PC] `ros2 topic echo /line_idx` while
  sliding the stationary robot across the tape; inspect camera alignment/lighting.
- Calibration timeout: fix `/mean_img_rgb` and retry. Incomplete calibration is not
  saved, and the automatic demo does not proceed after a calibration failure.

## Checks without ROS

[PC] From the repository root (also works with plain Python on Windows):

```bash
python3 d2_full_route/test_logic.py
```

Logic assertions cover classifications, bad calibration files, noise/debounce,
consecutive same-color offices, a complete lap, custom counts, permanent completion,
PID math/clipping/reset, and missing/stale inputs. Python compilation and Bash
syntax are checked locally. ROS/colcon, SSH setup and GNOME terminal launching,
actual camera classification, steering sign/gain, the full-lap stopping pose,
sensor-dropout stopping/recovery, and Ctrl+C stopping still require the lab hardware.
