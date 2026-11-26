"""Run with plain Python; no ROS, numpy, or installation needed."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src/route_follower'))
from route_follower.logic import (DEFAULT_COLORS, PID, Route, classify, load_colors,
                                  sensors_fresh, valid_rgb)


def main():
    for color, rgb in DEFAULT_COLORS.items():
        assert classify(rgb, DEFAULT_COLORS) == color
    assert not valid_rgb([float('nan'), 0, 0])
    assert not valid_rgb([0, 256, 0])
    assert not valid_rgb([1, 2])
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'colors.json'
        assert load_colors(path)[1] is not None
        path.write_text(json.dumps(DEFAULT_COLORS))
        assert load_colors(path) == (DEFAULT_COLORS, None)
        path.write_text('{"blue": [0, 0, 0]}')
        assert load_colors(path)[1] is not None

    pid = PID(.002, 0, 0, .5)
    assert pid.update(0, .05) == 0
    assert pid.update(100, .05) == .2
    assert pid.update(320, .05) == .5
    assert pid.update(-319, .05) == -.5
    pid = PID(0, 1, 1, 10)
    assert pid.update(1, 1) == 1
    assert pid.update(2, 1) == 4
    pid.reset()
    assert pid.update(2, 1) == 2

    route = Route()
    for _ in range(10):
        assert route.observe('orange') is None
    assert route.count == 0  # Starting patch is not an arrival.
    for color in ['line', 'line', 'blue', 'line', 'line']:
        route.observe(color)
    assert route.state == 'ON_PATCH'  # Flicker must not trigger a transition.
    route.reset_pending()  # A stale-data stop breaks consecutiveness.
    route.observe('line')
    assert route.state == 'ON_PATCH'
    route.observe('line')
    route.observe('line')
    assert route.state == 'FOLLOW_LINE'
    # Repeated same-color offices are distinct only after a line segment.
    colors = ['orange', 'orange', 'blue', 'green', 'yellow', 'blue',
              'green', 'orange', 'yellow', 'green', 'blue']
    for index, color in enumerate(colors, 1):
        assert route.observe(color) is None
        assert route.observe(color) is None
        assert route.observe(color) == color
        assert route.count == index
        for _ in range(10):
            assert route.observe(color) is None
        for _ in range(3):
            route.observe('line')
    assert route.state == 'DONE' and route.count == 11
    for _ in range(20):
        route.observe('green')
        route.observe('line')
    assert route.state == 'DONE' and route.count == 11
    short = Route(1)
    for c in ['line']*3 + ['blue', 'green', 'yellow']:
        short.observe(c)
    assert short.state == 'DONE'  # Debounce patch-vs-line, not exact patch hue.
    for n in [0, -1]:
        try:
            Route(n)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid count accepted')
    assert not sensors_fresh(10, None, 10, 1)
    assert not sensors_fresh(10, 10, None, 1)
    assert not sensors_fresh(10, 8.99, 10, 1)
    assert not sensors_fresh(10, 10, 8.99, 1)
    assert sensors_fresh(10, 9, 10, 1)
    print('All D2 logic assertions passed.')


if __name__ == '__main__':
    main()
