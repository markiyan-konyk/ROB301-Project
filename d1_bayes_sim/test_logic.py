"""Plain-Python assertions for probability math and the supplied scenario."""

from math import isclose

from bayes import MAP, MEASUREMENT_MODEL, MOTION_MODEL, predict, update
from logic import normalize, predict_cyclic, update_likelihood
from simulate import best_indices, simulate, U


def close(actual, expected):
    assert len(actual) == len(expected)
    assert all(isclose(a, b, abs_tol=1e-12) for a, b in zip(actual, expected))


def main():
    close(normalize([1, 2, 1]), [0.25, 0.5, 0.25])
    close(predict_cyclic([1, 0, 0], (0.2, 0.3, 0.5)), [0.3, 0.5, 0.2])
    close(update_likelihood([0.5, 0.5], [0.2, 0.8]), [0.2, 0.8])
    for weights in ([], [0, 0], [-1, 2], [float('nan')], [float('inf')]):
        try:
            normalize(weights)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Invalid belief accepted: {weights}')

    for probabilities in MOTION_MODEL.values():
        assert isclose(sum(probabilities), 1)
    for col in range(4):
        assert isclose(sum(row[col] for row in MEASUREMENT_MODEL.values()), 1)
    n = len(MAP)
    for source in range(n):
        p = [float(i == source) for i in range(n)]
        for u, (back, stay, forward) in MOTION_MODEL.items():
            expected = [0.0] * n
            expected[(source - 1) % n] = back
            expected[source] = stay
            expected[(source + 1) % n] = forward
            close(predict(p, u), expected)
        close(update(p, 'nothing'), p)
        assert p[source] == 1  # Inputs must not be mutated.

    history = simulate()
    assert len(history) == 13
    for row in history:
        assert all(0 <= p <= 1 for p in row)
        assert isclose(sum(row), 1)
    close(history[0], [1 / n] * n)
    assert best_indices(history[1]) == [3, 4, 7]  # Offices 5, 6, 9 tie.
    assert isclose(history[1][7], 0.25)
    close(update(history[4], 'nothing'), history[4])
    close(history[5], predict(history[4], 1))
    close(history[9], update(predict(history[8], 0), 'orange'))
    assert best_indices(history[8]) == [3]
    assert best_indices(history[9]) == [3]
    assert best_indices(history[-1]) == [6]  # Office 8.
    assert 0.865 < history[-1][6] < 0.875
    assert sum(u for u in U if u is not None) == 11
    print('All Bayes math and Table 3 assertions passed.')


if __name__ == '__main__':
    main()
