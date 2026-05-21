"""
tests/test_memory_db.py — Property tests P5 para memory_db.py

**Validates: Requirements 6.3, 6.4, 6.5**

Property 5: Mensajes de sesión agrupados correctamente (round-trip)
  - Guardar N mensajes con un session_id y luego cargarlos con
    `load_by_session(session_id)` debe retornar exactamente N mensajes,
    todos con el mismo session_id.
"""

from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# P5: Round-trip de sesión — count y session_id correctos
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    session_id=st.integers(min_value=1, max_value=9999),
    n_mensajes=st.integers(min_value=1, max_value=10),
)
def test_session_grouping_roundtrip(session_id, n_mensajes):
    """
    **Validates: Requirements 6.3, 6.4, 6.5**

    Guardar `n_mensajes` conversaciones con `session_id` y luego recuperarlas
    con `load_by_session(session_id)` debe retornar exactamente `n_mensajes`
    registros, todos con `session_id` correcto.
    """
    from memory_db import MemoryDB

    db = MemoryDB(":memory:")
    try:
        for i in range(n_mensajes):
            db.save_conversation(
                f"entrada_{i}",
                f"respuesta_{i}",
                "neutral",
                session_id,
            )

        resultado = db.load_by_session(session_id)

        assert len(resultado) == n_mensajes, (
            f"Se esperaban {n_mensajes} mensajes, se obtuvieron {len(resultado)} "
            f"(session_id={session_id})"
        )
        assert all(r.get("session_id") == session_id for r in resultado), (
            f"Algún registro tiene session_id incorrecto: "
            f"{[r.get('session_id') for r in resultado]} (esperado={session_id})"
        )
    finally:
        db.close()
