# Desktop App — Alisha IA

Aplicación de escritorio instalable con UI estilo JARVIS.

## Arquitectura

```
Desktop App (Tauri/Electron/pywebview)
├── UI Web Local (React/Vue/Vanilla JS)
│   ├── Orbe principal animado
│   ├── Panel de chat
│   ├── Panel de módulos
│   └── Timeline de actividad
├── Backend Python (localhost API)
│   └── core/, memory/, personality/, etc.
└── Avatar Live2D (proceso independiente)
    └── avatar/cabina_virtual.py
```

## Opciones de implementación

### Opción 1: Tauri (Recomendado)
- **Pros:** Liviano (~3 MB), rápido, seguro, Rust + Web
- **Contras:** Requiere Rust instalado para build
- **Instalación:** `npm install -g @tauri-apps/cli`

### Opción 2: Electron
- **Pros:** Maduro, muchos ejemplos, fácil desarrollo
- **Contras:** Pesado (~150 MB), consume más RAM
- **Instalación:** `npm install electron`

### Opción 3: pywebview
- **Pros:** 100% Python, simple, usa WebView2 nativo
- **Contras:** Menos control sobre la ventana, menos features
- **Instalación:** Ya está en requirements.txt

## Estado actual

🚧 **En desarrollo**

Por ahora, Alisha corre como:
- Servidor web en `localhost:5000`
- Avatar Live2D en ventana separada
- Tray icon para control

La app de escritorio unificada está pendiente.

## Roadmap

1. ✅ Definir arquitectura
2. ⏳ Diseñar UI estilo JARVIS
3. ⏳ Implementar orbe principal
4. ⏳ Conectar con backend via WebSocket
5. ⏳ Integrar avatar como overlay
6. ⏳ Crear instalador Windows

## UI Design — Estilo JARVIS

### Pantalla principal

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌──────────┐         ╭─────╮         ┌──────────────────┐ │
│  │          │         │  ◉  │         │  ┌─ Cerebro      │ │
│  │  Chat    │         │     │         │  ├─ Memoria      │ │
│  │          │         │     │         │  ├─ Voz          │ │
│  │  > Hola  │         ╰─────╯         │  ├─ Visión       │ │
│  │  < Che   │      Orbe Principal     │  ├─ Telegram     │ │
│  │          │                         │  ├─ Tareas       │ │
│  │          │                         │  └─ Sistema      │ │
│  └──────────┘                         └──────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Timeline: vio pantalla → pensando → ejecutó tarea   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Paleta de colores

- **Fondo:** `#0a0e1a` (azul oscuro casi negro)
- **Orbe principal:** `#00d4ff` (cyan eléctrico)
- **Acentos:** `#ffffff` (blanco), `#4a9eff` (azul), `#ffb84d` (ámbar)
- **Texto:** `#e0e6ed` (gris claro)
- **Paneles:** `#141824` con borde `#1e2433`

### Estados del orbe

| Estado | Visual | Color |
|--------|--------|-------|
| idle | Pulso suave | Cyan |
| listening | Ondas de audio | Cyan brillante |
| thinking | Anillos rotando | Azul |
| speaking | Onda sincronizada | Cyan + blanco |
| working | Segmentos activos | Azul + cyan |
| error | Pulso lento | Ámbar/rojo |
| sleep | Brillo bajo | Cyan tenue |

## Desarrollo

```bash
# Instalar dependencias
npm install

# Desarrollo (hot reload)
npm run dev

# Build para producción
npm run build

# Crear instalador
npm run package
```

## Integración con el avatar

El avatar Live2D debe poder:
1. Correr independiente de la app
2. Compartir estado via `data/chibi_state.json`
3. Recibir comandos via API local
4. Overlay sobre la app o ventana separada

## Notas técnicas

- La UI se conecta a `localhost:5000` via WebSocket
- El backend Python ya existe y funciona
- El avatar ya existe en `avatar/cabina_virtual.py`
- Solo falta unificar todo en una app instalable
