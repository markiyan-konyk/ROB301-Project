#!/usr/bin/env python3

"""
Plot a localizer CSV log: position estimate and its variance over time.

Usage::

    ros2 run lab_3 plot_kf_log                 # newest log in ~/lab3_logs
    ros2 run lab_3 plot_kf_log ~/lab3_logs/ekf_20261104-101500.csv [--show]

Saves a PNG next to the CSV. Top panel: the estimate with its 2-sigma band,
the position implied by each raw bearing on its own, and the mail-route
addresses. Bottom panel: the variance P. Grey shading marks stretches with no
tower sighting (e.g. obstructions).
"""

import argparse
import csv
import glob
import os

import numpy as np

ADDRESSES = [('4', 0.61), ('8', 1.22), ('16', 2.44), ('20', 3.05)]
GAP = 0.5            # [s] no bearing for longer than this counts as "no sighting"

BLUE, ORANGE = '#2a78d6', '#eb6834'
INK, INK_2, MUTED, SHADE = '#0b0b0b', '#52514e', '#8a8984', '#e6e5e1'


def read_log(path):
    meta = {}
    rows = []
    with open(path) as f:
        first = f.readline()
        if first.startswith('#'):
            for kv in first[1:].split():
                k, _, v = kv.partition('=')
                meta[k] = v
        else:
            f.seek(0)
        for r in csv.DictReader(f):
            rows.append(r)
    if not rows:
        raise SystemExit(f'{path} has no data rows yet (did the localizer run?)')
    cols = {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}
    return meta, cols


def no_sighting_spans(t, z):
    """Return (start, end) intervals with no bearing for more than GAP seconds."""
    seen = t[np.isfinite(z)]
    edges = np.concatenate([[t[0]], seen, [t[-1]]])
    return [(a, b) for a, b in zip(edges[:-1], edges[1:]) if b - a > GAP]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('log', nargs='?',
                    help='CSV written by the localizer node (default: newest in ~/lab3_logs)')
    ap.add_argument('--truth', help='optional CSV with columns t,x (ground truth)')
    ap.add_argument('--out', help='output PNG (default: next to the CSV)')
    ap.add_argument('--show', action='store_true', help='also open a window')
    args = ap.parse_args(argv)
    if args.log is None:
        logs = glob.glob(os.path.expanduser('~/lab3_logs/*.csv'))
        if not logs:
            ap.error('no logs in ~/lab3_logs yet: run a demo first')
        args.log = max(logs, key=os.path.getmtime)
        print(f'plotting newest log: {args.log}')

    import matplotlib
    if not args.show:
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    meta, c = read_log(args.log)
    t, x, P = c['t'], c['x_hat'], c['P']
    sigma2 = 2.0 * np.sqrt(P)
    h, d = float(meta.get('h', 0.6)), float(meta.get('d', 1.8))
    use_lidar = meta.get('use_lidar', 'True') == 'True'

    plt.rcParams.update({
        'font.size': 10, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK_2,
        'xtick.color': INK_2, 'ytick.color': INK_2, 'axes.spines.top': False,
        'axes.spines.right': False, 'axes.grid': True, 'grid.color': SHADE,
        'grid.linewidth': 0.6,
    })
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(9, 6.5),
                                   gridspec_kw={'height_ratios': [3, 2]})

    spans = no_sighting_spans(t, c['z'])
    for ax in (ax1, ax2):
        for i, (a, b) in enumerate(spans):
            ax.axvspan(a, b, color=SHADE, alpha=0.7, lw=0,
                       label='no tower sighting' if (ax is ax1 and i == 0) else None)

    for name, xa in ADDRESSES:
        ax1.axhline(xa, color=MUTED, lw=0.8, ls=':', zorder=1)
        ax1.annotate(f'{name} Bloor', (1.0, xa), xycoords=('axes fraction', 'data'),
                     xytext=(4, 0), textcoords='offset points', va='center',
                     fontsize=8, color=INK_2, annotation_clip=False)

    # Position implied by each bearing on its own
    z = c['z']
    m = np.isfinite(z) & (np.abs(np.sin(z)) > 1e-3)
    x_meas = d - h * np.cos(z[m]) / np.sin(z[m])
    ax1.scatter(t[m], x_meas, s=9, color=ORANGE, lw=0, alpha=0.8, zorder=2,
                label='lidar-only fix (from one bearing)'
                if use_lidar else 'lidar-only fix (not used)')

    ax1.fill_between(t, x - sigma2, x + sigma2, color=BLUE, alpha=0.18, lw=0,
                     label='±2σ', zorder=3)
    ax1.plot(t, x, color=BLUE, lw=1.6, zorder=4,
             label='EKF estimate' if use_lidar else 'dead-reckoning estimate')

    if args.truth:
        # columns t (ROS time, s) and x (m); shifted onto the log's time axis
        tr = np.genfromtxt(args.truth, delimiter=',', names=True)
        t_tr = tr['t'] - float(meta.get('t0', 0.0))
        ax1.plot(t_tr, tr['x'], color=INK, lw=1.0, ls='--', zorder=5, label='ground truth')

    ax1.set_ylabel('position x [m]')
    lo = min(np.nanmin(x - sigma2), -0.1)
    hi = max(np.nanmax(x + sigma2), 3.2)
    ax1.set_ylim(max(lo, -1.0), min(hi, 4.5))
    ax1.legend(loc='lower right', fontsize=8, framealpha=0.9, edgecolor='none')

    ax2.plot(t, P, color=BLUE, lw=1.6)
    ax2.set_yscale('log')
    ax2.set_ylabel('variance P [m²]')
    ax2.set_xlabel('time [s]')

    rej = c['status'] < 0
    if rej.any():
        ax2.scatter(t[rej], P[rej], marker='x', s=16, color=INK_2, lw=1,
                    label='bearing rejected by gate', zorder=5)
        ax2.legend(loc='upper right', frameon=False, fontsize=8)

    title = os.path.basename(args.log)
    final = f'final x = {x[-1]:.3f} m ± {sigma2[-1]:.3f} m (2σ)'
    fig.suptitle(f'{title}    {final}', fontsize=10, color=INK, x=0.02, ha='left')
    fig.tight_layout(rect=(0, 0, 0.95, 0.97))

    out = args.out or os.path.splitext(args.log)[0] + '.png'
    fig.savefig(out, dpi=150)
    print(f'saved {out}')
    if args.show:
        plt.show()
    plt.close(fig)
    return out


if __name__ == '__main__':
    main()
