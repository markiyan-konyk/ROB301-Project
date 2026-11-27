# lab_3: ROB301 Lab 3, EKF localization from the CN Tower bearing


Stopping at the Table 1 addresses and line following are your own code (your Lab 2
line follower).

Already provided: the noisy speed (`noisy_vel_publisher`), tower detection, a CSV log of
every localizer run and a plot of it, and a live plot.

## Build (Remote PC)

```bash
cd ~/ros2_ws && colcon build --packages-select lab_3 --symlink-install
source install/setup.bash        # in every new terminal
```

## Run

| Machine | Command |
|---|---|
| TurtleBot | `ros2 launch turtlebot3_bringup robot.launch.py` |
| TurtleBot | `ros2 launch camera camera.launch.py` (camera and `/line_idx`, as in Lab 2) |
| Remote PC | `ros2 launch lab_3 lab3.launch.py` (tower bearing `/scan_angle`, noisy speed `/cmd_vel_noisy`) |
| Remote PC | your line follower (publishes on `/cmd_vel`) |
| Remote PC | `ros2 run lab_3 localizer` (add `--ros-args -p use_lidar:=false` for 4.2) |
| Remote PC | `ros2 run lab_3 live_plot` (optional: live estimate and variance) |

Each localizer run is saved in `~/lab3_logs/` and plotted when you stop it with Ctrl+C.
To plot a run again: `ros2 run lab_3 plot_kf_log` (newest log) or
`ros2 run lab_3 plot_kf_log ~/lab3_logs/<file>.csv`.

## Tips

* On Jazzy the velocity topics are `TwistStamped`: the speed is `msg.twist.linear.x`.
* The tower detector takes anything 0.50–0.65 m to the left of the robot and within 2 m
  for the tower. Keep that area clear, people included, especially near the start.
