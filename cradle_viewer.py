"""
cradle_viewer.py — Ventana de visualización de la Cuna Virtual de Alisha.

Muestra en tiempo real:
- Estado emocional y energía de Alisha
- Pensamientos espontáneos que genera
- Animación del chibi con su estado actual
- Historial de pensamientos del día
- Indicadores de dopamina, cansancio y humor

Ejecutar directamente: python cradle_viewer.py
O desde ia.py al elegir modo "v" (visual)
"""
import json
import math
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import pygame
import pygame.gfxdraw

# ---------------------------------------------------------------------------
# Configuración visual
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 480, 620
FPS = 60

# Paleta rosada
BG          = (30, 18, 28)
BG_PANEL    = (45, 28, 42)
PINK        = (244, 143, 177)
PINK_LIGHT  = (252, 228, 236)
PINK_DARK   = (194,  24,  91)
PURPLE      = (156,  39, 176)
PURPLE_LITE = (206, 147, 216)
WHITE       = (255, 255, 255)
GRAY        = (180, 160, 175)
GREEN       = (129, 199, 132)
YELLOW      = (255, 241, 118)
ORANGE      = (255, 183,  77)
RED         = (239,  83,  80)

from config import DATA_DIR
STATE_FILE   = DATA_DIR / "chibi_state.json"
CRADLE_FILE  = DATA_DIR / "cradle_state.json"

# ---------------------------------------------------------------------------
# Lector de estado
# ---------------------------------------------------------------------------

def leer_estado_chibi() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"estado": "neutral", "hablando": False, "texto": "", "modo": "IDLE"}


def leer_estado_cuna() -> dict:
    try:
        if CRADLE_FILE.exists():
            return json.loads(CRADLE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"energia": 0.7, "humor": "neutral", "temas_recientes": []}


def leer_estado_emocional() -> dict:
    try:
        from emotion_engine import EmotionEngine
        return EmotionEngine.get_instance().obtener_estado_actual()
    except Exception:
        return {"estado": "neutral", "dopamina": 0.6, "cansancio": 0.0, "intensidad": 0.5}


def leer_pensamientos_cuna() -> list[str]:
    try:
        from virtual_cradle import get_cuna
        cuna = get_cuna()
        if cuna:
            return cuna._pensamientos_hoy[-8:]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Dibujado del chibi (versión compacta para el viewer)
# ---------------------------------------------------------------------------

class MiniChibi:
    """Chibi animado compacto para el viewer."""

    def __init__(self, x: int, y: int, size: int = 120):
        self.x, self.y, self.size = x, y, size
        self.blink_timer = 0.0
        self.blink_open = True
        self.float_timer = 0.0
        self.bounce_timer = 0.0
        self.mouth_open = 0.0

    def update(self, dt: float, estado: str, hablando: bool) -> None:
        self.float_timer += dt * 1.5
        self.bounce_timer += dt * 4

        self.blink_timer += dt
        if self.blink_open and self.blink_timer > 3.0:
            self.blink_open = False
            self.blink_timer = 0
        elif not self.blink_open and self.blink_timer > 0.1:
            self.blink_open = True
            self.blink_timer = 0

        if hablando:
            self.mouth_open = 0.5 + 0.5 * math.sin(time.time() * 14)
        else:
            self.mouth_open = max(0.0, self.mouth_open - dt * 6)

    def draw(self, surface: pygame.Surface, estado: str, hablando: bool) -> None:
        s = self.size
        cx = self.x + s // 2
        float_y = int(math.sin(self.float_timer) * 3)
        bounce_y = int(abs(math.sin(self.bounce_timer)) * 4) if estado in ("alegría", "entusiasmo") else 0
        cy = self.y + s // 2 + float_y - bounce_y
        fr = s // 6

        # Cabello
        pygame.draw.ellipse(surface, (194, 24, 91),
                            (cx - fr - 2, cy - fr - 5, (fr + 2) * 2, fr * 2))
        pygame.draw.ellipse(surface, (194, 24, 91),
                            (cx - fr * 2 + 4, cy - fr // 2, fr, int(fr * 1.5)))
        pygame.draw.ellipse(surface, (194, 24, 91),
                            (cx + fr - 4, cy - fr // 2, fr, int(fr * 1.5)))

        # Cara
        pygame.draw.circle(surface, (255, 224, 178), (cx, cy), fr)
        pygame.draw.circle(surface, PINK_DARK, (cx, cy), fr, 2)

        # Ojos
        ey = cy - fr // 5
        edx = fr // 3
        er = max(2, fr // 5)

        if estado in ("alegría", "entusiasmo"):
            for side in (-1, 1):
                ex = cx + side * edx
                rect = pygame.Rect(ex - er, ey - er // 2, er * 2, er)
                pygame.draw.arc(surface, (74, 32, 64), rect, math.pi, 0, 2)
            # Mejillas
            for side in (-1, 1):
                blush = pygame.Surface((er * 3, er), pygame.SRCALPHA)
                blush.fill((255, 150, 180, 120))
                surface.blit(blush, (cx + side * edx - er, ey + er))
        elif estado == "cansancio":
            for side in (-1, 1):
                ex = cx + side * edx
                pygame.draw.circle(surface, (74, 32, 64), (ex, ey), er)
                pygame.draw.rect(surface, (255, 224, 178),
                                 (ex - er - 1, ey - er - 1, er * 2 + 2, er))
        elif estado == "curiosidad":
            if self.blink_open:
                pygame.draw.circle(surface, (74, 32, 64), (cx - edx, ey), er)
                pygame.draw.circle(surface, (74, 32, 64), (cx + edx, ey), int(er * 1.4))
                pygame.draw.circle(surface, WHITE, (cx + edx - er // 2, ey - er // 2), er // 2)
        else:
            for side in (-1, 1):
                ex = cx + side * edx
                if self.blink_open:
                    pygame.draw.circle(surface, (74, 32, 64), (ex, ey), er)
                    pygame.draw.circle(surface, WHITE, (ex - er // 3, ey - er // 3), er // 3)
                else:
                    pygame.draw.line(surface, (74, 32, 64),
                                     (ex - er, ey), (ex + er, ey), 2)

        # Boca
        my = cy + fr // 2
        mo = int(self.mouth_open * fr // 3)
        if estado in ("alegría", "entusiasmo"):
            rect = pygame.Rect(cx - fr // 3, my - fr // 6, int(fr // 1.5), fr // 3)
            pygame.draw.arc(surface, PINK_DARK, rect, math.pi, 0, 2)
        elif mo > 2:
            pygame.draw.ellipse(surface, (255, 200, 210),
                                (cx - fr // 4, my - mo // 2, fr // 2, mo))
        else:
            pygame.draw.line(surface, PINK_DARK,
                             (cx - fr // 4, my), (cx + fr // 4, my), 2)

        # Cuerpo
        bx = cx - fr + 4
        by = cy + fr - 2
        bw = (fr - 4) * 2
        bh = fr + fr // 2
        body = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(body, (248, 187, 208, 255), (0, 0, bw, bh), border_radius=8)
        pygame.draw.rect(body, (*PINK_DARK, 200), (0, 0, bw, bh), border_radius=8, width=2)
        surface.blit(body, (bx, by))
        pygame.draw.circle(surface, (233, 30, 100), (cx, by + bh // 4), max(2, fr // 6))


# ---------------------------------------------------------------------------
# Barra de indicador
# ---------------------------------------------------------------------------

def draw_bar(surface: pygame.Surface, x: int, y: int, w: int, h: int,
             valor: float, color_fill: tuple, label: str, font: pygame.font.Font) -> None:
    """Dibuja una barra de progreso con etiqueta."""
    # Fondo
    pygame.draw.rect(surface, BG_PANEL, (x, y, w, h), border_radius=4)
    pygame.draw.rect(surface, (80, 60, 75), (x, y, w, h), border_radius=4, width=1)

    # Relleno
    fill_w = max(4, int(w * max(0.0, min(1.0, valor))))
    if fill_w > 4:
        pygame.draw.rect(surface, color_fill, (x, y, fill_w, h), border_radius=4)

    # Etiqueta
    pct = int(valor * 100)
    texto = f"{label}: {pct}%"
    surf = font.render(texto, True, WHITE)
    surface.blit(surf, (x + 6, y + (h - surf.get_height()) // 2))


# ---------------------------------------------------------------------------
# Ventana principal del viewer
# ---------------------------------------------------------------------------

class CradleViewer:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Cuna Virtual — Alisha")

        try:
            self.font_title  = pygame.font.SysFont("Segoe UI", 18, bold=True)
            self.font_body   = pygame.font.SysFont("Segoe UI", 13)
            self.font_small  = pygame.font.SysFont("Segoe UI", 11)
            self.font_estado = pygame.font.SysFont("Segoe UI", 15, bold=True)
        except Exception:
            self.font_title  = pygame.font.Font(None, 20)
            self.font_body   = pygame.font.Font(None, 14)
            self.font_small  = pygame.font.Font(None, 12)
            self.font_estado = pygame.font.Font(None, 16)

        self.clock  = pygame.time.Clock()
        self.chibi  = MiniChibi(x=WIDTH // 2 - 60, y=20, size=120)

        # Estado
        self.estado_chibi  = {}
        self.estado_cuna   = {}
        self.estado_emo    = {}
        self.pensamientos  = []
        self.scroll_offset = 0

        # Animación de pensamiento nuevo
        self._nuevo_pensamiento_timer = 0.0
        self._ultimo_pensamiento_count = 0

        # Actualizar estado en background
        self._ultimo_update = 0.0

    def _actualizar_estado(self) -> None:
        self.estado_chibi = leer_estado_chibi()
        self.estado_cuna  = leer_estado_cuna()
        self.estado_emo   = leer_estado_emocional()
        nuevos = leer_pensamientos_cuna()
        if len(nuevos) > self._ultimo_pensamiento_count:
            self._nuevo_pensamiento_timer = 2.0
            self._ultimo_pensamiento_count = len(nuevos)
        self.pensamientos = nuevos

    def _color_estado(self, estado: str) -> tuple:
        colores = {
            "alegría":      (255, 213, 79),
            "entusiasmo":   (255, 167, 38),
            "curiosidad":   (129, 212, 250),
            "preocupación": (255, 138, 101),
            "frustración":  (239, 83, 80),
            "cansancio":    (161, 136, 127),
            "neutral":      (206, 147, 216),
            "nostalgia":    (149, 117, 205),
        }
        return colores.get(estado, PURPLE_LITE)

    def _emoji_estado(self, estado: str) -> str:
        emojis = {
            "alegría": "✨", "entusiasmo": "⚡", "curiosidad": "🔍",
            "preocupación": "💭", "frustración": "😤", "cansancio": "😴",
            "neutral": "💜", "nostalgia": "🌙",
        }
        return emojis.get(estado, "💜")

    def _wrap_text(self, texto: str, font: pygame.font.Font, max_w: int) -> list[str]:
        words = texto.split()
        lines = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if font.size(test)[0] > max_w:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    def draw(self) -> None:
        self.screen.fill(BG)

        estado = self.estado_chibi.get("estado", "neutral")
        hablando = self.estado_chibi.get("hablando", False)
        modo = self.estado_chibi.get("modo", "IDLE")
        emo = self.estado_emo

        # ── Header ──────────────────────────────────────────────────────
        pygame.draw.rect(self.screen, BG_PANEL, (0, 0, WIDTH, 160))
        pygame.draw.line(self.screen, PINK_DARK, (0, 160), (WIDTH, 160), 1)

        # Chibi
        self.chibi.draw(self.screen, estado, hablando)

        # Nombre y estado
        color_e = self._color_estado(estado)
        emoji = self._emoji_estado(estado)
        titulo = self.font_title.render("✦ Alisha — Cuna Virtual", True, PINK_LIGHT)
        self.screen.blit(titulo, (WIDTH // 2 - titulo.get_width() // 2, 140))

        # Modo actual
        modo_colores = {
            "IDLE": GRAY, "THINKING": YELLOW, "WORKING": ORANGE,
            "OVERLOADED": RED, "SLEEPING": PURPLE_LITE,
        }
        modo_color = modo_colores.get(modo, GRAY)
        modo_surf = self.font_small.render(f"● {modo}", True, modo_color)
        self.screen.blit(modo_surf, (WIDTH - modo_surf.get_width() - 12, 8))

        # ── Panel de indicadores ─────────────────────────────────────────
        py = 170
        panel_h = 110
        pygame.draw.rect(self.screen, BG_PANEL, (10, py, WIDTH - 20, panel_h), border_radius=10)
        pygame.draw.rect(self.screen, (80, 50, 70), (10, py, WIDTH - 20, panel_h), border_radius=10, width=1)

        # Estado emocional badge
        badge_text = f"{emoji} {estado.upper()}"
        badge_surf = self.font_estado.render(badge_text, True, color_e)
        self.screen.blit(badge_surf, (20, py + 8))

        # Barras
        dopamina = emo.get("dopamina", 0.6)
        cansancio = emo.get("cansancio", 0.0)
        energia_cuna = self.estado_cuna.get("energia", 0.7)

        bar_w = WIDTH - 60
        draw_bar(self.screen, 20, py + 35, bar_w, 18,
                 dopamina, (255, 213, 79), "Dopamina", self.font_small)
        draw_bar(self.screen, 20, py + 58, bar_w, 18,
                 energia_cuna, (129, 199, 132), "Energía", self.font_small)
        draw_bar(self.screen, 20, py + 81, bar_w, 18,
                 cansancio, (239, 83, 80), "Cansancio", self.font_small)

        # ── Temas recientes ──────────────────────────────────────────────
        ty = py + panel_h + 12
        temas = self.estado_cuna.get("temas_recientes", [])
        if temas:
            label = self.font_small.render("Temas recientes:", True, GRAY)
            self.screen.blit(label, (14, ty))
            tx = 14 + label.get_width() + 8
            for tema in temas[-5:]:
                tag = self.font_small.render(f"#{tema}", True, PURPLE_LITE)
                if tx + tag.get_width() + 10 < WIDTH - 10:
                    pygame.draw.rect(self.screen, (60, 40, 60),
                                     (tx - 4, ty - 2, tag.get_width() + 8, tag.get_height() + 4),
                                     border_radius=6)
                    self.screen.blit(tag, (tx, ty))
                    tx += tag.get_width() + 14
            ty += 22

        # ── Pensamientos ─────────────────────────────────────────────────
        sep_y = ty + 4
        pygame.draw.line(self.screen, (80, 50, 70), (10, sep_y), (WIDTH - 10, sep_y), 1)

        header_y = sep_y + 8
        header = self.font_body.render("💭 Pensamientos de hoy", True, PINK_LIGHT)
        self.screen.blit(header, (14, header_y))

        # Indicador de pensamiento nuevo
        if self._nuevo_pensamiento_timer > 0:
            nuevo_surf = self.font_small.render("● nuevo", True, GREEN)
            self.screen.blit(nuevo_surf, (WIDTH - nuevo_surf.get_width() - 14, header_y + 2))

        # Lista de pensamientos con scroll
        list_y = header_y + 26
        list_h = HEIGHT - list_y - 10
        clip = pygame.Rect(10, list_y, WIDTH - 20, list_h)
        self.screen.set_clip(clip)

        y_cursor = list_y - self.scroll_offset
        line_h = self.font_body.get_height() + 2

        if not self.pensamientos:
            vacio = self.font_small.render("Todavía no generé pensamientos hoy...", True, GRAY)
            self.screen.blit(vacio, (20, y_cursor))
        else:
            for i, pensamiento in enumerate(reversed(self.pensamientos)):
                # Burbuja de pensamiento
                lines = self._wrap_text(pensamiento, self.font_body, WIDTH - 60)
                bh = len(lines) * line_h + 14
                bw = WIDTH - 40

                if y_cursor + bh > list_y and y_cursor < list_y + list_h:
                    # Color de fondo alternado
                    bg_color = (55, 35, 52) if i % 2 == 0 else (48, 30, 45)
                    pygame.draw.rect(self.screen, bg_color,
                                     (14, y_cursor, bw, bh), border_radius=8)
                    pygame.draw.rect(self.screen, (80, 50, 70),
                                     (14, y_cursor, bw, bh), border_radius=8, width=1)

                    # Texto
                    for j, line in enumerate(lines):
                        surf = self.font_body.render(line, True, PINK_LIGHT)
                        self.screen.blit(surf, (22, y_cursor + 7 + j * line_h))

                y_cursor += bh + 6

        self.screen.set_clip(None)

        # Scrollbar si hay contenido
        total_h = y_cursor + self.scroll_offset - list_y
        if total_h > list_h:
            sb_h = max(20, int(list_h * list_h / total_h))
            sb_y = list_y + int(self.scroll_offset * (list_h - sb_h) / max(1, total_h - list_h))
            pygame.draw.rect(self.screen, (80, 50, 70),
                             (WIDTH - 8, list_y, 4, list_h), border_radius=2)
            pygame.draw.rect(self.screen, PINK_DARK,
                             (WIDTH - 8, sb_y, 4, sb_h), border_radius=2)

        pygame.display.flip()

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            # Actualizar estado cada segundo
            now = time.time()
            if now - self._ultimo_update > 1.0:
                self._actualizar_estado()
                self._ultimo_update = now

            if self._nuevo_pensamiento_timer > 0:
                self._nuevo_pensamiento_timer -= dt

            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_UP:
                        self.scroll_offset = max(0, self.scroll_offset - 30)
                    elif event.key == pygame.K_DOWN:
                        self.scroll_offset += 30
                elif event.type == pygame.MOUSEWHEEL:
                    self.scroll_offset = max(0, self.scroll_offset - event.y * 25)

            # Actualizar chibi
            estado = self.estado_chibi.get("estado", "neutral")
            hablando = self.estado_chibi.get("hablando", False)
            self.chibi.update(dt, estado, hablando)

            self.draw()

        pygame.quit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def abrir_viewer() -> threading.Thread:
    """Abre el viewer en un hilo separado. Retorna el hilo."""
    def _run():
        viewer = CradleViewer()
        viewer.run()
    t = threading.Thread(target=_run, daemon=True, name="CradleViewer")
    t.start()
    return t


if __name__ == "__main__":
    print("Abriendo Cuna Virtual de Alisha...")
    print("↑↓ o scroll para navegar pensamientos | ESC para cerrar")
    viewer = CradleViewer()
    viewer.run()
