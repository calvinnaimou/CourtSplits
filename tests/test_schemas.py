import pytest

from api.schemas import round_to_half


@pytest.mark.parametrize("raw,expected", [
    (30.4345, 30.5),
    (30.5, 30.5),
    (30, 30),
    (30.0, 30.0),
    (30.99, 31.0),   # nearest 0.5 grid point, not floor+0.5
    (30.25, 30.5),   # exact tie rounds up, not banker's-rounding to 30.0
    (-6.5, -6.5),
    (-6.4, -6.5),
    (0, 0),
])
def test_round_to_half(raw, expected):
    assert round_to_half(raw) == expected
