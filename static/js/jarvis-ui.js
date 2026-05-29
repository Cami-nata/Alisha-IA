/**
 * jarvis-ui.js — Lógica JARVIS: orbe, módulos, timeline, estado en tiempo real.
 * Se carga DESPUÉS de app.js. Extiende su funcionalidad sin reemplazarla.
 */

// ── Estado del orbe ───────────────────────────────────────────────────────────
const ORB_STATES = {
  idle:      { label: "IDLE",      class: "idle",      dot: "green" },
  listening: { label: "ESCUCHANDO",class: "listening", dot: "cyan"  },
  thinking:  { label: "PENSANDO",  class: "thinking",  dot: "blue"  },
  speaking:  { label: "HABLANDO",  class: "speaking",  dot: "cyan"  },
  working:   { label: "TRABAJANDO",class: "working",   dot: "amber" },
  error:     { label: "ERROR",     class: "error",     dot: "amber" },
  sleep:     { label: "DORMIDA",   class: "sleep",     dot: "muted" },
};

let _orbState = "idle";
let _statusPollInterval = null;
let _timelineEvents = [];

// ── Orbe ──────────────────────────────────────────────────────────────────────

function setOrbState(state) {
  if (_orbState === state) return;
  _orbState = state;

  const orb   = document.getElementById("orb-principal");
  const label = document.getElementById("orb-label");
  const waves = document.getElementById("orb-waves");
  const badge = document.getElementById("estado-badge");
  const sysBadge = document.getElementById("system-state-badge");

  if (!orb) return;

  const cfg = ORB_STATES[state] || ORB_STATES.idle;

  // Clase del orbe
  orb.className = "j-orb " + cfg.class;

  // Label
  if (label) label.textContent = cfg.label;

  // Ondas de audio (solo en listening/speaking)
  if (waves) {
    waves.style.display = (state === "listening" || state === "speaking") ? "block" : "none";
  }

  // Badge header
  if (badge) {
    badge.textContent = cfg.label;
    badge.className = "j-badge " + (state === "idle" ? "" : state);
  }

  // System state badge sidebar
  if (sysBadge) {
    const mapa = {
      idle: "■ IDLE", thinking: "◆ THINKING",
      working: "▶ WORKING", error: "⚠ ERROR", sleep: "● SLEEP"
    };
    sysBadge.textContent = mapa[state] || "■ IDLE";
    sysBadge.className = "j-sys-badge " + (state === "error" ? "overloaded" : state);
  }
}

function toggleOrbMenu() {
  // Click en el orbe → si está dormida, despertar
  if (_orbState === "sleep") {
    despertarAlisha();
  }
}

// ── Timeline ──────────────────────────────────────────────────────────────────

const TIMELINE_ICONS = {
  "vio pantalla":          { dot: "blue",  icon: "👁" },
  "recibió telegram":      { dot: "cyan",  icon: "✈" },
  "pensando":              { dot: "blue",  icon: "🤔" },
  "esperando confirmación":{ dot: "amber", icon: "⏳" },
  "ejecutó tarea":         { dot: "green", icon: "✓" },
  "habló":                 { dot: "cyan",  icon: "🔊" },
  "error":                 { dot: "amber", icon: "⚠" },
  "sistema iniciado":      { dot: "green", icon: "◉" },
  "mensaje recibido":      { dot: "cyan",  icon: "💬" },
  "respuesta enviada":     { dot: "green", icon: "↗" },
};

function addTimelineEvent(text, type) {
  const track = document.getElementById("timeline-track");
  if (!track) return;

  const now = new Date();
  const timeStr = now.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });

  const key = text.toLowerCase();
  const cfg = Object.entries(TIMELINE_ICONS).find(([k]) => key.includes(k));
  const dotClass = cfg ? cfg[1].dot : "muted";
  const icon = cfg ? cfg[1].icon : "·";

  const ev = document.createElement("div");
  ev.className = "j-event recent";
  ev.innerHTML = `
    <div class="j-event-dot ${dotClass}"></div>
    <span>${icon} ${text}</span>
    <span class="j-event-time">${timeStr}</span>`;

  // Insertar al principio
  track.insertBefore(ev, track.firstChild);

  // Quitar clase "recent" después de 5s
  setTimeout(() => ev.classList.remove("recent"), 5000);

  // Mantener máx 12 eventos
  _timelineEvents.push(ev);
  if (_timelineEvents.length > 12) {
    const old = _timelineEvents.shift();
    if (old && old.parentNode) old.parentNode.removeChild(old);
  }
}

// ── Módulos ───────────────────────────────────────────────────────────────────

function setModuleState(modId, status, dotClass, text) {
  const mod    = document.getElementById("mod-" + modId);
  const dot    = document.getElementById("mod-" + modId + "-dot");
  const statusEl = document.getElementById("mod-" + modId + "-status");

  if (!mod) return;

  // Clase del módulo
  mod.className = "j-module" + (dotClass === "on" ? " active" : dotClass === "err" ? " error" : dotClass === "busy" ? " warning" : "");

  if (dot) dot.className = "j-mod-dot " + dotClass;
  if (statusEl && text) statusEl.textContent = text;
}

// ── Polling de estado ─────────────────────────────────────────────────────────

async function pollStatus() {
  try {
    const resp = await fetch("/api/status");
    if (!resp.ok) return;
    const data = await resp.json();

    // Actualizar barras de ánimo/energía
    const dopamina = data.dopamina ?? 0.75;
    const energia  = data.energia  ?? 0.8;
    const barraD = document.getElementById("barra-dopamina");
    const barraE = document.getElementById("barra-energia");
    if (barraD) barraD.style.width = Math.round(dopamina * 100) + "%";
    if (barraE) barraE.style.width = Math.round((energia ?? 0.8) * 100) + "%";

    // Estado emocional → orbe
    const modo = (data.modo || "IDLE").toLowerCase();
    const emo  = data.estado_emocional || "neutral";
    const hablando = data.hablando || false;

    if (hablando) {
      setOrbState("speaking");
    } else if (modo === "thinking") {
      setOrbState("thinking");
    } else if (modo === "working") {
      setOrbState("working");
    } else if (modo === "overloaded") {
      setOrbState("error");
    } else {
      // Mapear emoción a estado del orbe
      const emoMap = {
        "curiosidad": "thinking", "preocupación": "thinking",
        "frustración": "error",   "cansancio": "sleep",
      };
      setOrbState(emoMap[emo] || "idle");
    }

    // Módulo cerebro
    const engine = data.engine || "none";
    setModuleState("cerebro", "on", engine !== "none" ? "on" : "busy",
      engine !== "none" ? engine : "Iniciando...");

    // Módulo sistema
    const online = data.online !== false;
    setModuleState("sistema", "on", online ? "on" : "busy",
      online ? "Online" : "Sin internet");

    // Módulo avatar
    const hablando2 = data.hablando || false;
    setModuleState("avatar", "on", hablando2 ? "busy" : "on",
      hablando2 ? "Hablando" : "Live2D");

    // Telegram
    const telegramEnabled = data.telegram_enabled || false;
    setModuleState("telegram", telegramEnabled ? "on" : "off",
      telegramEnabled ? "on" : "off",
      telegramEnabled ? "Activo" : "Desactivado");

  } catch (e) {
    // Sin conexión al backend
    setOrbState("error");
    setModuleState("cerebro", "err", "err", "Sin conexión");
  }
}

// ── Historial JARVIS ──────────────────────────────────────────────────────────

async function cargarHistorial() {
  try {
    const resp = await fetch("/api/sesiones");
    if (!resp.ok) return;
    const sesiones = await resp.json();
    const lista = document.getElementById("historial-lista");
    if (!lista) return;

    lista.innerHTML = "";
    sesiones.slice(0, 20).forEach(s => {
      const item = document.createElement("div");
      item.className = "j-hist-item";
      item.textContent = s.titulo || "Conversación";
      item.title = s.inicio || "";
      item.onclick = () => cargarSesion(s.id, item);
      lista.appendChild(item);
    });
  } catch (e) {}
}

async function cargarSesion(sessionId, itemEl) {
  // Marcar activo
  document.querySelectorAll(".j-hist-item").forEach(el => el.classList.remove("activo"));
  if (itemEl) itemEl.classList.add("activo");

  try {
    const resp = await fetch(`/api/sesion/${sessionId}/mensajes`);
    if (!resp.ok) return;
    const mensajes = await resp.json();

    const area = document.getElementById("mensajes-area");
    const bienvenida = document.getElementById("bienvenida");
    if (!area) return;

    // Limpiar área
    area.innerHTML = "";
    if (bienvenida) area.appendChild(bienvenida);
    if (bienvenida) bienvenida.style.display = "none";

    // Renderizar mensajes
    mensajes.forEach(m => {
      if (typeof agregarMensaje === "function") {
        agregarMensaje(m.rol === "user" ? "usuario" : "ia", m.contenido, m.rol === "user" ? "usuario" : "ia");
      }
    });
  } catch (e) {}
}

// ── Trust widget ──────────────────────────────────────────────────────────────

async function cargarTrust() {
  try {
    const resp = await fetch("/api/perfil");
    if (!resp.ok) return;
    const data = await resp.json();

    const label = document.getElementById("trust-label");
    const xp    = document.getElementById("trust-xp");
    const bar   = document.getElementById("trust-bar");
    const tasks = document.getElementById("trust-tasks");
    const user  = document.getElementById("nombre-usuario-sidebar");

    if (user && data.nombre_usuario) user.textContent = data.nombre_usuario;

    // Trust data (si viene del backend)
    if (data.trust) {
      const t = data.trust;
      const niveles = ["🌱 Aprendiz", "🤝 Asistente", "💎 Partner"];
      if (label) label.textContent = niveles[t.nivel - 1] || "🌱 Aprendiz";
      if (xp)    xp.textContent = `XP: ${t.xp || 0}`;
      if (bar)   bar.style.width = Math.min(100, ((t.xp || 0) / (t.xp_next || 100)) * 100) + "%";
      if (tasks) tasks.textContent = `${t.tareas_completadas || 0} tareas completadas`;
    }

    // Barras de ánimo
    const barraD = document.getElementById("barra-dopamina");
    const barraE = document.getElementById("barra-energia");
    if (barraD && data.dopamina != null) barraD.style.width = Math.round(data.dopamina * 100) + "%";
    if (barraE && data.energia  != null) barraE.style.width = Math.round(data.energia  * 100) + "%";

  } catch (e) {}
}

// ── Media sync ────────────────────────────────────────────────────────────────

async function pollMedia() {
  try {
    const resp = await fetch("/api/status");
    if (!resp.ok) return;
    const data = await resp.json();
    const media = data.media_actual;
    const bar   = document.getElementById("media-sync-bar");
    const icon  = document.getElementById("media-sync-icon");
    const text  = document.getElementById("media-sync-text");

    if (media && media.title && bar) {
      bar.classList.add("visible");
      if (icon) icon.textContent = media.type === "video" ? "▶" : "♪";
      if (text) text.textContent = media.title.slice(0, 30);
    } else if (bar) {
      bar.classList.remove("visible");
    }
  } catch (e) {}
}

// ── Función pararAcciones (botón PARAR del panel) ─────────────────────────────

function pararAcciones() {
  fetch("/api/stop", { method: "POST" })
    .then(() => {
      addTimelineEvent("Acciones detenidas", "stop");
      setOrbState("idle");
      if (typeof mostrarToast === "function") mostrarToast("⏹ Acciones detenidas");
    })
    .catch(() => {});
}

// ── Integración con eventos de app.js ─────────────────────────────────────────

// Interceptar eventos de SocketIO para actualizar el orbe y timeline
(function patchSocketEvents() {
  if (typeof socket === "undefined") {
    // Reintentar cuando socket esté disponible
    setTimeout(patchSocketEvents, 200);
    return;
  }

  socket.on("pensando", (data) => {
    if (data.activo) {
      setOrbState("thinking");
      addTimelineEvent("pensando", "thinking");
    }
  });

  socket.on("respuesta_inicio", () => {
    setOrbState("speaking");
    addTimelineEvent("respondiendo", "speaking");
  });

  socket.on("respuesta_fin", () => {
    setOrbState("idle");
    addTimelineEvent("respuesta enviada", "done");
  });

  socket.on("respuesta", (data) => {
    setOrbState("idle");
    const fuente = data.fuente || "";
    if (fuente === "curiosidad") addTimelineEvent("comentario espontáneo", "curiosidad");
    else if (fuente === "vision") addTimelineEvent("vio pantalla", "vision");
    else addTimelineEvent("respuesta enviada", "done");
  });

  socket.on("engine_indicator", (data) => {
    if (data.engine) {
      setModuleState("cerebro", "on", "on", data.engine);
    }
  });

  // Telegram incoming (si el backend lo emite)
  socket.on("telegram_message", (data) => {
    addTimelineEvent("recibió telegram", "telegram");
    setModuleState("telegram", "on", "busy", "Mensaje recibido");
    setTimeout(() => setModuleState("telegram", "on", "on", "Activo"), 3000);
  });

  // Vision event
  socket.on("vision_event", (data) => {
    addTimelineEvent("vio pantalla", "vision");
    setModuleState("vision", "on", "busy", data.app || "Escaneando");
    setTimeout(() => setModuleState("vision", "on", "on", "Activo"), 2000);
  });

  // Propuesta de acción
  socket.on("propuesta_accion", () => {
    addTimelineEvent("esperando confirmación", "confirm");
    setOrbState("working");
  });

  // Nivel 3
  socket.on("nivel_3_unlock", () => {
    addTimelineEvent("¡Nivel 3 desbloqueado!", "level");
  });
})();

// ── Drag & drop (JARVIS) ──────────────────────────────────────────────────────

const _dragOverlay = document.getElementById("drag-overlay");

document.addEventListener("dragover", (e) => {
  e.preventDefault();
  if (_dragOverlay) _dragOverlay.style.display = "flex";
});

document.addEventListener("dragleave", (e) => {
  if (e.relatedTarget === null && _dragOverlay) {
    _dragOverlay.style.display = "none";
  }
});

document.addEventListener("drop", (e) => {
  e.preventDefault();
  if (_dragOverlay) _dragOverlay.style.display = "none";
  const files = Array.from(e.dataTransfer.files);
  if (files.length > 0 && typeof adjuntarArchivos === "function") {
    // Simular input de archivos
    const dt = new DataTransfer();
    files.forEach(f => dt.items.add(f));
    const fakeInput = { files: dt.files };
    adjuntarArchivos(fakeInput);
  }
});

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  // Estado inicial
  setOrbState("idle");
  addTimelineEvent("sistema iniciado", "init");

  // Cargar datos iniciales
  cargarHistorial();
  cargarTrust();

  // Polling de estado cada 3s
  _statusPollInterval = setInterval(pollStatus, 3000);
  pollStatus(); // inmediato

  // Polling de media cada 5s
  setInterval(pollMedia, 5000);

  // Actualizar historial cada 30s
  setInterval(cargarHistorial, 30000);

  console.log("[JARVIS UI] ✓ Sistema iniciado");
});
