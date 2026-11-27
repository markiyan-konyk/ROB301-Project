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
REJECTED = -1      # bearing rejected (only if you add outlier rejection, bonus)


class KalmanFilter(Node):

    def __init__(self, h, d, x_0, Q, R, P_0):
        super().__init__('localizer')

        self.h = h
        self.d = d

        self.Q = Q
        self.R = R
        self.P = P_0
        self.x = x_0

        # False -> pure dead reckoning (unfiltered baseline, Section 4.2)
        self.use_lidar = bool(self.declare_parameter('use_lidar', True).value)

        self.u = 0.0
        self.phi = 0.0
        # Set by scan_callback when a new bearing arrives. Bearings come at the
        # lidar rate (~5 Hz) and stop while the tower is hidden, but run_kf runs at
        # 30 Hz: use each bearing once, then clear the flag.
        self.new_measurement = False

        self.t0 = self.get_clock().now()

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
    def predict(self, u=0):
        """
        TODO: update the state via the motion model.

        Also update the covariance with the process noise.
        """
        return

    # Call within run_kf to update the state with the measurement
    def measurement_update(self):
        """TODO: update the state when a new measurement has arrived."""
        return

    def run_kf(self):
        now = self.get_clock().now()
        current_input = self.u

        # Written to the CSV log for plot_kf_log. Set them in your update step:
        # z: bearing used, z_pred: bearing the prediction expects, innovation: their
        # difference, K: Kalman gain, status: PREDICT_ONLY / UPDATED / REJECTED.
        z = z_pred = innovation = K = float('nan')
        status = PREDICT_ONLY

        # TODO: prediction step with current_input (every call).

        if self.new_measurement:
            self.new_measurement = False
            current_measurement = self.phi
            z = current_measurement
            # TODO: correction step with current_measurement, only when
            # self.use_lidar is True (False = dead reckoning, Section 4.2).

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

    # TODO: measure the tower position on your course
    h = 0.60            # y_CN: distance from the line to the tower centre [m]
    d = 0.60 * 3        # x_CN: tower centre along the line from O [m]

    x_0 = 0.0           # the robot starts at the origin O

    # TODO: choose these
    Q = 1.0             # process-noise intensity [m^2/s]
    R = 1.0             # bearing-measurement variance [rad^2]
    P_0 = 1.0           # initial variance of the position estimate [m^2]

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
