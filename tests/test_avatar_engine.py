"""
test_avatar_engine.py — Property-based tests for cabina_virtual.py.

Covers:
  P1 — SmoothDamp converge sin overshoot          (Requirements 1.1, 1.2)
  P3 — Amplitud y velocidad de balanceo en rango  (Requirements 2.1, 2.2, 2.4)
  P6 — Clasificación de píxel transparente        (Requirement 3.4)
"""
import sys
import os

# Ensure the project root is on sys.path so cabina_virtual can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings, strategies as st

from cabina_virtual import smooth_damp, es_pixel_transparente, EstadoInterno


# ─────────────────────────────────────────────────────────────────────────────
# P1 — SmoothDamp converge sin overshoot
# Validates: Requirements 1.1, 1.2
# ─────────────────────────────────────────────────────────────────────────────

@settings(max_examples=200)
@given(
    current=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    target=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
def test_smooth_damp_converges_no_overshoot(current, target):
    """
    **Validates: Requirements 1.1, 1.2**

    After 120 frames at 60 fps (smooth_time=0.12s) the output must:
    - Converge within 0.001 of the target.
    - Never overshoot when current starts below target.
    """
    vel = [0.0]
    initial_below = current < target
    for _ in range(120):
        current = smooth_damp(current, target, vel, 0.12, 0.016)
    assert abs(current - target) < 0.001
    if initial_below:
        assert current <= target + 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# P3 — Amplitud y velocidad de balanceo en rango válido
# Validates: Requirements 2.1, 2.2, 2.4
# ─────────────────────────────────────────────────────────────────────────────

@settings(max_examples=200)
@given(
    flow=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    dopamina=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
def test_amplitud_velocidad_balanceo_range(flow, dopamina):
    """
    **Validates: Requirements 2.1, 2.2, 2.4**

    For any (flow, dopamina) in [0, 1]²:
    - amplitud_balanceo() must be in [1.5, 5.0].
    - velocidad_balanceo() must be in [0.20, 0.45].
    """
    ei = EstadoInterno()
    ei.flow = flow
    ei.dopamina = dopamina
    assert 1.5 <= ei.amplitud_balanceo() <= 5.0
    assert 0.20 <= ei.velocidad_balanceo() <= 0.45


# ─────────────────────────────────────────────────────────────────────────────
# P6 — Clasificación de píxel transparente correcta
# Validates: Requirement 3.4
# ─────────────────────────────────────────────────────────────────────────────

@settings(max_examples=500)
@given(
    r=st.integers(min_value=0, max_value=255),
    g=st.integers(min_value=0, max_value=255),
    b=st.integers(min_value=0, max_value=255),
)
def test_pixel_transparente_clasificacion(r, g, b):
    """
    **Validates: Requirement 3.4**

    es_pixel_transparente(r, g, b) must return exactly the boolean expression:
      r < 30 AND g in [225, 255] AND b < 30
    for every (r, g, b) in [0, 255]³.
    """
    esperado = r < 30 and 225 <= g <= 255 and b < 30
    assert es_pixel_transparente(r, g, b) == esperado
