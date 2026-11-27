# ROB301 Final Project: rules for Codex

TurtleBot3 mail-delivery robot (read `ROB301_Final_Project.pdf`). The work is split into one
self-contained folder per deliverable. **Implement only the spec you are asked for** (`specs/`).
Goal: a demo that works reliably for the TA. Simple, straight to the point, no extras.

## Hardware and software (fixed)

- TurtleBot3 **Waffle Pi**: Raspberry Pi 3B, OpenCR, 360° lidar, Pi camera.
- **Ubuntu 24.04 + ROS 2 Jazzy** on both machines: the robot ("**Pi**") and the lab desktop
  ("**Remote PC**"). Python 3.12.
- The PDF's ROS 1 commands (`roscore`, `roslaunch`, `rosrun`, catkin, `final_project/nodes`) are
  outdated. The real commands:
  - [PI] `ros2 launch turtlebot3_bringup robot.launch.py` (motors, lidar, /odom)
  - [PI] `ros2 launch camera camera.launch.py` (camera, /line_idx, /mean_img_rgb)
  - [PC] `ros2 run <pkg> <executable>` (our code)
- Pi login: `ssh pi@<PI_IP>`, password `turtlebot`. ROS networking: `ROS_STATIC_PEERS` (each
  machine = the other's IP) and the same `ROS_DOMAIN_ID`, in each `~/.bashrc`.
  `reference/lab3_working/lab3_setup.sh` already does this correctly: reuse it.

## Workspace and layout (do not deviate)

- The **only** ROS workspace is `~/turtlebot3_ws` on both machines. Never create another one
  (no `~/ros2_ws`, no workspace inside the repo, no venv, no `pip install`, no `apt`).
  Allowed deps: rclpy, std_msgs, geometry_msgs, nav_msgs, sensor_msgs, numpy, matplotlib
  (cv_bridge only in the camera package, already on the Pi).
- Packages are **ament_python** with exactly the layout of `labs/lab_3`: `package.xml`, `setup.py`,
  `setup.cfg`, `resource/<pkg>`, `<pkg>/__init__.py`, console_scripts entry points. No CMake,
  no custom messages.
- Our nodes run on the **Remote PC**. Only the `camera` package runs on the **Pi**.
- Remote PC: `setup.sh` symlinks `<deliverable>/src/<pkg>` to `~/turtlebot3_ws/src/<pkg>` and runs
  `colcon build --symlink-install --packages-select <pkg>` (so edits are live, no rebuild).
  Pi: `setup.sh` copies `<deliverable>/src/camera` to `~/turtlebot3_ws/src/camera` and builds it there.

```
AGENTS.md, specs/          instructions (this)
reference/lab3_working/    WORKING Lab 3 code from our group: copy patterns from here (read-only)
labs/, final_project/      course starter code (read-only)
d1_bayes_sim/              Deliverable 1   (plain Python, no ROS)
d2_full_route/             Deliverable 2   package: route_follower
d3_bayes_node/             Deliverable 3   package: bayes_localization
d4_mail_delivery/          Deliverable 4   package: mail_robot
```

Each deliverable folder is fully self-contained: its own `README.md`, `setup.sh`, `src/camera`
and its own copy of any shared helper. No imports across folders. Package names differ, so all
deliverables can be built side by side in `~/turtlebot3_ws`.

## ROS interfaces

| Topic | Type | Notes |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/TwistStamped` | set `header.stamp`; `twist.linear.x`, `twist.angular.z` |
| `/line_idx` | `std_msgs/UInt32` | column (0-639) of the tape, 320 = centred. From `camera_mono` |
| `/mean_img_rgb` | `std_msgs/Float64MultiArray` | `data = [r, g, b]` (0-255), mean of the image. From `camera_rgb` |
| `/odom` | `nav_msgs/Odometry` | subscribe with `qos_profile_sensor_data`; yaw as in `labs/lab_0/lab_0/odometry.py` |

**Camera package**: copy `reference/lab3_working/src/camera` into each robot deliverable and change
only: (1) the launch file also starts `camera_rgb`, with the same remapping
(`camera/image` -> `image_raw`) as `camera_mono`; (2) `camera_rgb` subscribes with
`qos_profile_sensor_data`; (3) `LINE_IS_DARK` becomes a launch argument `line_is_dark`
(default `false` = white tape, as in the PDF) passed to `camera_mono` as a ROS parameter.

## Course map (Figure 1 of the PDF)

Offices 2..12 in driving order (office numbers increase; counter-clockwise in Figure 1, offices on
the robot's **left**, the loop wraps 12 -> 2):

```python
MAP = ['yellow', 'green', 'blue', 'orange', 'orange', 'green', 'blue', 'orange', 'yellow', 'green', 'blue']
#        2         3        4       5         6         7        8       9         10        11       12
```

Keep `MAP` as an editable constant at the top of the node file (the final map is announced on
demo day).

## Color sensing (D2-D4)

- Classes: `blue`, `green`, `yellow`, `orange` (office patches) and `line` (robot on the tape between offices).
- Executable `calibrate_colors` (interactive): for each class print "Place the robot on <class>,
  press Enter", average ~30 `/mean_img_rgb` samples, save all to `~/rob301_colors.json`. Then print
  the live classification for ~10 s so the user can check it.
- Classifier: nearest calibrated mean RGB (Euclidean). If the file is missing, use hard-coded
  defaults and log a loud warning.
- Debounce: switch between "on patch" and "on line" only after 3 consecutive frames agree.
- On a patch `/line_idx` is meaningless: drive straight (turn 0) until the line is back.

## Code rules

- One demo node per deliverable + a ROS-free `logic.py` (Bayes filter, classifier, PID) so the
  math can be tested with plain Python on Windows.
- Reuse the reference code: PID line follower `reference/lab3_working/src/lab_2/lab_2/lab_2.py`
  (SPEED 0.05, KP 0.002, KI 0, KD 0, MAX_TURN 0.5, CENTER 320); Ctrl+C stops the robot
  (`SignalHandlerOptions.NO` + send zero velocity 3 times, as in `delivery.py`).
- Tunable constants in one clearly marked block at the top of the node file.
- Do not move until `/line_idx` and `/mean_img_rgb` are both arriving; if either is older than
  1 s, stop the robot and log a warning.
- LF line endings for all `.sh` and `.py` (add `.gitattributes` with `* text=auto eol=lf`).

## Every robot deliverable (D2-D4) ships

**`setup.sh <PI_IP> [--launch] [--calibrate]`**, run once on the Remote PC. Based on
`reference/lab3_working/lab3_setup.sh` steps 1-6, with `PKG`, `WS=turtlebot3_ws` and
`LINE_IS_DARK=false` as variables at the top. With `--launch`, open gnome-terminal tabs:
[PI] bringup, [PI] camera (passing `line_is_dark`), wait ~25 s, check from the PC that
`/line_idx`, `/mean_img_rgb`, `/odom` exist (print OK / MISSING), then one [PC] tab that runs
`calibrate_colors` if `~/rob301_colors.json` is missing or `--calibrate` was given, then
`read -p "Robot in place? Press Enter to start"`, then the demo node.

**`README.md`**: what the demo shows; one-shot path (`git clone` the repo on the Remote PC,
`bash <folder>/setup.sh <PI_IP> --launch`); manual path as a table of terminals labelled [PI] /
[PC] with exact commands; the TA demo step by step; tuning knobs; short troubleshooting (copy
the relevant rows of `reference/lab3_working/TUTORIAL.md` section 6). Every command labelled
[PC] or [PI].

## Before you finish

No ROS on this machine, so: `python -m py_compile` every `.py`, test `logic.py` with plain-Python
asserts, `bash -n` every `.sh`. Say clearly what still needs testing on the robot.
