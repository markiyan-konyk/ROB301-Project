# D1: Bayesian localization simulation (no ROS)

Read `AGENTS.md` first. PDF section 4.1 + Attachment. Due 30 min into the first lab session, so it
must run on the lab Remote PC with only `python3`, numpy and matplotlib.

## Build `d1_bayes_sim/`

- `bayes.py`: `MAP` (from AGENTS.md), the two models below, `predict(p, u)`, `update(p, z)`.
  D3/D4 will copy this file, so keep it ROS-free and tidy.
- `simulate.py`: runs the Table 3 scenario, prints and plots the evolution.
- `run.sh`: `python3 simulate.py` (from its own folder).
- `README.md`: how to run, how to read the output, the answer, and a 5-line explanation of
  predict/update the group can say to the TA.

## Models

State = office index for offices 2..12 (11 states, cyclic: office 12 + 1 = office 2).
Uniform prior.

State model p(x_k+1 | x_k = X, u_k), Table 1 (wrap around the loop):

| x_k+1 | u=-1 | u=0 | u=+1 |
|---|---|---|---|
| X-1 | 0.85 | 0.05 | 0.05 |
| X   | 0.10 | 0.90 | 0.10 |
| X+1 | 0.05 | 0.05 | 0.85 |

Measurement model p(z | colour of x), Table 2 (columns = true colour):

| z | blue | green | yellow | orange |
|---|---|---|---|---|
| blue    | 0.60 | 0.20 | 0.05 | 0.05 |
| green   | 0.20 | 0.60 | 0.05 | 0.05 |
| yellow  | 0.05 | 0.05 | 0.65 | 0.20 |
| orange  | 0.05 | 0.05 | 0.15 | 0.60 |
| nothing | 0.10 | 0.10 | 0.10 | 0.10 |

## Scenario (Table 3) and loop

```
u = [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, None]
z = [None, 'orange', 'yellow', 'green', 'blue', 'nothing', 'green', 'blue', 'green', 'orange', 'yellow', 'green', 'blue']
```

For k = 0..12: if z_k, update (normalize); record the belief; if u_k, predict.

## Output

- Terminal: for each k a row with k, u_k, z_k, the belief per office (2 decimals) and
  "best: office N (p = 0.xx)".
- Figure: heatmap of the belief (rows = k, columns = offices 2..12), each cell annotated, best
  cell per row highlighted. Save `d1_bayes_sim/bayes_evolution.png`; show it if there is a display.
- Final answer lines: **End** = best office at k = 12. **Start** = end moved back by the
  commanded moves (sum of u = 11 = one full lap). Also print the first measured office (k = 1).

## Self-check (must match)

End: office 8 (p ≈ 0.87). k = 1 best is office 9, so the robot started at office 8 at k = 0
(11 moves = one full lap, so start = end = 8). k = 8 "green" is a misreading (robot at office 5,
orange; u_8 = 0 so it is still at 5 at k = 9).
