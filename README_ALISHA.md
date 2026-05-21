# 🎭 Alisha - Asistente IA Completa con Voz Mejorada

## ✨ Comando Ultra Simple

```bash
alisha
```

¡ESO ES TODO! 🎉

## 🎵 Voz Refinada y Natural

### 🎯 Mejoras de Voz Implementadas
- ✅ **Velocidad optimizada**: 175 WPM (más humana y natural)
- ✅ **Volumen máximo**: 1.0 para claridad perfecta
- ✅ **Puntuación inteligente**: Pausas reales en comas y puntos
- ✅ **Limpieza de texto**: Sin caracteres extraños ni roleplay
- ✅ **Voz femenina**: Elvira (España) - muy natural y expresiva

### 🎤 Voces Disponibles
```bash
python listar_voces.py    # Ver todas las voces disponibles
```

**Voces recomendadas para Alisha:**
- **elvira** - Española muy natural (por defecto)
- **dalia** - Mexicana dulce y cálida  
- **salome** - Colombiana expresiva
- **elena** - Argentina vibrante
- **helena** - Sistema Windows (SAPI)

## 🚀 Comandos Disponibles

### Comando Principal
```bash
alisha              # Inicia sistema completo
.\alisha.cmd        # Windows (alternativo)
python alisha       # Multiplataforma
```

### Comandos de Configuración
```bash
python listar_voces.py              # Listar y probar voces
python desktop_widget.py            # Solo Live2D + IA
python web_app.py                   # Solo interfaz web
```

## 🎨 Mejoras Implementadas

### 🎭 Interfaz Web Renovada
- ✅ Diseño moderno con animaciones suaves
- ✅ Sugerencias de conversación interactivas
- ✅ Estados emocionales visuales mejorados
- ✅ Logs limpios sin ruido técnico
- ✅ Mensajes únicos (sin duplicados)

### 🎵 Sistema de Voz Neural
- ✅ Voz femenina Elena (española suave)
- ✅ Múltiples opciones de voz disponibles
- ✅ Calidad neural de Microsoft Edge-TTS
- ✅ Configuración simple por comando

### 🖱️ Interactividad Completa
- ✅ Seguimiento natural de mouse
- ✅ Reacciones contextuales por clics
- ✅ Observación inteligente de aplicaciones
- ✅ Siempre visible sobre otras ventanas

## 📁 Archivos del Sistema

- **`alisha.py`** - 🎯 **COMANDO PRINCIPAL ÚNICO**
- `desktop_widget.py` - Sistema Live2D + IA integrado
- `web_app.py` - Interfaz web (se inicia automáticamente)
- `ia.py` - Motor de IA (se inicia automáticamente)
- `tts_engine.py` - Sistema de voz neural
- `config.py` - Configuración general
- `templates/index.html` - Interfaz web renovada

## 📍 Configuración del Personaje

### Posición y Tamaño
- **Ubicación**: Esquina inferior derecha (1600, 750)
- **Tamaño**: 400x600 px (medio cuerpo perfecto)
- **Modelo**: IceGirl completo con cuerpo y expresiones

### Interactividad
- **Seguimiento de Mouse**: Mirada natural que sigue el cursor
- **Reacciones por Clics**: 
  - 1 clic = Susto (惊讶)
  - 2 clics = Curiosidad (疑惑) 
  - 3+ clics = Enojo/Fastidio (生气/白眼)
- **Siempre al Frente**: Se mantiene visible sobre todas las ventanas
- **Observación**: Reacciona según la aplicación que uses

### Ruta del Modelo Live2D
```
C:\Program Files (x86)\Steam\steamapps\common\VTube Studio\VTube Studio_Data\StreamingAssets\Live2DModels\IceGirl_Live2d\IceGIrl Live2D\IceGirl.model3.json
```

### Personalización
Edita `config.py` para cambiar:
- Ruta del modelo Live2D
- Configuraciones de IA
- Rutas de aplicaciones

Edita `chibi_prefs.json` para cambiar:
- Posición del personaje
- Tamaño de ventana
- Comportamiento

## 🎮 Controles

### Personaje Live2D
- **Seguimiento de Mouse**: La mirada sigue naturalmente el cursor
- **Clics Interactivos**: 
  - 1 clic = Reacción de susto
  - 2 clics = Expresión de curiosidad
  - 3+ clics = Enojo o fastidio
- **Observación**: Reacciona a lo que haces en pantalla
- **Siempre Visible**: Se mantiene al frente de todas las ventanas
- **Arrastrar**: Mover el personaje (temporalmente desactiva click-through)

### Interfaz Web
- **Chat**: Conversa con Alisha
- **Controles**: Ajusta configuraciones
- **Estado**: Ve el estado emocional actual
- **Historial**: Revisa conversaciones anteriores

## 🔧 Solución de Problemas

### El personaje no aparece
1. Verifica que la ruta del modelo Live2D sea correcta
2. Asegúrate de tener PyQt6 instalado: `pip install PyQt6`
3. Verifica permisos de Windows

### Error de MongoDB
- El sistema funciona sin MongoDB usando memoria local
- Para usar MongoDB, configura la variable `MONGO_URI` en `.env`

### El navegador no se abre
- Abre manualmente: http://localhost:5000
- Verifica que el puerto 5000 esté libre

## 📁 Archivos del Sistema

- **`desktop_widget.py`** - 🎯 **SISTEMA PRINCIPAL UNIFICADO**
- `web_app.py` - Interfaz web (se inicia automáticamente)
- `ia.py` - Motor de IA (se inicia automáticamente)
- `config.py` - Configuración general
- `chibi_prefs.json` - Preferencias del personaje
- `templates/live2d_viewer.html` - Visor Live2D

## 🎨 Emociones Disponibles

El personaje Live2D responde a estas emociones:
- **Alegría** → 脸红 (rubor)
- **Entusiasmo** → 星星眼 (ojos de estrella)
- **Curiosidad** → 疑惑 (duda)
- **Preocupación** → 流泪 (lágrimas)
- **Frustración** → 生气 (enojo)
- **Cansancio** → 白眼 (ojos en blanco)
- **Neutral** → Expresión por defecto

## 💡 Uso Ultra Simple

1. **Inicio**: `python alisha.py` - ¡Un solo comando!
2. **Interacción**: Haz clics cerca del personaje para reacciones
3. **Seguimiento**: Mueve el mouse para que te siga con la mirada  
4. **Chat**: La interfaz web se abre automáticamente
5. **Voz**: Alisha habla con voz neural femenina

## ✨ Funcionalidades Confirmadas

### 🎭 Personaje Live2D
- ✅ Modelo IceGirl completo con cuerpo
- ✅ Posición: Esquina inferior derecha (1600, 750)
- ✅ Tamaño: 400x600px (medio cuerpo perfecto)
- ✅ Siempre al frente de todas las ventanas

### 🖱️ Interactividad Total
- ✅ Seguimiento suave de mouse con la mirada
- ✅ Reacciones por clics: 1=susto, 2=curiosidad, 3+=enojo
- ✅ Parpadeo automático en cada clic
- ✅ Inclinación sutil de cabeza

### 👁️ Observación Inteligente
- ✅ Detecta aplicación activa cada 15 segundos
- ✅ Reacciones específicas por tipo de app
- ✅ Expresiones contextuales automáticas

### 🤖 Sistema Completo
- ✅ Motor de IA con Llama 3.1
- ✅ Interfaz web moderna automática
- ✅ Memoria persistente y emociones
- ✅ Voz neural femenina (Elena/Alisha)
- ✅ Logs limpios sin ruido técnico

## 🎵 Voces Disponibles

- **alisha/elena** - Española suave (por defecto)
- **dalia** - Mexicana dulce y cálida
- **valentina** - Colombiana expresiva
- **camila** - Argentina vibrante

## 🔧 Solución de Problemas

### Si no aparece el personaje:
```bash
python alisha.py --clean    # Limpia procesos anteriores
```

### Si hay problemas de voz:
```bash
python alisha.py --voice elena    # Cambia a voz Elena
```

### Si la interfaz web no abre:
- Abre manualmente: http://localhost:5000
- Verifica que el puerto 5000 esté libre

¡Disfruta de tu asistente IA Alisha completa! 🎉

## 🔧 Configuración Avanzada

### Ajustes de Seguimiento de Mouse
```python
# En desktop_widget.py
MOUSE_TRACKING_ENABLED = True    # Activar/desactivar
MAX_EYE_OFFSET = 15             # Movimiento máximo ojos (px)
MAX_HEAD_TILT = 10              # Inclinación máxima cabeza (°)
SMOOTHING_FACTOR = 0.15         # Suavidad (0.1-1.0)
MOUSE_POLL_RATE = 60            # Frecuencia lectura mouse (Hz)
```

### Posición del Personaje
```json
// En chibi_prefs.json
{
  "x": 1600, "y": 750,           // Posición en pantalla
  "w": 400, "h": 600,            // Tamaño ventana
  "seguir_cursor": true,         // Seguimiento mouse
  "reacciones_clic": true,       // Reacciones por clics
  "observacion_pantalla": true   // Observación apps
}
```

### Expresiones Disponibles
- **脸红** (Rubor): Alegría, timidez
- **星星眼** (Ojos de estrella): Entusiasmo, diversión
- **疑惑** (Duda): Curiosidad, concentración
- **流泪** (Lágrimas): Tristeza, preocupación
- **生气** (Enojo): Frustración, molestia
- **白眼** (Ojos en blanco): Fastidio, cansancio
- **惊讶** (Sorpresa): Susto, asombro

¡Disfruta de tu asistente IA Alisha! 🎉