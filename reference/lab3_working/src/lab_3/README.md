# lab_3: ROB301 Lab 3, EKF localization from the CN Tower bearing

Full step-by-step instructions: `TUTORIAL.md` next to the `src` folder.

## Build (Remote PC)

```bash
cd ~/turtlebot3_ws && colcon build --symlink-install --packages-select lab_2 lab_3
source ~/turtlebot3_ws/install/setup.bash        # in every new terminal
```

## Run

| Machine | Command |
|---|---|
| TurtleBot | `ros2 launch turtlebot3_bringup robot.launch.py` |
| TurtleBot | `ros2 launch camera camera.launch.py` (camera and `/line_idx`) |
| Remote PC | `ros2 launch lab_3 lab3.launch.py` (tower bearing `/scan_angle`, noisy speed `/cmd_vel_noisy`) |
| Remote PC | `ros2 run lab_3 localizer` (add `--ros-args -p use_lidar:=false` for 4.2) |
| Remote PC | `ros2 run lab_3 delivery` (line following + 2 s stop at each address) |
| Remote PC | `ros2 run lab_3 live_plot` (optional: live estimate and variance) |

Each localizer run is saved in `~/lab3_logs/` and plotted when you stop it with Ctrl+C.
To plot a run again: `ros2 run lab_3 plot_kf_log` (newest log) or
`ros2 run lab_3 plot_kf_log ~/lab3_logs/<file>.csv`.

## Things to set

| File | Constant | What |
|---|---|---|
| `localizer.py` | `h`, `d` | tower position measured on your course [m] |
| `localizer.py` | `Q`, `R`, `P_0` | filter tuning |
| `scan_angle_publisher.py` | `ANGLE_OFFSET_DEG` | lidar calibration (Section 4.3) |
| `delivery.py` | `SPEED`, `KP`, `KI`, `KD` | line following (same as lab_2) |

## Tips

* On Jazzy the velocity topics are `TwistStamped`: the speed is `msg.twist.linear.x`.
* The tower detector takes anything 0.50–0.65 m to the left of the robot and within 2 m
  for the tower. Keep that area clear, people included, especially near the start.
