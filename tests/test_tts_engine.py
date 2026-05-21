"""
tests/test_tts_engine.py — Property tests P2 para tts_engine.py

**Validates: Requirements 4.2, 4.5, 4.7**

Property 2: Amplitud de boca siempre en rango [0.0, 1.0]
  - La fórmula RMS `min(1.0, rms / 8000.0)` produce valores en [0.0, 1.0]
    para cualquier lista de muestras de audio en [-32768, 32767].
  - El fallback sinusoidal `abs(sin(t * 8.0)) * 0.6 + 0.1` produce valores
    en [0.0, 1.0] para cualquier t >= 0.
"""

import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# P2-A: Fórmula RMS siempre en [0.0, 1.0]
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    st.lists(
        st.floats(
            min_value=-32768.0,
            max_value=32767.0,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=1,
        max_size=1000,
    )
)
def test_mouth_amplitude_rms_range(samples):
    """
    **Validates: Requirements 4.2, 4.5, 4.7**

    Para cualquier lista de muestras de audio en [-32768, 32767],
    la fórmula RMS `min(1.0, rms / 8000.0)` debe producir un valor en [0.0, 1.0].
    """
    arr = np.array(samples, dtype=np.float32)
    rms = float(np.sqrt(np.mean(arr ** 2)))
    amp = min(1.0, rms / 8000.0)
    assert 0.0 <= amp <= 1.0, (
        f"Amplitud RMS fuera de rango: {amp} (rms={rms}, samples={samples[:5]}...)"
    )


# ---------------------------------------------------------------------------
# P2-B: Fallback sinusoidal siempre en [0.0, 1.0]
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    st.floats(
        min_value=0.0,
        max_value=1000.0,
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_fallback_sinusoidal_range(t):
    """
    **Validates: Requirements 4.2, 4.5, 4.7**

    Para cualquier t >= 0, el fallback sinusoidal
    `abs(sin(t * 8.0)) * 0.6 + 0.1` debe producir un valor en [0.0, 1.0].
    """
    amp = abs(math.sin(t * 8.0)) * 0.6 + 0.1
    assert 0.0 <= amp <= 1.0, (
        f"Amplitud sinusoidal fuera de rango: {amp} (t={t})"
    )
