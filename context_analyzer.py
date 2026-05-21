"""
context_analyzer.py — Analizador inteligente de contexto de actividad del usuario.

Convierte información literal de ventanas/procesos en descripciones naturales y contextuales.
"""
import re
from typing import Dict, Optional

class ContextAnalyzer:
    """Analiza el contexto de la actividad del usuario y genera descripciones inteligentes."""
    
    def __init__(self):
        # Patrones para detectar tipos de actividad
        self.activity_patterns = {
            # Diseño y creatividad
            'design': {
                'sites': ['canva', 'figma', 'adobe', 'photoshop', 'illustrator', 'sketch'],
                'processes': ['photoshop', 'illustrator', 'figma', 'canva'],
                'descriptions': [
                    "trabajando en un diseño creativo",
                    "creando contenido visual", 
                    "diseñando algo interesante",
                    "explorando ideas visuales",
                    "dando forma a una idea creativa"
                ]
            },
            
            # Programación y desarrollo
            'coding': {
                'sites': ['github', 'stackoverflow', 'codepen', 'replit', 'codesandbox'],
                'processes': ['code', 'vscode', 'visual studio', 'atom', 'sublime'],
                'descriptions': [
                    "programando y resolviendo problemas",
                    "construyendo algo con código",
                    "explorando soluciones técnicas",
                    "desarrollando un proyecto",
                    "investigando sobre programación"
                ]
            },
            
            # Aprendizaje y investigación
            'learning': {
                'sites': ['youtube', 'coursera', 'udemy', 'khan', 'wikipedia', 'tutorial'],
                'processes': [],
                'descriptions': [
                    "aprendiendo algo nuevo",
                    "investigando un tema interesante",
                    "expandiendo conocimientos",
                    "estudiando y descubriendo",
                    "explorando nuevas ideas"
                ]
            },
            
            # Entretenimiento
            'entertainment': {
                'sites': ['netflix', 'youtube', 'twitch', 'spotify', 'video', 'music'],
                'processes': ['vlc', 'spotify', 'netflix'],
                'descriptions': [
                    "disfrutando de contenido multimedia",
                    "relajándose con entretenimiento",
                    "tomando un descanso creativo",
                    "disfrutando de un momento de ocio",
                    "explorando contenido interesante"
                ]
            },
            
            # Trabajo y productividad
            'work': {
                'sites': ['docs.google', 'office', 'notion', 'trello', 'slack'],
                'processes': ['word', 'excel', 'powerpoint', 'outlook', 'teams'],
                'descriptions': [
                    "trabajando en documentos importantes",
                    "organizando tareas y proyectos",
                    "siendo productivo con el trabajo",
                    "gestionando información",
                    "avanzando en proyectos"
                ]
            },
            
            # Comunicación y social
            'social': {
                'sites': ['whatsapp', 'telegram', 'discord', 'facebook', 'twitter', 'instagram'],
                'processes': ['discord', 'whatsapp', 'telegram'],
                'descriptions': [
                    "conectando con otras personas",
                    "manteniendo conversaciones",
                    "compartiendo momentos sociales",
                    "interactuando con la comunidad",
                    "cultivando relaciones"
                ]
            },
            
            # Compras y navegación
            'browsing': {
                'sites': ['amazon', 'mercadolibre', 'shopping', 'store', 'buy'],
                'processes': [],
                'descriptions': [
                    "explorando opciones de compra",
                    "investigando productos",
                    "navegando por la web",
                    "buscando algo específico",
                    "explorando el mundo digital"
                ]
            }
        }
    
    def analyze_activity(self, window_title: str, process_name: str) -> Optional[str]:
        """
        Analiza la actividad actual y retorna una descripción natural.
        
        Args:
            window_title: Título de la ventana activa
            process_name: Nombre del proceso activo
            
        Returns:
            Descripción natural de la actividad o None si no se puede determinar
        """
        if not window_title and not process_name:
            return None
            
        # Normalizar texto para análisis
        title_lower = window_title.lower() if window_title else ""
        process_lower = process_name.lower() if process_name else ""
        
        # Buscar patrones en cada categoría
        for activity_type, patterns in self.activity_patterns.items():
            # Verificar sitios web en el título
            for site in patterns['sites']:
                if site in title_lower:
                    return self._get_random_description(patterns['descriptions'])
            
            # Verificar procesos
            for proc in patterns['processes']:
                if proc in process_lower:
                    return self._get_random_description(patterns['descriptions'])
        
        # Si no se encuentra patrón específico, generar descripción genérica
        return self._generate_generic_description(title_lower, process_lower)
    
    def _get_random_description(self, descriptions: list) -> str:
        """Selecciona una descripción aleatoria de la lista."""
        import random
        return random.choice(descriptions)
    
    def _generate_generic_description(self, title: str, process: str) -> Optional[str]:
        """Genera una descripción genérica basada en el contexto."""
        generic_descriptions = [
            "concentrado en una tarea",
            "trabajando en algo interesante", 
            "explorando contenido digital",
            "navegando por información",
            "enfocado en una actividad"
        ]
        
        # Detectar navegadores
        browsers = ['chrome', 'firefox', 'edge', 'opera', 'safari', 'brave']
        if any(browser in process for browser in browsers):
            web_descriptions = [
                "navegando por la web",
                "explorando contenido online",
                "investigando en internet",
                "buscando información",
                "descubriendo cosas nuevas"
            ]
            return self._get_random_description(web_descriptions)
        
        # Detectar editores de texto
        editors = ['notepad', 'word', 'writer', 'text']
        if any(editor in process for editor in editors):
            writing_descriptions = [
                "escribiendo y organizando ideas",
                "trabajando con texto",
                "creando contenido escrito",
                "documentando pensamientos"
            ]
            return self._get_random_description(writing_descriptions)
        
        return self._get_random_description(generic_descriptions)
    
    def should_comment(self, last_activity: str, current_activity: str, time_since_last: int) -> bool:
        """
        Determina si debería hacer un comentario sobre la actividad actual.
        
        Args:
            last_activity: Última actividad comentada
            current_activity: Actividad actual
            time_since_last: Segundos desde el último comentario
            
        Returns:
            True si debería comentar
        """
        # No comentar si es la misma actividad
        if last_activity == current_activity:
            return False
            
        # No comentar muy frecuentemente (mínimo 2 minutos)
        if time_since_last < 120:
            return False
            
        # Solo comentar ocasionalmente (30% de probabilidad)
        import random
        return random.random() < 0.3

# Instancia global
_analyzer = ContextAnalyzer()

def analyze_user_activity(window_title: str, process_name: str) -> Optional[str]:
    """Función de conveniencia para analizar actividad del usuario."""
    return _analyzer.analyze_activity(window_title, process_name)

def should_comment_on_activity(last_activity: str, current_activity: str, time_since_last: int) -> bool:
    """Función de conveniencia para determinar si comentar."""
    return _analyzer.should_comment(last_activity, current_activity, time_since_last)