"""
tests/run_all_tests.py — Runner de tests de Alisha IA con reporte visual.

Ejecuta los 7 tests de test_alisha.py y muestra:
  ✓ VERDE  → test pasó
  ✗ ROJO   → test falló (con descripción del error)

Uso:
  python tests/run_all_tests.py

Exit codes:
  0 → todos los tests pasaron
  1 → algún test falló
"""
import sys
import os
import time
import traceback
from pathlib import Path

# Agregar raíz del proyecto al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Colores ANSI ───────────────────────────────────────────────────────────────
try:
    import colorama
    colorama.init()
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
except ImportError:
    GREEN = RED = YELLOW = CYAN = BOLD = RESET = ""


def _color(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"


# ── Importar tests ─────────────────────────────────────────────────────────────
try:
    from tests.test_alisha import (
        test_1_brain_responde,
        test_2_memoria_persiste,
        test_3_herramienta_pc,
        test_4_navegador,
        test_5_whatsapp_bridge,
        test_6_hotkey,
        test_7_seguridad,
    )
except ImportError:
    # Intentar import relativo
    sys.path.insert(0, str(ROOT / "tests"))
    from test_alisha import (
        test_1_brain_responde,
        test_2_memoria_persiste,
        test_3_herramienta_pc,
        test_4_navegador,
        test_5_whatsapp_bridge,
        test_6_hotkey,
        test_7_seguridad,
    )

# ── Lista de tests ─────────────────────────────────────────────────────────────
TESTS = [
    ("test_1_brain_responde",   "Brain responde en < 3 segundos",          test_1_brain_responde),
    ("test_2_memoria_persiste", "Memoria persiste entre reinicios",         test_2_memoria_persiste),
    ("test_3_herramienta_pc",   "PC Controller abre Notepad",               test_3_herramienta_pc),
    ("test_4_navegador",        "Browser Controller busca en Google",       test_4_navegador),
    ("test_5_whatsapp_bridge",  "WhatsApp Bridge corriendo en puerto 3000", test_5_whatsapp_bridge),
    ("test_6_hotkey",           "INSERT registrado en HotkeyManager",       test_6_hotkey),
    ("test_7_seguridad",        "SecurityManager pide confirmación",        test_7_seguridad),
]


def run_test(name: str, description: str, func) -> dict:
    """Ejecuta un test individual y retorna el resultado."""
    result = {
        "name":        name,
        "description": description,
        "passed":      False,
        "skipped":     False,
        "error":       "",
        "elapsed":     0.0,
    }

    inicio = time.time()
    try:
        func()
        result["passed"] = True
    except Exception as e:
        error_msg = str(e)
        # Detectar skip de pytest
        if "Skipped" in type(e).__name__ or "skip" in error_msg.lower():
            result["skipped"] = True
            result["error"] = error_msg
        else:
            result["passed"] = False
            result["error"] = error_msg
    finally:
        result["elapsed"] = time.time() - inicio

    return result


def print_header():
    print()
    print(_color("═" * 60, CYAN))
    print(_color("  ALISHA IA — Suite de Tests", BOLD + CYAN))
    print(_color("═" * 60, CYAN))
    print()


def print_result(i: int, result: dict):
    elapsed = f"{result['elapsed']:.2f}s"

    if result["passed"]:
        icon   = _color("✓", GREEN + BOLD)
        status = _color("PASÓ", GREEN + BOLD)
        line   = f"  {icon} [{i}] {result['description']:<42} {status}  ({elapsed})"
    elif result["skipped"]:
        icon   = _color("⚠", YELLOW + BOLD)
        status = _color("SKIP", YELLOW + BOLD)
        line   = f"  {icon} [{i}] {result['description']:<42} {status}  ({elapsed})"
    else:
        icon   = _color("✗", RED + BOLD)
        status = _color("FALLÓ", RED + BOLD)
        line   = f"  {icon} [{i}] {result['description']:<42} {status}  ({elapsed})"

    print(line)

    if not result["passed"] and not result["skipped"] and result["error"]:
        # Mostrar error resumido
        error_lines = result["error"].split("\n")
        for line in error_lines[:3]:
            if line.strip():
                print(f"       {_color('→', RED)} {line.strip()}")


def print_summary(results: list[dict]):
    total   = len(results)
    passed  = sum(1 for r in results if r["passed"])
    failed  = sum(1 for r in results if not r["passed"] and not r["skipped"])
    skipped = sum(1 for r in results if r["skipped"])
    total_time = sum(r["elapsed"] for r in results)

    print()
    print(_color("─" * 60, CYAN))
    print(f"  Resultados: ", end="")
    print(_color(f"{passed} pasaron", GREEN + BOLD), end="  ")
    if failed:
        print(_color(f"{failed} fallaron", RED + BOLD), end="  ")
    if skipped:
        print(_color(f"{skipped} saltados", YELLOW + BOLD), end="  ")
    print(f"  ({total_time:.2f}s total)")
    print(_color("─" * 60, CYAN))

    if failed == 0:
        print(_color("\n  ✓ Todos los tests pasaron. Alisha está lista.", GREEN + BOLD))
    else:
        print(_color(f"\n  ✗ {failed} test(s) fallaron. Revisar los errores arriba.", RED + BOLD))
    print()


def main() -> int:
    print_header()

    results = []
    for i, (name, description, func) in enumerate(TESTS, 1):
        print(f"  Ejecutando [{i}/{len(TESTS)}] {description}...", end="\r")
        result = run_test(name, description, func)
        results.append(result)
        print_result(i, result)

    print_summary(results)

    # Exit code: 0 si todos pasaron (o saltados), 1 si alguno falló
    failed = sum(1 for r in results if not r["passed"] and not r["skipped"])
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
