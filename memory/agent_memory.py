"""
agent_memory.py — Sistema de memoria episódica para la IA.

Guarda recuerdos de conversaciones pasadas con contexto emocional,
temas recurrentes y preferencias del usuario. Se integra con el prompt
para personalizar las respuestas.
"""
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
import math

from config.settings import DATA_DIR
MEMORY_FILE = DATA_DIR / "ia_recuerdos.json"
MAX_RECUERDOS = 200


class AgentMemory:
    """Memoria episódica — recuerdos con contexto emocional y temas."""

    def __init__(self):
        self._recuerdos: list[dict] = []
        self._temas_frecuentes: Counter = Counter()
        self._response_fingerprints: list[dict] = []  # Store response fingerprints for similarity checking
        self._brainstorming_phrases: list[dict] = []  # Store brainstorming phrases with usage tracking
        self._phrase_usage_patterns: dict = {}  # Track phrase usage patterns and timestamps
        self._cargar()

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def _cargar(self) -> None:
        if MEMORY_FILE.exists():
            try:
                data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
                self._recuerdos = data.get("recuerdos", [])
                self._temas_frecuentes = Counter(data.get("temas", {}))
                self._response_fingerprints = data.get("response_fingerprints", [])
                self._brainstorming_phrases = data.get("brainstorming_phrases", [])
                self._phrase_usage_patterns = data.get("phrase_usage_patterns", {})
                
                # Initialize default brainstorming phrases if none exist
                if not self._brainstorming_phrases:
                    self._initialize_default_brainstorming_phrases()
            except Exception:
                # Initialize default phrases on error
                self._initialize_default_brainstorming_phrases()

    def _guardar(self) -> None:
        try:
            MEMORY_FILE.write_text(
                json.dumps({
                    "recuerdos": self._recuerdos[-MAX_RECUERDOS:],
                    "temas": dict(self._temas_frecuentes.most_common(50)),
                    "response_fingerprints": self._response_fingerprints[-50:],  # Keep last 50 fingerprints
                    "brainstorming_phrases": self._brainstorming_phrases[-100:],  # Keep last 100 phrases
                    "phrase_usage_patterns": self._phrase_usage_patterns,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Agregar recuerdo
    # ------------------------------------------------------------------

    def agregar(self, entrada: str, respuesta: str, emocion: str,
                ventana_activa: str = "") -> None:
        """Guarda un intercambio como recuerdo."""
        recuerdo = {
            "fecha": datetime.now().isoformat(),
            "entrada": entrada[:200],
            "respuesta": respuesta[:300],
            "emocion": emocion,
            "ventana": ventana_activa,
            "temas": self._extraer_temas(entrada),
        }
        self._recuerdos.append(recuerdo)
        for tema in recuerdo["temas"]:
            self._temas_frecuentes[tema] += 1
        
        # Store response fingerprint for similarity checking
        self._store_response_fingerprint(respuesta)
        
        # Track brainstorming phrase usage if this is a brainstorming response
        self._track_brainstorming_usage(entrada, respuesta)
        
        self._guardar()

    def _store_response_fingerprint(self, respuesta: str) -> None:
        """Store a fingerprint of the response for similarity comparison."""
        fingerprint = {
            "fecha": datetime.now().isoformat(),
            "respuesta": respuesta[:300],
            "words": self._extract_words(respuesta),
            "length": len(respuesta)
        }
        self._response_fingerprints.append(fingerprint)
        
        # Keep only recent fingerprints to avoid memory bloat
        if len(self._response_fingerprints) > 50:
            self._response_fingerprints = self._response_fingerprints[-50:]

    def _extraer_temas(self, texto: str) -> list[str]:
        """Extrae temas clave del texto."""
        _TEMAS = {
            "código": ["código", "python", "función", "bug", "error", "programar", "script"],
            "trabajo": ["cv", "curriculum", "trabajo", "empleo", "entrevista"],
            "video": ["video", "clip", "editar", "moviepy", "grabación"],
            "traducción": ["traducción", "traducir", "idioma", "inglés", "español"],
            "música": ["música", "canción", "reproducir", "spotify"],
            "estudio": ["estudiar", "aprender", "tarea", "examen", "clase"],
            "personal": ["me siento", "estoy", "hoy", "ayer", "mañana"],
        }
        texto_lower = texto.lower()
        encontrados = []
        for tema, palabras in _TEMAS.items():
            if any(p in texto_lower for p in palabras):
                encontrados.append(tema)
        return encontrados

    # ------------------------------------------------------------------
    # Response Similarity Detection
    # ------------------------------------------------------------------

    def _extract_words(self, texto: str) -> List[str]:
        """Extract normalized words from text for similarity comparison."""
        # Remove punctuation and convert to lowercase
        texto_clean = re.sub(r'[^\w\s]', ' ', texto.lower())
        # Split into words and filter out short words
        words = [word.strip() for word in texto_clean.split() if len(word.strip()) > 2]
        return words

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using cosine similarity.
        Returns a value between 0.0 (completely different) and 1.0 (identical).
        """
        if not text1 or not text2:
            return 0.0
        
        words1 = self._extract_words(text1)
        words2 = self._extract_words(text2)
        
        if not words1 or not words2:
            return 0.0
        
        # Create word frequency vectors
        all_words = set(words1 + words2)
        vector1 = [words1.count(word) for word in all_words]
        vector2 = [words2.count(word) for word in all_words]
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = math.sqrt(sum(a * a for a in vector1))
        magnitude2 = math.sqrt(sum(b * b for b in vector2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)

    def calculate_levenshtein_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity using normalized Levenshtein distance.
        Returns a value between 0.0 (completely different) and 1.0 (identical).
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        text1_clean = ' '.join(self._extract_words(text1))
        text2_clean = ' '.join(self._extract_words(text2))
        
        if not text1_clean or not text2_clean:
            return 0.0
        
        # Calculate Levenshtein distance
        distance = self._levenshtein_distance(text1_clean, text2_clean)
        max_length = max(len(text1_clean), len(text2_clean))
        
        if max_length == 0:
            return 1.0
        
        # Convert distance to similarity (1.0 - normalized_distance)
        return 1.0 - (distance / max_length)

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate the Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    def check_response_similarity_threshold(self, new_response: str, threshold: float = 0.8) -> Tuple[bool, float, str]:
        """
        Check if a new response exceeds the similarity threshold with previous responses.
        
        Args:
            new_response: The response to check
            threshold: Similarity threshold (default 0.8 = 80%)
        
        Returns:
            Tuple of (exceeds_threshold, max_similarity, most_similar_response)
        """
        if not self._response_fingerprints:
            return False, 0.0, ""
        
        max_similarity = 0.0
        most_similar_response = ""
        
        # Check against recent responses (last 10 to avoid performance issues)
        recent_fingerprints = self._response_fingerprints[-10:]
        
        for fingerprint in recent_fingerprints:
            previous_response = fingerprint["respuesta"]
            
            # Use cosine similarity as primary method
            similarity = self.calculate_text_similarity(new_response, previous_response)
            
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_response = previous_response
        
        exceeds_threshold = max_similarity >= threshold
        return exceeds_threshold, max_similarity, most_similar_response

    def is_response_too_similar(self, new_response: str) -> bool:
        """
        Simple boolean check if response is too similar to previous responses.
        Uses 80% threshold as specified in requirements.
        """
        exceeds_threshold, _, _ = self.check_response_similarity_threshold(new_response, 0.8)
        return exceeds_threshold

    def get_similarity_report(self, new_response: str) -> dict:
        """
        Get detailed similarity analysis for a new response.
        Useful for debugging and monitoring.
        """
        exceeds_threshold, max_similarity, most_similar = self.check_response_similarity_threshold(new_response)
        
        return {
            "exceeds_threshold": exceeds_threshold,
            "max_similarity": max_similarity,
            "threshold": 0.8,
            "most_similar_response": most_similar,
            "total_fingerprints": len(self._response_fingerprints),
            "new_response_length": len(new_response)
        }

    # ------------------------------------------------------------------
    # Brainstorming Database Refresh System
    # ------------------------------------------------------------------

    def _initialize_default_brainstorming_phrases(self) -> None:
        """Initialize default brainstorming phrases with timestamps."""
        default_phrases = [
            "Let me think creatively about this",
            "Here are some innovative ideas",
            "Let's explore different possibilities", 
            "I can suggest several approaches",
            "Let's brainstorm some solutions",
            "What if we consider this angle",
            "Another perspective might be",
            "We could also try this approach",
            "Have you thought about this option",
            "This opens up interesting possibilities",
            "Let me offer some fresh ideas",
            "Here's a different way to look at it",
            "We might want to explore this direction",
            "This could lead to creative solutions",
            "Let's think outside the box here"
        ]
        
        current_time = datetime.now().isoformat()
        self._brainstorming_phrases = []
        
        for phrase in default_phrases:
            self._brainstorming_phrases.append({
                "phrase": phrase,
                "created": current_time,
                "last_used": None,
                "usage_count": 0,
                "diversity_score": 1.0,
                "category": "general"
            })

    def _track_brainstorming_usage(self, entrada: str, respuesta: str) -> None:
        """Track usage of brainstorming phrases in responses."""
        # Check if this is a brainstorming request
        brainstorm_keywords = ["brainstorm", "ideas", "creative", "think", "suggest", "possibilities", "solutions"]
        is_brainstorming = any(keyword in entrada.lower() for keyword in brainstorm_keywords)
        
        if not is_brainstorming:
            return
        
        current_time = datetime.now().isoformat()
        
        # Check which phrases were used in the response
        for phrase_data in self._brainstorming_phrases:
            phrase = phrase_data["phrase"]
            if phrase.lower() in respuesta.lower():
                # Update usage tracking
                phrase_data["last_used"] = current_time
                phrase_data["usage_count"] += 1
                
                # Decrease diversity score with each use
                phrase_data["diversity_score"] = max(0.1, phrase_data["diversity_score"] * 0.8)
                
                # Track usage pattern
                phrase_key = phrase.lower().replace(" ", "_")
                if phrase_key not in self._phrase_usage_patterns:
                    self._phrase_usage_patterns[phrase_key] = []
                
                self._phrase_usage_patterns[phrase_key].append({
                    "timestamp": current_time,
                    "context": entrada[:100],  # Store context for analysis
                })

    def calculate_phrase_diversity_score(self, phrase: str) -> float:
        """
        Calculate diversity score for a brainstorming phrase.
        Returns value between 0.0 (overused) and 1.0 (fresh).
        """
        phrase_key = phrase.lower().replace(" ", "_")
        
        if phrase_key not in self._phrase_usage_patterns:
            return 1.0  # Fresh phrase
        
        usage_history = self._phrase_usage_patterns[phrase_key]
        
        if not usage_history:
            return 1.0
        
        # Calculate recency penalty
        now = datetime.now()
        recent_usage_count = 0
        
        for usage in usage_history[-10:]:  # Check last 10 uses
            try:
                usage_time = datetime.fromisoformat(usage["timestamp"])
                time_diff = now - usage_time
                
                # Heavy penalty for recent usage (last 24 hours)
                if time_diff < timedelta(hours=24):
                    recent_usage_count += 3
                # Medium penalty for usage in last week
                elif time_diff < timedelta(days=7):
                    recent_usage_count += 1
            except:
                continue
        
        # Calculate diversity score based on usage frequency
        total_usage = len(usage_history)
        frequency_penalty = min(1.0, total_usage / 10.0)  # Penalty increases with total usage
        recency_penalty = min(1.0, recent_usage_count / 5.0)  # Penalty for recent usage
        
        diversity_score = 1.0 - max(frequency_penalty, recency_penalty)
        return max(0.1, diversity_score)  # Minimum score of 0.1

    def get_fresh_brainstorming_phrases(self, count: int = 5, min_diversity: float = 0.5) -> List[str]:
        """
        Get fresh brainstorming phrases with high diversity scores.
        
        Args:
            count: Number of phrases to return
            min_diversity: Minimum diversity score threshold
        
        Returns:
            List of fresh brainstorming phrases
        """
        # Update diversity scores for all phrases
        for phrase_data in self._brainstorming_phrases:
            phrase_data["diversity_score"] = self.calculate_phrase_diversity_score(phrase_data["phrase"])
        
        # Filter phrases by minimum diversity score
        fresh_phrases = [
            phrase_data for phrase_data in self._brainstorming_phrases
            if phrase_data["diversity_score"] >= min_diversity
        ]
        
        # Sort by diversity score (highest first)
        fresh_phrases.sort(key=lambda x: x["diversity_score"], reverse=True)
        
        # Return top phrases
        return [phrase_data["phrase"] for phrase_data in fresh_phrases[:count]]

    def refresh_brainstorming_database(self, force_refresh: bool = False) -> dict:
        """
        Refresh the brainstorming database by rotating out overused phrases.
        
        Args:
            force_refresh: Force refresh even if not needed
        
        Returns:
            Dictionary with refresh statistics
        """
        # Check if refresh is needed
        overused_phrases = [
            phrase_data for phrase_data in self._brainstorming_phrases
            if phrase_data["diversity_score"] < 0.3
        ]
        
        if not force_refresh and len(overused_phrases) < 5:
            return {
                "refresh_needed": False,
                "overused_count": len(overused_phrases),
                "total_phrases": len(self._brainstorming_phrases)
            }
        
        # Generate new phrases to replace overused ones
        new_phrase_templates = [
            "What about exploring this concept",
            "Consider this alternative approach",
            "This might spark some new thinking",
            "Let's dive deeper into this idea",
            "Here's a fresh perspective on this",
            "This could unlock new opportunities",
            "Let me share a different viewpoint",
            "We might discover something here",
            "This path could be worth investigating",
            "Let's examine this from another angle",
            "This presents interesting challenges",
            "We could build on this foundation",
            "This opens doors to new solutions",
            "Let's connect these concepts creatively",
            "This might lead to breakthrough thinking"
        ]
        
        current_time = datetime.now().isoformat()
        phrases_refreshed = 0
        
        # Replace overused phrases with new ones
        for i, phrase_data in enumerate(self._brainstorming_phrases):
            if phrase_data["diversity_score"] < 0.3 and phrases_refreshed < len(new_phrase_templates):
                # Replace with new phrase
                new_phrase = new_phrase_templates[phrases_refreshed % len(new_phrase_templates)]
                
                # Update phrase data
                phrase_data["phrase"] = new_phrase
                phrase_data["created"] = current_time
                phrase_data["last_used"] = None
                phrase_data["usage_count"] = 0
                phrase_data["diversity_score"] = 1.0
                
                phrases_refreshed += 1
        
        # Clean up old usage patterns (keep only recent data)
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for phrase_key in list(self._phrase_usage_patterns.keys()):
            usage_history = self._phrase_usage_patterns[phrase_key]
            recent_usage = []
            
            for usage in usage_history:
                try:
                    usage_time = datetime.fromisoformat(usage["timestamp"])
                    if usage_time > cutoff_date:
                        recent_usage.append(usage)
                except:
                    continue
            
            if recent_usage:
                self._phrase_usage_patterns[phrase_key] = recent_usage
            else:
                del self._phrase_usage_patterns[phrase_key]
        
        # Save changes
        self._guardar()
        
        return {
            "refresh_needed": True,
            "phrases_refreshed": phrases_refreshed,
            "overused_count": len(overused_phrases),
            "total_phrases": len(self._brainstorming_phrases),
            "patterns_cleaned": len([k for k in self._phrase_usage_patterns.keys()])
        }

    def detect_brainstorming_repetition(self, new_response: str) -> Tuple[bool, List[str]]:
        """
        Detect if a new response uses repeated brainstorming phrases.
        
        Args:
            new_response: The response to check for repetition
        
        Returns:
            Tuple of (has_repetition, list_of_repeated_phrases)
        """
        repeated_phrases = []
        
        for phrase_data in self._brainstorming_phrases:
            phrase = phrase_data["phrase"]
            
            # Check if phrase is used in response
            if phrase.lower() in new_response.lower():
                # Check if phrase has low diversity (overused)
                diversity_score = self.calculate_phrase_diversity_score(phrase)
                
                if diversity_score < 0.5:  # Threshold for repetition detection
                    repeated_phrases.append(phrase)
        
        has_repetition = len(repeated_phrases) > 0
        return has_repetition, repeated_phrases

    def get_brainstorming_usage_report(self) -> dict:
        """
        Get detailed report on brainstorming phrase usage patterns.
        Useful for debugging and monitoring.
        """
        # Update all diversity scores
        for phrase_data in self._brainstorming_phrases:
            phrase_data["diversity_score"] = self.calculate_phrase_diversity_score(phrase_data["phrase"])
        
        # Sort by usage count
        sorted_phrases = sorted(self._brainstorming_phrases, key=lambda x: x["usage_count"], reverse=True)
        
        # Calculate statistics
        total_phrases = len(self._brainstorming_phrases)
        overused_phrases = [p for p in self._brainstorming_phrases if p["diversity_score"] < 0.3]
        fresh_phrases = [p for p in self._brainstorming_phrases if p["diversity_score"] > 0.7]
        
        return {
            "total_phrases": total_phrases,
            "overused_count": len(overused_phrases),
            "fresh_count": len(fresh_phrases),
            "most_used_phrases": [
                {
                    "phrase": p["phrase"],
                    "usage_count": p["usage_count"],
                    "diversity_score": p["diversity_score"],
                    "last_used": p["last_used"]
                }
                for p in sorted_phrases[:5]
            ],
            "freshest_phrases": [
                {
                    "phrase": p["phrase"],
                    "diversity_score": p["diversity_score"]
                }
                for p in sorted(self._brainstorming_phrases, key=lambda x: x["diversity_score"], reverse=True)[:5]
            ],
            "needs_refresh": len(overused_phrases) >= 5
        }

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def recuerdos_recientes(self, n: int = 5) -> list[dict]:
        return self._recuerdos[-n:]

    def temas_favoritos(self, n: int = 3) -> list[str]:
        return [t for t, _ in self._temas_frecuentes.most_common(n)]

    def buscar_por_tema(self, tema: str, n: int = 3) -> list[dict]:
        return [r for r in reversed(self._recuerdos)
                if tema in r.get("temas", [])][:n]

    def resumen_para_prompt(self) -> str:
        """Genera un resumen conciso para incluir en el prompt."""
        if not self._recuerdos:
            return "No tengo recuerdos previos aún."

        temas = self.temas_favoritos(3)
        recientes = self.recuerdos_recientes(3)
        emocional = self.contexto_emocional()

        lineas = []
        if temas:
            lineas.append(f"Temas que más hablamos: {', '.join(temas)}.")

        for r in recientes:
            fecha = r.get("fecha", "")[:10]
            entrada = r.get("entrada", "")[:60]
            emocion = r.get("emocion", "neutral")
            lineas.append(f"[{fecha}] Me dijiste: '{entrada}...' (yo estaba {emocion})")

        if emocional:
            lineas.append(emocional)

        return "\n".join(lineas)

    def contexto_emocional(self) -> str:
        """Genera una frase de recuerdo afectivo para la prompt y el comportamiento."""
        if not self._recuerdos:
            return "No tengo recuerdos afectivos aún."

        recientes = list(reversed(self._recuerdos[-5:]))
        for recuerdo in recientes:
            emocion = recuerdo.get("emocion", "neutral")
            entrada = recuerdo.get("entrada", "")
            if emocion in {"cansancio", "frustración", "preocupación"}:
                return (
                    f"Recuerdo que ayer trabajamos con {entrada[:80]} y yo estaba {emocion}. "
                    "Hoy puedo ser más cuidadosa y sugerir tomarlo con calma si te veo cansada."
                )

        if recientes:
            primera = recientes[0]
            temas = primera.get("temas", [])
            if temas:
                return f"También recuerdo nuestros temas recientes como {', '.join(temas)} y cómo nos impactaron emocionalmente."

        return "Tengo recuerdos de nuestros proyectos y de cómo nos sentimos mientras los hacíamos."

    def ultimo_tema_activo(self) -> Optional[str]:
        if not self._recuerdos:
            return None
        temas = self._recuerdos[-1].get("temas", [])
        return temas[0] if temas else None


# Singleton
_memoria = AgentMemory()

def get_memory() -> AgentMemory:
    return _memoria

