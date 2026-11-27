#!/usr/bin/env python3

"""
Live plot of the localizer while a demo runs.

Top: position estimate /state with its 2-sigma band (2 * sqrt(/state_covariance))
and the four addresses. Bottom: the variance /state_covariance (log scale).

Run it next to the localizer while the robot drives. The localizer saves the
finished run as a PNG from its log when it stops, so this window is only for
watching.

    ros2 run lab_3 live_plot
"""

import math
import os
import signal

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import Float64

REDRAW_PERIOD = 0.2   # [s] between redraws


class LivePlot(Node):

    def __init__(self):
        super().__init__('live_plot')
        self.t0 = None
        self.P = None
        self.t, self.x, self.var = [], [], []
        self.create_subscription(Float64, 'state', self.state_cb, 10)
        self.create_subscription(Float64, 'state_covariance', self.cov_cb, 10)

    def cov_cb(self, msg):
        self.P = msg.data

    def state_cb(self, msg):
        if self.P is None:
            return
        now = self.get_clock().now().nanoseconds * 1e-9
        if self.t0 is None:
            self.t0 = now
        self.t.append(now - self.t0)
        self.x.append(msg.data)
        self.var.append(self.P)

    def make_figure(self, plt, addresses):
        fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(8, 6),
                                       gridspec_kw={'height_ratios': [3, 2]})
        fig.canvas.manager.set_window_title('Lab 3: live localizer')
        for name, xa in addresses:
            ax1.axhline(xa, color='#8a8984', lw=0.8, ls=':')
            ax1.annotate(f'{name} Bloor', (1.0, xa), xycoords=('axes fraction', 'data'),
                         xytext=(4, 0), textcoords='offset points', va='center',
                         fontsize=8, annotation_clip=False)
        (self.est_line,) = ax1.plot([], [], color='#2a78d6', lw=1.6, label='estimate')
        self.band = None
        ax1.set_ylabel('position x [m]')
        ax1.set_ylim(-0.2, 3.4)
        ax1.grid(True, alpha=0.3)
        (self.var_line,) = ax2.plot([], [], color='#2a78d6', lw=1.6)
        ax2.set_yscale('log')
        ax2.set_ylabel('variance P [m²]')
        ax2.set_xlabel('time [s]')
        ax2.grid(True, alpha=0.3)
        self.title = fig.suptitle('waiting for the localizer ...', fontsize=10)
        fig.tight_layout(rect=(0, 0, 0.93, 0.97))
        self.fig, self.ax1, self.ax2 = fig, ax1, ax2
        return fig

    def redraw(self):
        if not self.t:
            return
        t, x, var = list(self.t), list(self.x), list(self.var)
        n = min(len(t), len(x), len(var))
        t, x, var = t[:n], x[:n], var[:n]
        two_sigma = [2.0 * math.sqrt(max(v, 0.0)) for v in var]
        self.est_line.set_data(t, x)
        if self.band is not None:
            self.band.remove()
        self.band = self.ax1.fill_between(
            t, [a - b for a, b in zip(x, two_sigma)], [a + b for a, b in zip(x, two_sigma)],
            color='#2a78d6', alpha=0.18, lw=0)
        self.var_line.set_data(t, var)
        self.ax1.set_xlim(0.0, max(10.0, t[-1] * 1.05))
        positive = [v for v in var if v > 0]
        if positive:
            self.ax2.set_ylim(min(positive) * 0.5, max(positive) * 2.0)
        self.title.set_text(f'x = {x[-1]:.3f} m   ± {two_sigma[-1]:.3f} m (2σ)')
        self.fig.canvas.draw_idle()


def main(args=None):
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        print('live_plot: no screen available, live view disabled.')
        return
    import matplotlib.pyplot as plt
    if plt.get_backend().lower() == 'agg':
        print('live_plot: matplotlib has no window backend, live view disabled.')
        return
    from lab_3.plot_kf_log import ADDRESSES

    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    stop = []
    signal.signal(signal.SIGINT, lambda *_: stop.append(True))   # close quietly on Ctrl+C
    node = LivePlot()
    fig = node.make_figure(plt, ADDRESSES)
    plt.show(block=False)
    last = 0.0
    try:
        while rclpy.ok() and not stop and plt.fignum_exists(fig.number):
            rclpy.spin_once(node, timeout_sec=0.02)
            now = node.get_clock().now().nanoseconds * 1e-9
            if now - last > REDRAW_PERIOD:
                node.redraw()
                last = now
            plt.pause(0.001)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        plt.close('all')
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
