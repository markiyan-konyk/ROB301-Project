"""ROS-free color classification, PID, and route state machine."""
import json
import math
from pathlib import Path

CLASSES = ('blue', 'green', 'yellow', 'orange', 'line')
DEFAULT_COLORS = {
    'blue': [40, 60, 180], 'green': [50, 160, 60],
    'yellow': [210, 200, 50], 'orange': [220, 110, 30],
    'line': [160, 160, 160],
}
COLOR_FILE = Path.home() / 'rob301_colors.json'


def valid_rgb(rgb):
    return len(rgb) == 3 and all(math.isfinite(x) and 0 <= x <= 255 for x in rgb)


def load_colors(path=COLOR_FILE):
    """Return means and a warning (None on success)."""
    try:
        means = json.loads(Path(path).read_text())
        if not all(valid_rgb(means[c]) for c in CLASSES):
            raise ValueError('expected three finite RGB values in [0, 255] per class')
        return {c: means[c] for c in CLASSES}, None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return DEFAULT_COLORS.copy(), f'WARNING: USING UNCALIBRATED DEFAULT COLORS: {exc}. Run calibrate_colors!'


def classify(rgb, means):
    if not valid_rgb(rgb):
        raise ValueError('invalid RGB sample')
    return min(CLASSES, key=lambda c: sum((a-b)**2 for a, b in zip(rgb, means[c])))


class PID:
    def __init__(self, kp, ki, kd, limit):
        self.kp, self.ki, self.kd, self.limit = kp, ki, kd, limit
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.previous = None

    def update(self, error, dt):
        if dt <= 0:
            raise ValueError('dt must be positive')
        derivative = 0 if self.previous is None else (error-self.previous)/dt
        candidate = self.integral + error*dt
        raw = self.kp*error + self.ki*candidate + self.kd*derivative
        # Integrate only if not saturating further in the same direction.
        if abs(raw) <= self.limit or raw*self.ki*error < 0:
            self.integral = candidate
        self.previous = error
        return max(-self.limit, min(self.limit, raw))


class Route:
    def __init__(self, offices=11, debounce=3):
        if offices < 1 or debounce < 1:
            raise ValueError('offices and debounce must be positive')
        self.target, self.debounce = offices, debounce
        self.state = 'ON_PATCH'
        self.count = 0
        self.reset_pending()

    def reset_pending(self):
        self.pending = None
        self.frames = 0

    def observe(self, color):
        """Call once per fresh RGB frame; return a reached patch's color."""
        if color not in CLASSES:
            raise ValueError('unknown color')
        if self.state == 'DONE':
            return None
        kind = 'line' if color == 'line' else 'patch'
        self.frames = self.frames + 1 if kind == self.pending else 1
        self.pending = kind
        if self.frames < self.debounce:
            return None
        if self.state == 'ON_PATCH' and kind == 'line':
            self.state = 'FOLLOW_LINE'
        elif self.state == 'FOLLOW_LINE' and kind == 'patch':
            self.count += 1
            self.state = 'DONE' if self.count >= self.target else 'ON_PATCH'
            return color
        return None


def sensors_fresh(now, line_time, rgb_time, timeout):
    return all(t is not None and 0 <= now-t <= timeout for t in (line_time, rgb_time))
