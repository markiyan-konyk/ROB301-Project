"""Run Table 3: observe, record, then move. No ROS or robot required."""

import os
from math import isclose
from pathlib import Path
import sys

from bayes import MAP, predict, update

# Table 3 scenario. None means no observation/command, whereas 0 is a command.
U = [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, None]
Z = [None, 'orange', 'yellow', 'green', 'blue', 'nothing', 'green',
     'blue', 'green', 'orange', 'yellow', 'green', 'blue']


def best_indices(p):
    """Return tied maxima; choose the highest office for the printed best."""
    return [i for i, value in enumerate(p)
            if isclose(value, max(p), rel_tol=0, abs_tol=1e-12)]


def simulate():
    """Return beliefs at k=0..12, after sensing and before that row's move."""
    p = [1.0 / len(MAP)] * len(MAP)
    history = []
    for u, z in zip(U, Z):
        if z is not None:
            p = update(p, z)
        history.append(p.copy())
        if u is not None:
            p = predict(p, u)
    return history


def print_results(history):
    print(' k   u       z  ' + ' '.join(f'{i:>5}' for i in range(2, len(MAP) + 2)))
    for k, (u, z, p) in enumerate(zip(U, Z, history)):
        tied = best_indices(p)
        best = tied[-1]
        print(f'{k:2d} {str(u):>4} {str(z):>7}  '
              + ' '.join(f'{v:5.2f}' for v in p)
              + f'  best: office {best + 2} (p = {p[best]:.2f})'
              + (f' [tie: {", ".join(str(i + 2) for i in tied)}]' if len(tied) > 1 else ''))
    end = best_indices(history[-1])[-1]
    first = best_indices(history[1])[-1]
    moves = sum(u for u in U if u is not None)
    start = (end - moves) % len(MAP)
    print(f'\nEnd: office {end + 2} (p = {history[-1][end]:.2f})')
    print(f'Start: office {start + 2} (backtracking {moves} commanded moves)')
    print(f'First measured office (k = 1): office {first + 2} '
          f'(p = {history[1][first]:.2f})')
    print('k = 1 ties offices 5, 6, 9; the printed best uses the highest office number.')
    print('Start assumes commanded moves occurred; it is not a smoothed posterior.')


def plot_results(history):
    import matplotlib

    # Linux lab desktops show the figure; headless Linux saves it using Agg.
    if sys.platform.startswith('linux') and not (
            os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import numpy as np

    data = np.asarray(history)
    fig, ax = plt.subplots(figsize=(11, 8), layout='constrained')
    heatmap = ax.imshow(data, vmin=0, vmax=1, cmap='Blues', aspect='auto')
    for k, row in enumerate(data):
        for j, value in enumerate(row):
            ax.text(j, k, f'{value:.2f}', ha='center', va='center',
                    color='white' if value > 0.55 else 'black', fontsize=9)
        # Highlight all tied maxima, especially the uniform prior at k=0.
        for j in np.flatnonzero(np.isclose(row, row.max(), rtol=0, atol=1e-12)):
            ax.add_patch(Rectangle((j - 0.5, k - 0.5), 1, 1, fill=False,
                                   edgecolor='#e67e00', linewidth=2))
    ax.set_xticks(range(len(MAP)), range(2, len(MAP) + 2))
    ax.set_yticks(range(len(history)),
                  [f'{k}: {z or "prior"}' for k, z in enumerate(Z)])
    ax.set_xlabel('Office')
    ax.set_ylabel('Step k: observation (before command u_k)')
    ax.set_title('Bayesian localization: Table 3\nOrange outlines mark row maxima (including ties)')
    fig.colorbar(heatmap, ax=ax, label='Probability')
    output = Path(__file__).resolve().with_name('bayes_evolution.png')
    fig.savefig(output, dpi=160)
    print(f'Saved: {output}')
    if matplotlib.get_backend().lower() != 'agg':
        plt.show()
    plt.close(fig)


def main():
    history = simulate()
    print_results(history)
    plot_results(history)


if __name__ == '__main__':
    main()
