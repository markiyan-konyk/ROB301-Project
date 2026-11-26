"""Stationary calibration and live color monitor; never publishes velocity."""
import json
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import Float64MultiArray

from .logic import CLASSES, COLOR_FILE, classify, load_colors, valid_rgb

SAMPLES = 30
SAMPLE_TIMEOUT = 15.0
PREVIEW_SECONDS = 10.0


class ColorReader(Node):
    def __init__(self):
        super().__init__('color_reader')
        self.latest = None
        self.received = None
        self.samples = None
        self.create_subscription(Float64MultiArray, '/mean_img_rgb', self.on_rgb, qos_profile_sensor_data)

    def on_rgb(self, msg):
        if valid_rgb(msg.data):
            self.latest = list(msg.data)
            self.received = time.monotonic()
            if self.samples is not None:
                self.samples.append(self.latest)

    def monitor(self, means, duration=None):
        start = time.monotonic()
        next_print = start
        while duration is None or time.monotonic()-start < duration:
            rclpy.spin_once(self, timeout_sec=0.1)
            now = time.monotonic()
            if now >= next_print:
                if self.received is None or now-self.received > 1:
                    print('Waiting for fresh /mean_img_rgb', flush=True)
                else:
                    print(f'RGB {[round(x, 1) for x in self.latest]} -> {classify(self.latest, means)}', flush=True)
                next_print = now + 0.5


def run(calibrate, args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = ColorReader()
    try:
        if calibrate:
            means = {}
            for color in CLASSES:
                input(f'Place the robot on {color}, press Enter')
                # Drain previously queued readings before collecting this placement.
                end = time.monotonic() + 0.25
                while time.monotonic() < end:
                    rclpy.spin_once(node, timeout_sec=0.05)
                node.samples = []
                end = time.monotonic() + SAMPLE_TIMEOUT
                while len(node.samples) < SAMPLES:
                    if time.monotonic() >= end:
                        raise RuntimeError('Timed out collecting RGB; check camera/network. Calibration not saved.')
                    rclpy.spin_once(node, timeout_sec=0.1)
                means[color] = [sum(s[i] for s in node.samples[:SAMPLES])/SAMPLES for i in range(3)]
                node.samples = None
                print(f'{color}: {means[color]}', flush=True)
            temporary = COLOR_FILE.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(means, indent=2) + '\n')
            temporary.replace(COLOR_FILE)
            print(f'Saved {COLOR_FILE}. Move across patches and line for a 10 s check.', flush=True)
            node.monitor(means, PREVIEW_SECONDS)
        else:
            means, warning = load_colors()
            if warning:
                node.get_logger().warning(warning)
            node.monitor(means)
    except (KeyboardInterrupt, EOFError):
        if calibrate:
            raise SystemExit('Calibration interrupted; demo will not start.')
    except (OSError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        node.destroy_node()
        rclpy.shutdown()


def calibrate_main(args=None):
    run(True, args)


def monitor_main(args=None):
    run(False, args)
