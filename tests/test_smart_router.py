"""
tests/test_smart_router.py — Property test P4 para brain.py

**Validates: Requirement 9.2**

Property 4: SmartRouter selecciona Ollama cuando no hay internet.
  Para cualquier query, si ConnectivityChecker.is_online() retorna False,
  SmartRouter.analyze(query) debe retornar engine == "ollama".
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from brain import SmartRouter


# ---------------------------------------------------------------------------
# P4: SmartRouter selecciona Ollama cuando no hay internet
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    query=st.text(min_size=1, max_size=200)
)
def test_router_offline_uses_ollama(query):
    """
    **Validates: Requirement 9.2**

    Para cualquier query, si ConnectivityChecker.is_online() retorna False,
    SmartRouter.analyze() debe retornar una RoutingDecision con engine == "ollama".
    """
    router = SmartRouter()
    with patch.object(router._connectivity, "is_online", return_value=False):
        decision = router.analyze(query)

    assert decision.engine == "ollama", (
        f"Se esperaba engine='ollama' sin internet, "
        f"pero se obtuvo engine={decision.engine!r} para query={query!r}"
    )
