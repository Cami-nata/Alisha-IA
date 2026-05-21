"""
terminal_ui.py — Interfaz de terminal bonita para Alisha.
Usa Rich para colores, paneles y texto estilizado.
"""
import re
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.columns import Columns
from rich import box

# Paleta rosa pastel
PINK       = "bold #f48fb1"
PINK_LIGHT = "#f9d4e2"
PINK_DARK  = "#c2185b"
WHITE      = "white"
GRAY       = "#9c6080"
GREEN      = "#a6e3a1"
YELLOW     = "#f9e2af"
RED        = "#f38ba8"

console = Console()


def limpiar_asteriscos(texto: str) -> str:
    texto = re.sub(r'\*[^*\n]+\*', '', texto)
    return re.sub(r'  +', ' ', texto).strip()


def mostrar_bienvenida(nombre_ia: str, nombre_usuario: str) -> None:
    """Muestra el banner de bienvenida."""
    console.clear()

    banner = Text(justify="center")
    banner.append("\n  ✦ ", style=PINK)
    banner.append(nombre_ia.upper(), style=f"bold {PINK_DARK}")
    banner.append("  ✦\n", style=PINK)
    banner.append(f"  Tu compañera virtual\n", style=GRAY)

    console.print(Panel(
        banner,
        border_style=PINK,
        box=box.ROUNDED,
        padding=(0, 4),
    ))

    console.print(
        f"  Hola [bold {PINK_DARK}]{nombre_usuario}[/]! "
        f"Escribe [dim]/ayuda[/] para ver comandos.\n",
        style=PINK_LIGHT,
    )


def mostrar_mensaje_ia(nombre_ia: str, texto: str, emocion: str = "neutral") -> None:
    """Muestra un mensaje de la IA con estilo."""
    texto = limpiar_asteriscos(texto)
    if not texto:
        return

    # Color según emoción
    colores = {
        "alegría":      "#f9e2af",
        "entusiasmo":   "#f48fb1",
        "curiosidad":   "#89b4fa",
        "preocupación": "#cba6f7",
        "frustración":  "#f38ba8",
        "cansancio":    "#9c6080",
        "neutral":      "#f9d4e2",
    }
    color = colores.get(emocion, "#f9d4e2")

    # Emoji según emoción
    emojis = {
        "alegría":      "🌸",
        "entusiasmo":   "✨",
        "curiosidad":   "🤔",
        "preocupación": "💜",
        "frustración":  "😤",
        "cansancio":    "😴",
        "neutral":      "💬",
    }
    emoji = emojis.get(emocion, "💬")

    hora = datetime.now().strftime("%H:%M")

    console.print(
        f"\n [bold {PINK_DARK}]{emoji} {nombre_ia}[/] [dim]{hora}[/]"
    )
    console.print(
        Panel(
            texto,
            border_style=color,
            box=box.ROUNDED,
            padding=(0, 2),
            style=f"{color}",
        )
    )


def mostrar_mensaje_usuario(nombre: str, texto: str) -> None:
    """Muestra el mensaje del usuario."""
    hora = datetime.now().strftime("%H:%M")
    console.print(
        f"\n [bold white]👤 {nombre}[/] [dim]{hora}[/]"
    )
    console.print(
        Panel(
            texto,
            border_style="white",
            box=box.ROUNDED,
            padding=(0, 2),
            style="white",
        )
    )


def mostrar_pensando(nombre_ia: str) -> None:
    """Muestra indicador de que Alisha está pensando."""
    console.print(f"\n  [{PINK}]{nombre_ia} está pensando...[/]", end="\r")


def mostrar_sistema(texto: str) -> None:
    """Muestra un mensaje del sistema."""
    texto = limpiar_asteriscos(texto)
    console.print(f"\n  [dim italic {GRAY}]{texto}[/]")


def mostrar_error(texto: str) -> None:
    """Muestra un error."""
    console.print(f"\n  [{RED}]⚠ {texto}[/]")


def mostrar_ayuda() -> None:
    """Muestra el panel de ayuda."""
    console.print(Panel(
        "[bold]Comandos disponibles:[/]\n\n"
        f"  [{PINK}]/reiniciar[/]  — borra el historial\n"
        f"  [{PINK}]/memoria[/]    — borra toda la memoria\n"
        f"  [{PINK}]/perfil[/]     — reinicia tu perfil\n"
        f"  [{PINK}]/ayuda[/]      — muestra este mensaje\n"
        f"  [{PINK}]salir[/]       — cierra Alisha",
        title="[bold]Ayuda[/]",
        border_style=PINK,
        box=box.ROUNDED,
        padding=(0, 2),
    ))


def pedir_input(nombre: str) -> str:
    """Pide input al usuario con estilo."""
    try:
        return console.input(f"\n  [bold {PINK_DARK}]Tú:[/] ").strip()
    except (EOFError, KeyboardInterrupt):
        return "salir"


def pedir_confirmacion(pregunta: str) -> bool:
    """Pide confirmación con estilo."""
    console.print(f"\n  [{YELLOW}]⚠ {pregunta}[/]", end=" ")
    try:
        resp = console.input(f"[dim][s/N]:[/] ").strip().lower()
        return resp in ("s", "si", "sí", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def mostrar_estado_emocional(estado: str, dopamina: float, energia: float) -> None:
    """Muestra el estado interno de Alisha en una barra pequeña."""
    barra_dopamina = "█" * int(dopamina * 10) + "░" * (10 - int(dopamina * 10))
    barra_energia  = "█" * int(energia * 10)  + "░" * (10 - int(energia * 10))
    console.print(
        f"  [dim]Estado: {estado} | "
        f"Dopamina [{PINK}]{barra_dopamina}[/] | "
        f"Energía [{GREEN}]{barra_energia}[/][/]"
    )
