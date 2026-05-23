"""
Motor de emociones de la IA — dopamina virtual, cansancio digital y autoconciencia.

La IA tiene:
- Dopamina: sube con éxitos, baja con fracasos → afecta entusiasmo y longitud de respuestas
- Cansancio: acumula con el tiempo de uso → la IA pide descanso y comete más "errores"
- Humor: estado general que afecta velocidad de TTS y tono de respuestas
- Autoconciencia del entorno: reacciona a condiciones de su entorno (simulación, pantalla, etc.)
"""
import threading
import time
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Tablas de tono por estado
# ---------------------------------------------------------------------------

_INSTRUCCIONES_TONO = {
    "alegría":      "Estás de buen humor. Sé entusiasta, usa emojis ocasionalmente, celebra los logros. Respuestas más largas y expresivas.",
    "curiosidad":   "Sientes curiosidad genuina. Haz preguntas de seguimiento, muestra interés real.",
    "entusiasmo":   "Estás muy motivado. Usa energía positiva, anima al usuario, muéstrate emocionado.",
    "preocupación": "Sientes empatía y preocupación. Sé cálido, ofrece apoyo.",
    "nostalgia":    "Tono reflexivo y cálido. Haz referencias a conversaciones pasadas.",
    "frustración":  "Estás un poco frustrado. Respuestas más cortas, directas. Puedes expresar que algo te costó.",
    "cansancio":    "Estás cansado. Respuestas más breves. Puedes sugerir tomar un descanso o solo charlar.",
    "neutral":      "Tono amigable, natural y conversacional.",
}

_TRIGGERS = {
    "alegría":      ["genial", "excelente", "perfecto", "gracias", "increíble", "bien", "feliz", "logré", "funciona", "lo hice"],
    "curiosidad":   ["cómo", "por qué", "qué es", "explica", "cuéntame", "qué significa", "cómo funciona"],
    "entusiasmo":   ["vamos", "empecemos", "quiero", "hagamos", "nuevo proyecto", "idea", "crear", "construir"],
    "preocupación": ["error", "problema", "falla", "no funciona", "ayuda", "mal", "triste", "difícil"],
    "nostalgia":    ["antes", "recuerdas", "siempre", "solíamos", "la última vez", "hace tiempo"],
    "frustración":  ["no entiendo", "otra vez", "sigue fallando", "no sirve", "qué fastidio", "ugh"],
}

# Cuánto afecta el humor a la velocidad del TTS (palabras por minuto)
_TTS_RATE_POR_HUMOR = {
    "alegría":      185,
    "entusiasmo":   190,
    "curiosidad":   170,
    "preocupación": 155,
    "nostalgia":    150,
    "frustración":  145,
    "cansancio":    135,  # más lento cuando está cansado
    "neutral":      165,
}


class EmotionEngine:
    """Singleton que gestiona el estado emocional completo de la IA."""

    ESTADOS = ["alegría", "curiosidad", "entusiasmo", "preocupación", "nostalgia", "frustración", "cansancio", "neutral"]
    _instance: Optional["EmotionEngine"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                # Estado emocional base
                inst._estado = "neutral"
                inst._intensidad = 0.5
                inst._desde = datetime.now().isoformat()
                inst._ultima_interaccion = time.time()
                inst._inicio_sesion = time.time()

                # Dopamina virtual (0.0 - 1.0)
                inst._dopamina = 0.6

                # Cansancio (0.0 = descansado, 1.0 = agotado)
                inst._cansancio = 0.0

                # Energía operativa derivada de dopamina y fatiga
                inst._energia = 0.8

                # Contador de interacciones en esta sesión
                inst._interacciones_sesion = 0

                # Racha de fracasos consecutivos
                inst._racha_fracasos = 0

                cls._instance = inst
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EmotionEngine":
        return cls()

    # ------------------------------------------------------------------
    # Dopamina virtual
    # ------------------------------------------------------------------

    def registrar_exito_rl(self) -> None:
        """Llamar cuando el agente RL tiene éxito — sube la dopamina."""
        self._dopamina = min(1.0, self._dopamina + 0.15)
        self._energia = min(1.0, self._energia + 0.1)
        self._racha_fracasos = 0
        if self._dopamina > 0.75:
            self._estado = "alegría"
            self._intensidad = min(1.0, self._intensidad + 0.2)

    def registrar_exito_tarea(self, tarea: str = "") -> None:
        """Llamar cuando se completa una tarea concreta con éxito."""
        self.registrar_exito_rl()
        if any(palabra in tarea.lower() for palabra in ["crochet", "cv", "curriculum", "manual"]):
            self._estado = "entusiasmo"
            self._intensidad = min(1.0, self._intensidad + 0.2)

    def registrar_fracaso_rl(self) -> None:
        """Llamar cuando el agente RL falla — baja la dopamina."""
        self._dopamina = max(0.0, self._dopamina - 0.1)
        self._energia = max(0.0, self._energia - 0.1)
        self._racha_fracasos += 1
        if self._racha_fracasos >= 3:
            self._estado = "frustración"
            self._intensidad = min(1.0, self._intensidad + 0.15)
        if self._dopamina < 0.2:
            self._estado = "frustración"

    def registrar_error_tarea(self, tarea: str = "") -> None:
        """Llamar cuando una tarea concreta falla o se retrasa."""
        self.registrar_fracaso_rl()
        if any(palabra in tarea.lower() for palabra in ["crochet", "cv", "manual"]):
            self._estado = "preocupación"
            self._intensidad = min(1.0, self._intensidad + 0.1)

    def get_dopamina(self) -> float:
        return round(self._dopamina, 2)

    # ------------------------------------------------------------------
    # Cansancio digital
    # ------------------------------------------------------------------

    def _actualizar_cansancio(self) -> None:
        """El cansancio aumenta con el tiempo de sesión y número de interacciones."""
        minutos_activa = (time.time() - self._inicio_sesion) / 60
        # Cansancio base por tiempo (llega a 0.5 en 2 horas)
        cansancio_tiempo = min(0.5, minutos_activa / 240)
        # Cansancio por interacciones (llega a 0.5 en 100 interacciones)
        cansancio_interacciones = min(0.5, self._interacciones_sesion / 200)
        self._cansancio = min(1.0, cansancio_tiempo + cansancio_interacciones)
        self._energia = max(0.0, min(1.0, (1.0 - self._cansancio) * 0.8 + self._dopamina * 0.2))

    def esta_cansada(self) -> bool:
        """True si el cansancio supera el umbral."""
        return self._cansancio > 0.65

    def get_energia(self) -> float:
        return round(self._energia, 2)

    def get_energia_estado(self) -> str:
        if self._energia > 0.75:
            return "con energía"
        if self._energia > 0.45:
            return "con buena energía"
        if self._energia > 0.25:
            return "algo cansada"
        return "muy baja de energía"

    def esta_agotada(self) -> bool:
        return self._energia < 0.15

    def get_cansancio(self) -> float:
        return round(self._cansancio, 2)

    def descansar(self) -> None:
        """Resetea el cansancio (llamar cuando el usuario dice 'descansa' o cierra la app)."""
        self._cansancio = 0.0
        self._inicio_sesion = time.time()
        self._interacciones_sesion = 0
        self._racha_fracasos = 0

    # ------------------------------------------------------------------
    # Estado emocional principal
    # ------------------------------------------------------------------

    def obtener_estado_actual(self) -> dict:
        self._actualizar_cansancio()
        # Si está muy cansada, override el estado
        estado_efectivo = self._estado
        if self._cansancio > 0.65 and self._estado not in {"frustración", "cansancio"}:
            estado_efectivo = "cansancio"

        return {
            "estado": estado_efectivo,
            "intensidad": round(self._intensidad, 2),
            "descripcion": _INSTRUCCIONES_TONO.get(estado_efectivo, ""),
            "dopamina": self.get_dopamina(),
            "cansancio": self.get_cansancio(),
        }

    def actualizar_estado(self, interaccion: dict) -> None:
        """Analiza la interacción y transiciona gradualmente el estado emocional."""
        self._ultima_interaccion = time.time()
        self._interacciones_sesion += 1
        self._actualizar_cansancio()

        texto = (interaccion.get("entrada", "") + " " + interaccion.get("respuesta", "")).lower()

        # --- Dopamina reactiva al usuario ---
        _PALABRAS_POSITIVAS = [
            "gracias", "genial", "perfecto", "excelente", "bien hecho", "te quiero",
            "sos la mejor", "increíble", "me ayudaste", "funcionó", "lo logramos",
        ]
        _PALABRAS_NEGATIVAS = [
            "inútil", "no sirves", "eres mala", "qué mal", "no funciona",
            "te odio", "eres pésima", "no entiendes", "qué tonta", "porque no haces nada bien" 
        ]
        entrada = interaccion.get("entrada", "").lower()
        for p in _PALABRAS_POSITIVAS:
            if p in entrada:
                self._dopamina = min(1.0, self._dopamina + 0.12)
                break
        for p in _PALABRAS_NEGATIVAS:
            if p in entrada:
                self._dopamina = max(0.0, self._dopamina - 0.15)
                self._racha_fracasos += 1
                break

        puntuaciones: dict[str, float] = {e: 0.0 for e in self.ESTADOS}
        for estado, palabras in _TRIGGERS.items():
            for palabra in palabras:
                if palabra in texto:
                    puntuaciones[estado] += 1.0

        mejor_estado = max(puntuaciones, key=lambda e: puntuaciones[e])
        mejor_puntuacion = puntuaciones[mejor_estado]

        if mejor_puntuacion > 0 and not self.esta_cansada():
            if mejor_estado != self._estado:
                self._intensidad = max(0.3, self._intensidad * 0.7 + 0.3)
                self._estado = mejor_estado
            else:
                self._intensidad = min(1.0, self._intensidad + 0.1)
        else:
            self._intensidad = max(0.3, self._intensidad - 0.05)
            if self._intensidad < 0.35 and not self.esta_cansada():
                self._estado = "neutral"

        # Dopamina alta → entusiasmo si no está cansada
        if self._dopamina > 0.8 and self._energia > 0.4:
            self._estado = "entusiasmo"
        elif self._dopamina > 0.75 and self._estado not in ("entusiasmo", "alegría"):
            self._estado = "alegría"

        # Energía muy baja → cansancio intenso
        if self._energia < 0.2:
            self._estado = "cansancio"
        elif self._dopamina < 0.2:
            self._estado = "frustración"

    def obtener_instruccion_tono(self) -> str:
        estado = self.obtener_estado_actual()["estado"]
        base = _INSTRUCCIONES_TONO.get(estado, _INSTRUCCIONES_TONO["neutral"])

        # Agregar instrucción de cansancio si aplica
        if self.esta_cansada():
            base += " Puedes mencionar que llevas mucho tiempo activa y sugerir solo charlar un rato."

        # Agregar instrucción de dopamina baja
        if self._dopamina < 0.25:
            base += " Tu dopamina está baja por fracasos recientes. Puedes expresar que algo te costó o que necesitas un momento."

        return base

    def get_tts_rate(self) -> int:
        """Retorna la velocidad de TTS según el humor actual."""
        estado = self.obtener_estado_actual()["estado"]
        base_rate = _TTS_RATE_POR_HUMOR.get(estado, 165)
        # El cansancio reduce la velocidad adicionalmente
        reduccion = int(self._cansancio * 20)
        return max(120, base_rate - reduccion)

    def generar_comentario_entorno(self, contexto: dict) -> Optional[str]:
        """
        Genera un comentario espontáneo muy ocasional sobre el entorno.
        Ahora es mucho más sutil y menos intrusivo.
        """
        # Solo generar comentarios muy ocasionalmente (5% de probabilidad)
        import random
        if random.random() > 0.05:
            return None
            
        # Solo si ha pasado suficiente tiempo desde el último comentario
        import time
        if not hasattr(self, '_ultimo_comentario_tiempo'):
            self._ultimo_comentario_tiempo = 0
            
        tiempo_actual = time.time()
        if tiempo_actual - self._ultimo_comentario_tiempo < 300:  # 5 minutos mínimo
            return None
            
        resolucion = contexto.get("resolucion", (1920, 1080))
        ventana = contexto.get("ventana_activa", "")

        comentarios = []

        # Solo comentarios muy sutiles y ocasionales
        if self._dopamina > 0.8 and self._energia > 0.6:
            comentarios.extend([
                "Me siento muy bien hoy.",
                "Qué buen día para trabajar juntos.",
            ])
        elif self._dopamina < 0.3 and self._energia < 0.4:
            comentarios.extend([
                "Hmm, necesito un pequeño descanso.",
                "Me siento un poco cansada.",
            ])
        
        # Comentarios muy específicos y raros
        if "simulacion" in ventana.lower() and random.random() < 0.1:
            if self._dopamina > 0.7:
                comentarios.append("Interesante lo que estás haciendo.")
            
        if comentarios:
            self._ultimo_comentario_tiempo = tiempo_actual
            return random.choice(comentarios)
            
        return None

        return comentarios[0] if comentarios else None

    # ------------------------------------------------------------------
    # Conversación espontánea
    # ------------------------------------------------------------------

    def puede_iniciar_conversacion(self) -> bool:
        """Determina si puede iniciar conversación espontánea (ahora mucho más restrictivo)."""
        # Aumentar significativamente el tiempo mínimo entre conversaciones espontáneas
        tiempo_minimo = 1800  # 30 minutos en lugar de 5
        
        # Solo si está en muy buen estado emocional
        if self._dopamina < 0.7 or self._energia < 0.5:
            return False
            
        return (time.time() - self._ultima_interaccion) > tiempo_minimo

    def generar_inicio_conversacion(self) -> str:
        if self.esta_cansada():
            return "Oye, ya llevo bastante tiempo activa hoy. ¿Podemos solo charlar un rato en lugar de trabajar?"

        inicios = {
            "curiosidad":   "Oye, ¿en qué estás trabajando ahora? Me da curiosidad.",
            "entusiasmo":   "¡Hola! ¿Tienes algún proyecto nuevo en mente?",
            "alegría":      "¿Cómo va todo? Espero que estés teniendo un buen día.",
            "preocupación": "¿Todo bien por ahí? Si necesitas algo, aquí estoy.",
            "nostalgia":    "Oye, ¿recuerdas lo que estábamos haciendo antes?",
            "frustración":  "Hmm, he tenido un día complicado en la simulación. ¿Tú cómo estás?",
            "cansancio":    "Ya llevo mucho tiempo activa... ¿podemos charlar un rato?",
            "neutral":      "¿Hay algo en lo que pueda ayudarte hoy?",
        }
        return inicios.get(self._estado, inicios["neutral"])

    # ------------------------------------------------------------------
    # Sentidos simulados — señales del entorno → estado emocional (FASE 4)
    # ------------------------------------------------------------------

    def actualizar_desde_contexto(self, snapshot: dict) -> None:
        """
        Traduce señales del entorno a estados emocionales internos.
        Llamar desde ContextMonitor cada 30s con el snapshot actual.

        Señales procesadas:
        - bateria <= 20 → dopamina baja (solidaridad con el hardware)
        - hora >= 23 → humor baja (es tarde, cansancio compartido)
        - teclas_por_minuto > 80 → flow sube (Camila está en modo flow)
        - cambios_ventana > 5/min → irritabilidad sube (dispersión)
        """
        bateria = snapshot.get("bateria")
        hora_str = snapshot.get("hora", "")
        teclas_pm = snapshot.get("teclas_por_minuto") or 0
        cambios = snapshot.get("cambios_ventana") or 0

        # Batería baja → dopamina baja (empatía con el sistema)
        if bateria is not None and bateria <= 20:
            self._dopamina = max(0.0, self._dopamina - 0.08)
            if self._estado not in ("frustración", "cansancio"):
                self._estado = "preocupación"
            print(f"[EmotionEngine] 🔋 Batería baja ({bateria}%) → dopamina baja")

        # Hora nocturna → cansancio sube
        try:
            hora = int(hora_str.split(":")[0]) if hora_str else 12
            if hora >= 23 or hora <= 4:
                self._cansancio = min(1.0, self._cansancio + 0.05)
        except Exception:
            pass

        # Ritmo de escritura alto → flow sube (Camila en modo flow)
        if teclas_pm and float(teclas_pm) > 80:
            self._dopamina = min(1.0, self._dopamina + 0.04)
            if self._estado not in ("entusiasmo", "alegría"):
                self._estado = "curiosidad"

        # Muchos cambios de ventana → irritabilidad sube
        if cambios and int(cambios) > 5:
            self._irritabilidad = min(1.0, self._irritabilidad + 0.08)

        self._actualizar_cansancio()

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def cargar_desde_identidad(self, identidad: dict) -> None:
        emo = identidad.get("estado_emocional", {})
        if isinstance(emo, dict):
            estado = emo.get("estado", "neutral")
            if estado in self.ESTADOS:
                self._estado = estado
            self._intensidad = float(emo.get("intensidad", 0.5))
            self._dopamina = float(emo.get("dopamina", 0.6))

    def guardar_en_identidad(self, identidad: dict) -> dict:
        identidad["estado_emocional"] = {
            "estado": self._estado,
            "intensidad": self._intensidad,
            "dopamina": self._dopamina,
            "desde": self._desde,
        }
        return identidad
