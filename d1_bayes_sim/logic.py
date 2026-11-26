"""ROS-free discrete Bayes-filter math; uses only the Python standard library."""

from math import isfinite


def normalize(values):
    """Return a fresh probability list from nonnegative finite weights."""
    weights = list(values)
    if not weights or any(not isfinite(v) or v < 0 for v in weights):
        raise ValueError("Belief must contain finite, nonnegative weights.")
    total = sum(weights)
    if not isfinite(total) or total <= 0:
        raise ValueError("Belief must have positive finite total weight.")
    return [v / total for v in weights]


def predict_cyclic(p, probabilities):
    """Distribute each state's belief to offsets -1, 0, +1, cyclically."""
    p = normalize(p)
    result = [0.0] * len(p)
    for source, mass in enumerate(p):
        for offset, probability in zip((-1, 0, 1), probabilities):
            result[(source + offset) % len(p)] += mass * probability
    return normalize(result)


def update_likelihood(p, likelihood):
    """Multiply prior by measurement likelihood and normalize."""
    p = normalize(p)
    if len(p) != len(likelihood):
        raise ValueError("Belief and likelihood must have the same length.")
    return normalize([mass * chance for mass, chance in zip(p, likelihood)])
