"""
alisha_memoria_semantica.py — Memoria semántica de Alisha.

Permite buscar recuerdos por significado, no solo por palabras exactas.
Usa TF-IDF simple (sin dependencias extra) como motor de búsqueda.

Ejemplo:
  "aquella vez que hablamos de tu CV" → encuentra la conversación sobre el CV
  "cuando me ayudaste con el diseño" → encuentra conversaciones de diseño
"""
from __future__ import annotations

import json
import math
import re
import threading
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from config.settings import DATA_DIR
INDICE_FILE   = DATA_DIR / "alisha_indice_semantico.json"
MEMORIA_FILE  = DATA_DIR / "ia_recuerdos.json"


# ── Preprocesamiento de texto ─────────────────────────────────────────────────

_STOPWORDS_ES = {
    "de", "la", "el", "en", "y", "a", "que", "es", "se", "no", "te",
    "lo", "le", "da", "su", "por", "con", "una", "un", "para", "al",
    "del", "los", "las", "me", "mi", "tu", "si", "ya", "hay", "fue",
    "ser", "son", "está", "como", "más", "pero", "o", "e", "ni",
    "muy", "bien", "también", "cuando", "qué", "cómo", "dónde",
}

def _tokenizar(texto: str) -> list[str]:
    """Tokeniza y limpia el texto."""
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', ' ', texto)
    tokens = texto.split()
    return [t for t in tokens if t not in _STOPWORDS_ES and len(t) > 2]


# ── Índice TF-IDF ─────────────────────────────────────────────────────────────

class IndiceSemantico:
    """
    Índice TF-IDF simple para búsqueda semántica de recuerdos.
    Se construye sobre ia_recuerdos.json y se persiste en alisha_indice_semantico.json.
    """

    def __init__(self):
        self._documentos: list[dict] = []   # [{id, texto, metadata}]
        self._idf: dict[str, float] = {}
        self._tf: list[dict[str, float]] = []
        self._lock = threading.Lock()
        self._cargar_o_construir()

    def _cargar_o_construir(self):
        """Carga el índice si existe, o lo construye desde ia_recuerdos.json."""
        if INDICE_FILE.exists():
            try:
                data = json.loads(INDICE_FILE.read_text(encoding="utf-8"))
                self._documentos = data.get("documentos", [])
                self._idf        = data.get("idf", {})
                self._tf         = data.get("tf", [])
                return
            except Exception:
                pass
        self._construir()

    def _construir(self):
        """Construye el índice desde ia_recuerdos.json."""
        try:
            if not MEMORIA_FILE.exists():
                return
            data = json.loads(MEMORIA_FILE.read_text(encoding="utf-8"))
            recuerdos = data.get("recuerdos", [])

            self._documentos = []
            for i, r in enumerate(recuerdos):
                texto = f"{r.get('entrada','')} {r.get('respuesta','')}"
                self._documentos.append({
                    "id":       i,
                    "texto":    texto[:500],
                    "entrada":  r.get("entrada", "")[:200],
                    "respuesta":r.get("respuesta", "")[:200],
                    "emocion":  r.get("emocion", "neutral"),
                    "fecha":    r.get("fecha", ""),
                })

            self._calcular_tfidf()
            self._guardar()
        except Exception:
            pass

    def _calcular_tfidf(self):
        """Calcula TF-IDF para todos los documentos."""
        N = len(self._documentos)
        if N == 0:
            return

        # TF por documento
        self._tf = []
        df: dict[str, int] = defaultdict(int)

        for doc in self._documentos:
            tokens = _tokenizar(doc["texto"])
            tf_doc = Counter(tokens)
            total  = max(len(tokens), 1)
            tf_norm = {t: c / total for t, c in tf_doc.items()}
            self._tf.append(tf_norm)
            for t in tf_doc:
                df[t] += 1

        # IDF
        self._idf = {
            t: math.log(N / (1 + df[t]))
            for t in df
        }

    def _guardar(self):
        try:
            INDICE_FILE.write_text(json.dumps({
                "documentos": self._documentos,
                "idf":        self._idf,
                "tf":         self._tf,
            }, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def buscar(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Busca los recuerdos más relevantes para la query.
        Retorna lista de {entrada, respuesta, emocion, score}.
        """
        with self._lock:
            if not self._documentos:
                return []

            tokens_q = _tokenizar(query)
            if not tokens_q:
                return []

            # TF-IDF del query
            tf_q = Counter(tokens_q)
            total_q = max(len(tokens_q), 1)

            # Calcular similitud coseno con cada documento
            scores = []
            for i, tf_doc in enumerate(self._tf):
                score = 0.0
                for t, tf_val in tf_q.items():
                    if t in tf_doc and t in self._idf:
                        tfidf_q   = (tf_val / total_q) * self._idf[t]
                        tfidf_doc = tf_doc[t] * self._idf[t]
                        score    += tfidf_q * tfidf_doc
                scores.append((i, score))

            # Ordenar por score
            scores.sort(key=lambda x: x[1], reverse=True)
            resultados = []
            for i, score in scores[:top_k]:
                if score > 0:
                    doc = self._documentos[i]
                    resultados.append({
                        "entrada":  doc["entrada"],
                        "respuesta":doc["respuesta"],
                        "emocion":  doc["emocion"],
                        "fecha":    doc["fecha"],
                        "score":    round(score, 4),
                    })
            return resultados

    def agregar_recuerdo(self, entrada: str, respuesta: str,
                         emocion: str = "neutral"):
        """Agrega un nuevo recuerdo al índice en tiempo real."""
        with self._lock:
            i = len(self._documentos)
            texto = f"{entrada} {respuesta}"
            self._documentos.append({
                "id":       i,
                "texto":    texto[:500],
                "entrada":  entrada[:200],
                "respuesta":respuesta[:200],
                "emocion":  emocion,
                "fecha":    "",
            })
            # Recalcular TF-IDF (solo si hay pocos documentos, sino es costoso)
            if len(self._documentos) % 10 == 0:
                self._calcular_tfidf()
                self._guardar()
            else:
                # Agregar TF del nuevo documento
                tokens = _tokenizar(texto)
                tf_doc = Counter(tokens)
                total  = max(len(tokens), 1)
                self._tf.append({t: c / total for t, c in tf_doc.items()})

    def reconstruir(self):
        """Reconstruye el índice desde cero (llamar cuando cambia ia_recuerdos.json)."""
        with self._lock:
            self._construir()

    def resumen_para_prompt(self, query: str, max_chars: int = 400) -> str:
        """
        Genera un resumen de recuerdos relevantes para incluir en el prompt.
        """
        resultados = self.buscar(query, top_k=3)
        if not resultados:
            return ""

        partes = ["Recuerdos relevantes:"]
        chars = 0
        for r in resultados:
            linea = f"- Dijiste: '{r['entrada'][:80]}' → Respondí: '{r['respuesta'][:80]}'"
            if chars + len(linea) > max_chars:
                break
            partes.append(linea)
            chars += len(linea)

        return "\n".join(partes)


# ── Singleton ─────────────────────────────────────────────────────────────────
_indice: Optional[IndiceSemantico] = None

def get_indice() -> IndiceSemantico:
    global _indice
    if _indice is None:
        _indice = IndiceSemantico()
    return _indice

def buscar_recuerdos(query: str, top_k: int = 3) -> list[dict]:
    """API pública para buscar recuerdos."""
    return get_indice().buscar(query, top_k)

def agregar_a_indice(entrada: str, respuesta: str, emocion: str = "neutral"):
    """Agrega un recuerdo al índice semántico."""
    get_indice().agregar_recuerdo(entrada, respuesta, emocion)

