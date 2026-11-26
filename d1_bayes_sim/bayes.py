"""Course map and Tables 1/2. Index 0 is office 2; index 10 is office 12."""

from logic import predict_cyclic, update_likelihood

# Editable map in driving order; the loop wraps from office 12 to office 2.
MAP = ['yellow', 'green', 'blue', 'orange', 'orange', 'green',
       'blue', 'orange', 'yellow', 'green', 'blue']

# Table 1: command -> probabilities of actual offsets (-1, 0, +1).
MOTION_MODEL = {
    -1: (0.85, 0.10, 0.05),
    0: (0.05, 0.90, 0.05),
    1: (0.05, 0.10, 0.85),
}

# Table 2: measurement rows, TRUE colour columns (not the reverse).
COLORS = ('blue', 'green', 'yellow', 'orange')
MEASUREMENT_MODEL = {
    'blue': (0.60, 0.20, 0.05, 0.05),
    'green': (0.20, 0.60, 0.05, 0.05),
    'yellow': (0.05, 0.05, 0.65, 0.20),
    'orange': (0.05, 0.05, 0.15, 0.60),
    'nothing': (0.10, 0.10, 0.10, 0.10),
}


def predict(p, u):
    """Apply command u, including the uncertain stationary command u=0."""
    if len(p) != len(MAP):
        raise ValueError("Belief must have one entry per office.")
    if u not in MOTION_MODEL:
        raise ValueError("Command must be -1, 0, or +1.")
    return predict_cyclic(p, MOTION_MODEL[u])


def update(p, z):
    """Condition on z; 'nothing' is a reading, unlike the absent reading None."""
    if len(p) != len(MAP):
        raise ValueError("Belief must have one entry per office.")
    if z not in MEASUREMENT_MODEL:
        raise ValueError("Unknown colour measurement.")
    row = MEASUREMENT_MODEL[z]
    return update_likelihood(p, [row[COLORS.index(color)] for color in MAP])
