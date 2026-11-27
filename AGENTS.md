# ROB301 Final Project: rules for Codex

TurtleBot3 mail-delivery robot (read `ROB301_Final_Project.pdf`). The work is split into one
self-contained folder per deliverable. **Implement only the spec you are asked for** (`specs/`).
Goal: a demo that works reliably for the TA. Simple, straight to the point, no extras.

There is no earlier working code for this project. Write everything fresh, using only what is in
this repo: the PDFs, the course starter code (`labs/`, `final_project/`) and `Resources/camera`.
Do not look for or reuse code from anywhere else.

## Hardware and software (fixed)

- TurtleBot3 **Waffle Pi**: Raspberry Pi 3B, OpenCR, 360° lidar, Pi camera.
- **Ubuntu 24.04 + ROS 2 Jazzy** on both machines: the robot ("**Pi**") and the lab desktop
  ("**Remote PC**"). Python 3.12. See `labs/ROB301_Lab0.pdf`.
- The final-project PDF's ROS 1 commands (`roscore`, `roslaunch`, `rosrun`, catkin,
  `final_project/nodes`) are outdated. The real commands:
  - [PI] `ros2 launch turtlebot3_bringup robot.launch.py` (motors, lidar, /odom)
  - [PI] `ros2 launch camera camera.launch.py` (camera driver + /line_idx + /mean_img_rgb; it
    already starts `v4l2_camera`, so never also run `v4l2_camera_node`)
  - [PC] `ros2 run <pkg> <executable>` (our code)
- Pi login: `ssh pi@<PI_IP>`, password `turtlebot`. ROS networking (Lab 0, 4.2.2):
  `ROS_STATIC_PEERS` in each machine's `~/.bashrc` must be the **other** machine's IP. Both
  machines must also have the same `ROS_DOMAIN_ID`.

## Workspace and layout (do not deviate)

- Remote PC workspace: `~/ros2_ws` (as in `labs/lab_3/README.md`). Pi workspace: `~/turtlebot3_ws`
  (holds the TurtleBot3 drivers and the `camera` package; confirmed on our robot). Hard-code
  both; never auto-detect a workspace, never run `colcon` in a home folder. Never create any
  other workspace (none inside the repo, no venv, no `pip install`, no `apt`). Allowed deps:
  rclpy, std_msgs, geometry_msgs, nav_msgs, sensor_msgs, numpy, matplotlib.
- The Pi's `~/.bashrc` (set up by the lab) sources `/opt/ros/jazzy` and `~/turtlebot3_ws` and
  exports `TURTLEBOT3_MODEL` and `LDS_MODEL`; bringup needs all of them. Anything that runs on the
  Pi must go through it, like a normal ssh terminal:
  `ssh -t pi@<PI_IP> "bash -ic 'ros2 launch turtlebot3_bringup robot.launch.py'"`.
  Never replace it with your own `source` / `export` lines.
- Packages are **ament_python** with exactly the layout of `labs/lab_3`: `package.xml`, `setup.py`,
  `setup.cfg`, `resource/<pkg>`, `<pkg>/__init__.py`, console_scripts entry points. No CMake,
  no custom messages.
- Our nodes run on the **Remote PC**. Only the `camera` package runs on the **Pi**.

```
AGENTS.md, specs/          instructions (this)
Resources/camera/          camera package for the Pi (from our teammate): copy d2_full_route/src/camera
labs/, final_project/      course starter code and lab PDFs (read-only)
d1_bayes_sim/              Deliverable 1   (plain Python, no ROS)
d2_full_route/             Deliverable 2   package: route_follower
d3_bayes_node/             Deliverable 3   package: bayes_localization
d4_mail_delivery/          Deliverable 4   package: mail_robot
```

Each deliverable folder is fully self-contained: its own `README.md`, `setup.sh`, its own
`src/camera` (copy `d2_full_route/src/camera`: the teammate's package with both camera
subscriptions switched to `qos_profile_sensor_data`, without which a best-effort camera driver
gives no images), and its own copy of any shared helper. No imports across
folders. Package names differ, so all deliverables can be built side by side.

## ROS interfaces

| Topic | Type | Notes |
|---|---|---|
| `/cmd_vel` | `geometry_msgs/TwistStamped` | set `header.stamp`; `twist.linear.x` [m/s], `twist.angular.z` [rad/s] |
| `/line_idx` | `std_msgs/UInt32` | column (0-639) of the brightest stripe = the white tape, 320 = centred. From `camera_mono` |
| `/mean_img_rgb` | `std_msgs/Float64MultiArray` | `data = [r, g, b]` (0-255), mean of the top 200 image rows. From `camera_rgb` |
| `/odom` | `nav_msgs/Odometry` | subscribe with `qos_profile_sensor_data`; yaw as in `labs/lab_0/lab_0/odometry.py` |

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
  press Enter", average ~30 `/mean_img_rgb` samples, save all to `~/rob301_colors.json`
  (`{"blue": [r, g, b], ..., "line": [r, g, b]}`). Then print the live classification for ~10 s
  so the user can check it.
- Classifier: nearest calibrated mean RGB (Euclidean). If the file is missing, use hard-coded
  defaults and log a loud warning.
- Debounce: switch between "on patch" and "on line" only after 3 consecutive frames agree.
- On a patch `/line_idx` is meaningless: drive straight (turn 0) until the line is back.

## Code rules

- One demo node per deliverable + a ROS-free `logic.py` (Bayes filter, classifier, PID) so the
  math can be tested with plain Python on Windows.
- Line following: PID on the error `320 - line_idx` (Lab 2 PDF), turn rate clipped to ±0.5 rad/s.
  Start conservative: SPEED 0.05 m/s, P only, KP ≈ 0.002 (rad/s per pixel). Tuned on the robot.
- Ctrl+C must stop the robot: init rclpy with `SignalHandlerOptions.NO`, catch
  KeyboardInterrupt, publish zero velocity a few times, then shut down.
- Tunable constants in one clearly marked block at the top of the node file.
- Do not move until `/line_idx` and `/mean_img_rgb` are both arriving; if either is older than
  1 s, stop the robot and log a warning.
- LF line endings for all `.sh` and `.py` (add `.gitattributes` with `* text=auto eol=lf`).

## Every robot deliverable (D2-D4) ships

**`setup.sh <PI_IP> [--launch] [--calibrate]`**: copy `d2_full_route/setup.sh` (the fixed,
known-good version) and change only `PKG`, the demo command in step 7 and any extra tabs the spec
asks for. Do not redesign it. Its steps: 1 ping + PC IP, 2 ssh key (`~/.ssh/id_ed25519`),
3 `ROS_STATIC_PEERS` / `ROS_DOMAIN_ID` in both `~/.bashrc`, 4 Pi: fix + check its ROS environment,
copy and build `camera` in `~/turtlebot3_ws`, 5 PC: symlink + build the package in `~/ros2_ws`,
6 `ros2 daemon stop` on both (`|| true`), 7 `--launch`: terminal tabs + topic check + demo tab.

Rules it follows, keep them:

- Plain bash, lab3-style. Remote multi-line edits via `ssh pi@<PI_IP> bash -s -- args <<'EOF'`;
  no Python to edit files, no clever quoting.
- Pi commands that need the robot environment run through the Pi's `~/.bashrc` (`bash -ic`, see
  Workspace above). Its "cannot set terminal process group / no job control" warnings without a
  tty are harmless noise.
- Pi workspace is `~/turtlebot3_ws`, hard-coded. Building `camera` only needs
  `source /opt/ros/jazzy/setup.bash && cd ~/turtlebot3_ws && colcon build --packages-select camera`.
- Before launching, check (through the Pi's `~/.bashrc`) that `turtlebot3_bringup`, `camera` and
  `v4l2_camera` are found and `TURTLEBOT3_MODEL` / `LDS_MODEL` are set; if not, print the Pi's
  `~/.bashrc` ROS lines and stop with a clear message.
- Commands that legitimately "fail" when nothing is wrong (`ros2 daemon stop`) get `|| true`.
- Never run `bash -i` / `bash -ic` on the PC from inside the script: the interactive shell takes
  over the terminal and the script gets `[1]+ Stopped`. In the script, `source
  /opt/ros/jazzy/setup.bash` and export `ROS_STATIC_PEERS` / `ROS_DOMAIN_ID` directly; read values
  from `~/.bashrc` with grep. `bash -ic` is fine only inside a new gnome-terminal tab or on the Pi
  over ssh.
- Every README has a "Start the robot by hand" box near the top: the exact [PC] `ros2 run`
  commands to calibrate and start the demo once bringup and the camera are up.
- Topic checks poll (`ros2 topic list` every 5 s, up to 90 s): the Pi 3B is slow to start and a
  just-restarted daemon misses topics on the first call. A failed check only warns; it never
  stops the script before the demo tab opens (the node itself waits for its topics).
- Every README has a "Robot does not move" checklist: `ros2 node list` (our node + bringup),
  `ros2 topic hz` of the input topics, `ros2 topic echo /cmd_vel --once`.

**`README.md`**: what the demo shows; one-shot path (`git clone` the repo on the Remote PC,
`bash <folder>/setup.sh <PI_IP> --launch`, open new terminals afterwards); manual path as a table
of terminals labelled [PI] / [PC] with exact commands ([PI] rows are just `ssh pi@<PI_IP>` then
the `ros2 launch` command, no extra `source` / `export`); the TA demo step by step; tuning knobs;
short troubleshooting (topics missing on the PC -> network step 3 and new terminals; robot turns
away from the line -> flip KP sign; patches missed -> recalibrate). Every command labelled [PC]
or [PI].

## Before you finish

No ROS on this machine, so: `python -m py_compile` every `.py`, test `logic.py` with plain-Python
asserts, `bash -n` every `.sh`. Say clearly what still needs testing on the robot.
