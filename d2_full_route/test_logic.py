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

    # Regression, calibration from our robot (lab run 1): half-visible blue/orange patches mix
    # with the floor and land nearest to yellow. They must not count as extra offices.
    lab = {'blue': [186.5, 181.6, 183.2], 'green': [184.7, 189.3, 184.2],
           'yellow': [199.6, 170.6, 151.8], 'orange': [250.3, 124.9, 101.3],
           'line': [150.8, 133.5, 140.9]}

    def mix(patch, f):
        return [f*a + (1-f)*b for a, b in zip(lab[patch], lab['line'])]

    assert classify(mix('blue', .5), lab) == 'line'      # was 'yellow'
    assert classify(mix('orange', .5), lab) == 'line'    # was 'yellow'
    assert classify(lab['yellow'], lab) == 'yellow'
    lap = Route(3, debounce=4)
    for _ in range(4):
        lap.observe('line')
    reported = []
    for patch in ['blue', 'orange', 'yellow']:
        frames = [mix(patch, f) for f in (.3, .5, .7)] + [lab[patch]]*8 + \
                 [mix(patch, f) for f in (.7, .5, .3)] + [lab['line']]*6
        for rgb in frames:
            hit = lap.observe(classify(rgb, lab))
            if hit:
                reported.append(hit)
    assert reported == ['blue', 'orange', 'yellow'], reported
    print('All D2 logic assertions passed.')


if __name__ == '__main__':
    main()
