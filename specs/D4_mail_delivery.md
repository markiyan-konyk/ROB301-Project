# D4: proof-of-concept mail delivery

Read `AGENTS.md` first. PDF section 4.4. Due by the end of the third lab session.

Demo: from a random start patch, deliver to 3 given offices. At each target: stop on the office,
rotate 90° left, pause, rotate back, continue. Stop after the third delivery.

## Build `d4_mail_delivery/`

Start by copying `d3_bayes_node/` entirely and renaming the package `bayes_localization` ->
`mail_robot` (all places, as in D3). Then make executable `mail_robot` (replaces `localizer`, keeps
its Bayes logic, `/belief` and `belief_plot`):

- Run: `ros2 run mail_robot mail_robot 3 7 10` (3 target offices, any order, each in 2..12;
  refuse to start otherwise). `MAP` at the top of the file.
- After each patch's Bayes update: if `p(best) >= DELIVER_P` (0.7) and best is a remaining target:
  1. keep driving straight PATCH_CENTER_DIST (0.10 m, measured with `/odom`) to be on the office,
  2. stop, rotate +90° (left) using `/odom` yaw (ANGULAR_SPEED 0.4 rad/s, wrap-safe angle error),
  3. pause 2 s, rotate back -90°,
  4. log `Delivered to office N (k of 3)`, then continue straight until the line is back.
- If it is not confident when it passes a target, keep going: it will come round again.
- After the third delivery: stop, print a summary, keep the robot stopped.
- `setup.sh --launch`: the final [PC] tab asks `Target offices (e.g. 3 7 10):` and passes them.

## README extras

A "Demo day" checklist at the top: (1) map announced -> edit `MAP`; (2) targets given ->
type them; (3) place the robot on the start patch facing the driving direction; (4) Enter.
Second attempt: the robot may be put back on the line by hand (small penalty). Tuning:
PATCH_CENTER_DIST if it stops before/after the patch centre, DELIVER_P, ANGULAR_SPEED.
