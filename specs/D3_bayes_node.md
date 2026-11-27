# D3: Bayesian localization node

Read `AGENTS.md` first. PDF section 4.3. Due by the end of the second lab session.

Demo: the robot drives the loop from an unknown start; the belief over offices starts uniform and
converges to the correct office after it has passed a few offices.

## Build `d3_bayes_node/`

Start by copying `d2_full_route/` entirely and renaming the package `route_follower` ->
`bayes_localization` (folder, setup.py, package.xml, resource file, entry points, PKG in setup.sh).
Then add:

- In `logic.py`: `predict` / `update` / the Table 1 and Table 2 models, copied from
  `d1_bayes_sim/bayes.py`.
- Executable `localizer` (replaces `route_follower`): same driving state machine as D2, plus Bayes:
  - `MAP` constant at the top of the file (AGENTS.md).
  - Keep D2's driving, classifier and counting exactly as they are (lab-tested; see AGENTS.md).
  - Measurement z of a patch = majority class of its first VOTE_FRAMES (8) patch frames; if the
    majority share is < 0.6, z = `nothing`.
  - Blue and green read almost the same on our robot. Measure the real confusion first: run
    `color_monitor` with the robot fully on each patch colour and note how often blue reads as
    green and vice versa, then put those numbers in the Table 2 measurement model (the Bayes
    filter copes with confusion it knows about). README shows how to redo this.
  - First patch (the start patch): update only. Every later patch: `predict(u=+1)` then `update(z)`.
  - After each update print one line per office with its probability (and a small text bar),
    then `Best guess: office N (p = 0.xx)`, adding `CONFIDENT` when p > 0.8.
  - Publish `/belief` (`std_msgs/Float64MultiArray`, 11 values, offices 2..12).
  - Runs until Ctrl+C (optional arg N = stop after N patches).
- Executable `belief_plot`: live matplotlib bar chart of `/belief` with office numbers and the best
  office highlighted. Same structure as the course's `labs/lab_3/lab_3/live_plot.py` (exits
  quietly without a display).
- `setup.sh --launch` also opens a [PC] tab with `belief_plot`.

## README extras

TA demo: put the map in `MAP`; place the robot on any patch facing the driving direction; start;
show the belief after each office (terminal + plot): spread over same-colour offices at first,
then one office above 0.8 after 3 to 5 offices. Tell the TA where it really started so they can
check. Mention that the Table 2 values can be retuned from what `color_monitor` shows.
