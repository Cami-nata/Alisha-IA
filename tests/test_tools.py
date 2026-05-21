"""
tests/test_tools.py — Property tests P7 y P9 para tools.py

**P7 — Validates: Requirement 8.2**
  Parser de TOOL_CALL es round-trip correcto.

**P9 — Validates: Requirement 8.1**
  Herramientas no aceptan parámetros de coordenadas absolutas.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from tools import parsear_tool_call, _COORD_PARAMS


# ---------------------------------------------------------------------------
# Estrategias auxiliares
# ---------------------------------------------------------------------------

# Identificadores Python válidos (letras, dígitos, guión bajo; no empieza con dígito)
_ident_chars = st.characters(
    whitelist_categories=("Ll", "Lu", "Nd"),
    whitelist_characters="_",
)
_ident_strategy = st.text(
    alphabet=_ident_chars,
    min_size=1,
    max_size=20,
).filter(lambda s: s[0].isalpha() or s[0] == "_")

# Valores de parámetros: sin comillas, comas ni paréntesis para no romper el parser
_value_strategy = st.text(
    alphabet=st.characters(
        blacklist_characters='",)=\n\r\t',
        blacklist_categories=("Cs",),
    ),
    min_size=0,
    max_size=30,
)


# ---------------------------------------------------------------------------
# P7: Round-trip parser TOOL_CALL
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    nombre=_ident_strategy,
    params=st.dictionaries(_ident_strategy, _value_strategy, max_size=4),
)
def test_tool_call_roundtrip(nombre, params):
    """
    **Validates: Requirement 8.2**

    Formatear un TOOL_CALL y luego parsearlo debe recuperar exactamente
    el mismo nombre y parámetros.
    """
    # Construir el texto TOOL_CALL
    params_str = ", ".join(f'{k}="{v}"' for k, v in params.items())
    texto = f"TOOL_CALL: {nombre}({params_str})"

    resultado = parsear_tool_call(texto)

    assert resultado is not None, f"parsear_tool_call retornó None para: {texto!r}"
    nombre_parsed, params_parsed = resultado

    assert nombre_parsed == nombre, (
        f"Nombre incorrecto: esperado {nombre!r}, obtenido {nombre_parsed!r}"
    )
    for k, v in params.items():
        assert params_parsed.get(k) == v, (
            f"Parámetro {k!r}: esperado {v!r}, obtenido {params_parsed.get(k)!r}"
        )


# ---------------------------------------------------------------------------
# P9: Herramientas no aceptan parámetros de coordenadas absolutas
# ---------------------------------------------------------------------------

def test_tools_no_coord_params():
    """
    **Validates: Requirement 8.1**

    Ninguna herramienta registrada en el registro global debe tener
    parámetros con nombres de coordenadas absolutas.
    """
    from tools import _TOOLS

    for nombre_tool, tool in _TOOLS.items():
        # Obtener los parámetros de la herramienta
        params_tool = getattr(tool, "parametros", {}) or {}
        coords_encontradas = _COORD_PARAMS & set(params_tool.keys())
        assert not coords_encontradas, (
            f"Herramienta '{nombre_tool}' tiene parámetros de coordenadas: "
            f"{coords_encontradas}"
        )
