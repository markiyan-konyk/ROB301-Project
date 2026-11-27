#!/usr/bin/env python3

"""
Extended Kalman filter (EKF) for 1-D localization along Bloor St.

ROB301 Lab 3. Symbols (SI units throughout):

    x       robot position along the line [m]            (the state)
    u       commanded forward speed [m/s]                (/cmd_vel_noisy)
    phi     bearing of the CN Tower [rad], measured counter-clockwise
            from the robot's heading (+x)                (/scan_angle)
    (d, h)  tower position (x_CN, y_CN) [m]
    T       time between filter iterations [s]
    P       variance of the position estimate [m^2]
    Q       process-noise intensity [m^2/s]
    R       variance of one bearing measurement [rad^2]

Usage
    EKF (Section 4.4):          ros2 run lab_3 localizer
    Dead reckoning (4.2):       ros2 run lab_3 localizer --ros-args -p use_lidar:=false
    Bonus (wrong start):        ros2 run lab_3 localizer --ros-args -p x_0:=0.5 -p P_0:=0.25

Every run is logged to ~/lab3_logs/*.csv and plotted automatically when the node
stops (Ctrl+C). Plot a log again with: ros2 run lab_3 plot_kf_log
"""

import csv
import importlib
import math
import os
import signal
import subprocess
import time

from geometry_msgs.msg import TwistStamped
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import Float64

# Values of the `status` column in the CSV log
PREDICT_ONLY = 0   # no new bearing this step: prediction only
UPDATED = 1        # bearing fused into the estimate
REJECTED = -1      # bearing rejected by the outlier gate (bonus)

GATE = 3.0         # reject bearings more than 3 standard deviations from expected


class KalmanFilter(Node):

    def __init__(self, h, d, x_0, Q, R, P_0):
        super().__init__('localizer')

        self.h = h
        self.d = d

        self.Q = Q
        self.R = R

        # Start position [m] and its variance [m^2]. Can be changed from the command
        # line for the bonus, e.g.  --ros-args -p x_0:=0.5 -p P_0:=0.25
        # (always type a decimal point, 1.0 not 1)
        self.x = float(self.declare_parameter('x_0', x_0).value)
        self.P = float(self.declare_parameter('P_0', P_0).value)

        # False -> pure dead reckoning (unfiltered baseline, Section 4.2)
        self.use_lidar = bool(self.declare_parameter('use_lidar', True).value)

        self.u = 0.0
        self.phi = 0.0
        # Set by scan_callback when a new bearing arrives. Bearings come at the
        # lidar rate (~5 Hz) and stop while the tower is hidden, but run_kf runs at
        # 30 Hz: use each bearing once, then clear the flag.
        self.new_measurement = False

        self.t0 = self.get_clock().now()
        self.last_time = self.t0     # time of the previous filter step

        self.state_pub = self.create_publisher(
            Float64,
            'state',
            1
        )

        self.cov_pub = self.create_publisher(
            Float64,
            'state_covariance',
            1
        )

        self.scan_sub = self.create_subscription(
            Float64,
            'scan_angle',
            self.scan_callback,
            1
        )

        self.cmd_sub = self.create_subscription(
            TwistStamped,
            'cmd_vel_noisy',
            self.cmd_callback,
            1
        )

        log_dir = str(self.declare_parameter('log_dir', '~/lab3_logs').value)
        self.log_path = None
        self.log_file, self.log = self._open_log(log_dir)

        # Run the Kalman filter at 30 Hz
        self.timer = self.create_timer(
            1.0 / 30.0,
            self.run_kf
        )

    def _open_log(self, log_dir):
        if log_dir.strip().lower() in ('', 'none', 'off', 'false'):
            return None, None
        log_dir = os.path.expanduser(log_dir)
        os.makedirs(log_dir, exist_ok=True)
        tag = 'ekf' if self.use_lidar else 'deadreckoning'
        path = os.path.join(log_dir, f'{tag}_{time.strftime("%Y%m%d-%H%M%S")}.csv')
        self.log_path = path
        f = open(path, 'w', newline='')
        f.write(f'# h={self.h} d={self.d} x_0={self.x} P_0={self.P} Q={self.Q} '
                f'R={self.R} use_lidar={self.use_lidar} '
                f't0={self.t0.nanoseconds * 1e-9:.3f}\n')
        writer = csv.writer(f)
        writer.writerow(['t', 'x_hat', 'P', 'u', 'z', 'z_pred', 'innovation', 'K', 'status'])
        self.get_logger().info(
            f'Logging to {path}  (plot with: ros2 run lab_3 plot_kf_log {path})')
        return f, writer

    def cmd_callback(self, cmd_msg):
        # TwistStamped wraps the velocities in .twist
        self.u = cmd_msg.twist.linear.x

    # Store the most recent bearing and flag it as new
    def scan_callback(self, msg):
        self.phi = msg.data
        self.new_measurement = True

    # Call within run_kf to propagate the state with the motion model
    def predict(self, u, T):
        """
        Motion model:  x_k+1 = x_k + T u_k        (A_k = 1, B_k = T)

        The variance grows by the process noise: P_k+1 = P_k + Q T
        """
        self.x = self.x + T * u
        self.P = self.P + self.Q * T

    # Call within run_kf to update the state with the measurement
    def measurement_update(self, z):
        """
        Measurement model:  phi = atan2(h, d - x)
        Linearized:         D_k = d phi / dx = h / ((d - x)^2 + h^2)

        Returns (z_pred, innovation, K, status) for the log.
        """
        dx = self.d - self.x
        z_pred = math.atan2(self.h, dx)            # bearing we expect to see
        D = self.h / (dx * dx + self.h * self.h)   # slope of the measurement model
        S = D * self.P * D + self.R                # variance of the innovation
        innovation = z - z_pred

        # Bonus: ignore a bearing that is far from what we expect (more than
        # GATE standard deviations), e.g. a person standing next to the robot
        if innovation * innovation > GATE * GATE * S:
            return z_pred, innovation, float('nan'), REJECTED

        K = self.P * D / S                         # Kalman gain
        self.x = self.x + K * innovation
        self.P = (1.0 - K * D) * self.P
        return z_pred, innovation, K, UPDATED

    def run_kf(self):
        now = self.get_clock().now()
        T = (now - self.last_time).nanoseconds * 1e-9   # time since last step [s]
        self.last_time = now
        current_input = self.u

        # Written to the CSV log for plot_kf_log.
        # z: bearing used, z_pred: bearing the prediction expects, innovation: their
        # difference, K: Kalman gain, status: PREDICT_ONLY / UPDATED / REJECTED.
        z = z_pred = innovation = K = float('nan')
        status = PREDICT_ONLY

        # Prediction step (every call)
        self.predict(current_input, T)

        # Correction step (only when a new bearing arrived, and only in EKF mode;
        # use_lidar False = dead reckoning, Section 4.2)
        if self.new_measurement:
            self.new_measurement = False
            z = self.phi
            if self.use_lidar:
                z_pred, innovation, K, status = self.measurement_update(z)
                if status == REJECTED:
                    self.get_logger().warn(
                        f'Bearing {math.degrees(z):.1f} deg rejected as an outlier '
                        f'(expected {math.degrees(z_pred):.1f} deg)',
                        throttle_duration_sec=1.0)

        msg = Float64()
        msg.data = float(self.x)
        self.state_pub.publish(msg)

        cov = Float64()
        cov.data = float(self.P)
        self.cov_pub.publish(cov)

        if self.log is not None:
            t = (now - self.t0).nanoseconds * 1e-9
            self.log.writerow([f'{t:.4f}', f'{self.x:.5f}', f'{self.P:.6g}',
                               f'{current_input:.4f}', f'{z:.5f}', f'{z_pred:.5f}',
                               f'{innovation:.5f}', f'{K:.5f}', status])

        self.get_logger().info(
            f'x = {self.x:6.3f} m   2-sigma = {2.0 * math.sqrt(self.P):.3f} m',
            throttle_duration_sec=1.0)

    def destroy_node(self):
        if self.log_file is not None:
            self.log_file.close()
            self.log_file = self.log = None
        super().destroy_node()


def save_and_show_plot(path):
    """Plot a finished run next to its CSV and open the PNG on screen (best effort)."""
    try:
        from lab_3.plot_kf_log import main as plot_main
        png = plot_main([path])
    except (Exception, SystemExit) as e:
        print(f'Could not plot {path}: {e}')
        return
    if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
        try:
            subprocess.Popen(['xdg-open', png], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass


def preload_plotting():
    """Import matplotlib now, so plotting at shutdown is quick."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        importlib.import_module('matplotlib.pyplot')
    except Exception:
        pass


def main(args=None):
    # Ctrl+C is handled here rather than by rclpy, so the log can be closed and plotted.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)

    # MEASURE THESE ON YOUR COURSE (tape measure, see the tutorial)
    h = 0.60            # y_CN: distance from the line to the tower centre [m]
    d = 1.80            # x_CN: tower centre along the line from O [m]

    x_0 = 0.0           # the robot starts at the origin O

    # Filter tuning
    Q = 1e-4                    # process-noise intensity [m^2/s] (bigger = trust odometry less)
    R = math.radians(2.0) ** 2  # bearing variance [rad^2] (2 deg standard deviation)
    P_0 = 0.01                  # initial variance [m^2] (10 cm standard deviation)

    kf = KalmanFilter(h, d, x_0, Q, R, P_0)
    preload_plotting()

    try:
        rclpy.spin(kf)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        # A second Ctrl+C must not cut the clean-up short
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        kf.destroy_node()
        rclpy.try_shutdown()
        if kf.log_path is not None:
            save_and_show_plot(kf.log_path)


if __name__ == '__main__':
    main()
