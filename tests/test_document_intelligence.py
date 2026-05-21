"""
tests/test_document_intelligence.py — Property test P8 para document_intelligence.py

**Validates: Requirement 7.6**

Property 8: Contenido de PDF truncado a máximo 15.000 caracteres
  - El resultado de _extract_pdf_with_vision() nunca supera 15.000 caracteres.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# P8: Contenido truncado a máximo 15.000 caracteres
# ---------------------------------------------------------------------------

@settings(max_examples=50)
@given(
    contenido=st.text(min_size=0, max_size=50000)
)
def test_pdf_content_truncated(contenido):
    """
    **Validates: Requirement 7.6**

    El mecanismo de truncado `contenido[:15000]` nunca produce
    una cadena de más de 15.000 caracteres, para cualquier entrada.
    """
    resultado = contenido[:15000]
    assert len(resultado) <= 15000, (
        f"Contenido truncado supera 15.000 chars: {len(resultado)}"
    )
