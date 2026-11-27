# D2: full route execution (no localization)

Read `AGENTS.md` first. PDF section 4.2. Due by the end of the first lab session.

Demo: the robot starts on **any** office patch, drives ahead until it sees the line, follows the
line to the next patch, crosses it, and so on until it has gone once around the whole loop.

## Build `d2_full_route/`

```
d2_full_route/
  README.md
  setup.sh                 (see AGENTS.md; PKG=route_follower)
  src/camera/              (modified copy, see AGENTS.md)
  src/route_follower/      ament_python package
```

Executables of `route_follower`:

- `route_follower`: the demo node. `ros2 run route_follower route_follower [N]`, N = number of
  offices to pass before stopping (default 11 = full lap, back at the start office).
- `calibrate_colors`: as in AGENTS.md.
- `color_monitor`: prints mean RGB + class twice a second (debugging, and shows the TA the
  patch detector).

## Node behaviour (control timer at 20 Hz)

- Start state `ON_PATCH` (the robot starts on a patch).
- `ON_PATCH`: drive straight at SPEED, turn 0. When `line` is debounced -> `FOLLOW_LINE`.
- `FOLLOW_LINE`: PID on `/line_idx` (gains from the reference lab_2). When a patch colour is
  debounced -> count it, log `Office #n reached: <colour>`, -> `ON_PATCH`.
- After N patches: stop, log "Full route done", stay stopped.
- Safety rules from AGENTS.md (wait for both topics, stop on stale data, Ctrl+C stops).
- Tunables at the top: SPEED, KP, KI, KD, MAX_TURN, CENTER, DEBOUNCE, NUM_OFFICES.

## README extras

TA demo: place the robot on any patch, facing the driving direction (office numbers increasing),
run, the terminal lists each office colour, the robot stops back at its start office. Tuning: if it
turns away from the line flip KP; if it wobbles lower KP/SPEED; if patches are missed recalibrate
(`setup.sh <PI_IP> --launch --calibrate`) or check `color_monitor`; if `/line_idx` doesn't
follow the tape, set `LINE_IS_DARK` in `setup.sh`.
