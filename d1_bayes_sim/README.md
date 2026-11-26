# Deliverable 1: Bayesian localization simulation

Runs the project Attachment's Tables 1-3 on the 11-office cyclic map. No ROS,
Pi, camera, or robot is needed. Runtime dependencies: Python 3, NumPy and
Matplotlib already available on the Remote PC. Nothing is installed by setup.

## Run on the Remote PC

From a fresh checkout, [PC]:

```bash
git clone https://github.com/markiyan-konyk/ROB301-Project.git
cd ROB301-Project
bash d1_bayes_sim/setup.sh
bash d1_bayes_sim/run.sh
```

For an existing checkout, use the last two commands from its root. The runner
works from any working directory when given its correct path.

| Terminal | Manual command (from the repository root) | Purpose |
|---|---|---|
| [PC] | `python3 d1_bayes_sim/simulate.py` | Print all 13 beliefs, save the heatmap, and display it on a desktop |
| [PC] | `MPLBACKEND=Agg python3 d1_bayes_sim/simulate.py` | Save without opening a window |
| [PC] | `python3 d1_bayes_sim/test_logic.py` | Run plain-Python assertion checks |

On Windows [PC], use `python d1_bayes_sim/simulate.py` and
`python d1_bayes_sim/test_logic.py`; Bash is not needed.

## Read the output and answer

Each terminal row contains k, the outgoing command u_k, observation z_k, and
probabilities for offices 2..12 (rounded to two decimals). Each belief is
recorded **after observation z_k but before command u_k**. The heatmap
`bayes_evolution.png` is always saved beside the script. Rows are time steps;
columns are offices; darker blue means higher probability. Orange outlines
show every tied maximum. Rounded entries need not sum to exactly 1.00.

- **End:** office **8**, probability approximately **0.87** at k=12.
- **Start:** office **8**, obtained by moving back 11 commanded steps (one lap)
  from the end. This is the requested commanded-path inference, not a posterior
  over the starting location accounting for all possible motion errors.
- **First measured office, k=1:** office **9** is a joint best with offices
  **5 and 6**, each at probability 0.25. An orange reading alone cannot separate
  these offices. The printed tie-break chooses the highest office number to
  match the spec's office 9; all ties are disclosed and plotted.
- At k=8, the commanded path is at orange office 5 but reads green. The filter
  still ranks office 5 highest (about 0.36). The u_8=0 model retains 90% at
  each state and spreads 5% each way; it must not be skipped. The orange reading
  at k=9 increases office 5's probability to about 0.81.
- At k=10, the commanded path is at orange office 6 but reads yellow, another
  allowed sensor error. The model still ranks office 6 highest.

`None` means no observation or command. The observation `nothing` has likelihood
0.10 for every colour, so it leaves the normalized belief unchanged.

## TA demo

1. On [PC], run `bash d1_bayes_sim/run.sh` from the repository root.
2. Show the uniform prior at k=0 and the orange-office tie at k=1.
3. Show the mistaken green measurement at k=8 and recovery at k=9.
4. Show the final office 8 estimate and explain the one-lap start inference.
5. Present the following five-line explanation, then close the figure window.

## Five-line explanation

1. We start with equal probability at each of the 11 offices because the start is unknown.
2. Prediction spreads each office's probability to its neighbours using the command's motion probabilities.
3. Office indices wrap around, so moving forward from office 12 leads to office 2.
4. Update multiplies each office's belief by the likelihood of the observed colour, then normalizes.
5. We observe, record, and then predict at each step, so repeated colours and occasional misreadings are handled probabilistically.

## Files and changes for another scenario

`bayes.py` holds editable `MAP`, both model tables, and `predict`/`update`.
`logic.py` holds ROS-free math using only the standard library. Copy both files
together for a later deliverable. `simulate.py` holds Table 3's `U` and `Z`;
keep them the same length. The provided answer applies only to the original
map, tables, and scenario. `src/camera` is an unchanged copy required by the
repository layout; D1 neither imports nor builds it.

## Troubleshooting and remaining checks

If NumPy or Matplotlib is missing, use the lab's configured Python environment;
setup only checks dependencies. On a headless Linux PC the PNG is saved without
a window. If a desktop backend fails, use the explicit `MPLBACKEND=Agg` command
above and open the saved PNG. No new terminals or ROS networking are needed.

D1 needs no robot testing. Verify the interactive plot opens on the lab PC
before presenting. Physical motion, camera sensing, and empirical model
probabilities remain untested and belong to later deliverables.
