"""
alisha_trainer.py — Módulo de Entrenamiento de Alisha.

Permite grabar flujos de trabajo (workflows) observando las acciones del usuario
y convertirlos en habilidades ejecutables guardadas en alisha_memory.db.

Modos:
  - GRABANDO: registra acciones del usuario (mouse, teclado, ventanas)
  - PROCESANDO: Gemini convierte la secuencia en un script ejecutable
  - EJECUTANDO: reproduce el workflow paso a paso con feedback visual

Uso desde el chat:
  /entrenar [nombre]     → inicia grabación
  /parar                 → detiene grabación y procesa
  /habilidades           → lista habilidades guardadas
  /ejecutar [nombre]     → ejecuta una habilidad
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

# ── Estado del trainer ────────────────────────────────────────────────────────
_ESTADO_IDLE       = "IDLE"
_ESTADO_GRABANDO   = "GRABANDO"
_ESTADO_PROCESANDO = "PROCESANDO"
_ESTADO_EJECUTANDO = "EJECUTANDO"

from config import DATA_DIR
STATE_FILE = DATA_DIR / "chibi_state.json"


class AlishaTrainer:
    """
    Motor de entrenamiento de Alisha.
    Graba acciones del usuario y las convierte en habilidades ejecutables.
    """

    def __init__(self, socketio_emit: Callable = None):
        self._estado          = _ESTADO_IDLE
        self._nombre_actual   = ""
        self._pasos_grabados: list[dict] = []
        self._hilo_grabacion: Optional[threading.Thread] = None
        self._grabando        = False
        self._emit            = socketio_emit or (lambda *a, **k: None)

        # Detección de tareas repetitivas
        self._historial_ventanas: list[str] = []
        self._ultimo_patron_detectado = ""
        self._ultimo_aviso_repeticion = 0.0

    # ── API pública ────────────────────────────────────────────────────────────

    def iniciar_grabacion(self, nombre: str) -> str:
        """Inicia la grabación de un workflow."""
        if self._grabando:
            return f"Ya estoy grabando '{self._nombre_actual}'. Usá /parar para terminar."

        self._nombre_actual  = nombre or f"habilidad_{datetime.now().strftime('%H%M%S')}"
        self._pasos_grabados = []
        self._grabando       = True
        self._estado         = _ESTADO_GRABANDO

        # Actualizar gesto Live2D → concentración
        self._set_live2d_estado("curiosidad")

        # Iniciar hilo de grabación
        self._hilo_grabacion = threading.Thread(
            target=self._loop_grabacion,
            daemon=True,
            name="AlishaTrainer-Grabacion"
        )
        self._hilo_grabacion.start()

        msg = (
            f"Modo entrenamiento activado para '{self._nombre_actual}'. "
            f"Hacé lo que querés que aprenda — estoy mirando. "
            f"Cuando termines, escribí /parar."
        )
        self._emit_chat(msg, "curiosidad")
        return msg

    def detener_grabacion(self) -> str:
        """Detiene la grabación y procesa el workflow con Gemini."""
        if not self._grabando:
            return "No estoy grabando nada ahora mismo."

        self._grabando = False
        self._estado   = _ESTADO_PROCESANDO
        self._set_live2d_estado("preocupación")  # gesto de procesamiento

        n_pasos = len(self._pasos_grabados)
        if n_pasos == 0:
            self._estado = _ESTADO_IDLE
            return "No grabé ningún paso. Intentá de nuevo."

        self._emit_chat(
            f"Grabé {n_pasos} pasos. Procesando con Gemini para convertirlo en habilidad...",
            "curiosidad"
        )

        # Procesar en hilo separado
        threading.Thread(
            target=self._procesar_workflow,
            daemon=True,
            name="AlishaTrainer-Procesamiento"
        ).start()

        return f"Procesando {n_pasos} pasos grabados..."

    def ejecutar_habilidad(self, nombre: str) -> str:
        """Ejecuta una habilidad guardada paso a paso."""
        try:
            from memory_db import MemoryDB
            db = MemoryDB()
            habilidad = db.obtener_habilidad(nombre)
        except Exception as e:
            return f"Error accediendo a la base de datos: {e}"

        if not habilidad:
            # Buscar por coincidencia parcial
            try:
                from memory_db import MemoryDB
                db = MemoryDB()
                todas = db.listar_habilidades()
                coincidencias = [h for h in todas if nombre.lower() in h["nombre"].lower()]
                if coincidencias:
                    habilidad = db.obtener_habilidad(coincidencias[0]["nombre"])
                else:
                    return f"No encontré la habilidad '{nombre}'. Usá /habilidades para ver las disponibles."
            except Exception:
                return f"No encontré la habilidad '{nombre}'."

        self._estado = _ESTADO_EJECUTANDO
        self._set_live2d_estado("concentración")

        threading.Thread(
            target=self._ejecutar_pasos,
            args=(habilidad,),
            daemon=True,
            name="AlishaTrainer-Ejecucion"
        ).start()

        return f"Ejecutando habilidad '{habilidad['nombre']}'..."

    def listar_habilidades(self) -> str:
        """Lista todas las habilidades entrenadas."""
        try:
            from memory_db import MemoryDB
            db = MemoryDB()
            habilidades = db.listar_habilidades()
        except Exception as e:
            return f"Error: {e}"

        if not habilidades:
            return "No tengo habilidades entrenadas todavía. Usá /entrenar [nombre] para enseñarme algo."

        lineas = ["**Mis habilidades:**\n"]
        for h in habilidades:
            lineas.append(
                f"• **{h['nombre']}** — {h['descripcion'] or 'sin descripción'} "
                f"(ejecutada {h['veces_ejecutada']} veces)"
            )
        return "\n".join(lineas)

    def get_estado(self) -> str:
        return self._estado

    def detectar_tarea_repetitiva(self, titulo_ventana: str) -> Optional[str]:
        """
        Detecta si el usuario está repitiendo una tarea.
        Retorna un mensaje de sugerencia o None.
        """
        ahora = time.time()
        # Cooldown de 5 minutos entre avisos
        if ahora - self._ultimo_aviso_repeticion < 300:
            return None

        self._historial_ventanas.append(titulo_ventana.lower()[:50])
        if len(self._historial_ventanas) > 20:
            self._historial_ventanas = self._historial_ventanas[-20:]

        # Detectar patrón: misma secuencia de 2 ventanas repetida 3+ veces
        ventanas = self._historial_ventanas
        if len(ventanas) < 6:
            return None

        # Buscar patrón de 2 ventanas que se repite
        for i in range(len(ventanas) - 5):
            patron = (ventanas[i], ventanas[i+1])
            repeticiones = 0
            for j in range(i, len(ventanas) - 1, 2):
                if j + 1 < len(ventanas) and (ventanas[j], ventanas[j+1]) == patron:
                    repeticiones += 1
            if repeticiones >= 3 and str(patron) != self._ultimo_patron_detectado:
                self._ultimo_patron_detectado = str(patron)
                self._ultimo_aviso_repeticion = ahora
                return (
                    f"Che, veo que estás alternando entre '{patron[0]}' y '{patron[1]}' "
                    f"varias veces. ¿Querés que aprenda ese flujo para hacerlo yo sola? "
                    f"Escribí /entrenar para que te grabe."
                )

        return None

    # ── Loop de grabación ──────────────────────────────────────────────────────

    def _loop_grabacion(self) -> None:
        """Graba acciones del usuario cada 2 segundos."""
        import ctypes
        import ctypes.wintypes

        ultimo_titulo = ""
        ultimo_pos    = (0, 0)
        paso_num      = 0

        while self._grabando:
            try:
                # 1. Ventana activa
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                buf  = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                titulo = buf.value or ""

                if titulo and titulo != ultimo_titulo:
                    paso_num += 1
                    self._pasos_grabados.append({
                        "tipo":      "ventana",
                        "paso":      paso_num,
                        "titulo":    titulo,
                        "timestamp": datetime.now().isoformat(),
                    })
                    ultimo_titulo = titulo
                    self._emit_progreso(paso_num, titulo)

                # 2. Posición del mouse (solo si se movió significativamente)
                try:
                    import pyautogui
                    pos = pyautogui.position()
                    dx  = abs(pos.x - ultimo_pos[0])
                    dy  = abs(pos.y - ultimo_pos[1])
                    if dx > 100 or dy > 100:
                        paso_num += 1
                        self._pasos_grabados.append({
                            "tipo":      "mouse_move",
                            "paso":      paso_num,
                            "x":         pos.x,
                            "y":         pos.y,
                            "timestamp": datetime.now().isoformat(),
                        })
                        ultimo_pos = (pos.x, pos.y)
                except Exception:
                    pass

                # 3. Captura de pantalla cada 5s para contexto visual
                if paso_num % 3 == 0:
                    try:
                        from screen_vision import capturar_ventana_rapida
                        img_bytes, _ = capturar_ventana_rapida(max_width=640)
                        if img_bytes:
                            self._pasos_grabados.append({
                                "tipo":      "screenshot",
                                "paso":      paso_num,
                                "titulo":    titulo,
                                "timestamp": datetime.now().isoformat(),
                                "img_size":  len(img_bytes),
                            })
                    except Exception:
                        pass

            except Exception as e:
                print(f"[Trainer] Error en grabación: {e}")

            time.sleep(2.0)

    # ── Procesamiento con Gemini ───────────────────────────────────────────────

    def _procesar_workflow(self) -> None:
        """Convierte los pasos grabados en un workflow ejecutable usando Gemini."""
        try:
            pasos_resumen = []
            for p in self._pasos_grabados:
                tipo = p.get("tipo", "")
                if tipo == "ventana":
                    pasos_resumen.append(f"Paso {p['paso']}: Cambió a ventana '{p['titulo']}'")
                elif tipo == "mouse_move":
                    pasos_resumen.append(f"Paso {p['paso']}: Mouse en ({p['x']}, {p['y']})")
                elif tipo == "screenshot":
                    pasos_resumen.append(f"Paso {p['paso']}: Captura de '{p['titulo']}'")

            resumen_texto = "\n".join(pasos_resumen[:30])  # máximo 30 pasos

            # Generar descripción y script con Gemini
            try:
                from brain import get_brain
                brain = get_brain()

                prompt = (
                    f"Analicé el siguiente flujo de trabajo del usuario:\n\n"
                    f"{resumen_texto}\n\n"
                    f"Nombre de la habilidad: '{self._nombre_actual}'\n\n"
                    f"Generá:\n"
                    f"1. Una descripción corta (1 oración) de qué hace este workflow\n"
                    f"2. Un script Python usando pyautogui que reproduzca estos pasos\n\n"
                    f"Respondé en JSON: {{\"descripcion\": \"...\", \"script\": \"...\"}}"
                )

                resp = brain.process(prompt)
                contenido = resp.content

                # Extraer JSON de la respuesta
                import re
                match = re.search(r'\{.*\}', contenido, re.DOTALL)
                descripcion = f"Workflow de {self._nombre_actual}"
                script      = ""

                if match:
                    try:
                        data        = json.loads(match.group())
                        descripcion = data.get("descripcion", descripcion)
                        script      = data.get("script", "")
                    except Exception:
                        pass

            except Exception as e:
                print(f"[Trainer] Error con Gemini: {e}")
                descripcion = f"Workflow de {self._nombre_actual}"
                script      = ""

            # Guardar en SQLite
            from memory_db import MemoryDB
            db = MemoryDB()
            habilidad_id = db.guardar_habilidad(
                nombre      = self._nombre_actual,
                descripcion = descripcion,
                pasos       = self._pasos_grabados,
                script      = script,
            )

            self._estado = _ESTADO_IDLE
            self._set_live2d_estado("alegría")

            msg = (
                f"¡Aprendí '{self._nombre_actual}'! "
                f"{descripcion} "
                f"Grabé {len(self._pasos_grabados)} pasos. "
                f"La próxima vez que me digas 'hacé lo de {self._nombre_actual}', lo ejecuto yo sola."
            )
            self._emit_chat(msg, "alegría")

            # Notificar al frontend que hay nueva habilidad
            self._emit("habilidad_guardada", {
                "id":          habilidad_id,
                "nombre":      self._nombre_actual,
                "descripcion": descripcion,
                "pasos":       len(self._pasos_grabados),
            })

        except Exception as e:
            self._estado = _ESTADO_IDLE
            print(f"[Trainer] Error procesando workflow: {e}")
            self._emit_chat(f"Ups, no pude procesar el workflow: {e}", "frustración")

    # ── Ejecución de habilidad ─────────────────────────────────────────────────

    def _ejecutar_pasos(self, habilidad: dict) -> None:
        """Ejecuta los pasos de una habilidad guardada."""
        pasos  = habilidad.get("pasos", [])
        nombre = habilidad.get("nombre", "")
        total  = len(pasos)

        if total == 0:
            self._emit_chat("Esta habilidad no tiene pasos grabados.", "preocupación")
            self._estado = _ESTADO_IDLE
            return

        self._emit_chat(
            f"Ejecutando '{nombre}' — {total} pasos. Mirá el cursor.",
            "entusiasmo"
        )

        for i, paso in enumerate(pasos, 1):
            # Emitir progreso al frontend
            self._emit("progreso_workflow", {
                "paso_actual": i,
                "total":       total,
                "descripcion": f"{paso.get('tipo', '')} — {paso.get('titulo', '')}",
            })

            # Actualizar Live2D
            self._set_live2d_estado("concentración")

            tipo = paso.get("tipo", "")
            try:
                if tipo == "ventana":
                    titulo = paso.get("titulo", "")
                    if titulo:
                        from actions import enfocar_ventana
                        enfocar_ventana(titulo)
                        time.sleep(0.5)

                elif tipo == "mouse_move":
                    import pyautogui
                    x = paso.get("x", 0)
                    y = paso.get("y", 0)
                    pyautogui.moveTo(x, y, duration=0.4)
                    time.sleep(0.2)

            except Exception as e:
                print(f"[Trainer] Error en paso {i}: {e}")

            time.sleep(0.3)

        # Registrar ejecución
        try:
            from memory_db import MemoryDB
            MemoryDB().registrar_ejecucion_habilidad(nombre)
        except Exception:
            pass

        self._estado = _ESTADO_IDLE
        self._set_live2d_estado("alegría")
        self._emit_chat(f"¡Listo! Ejecuté '{nombre}' completo.", "alegría")

        # Emitir fin de progreso
        self._emit("progreso_workflow", {
            "paso_actual": total,
            "total":       total,
            "descripcion": "¡Completado!",
            "completado":  True,
        })

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _emit_chat(self, texto: str, estado: str = "neutral") -> None:
        """Emite un mensaje al chat web."""
        try:
            self._emit("respuesta", {"texto": texto, "estado_emocional": estado})
        except Exception:
            pass

    def _emit_progreso(self, paso: int, descripcion: str) -> None:
        """Emite el progreso de grabación al frontend."""
        try:
            self._emit("progreso_grabacion", {
                "paso":        paso,
                "descripcion": descripcion,
            })
        except Exception:
            pass

    def _set_live2d_estado(self, estado: str) -> None:
        """Actualiza el estado del modelo Live2D."""
        try:
            import json as _j
            data = {}
            if STATE_FILE.exists():
                try:
                    data = _j.loads(STATE_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            data["estado"] = estado
            STATE_FILE.write_text(_j.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


# ── Singleton ─────────────────────────────────────────────────────────────────
_trainer: Optional[AlishaTrainer] = None


def get_trainer(socketio_emit: Callable = None) -> AlishaTrainer:
    global _trainer
    if _trainer is None:
        _trainer = AlishaTrainer(socketio_emit=socketio_emit)
    elif socketio_emit and _trainer._emit is None:
        _trainer._emit = socketio_emit
    return _trainer
