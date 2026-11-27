# ROB301 Lab 3, step by step

## 0. Read this first

There are two computers:

* **Remote PC**: the lab desktop (Ubuntu 24.04, ROS 2 Jazzy). You type everything here.
* **Pi**: the TurtleBot's Raspberry Pi. You reach it from a Remote PC terminal with ssh.

Every command block below is labelled:

* **[PC]**: a normal terminal on the Remote PC.
* **[PI]**: a Remote PC terminal in which you first ran `ssh pi@<PI_IP>` (password `turtlebot`).
  The prompt changes to `pi@...`.

Replace `<PI_IP>` with your robot's IP and `<PC_IP>` with the Remote PC's IP (step 2 shows how
to find it). A number after the label (`[PI 1]`, `[PC 2]`) means "keep this terminal open,
it keeps running".

### What runs where

| Terminal | What | Command |
|---|---|---|
| [PI 1] | robot drivers (motors, lidar `/scan`) | `ros2 launch turtlebot3_bringup robot.launch.py` |
| [PI 2] | camera + `/line_idx` | `ros2 launch camera camera.launch.py` |
| [PC 1] | tower bearing `/scan_angle` + noisy speed `/cmd_vel_noisy` | `ros2 launch lab_3 lab3.launch.py` |
| [PC 2] | the filter (`/state`, `/state_covariance`) | `ros2 run lab_3 localizer` |
| [PC 3] | line following + 2 s stop at each address | `ros2 run lab_3 delivery` |
| [PC 4] | optional live plot | `ros2 run lab_3 live_plot` |

### Where the code lives

| Package | Machine | Folder |
|---|---|---|
| `camera` | Pi | `~/turtlebot3_ws/src/camera` (copied there) |
| `lab_2`, `lab_3` | Remote PC | `~/turtlebot3_ws/src/` (links to `~/lab3/src/`) |

**Always edit the code in `~/lab3/src/` on the Remote PC.** The Remote PC workspace links
to it, so edits to `lab_2`/`lab_3` are live the next time you `ros2 run` (no rebuild).
Edits to `camera` must be copied to the Pi again (step 3, or rerun the script).

### Mistakes in the lab manuals

| Manual says | Correct |
|---|---|
| `ros2 run camera camera.launch.py` | `ros2 launch camera camera.launch.py` |
| `ros2 launch turtlebot3_bringup turtlebot3_robot.launch` | `ros2 launch turtlebot3_bringup robot.launch.py` |
| Lab 2: bringup on [Remote PC], lab_2 on [Turtlebot PC] | the other way round: bringup always runs on the Pi |

---

## 1. Put the files on the Remote PC (once)

Copy the whole `lab3` folder (the one containing `src/`, `TUTORIAL.md`, `lab3_setup.sh`)
to the Remote PC's home folder by USB stick, OneDrive, email, or git. Check:

**[PC]**
```bash
ls ~/lab3/src          # must show: camera  lab_2  lab_3
```

> **Shortcut:** `bash ~/lab3/lab3_setup.sh <PI_IP>` does steps 2 and 3 for you
> (network config on both machines, copy, build). Add `--launch` to also open the [PI 1],
> [PI 2] and [PC 1] terminals. Then go to step 4 (open **new** terminals first).

---

## 2. Network (every session: the Pi's IP can change)

ROS 2 here only talks to the machines listed in `ROS_STATIC_PEERS`. **Each machine must list
the other machine's current IP**, and `ROS_DOMAIN_ID` must be the same on both. If either is
wrong, topics like `/line_idx` exist on the Pi but never show up on the Remote PC.

**2.1** Turn the robot on (plug in the battery) and wait about a minute until the lidar spins.

**2.2** Find the IPs.

**[PC]**
```bash
ping -c 3 <PI_IP>                      # must get replies
ip route get <PI_IP>                   # the number after "src" is <PC_IP>
```

**2.3** Check the settings on both machines.

**[PC]**
```bash
echo $ROS_STATIC_PEERS                 # must be <PI_IP>
echo $ROS_DOMAIN_ID                    # note this number (empty = 0)
```

**[PI]**
```bash
ssh pi@<PI_IP>                         # password: turtlebot
echo $ROS_STATIC_PEERS                 # must be <PC_IP>
echo $ROS_DOMAIN_ID                    # must be the same as on the PC
```

**2.4** Only if something was wrong, fix it. Each command removes the old line from `~/.bashrc`
and writes the correct one.

**[PC]**
```bash
sed -i '/ROS_STATIC_PEERS/d' ~/.bashrc && echo "export ROS_STATIC_PEERS=<PI_IP>" >> ~/.bashrc
```

**[PI]**
```bash
sed -i '/ROS_STATIC_PEERS/d' ~/.bashrc && echo "export ROS_STATIC_PEERS=<PC_IP>" >> ~/.bashrc
# only if the domain IDs differed (use the PC's number):
sed -i '/ROS_DOMAIN_ID/d' ~/.bashrc && echo "export ROS_DOMAIN_ID=<PC_DOMAIN_ID>" >> ~/.bashrc
```

Then **close every terminal (PC and PI) and open new ones**. Old terminals keep the old
values. In one new terminal on each machine run:

**[PC]** and **[PI]**
```bash
ros2 daemon stop                       # forget old discovery info
```

---

## 3. Copy and build the code

### 3.1 Pi: the camera package

**[PC]**: copy it (removes the old copy on the Pi first):
```bash
ssh pi@<PI_IP> "rm -rf ~/turtlebot3_ws/src/camera"
scp -r ~/lab3/src/camera pi@<PI_IP>:~/turtlebot3_ws/src/
```

**[PI]**: build it (1-2 min on the Pi):
```bash
cd ~/turtlebot3_ws
rm -rf build/camera install/camera
colcon build --symlink-install --packages-select camera
source ~/turtlebot3_ws/install/setup.bash
```

### 3.2 Remote PC: lab_2 and lab_3

**[PC]**: link the code into the workspace. If `~/turtlebot3_ws/src/lab_2` or `lab_3`
already exist from an old attempt, the `mv` moves them to `~/lab3_old/`.
```bash
mkdir -p ~/turtlebot3_ws/src ~/lab3_old
for p in lab_2 lab_3; do
  [ -e ~/turtlebot3_ws/src/$p ] && [ ! -L ~/turtlebot3_ws/src/$p ] && mv ~/turtlebot3_ws/src/$p ~/lab3_old/$p-$(date +%s)
  ln -sfn ~/lab3/src/$p ~/turtlebot3_ws/src/$p
done
```

**[PC]**: build:
```bash
cd ~/turtlebot3_ws
rm -rf build/lab_2 build/lab_3 install/lab_2 install/lab_3
colcon build --symlink-install --packages-select lab_2 lab_3
source ~/turtlebot3_ws/install/setup.bash
```

**[PC]**: make every new terminal source the workspace (once):
```bash
grep -q "turtlebot3_ws/install/setup.bash" ~/.bashrc || echo "source ~/turtlebot3_ws/install/setup.bash" >> ~/.bashrc
```

Check: `ros2 pkg executables lab_3` must list `delivery`, `localizer`, `scan_angle_publisher`, ...

---

## 4. Start the robot and check /line_idx

**[PI 1]**: robot drivers, leave running:
```bash
ssh pi@<PI_IP>
ros2 launch turtlebot3_bringup robot.launch.py
```

**[PI 2]**: camera, leave running:
```bash
ssh pi@<PI_IP>
ros2 launch camera camera.launch.py
```
Wait for the line `Got images (640x480), publishing /line_idx`.

**Check on the Pi first.**

**[PI]**: a third ssh terminal:
```bash
ros2 topic hz /line_idx                # about 10-30 Hz. Ctrl+C to stop.
```

**Then check on the Remote PC.**

**[PC]**
```bash
ros2 topic list                        # must include /scan /cmd_vel /odom /line_idx
ros2 topic hz /line_idx                # same rate as on the Pi
ros2 topic echo /line_idx              # about 320 when the tape is in the middle of the image
```
Slide the robot by hand left/right across the tape: the number must follow the tape. If it
sits near 0 or 640, or jumps around, see "line_idx doesn't follow the tape" in step 6.

If it works on the Pi but not on the PC, the problem is step 2 (network), not the code.

---

## 5. Lab 3 demos

### 5.0 Measure the course (once)

* **O** is the start of the line. **x** runs along the line, the tower is on the robot's
  **left**. Use the lidar (the spinning part on top) as "the robot's position".
* `d` is the distance along the line from O to the point closest to the tower centre [m].
* `h` is the distance from the line to the tower centre [m].

Put both in `~/lab3/src/lab_3/lab_3/localizer.py`:
```python
h = 0.60            # y_CN
d = 1.80            # x_CN
```

The tower detector accepts anything 0.50-0.65 m to the left of the robot and within 2 m.
If your `h` is far from 0.6 m, change `Y_MIN, Y_MAX` in `scan_angle_publisher.py` so that
`h - tower radius` falls inside. Keep that strip clear: people count as towers.

### 5.1 Section 4.1: line following (tuning, no demo needed)

Robot on the line.

**[PC 1]**
```bash
ros2 run lab_2 lab_2
```
Ctrl+C stops the robot. Tune `KP` (then `KI`, `KD`, `SPEED`) at the top of
`~/lab3/src/lab_2/lab_2/lab_2.py` and run again (no rebuild needed). If the robot turns
**away** from the line, flip the sign of `KP`.

**Copy your final gains into the top of `~/lab3/src/lab_3/lab_3/delivery.py`.**

### 5.2 Section 4.2: unfiltered localization (dead reckoning), demo to TA

Robot at **O**, on the line, facing +x. Start these in order:

**[PC 1]**
```bash
ros2 launch lab_3 lab3.launch.py
```
**[PC 2]**
```bash
ros2 run lab_3 localizer --ros-args -p use_lidar:=false
```
**[PC 3]**
```bash
ros2 run lab_3 delivery
```

The robot drives and stops for 2 s at 61, 122, 244 and 305 cm (according to its own
estimate). At each stop, measure the real position with a tape measure and write down
the error. After the last stop:

* Ctrl+C in **[PC 3]** (delivery).
* Ctrl+C in **[PC 2]** (localizer): the plot is saved as `~/lab3_logs/deadreckoning_<time>.png`
  and opens on screen.

For another run: put the robot back at O and restart **[PC 2]** and **[PC 3]**. **[PC 1]**
can keep running.

### 5.3 Section 4.3: lidar calibration, demo to TA

**[PC 1]**: if not already running:
```bash
ros2 launch lab_3 lab3.launch.py
```
It prints `raw ... deg   published ... deg` once per second.

1. Put the robot on the line at x = d, facing +x. The tower is now exactly to the left,
   so the true bearing is **90°**.
2. Read the `raw` angle, e.g. `raw 86.0 deg`.
3. In `~/lab3/src/lab_3/lab_3/scan_angle_publisher.py` set
   `ANGLE_OFFSET_DEG = 90 - raw` (here `4.0`).
4. Ctrl+C **[PC 1]**, start it again. `published` must now be within 1° of 90.
5. Check a second spot: at x = d - h the true bearing is 45°.

### 5.4 Section 4.4: EKF, demo to TA (twice)

Same as 5.2 but with the filter on. Robot at **O**.

**[PC 1]**
```bash
ros2 launch lab_3 lab3.launch.py        # keep running from before, or start it
```
**[PC 2]**
```bash
ros2 run lab_3 localizer
```
**[PC 4]** (optional, live estimate and variance):
```bash
ros2 run lab_3 live_plot
```
**[PC 3]**
```bash
ros2 run lab_3 delivery
```

* **Run 1, no obstructions.** Measure the error at each stop as in 5.2. Ctrl+C **[PC 3]**,
  then **[PC 2]**: the plot (`~/lab3_logs/ekf_<time>.png`) shows the estimate, the ±2σ band
  and when the tower was seen.
* **Run 2, with obstructions** (the TA blocks the tower). Same commands. The variance grows
  while the tower is hidden and shrinks again when it is seen.

### 5.5 Bonus: wrong starting guess

Robot really at **O**, but tell the filter it is somewhere else, with a variance that
covers the error:

**[PC 2]**
```bash
ros2 run lab_3 localizer --ros-args -p x_0:=0.5 -p P_0:=0.25
```
(Always write numbers with a decimal point: `1.0`, not `1`.) If `P_0` is too small for the
error, the filter rejects every bearing as an outlier (marked in the plot, warnings in
the terminal): increase `P_0`.

### 5.6 Plot a run again

**[PC]**
```bash
ros2 run lab_3 plot_kf_log                               # newest run
ros2 run lab_3 plot_kf_log ~/lab3_logs/ekf_<time>.csv    # a specific run
```

### 5.7 Shut down

Ctrl+C in every terminal: delivery first (stops the robot), bringup **[PI 1]** last.

---

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| `/line_idx` missing on the **PC** but fine on the **Pi** | Network: redo step 2 on **both** machines, open **new** terminals, `ros2 daemon stop` on both. |
| `/line_idx` missing on the **Pi** too | Is **[PI 2]** running without errors? `Package 'camera' not found` means redo step 3.1 in that terminal (or `source ~/turtlebot3_ws/install/setup.bash`). |
| [PI 2] says `Waiting for camera images...` forever | **[PI]** `ros2 topic hz /image_raw`. No images means the camera driver failed: read the errors in [PI 2], check `ls /dev/video*`, make sure no second camera node is running (`ros2 node list`; do **not** also run `ros2 run v4l2_camera v4l2_camera_node`), reseat the ribbon cable, `sudo reboot` the Pi. |
| `No module named cv_bridge` in [PI 2] | Ask the TA (`sudo apt install ros-jazzy-cv-bridge`). |
| `line_idx` doesn't follow the tape | In `~/lab3/src/camera/camera/camera_mono.py` flip `LINE_IS_DARK` (`True` = black tape on a light floor). Copy and rebuild on the Pi (step 3.1), restart [PI 2]. |
| `ros2 run camera camera.launch.py` error | It's `ros2 launch camera camera.launch.py`. |
| Bringup error about `TURTLEBOT3_MODEL` / `LDS_MODEL` | **[PI]** `echo $TURTLEBOT3_MODEL $LDS_MODEL` must print `waffle_pi LDS-0x`. Ask the TA. |
| `Package 'lab_3' not found` / `No executable found` | `source ~/turtlebot3_ws/install/setup.bash`. Still missing: rebuild (step 3.2). |
| An old version of the code runs | `ros2 pkg prefix lab_3` must print `.../turtlebot3_ws/install/lab_3`. If not, another workspace with a `lab_3` is sourced in `~/.bashrc`: remove that line. |
| colcon: `failed to create symbolic link ... Is a directory` | `rm -rf build/<pkg> install/<pkg>`, build again. |
| Robot doesn't move | Is [PI 1] running? Delivery prints `Waiting for /line_idx and /state` until both the camera and the localizer run. `ros2 topic echo /cmd_vel` must show messages. |
| Robot turns away from the line | Flip the sign of `KP`. |
| Robot wobbles a lot | Lower `KP` or `SPEED`, add a little `KD`. `ros2 topic hz /line_idx` should be above about 10 Hz. |
| `/scan_angle` prints nothing | Is `/scan` arriving on the PC (`ros2 topic hz /scan`)? Is the tower on the **left**, 0.50-0.65 m sideways and within 2 m? |
| Estimate jumps or bearings get rejected | Do the calibration (5.3), re-measure `h` and `d`, clear people out of the strip next to the robot. |
| `expecting type 'DOUBLE'` | Write `-p x_0:=1.0`, not `1`. |
| Plot didn't open | It's saved next to the CSV in `~/lab3_logs/` (`xdg-open ~/lab3_logs/<file>.png`). |
| ssh: `REMOTE HOST IDENTIFICATION HAS CHANGED` | Different robot with the same IP: `ssh-keygen -R <PI_IP>`. |
| Script: `/bin/bash^M: bad interpreter` or `$'\r': command not found` | The file got Windows line endings: `sed -i 's/\r$//' ~/lab3/lab3_setup.sh`. |
