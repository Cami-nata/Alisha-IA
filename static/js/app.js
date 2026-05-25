/**
 * app.js — Lógica del chat: SocketIO, mensajes, archivos, menú adjuntos,
 * generación de imágenes, drag & drop.
 */

const socket = io({
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 2000,
  timeout: 20000,
  transports: ["websocket", "polling"],
});

// ── Estado global ─────────────────────────────────────────────────────────────
let estadoActual      = "neutral";
let archivosAdjuntos  = [];
let enviando          = false;
let grabando          = false;
let mediaRecorder     = null;
let audioChunks       = [];
let _streamBuffer     = "";
let _streamEstado     = "neutral";
let _streamMsgEl      = null;
let _reconectando     = false;
let _overlayEl        = null;
let _intentoReconexion = 0;
let _barraGrabacion   = null;
let _barraProgreso    = null;

// Toggles del menú de adjuntos
let _razonamientoActivo  = false;
let _busquedaWebActiva   = false;
let _investigacionActiva = false;

// ── Elementos DOM ─────────────────────────────────────────────────────────────
const mensajesArea  = document.getElementById("mensajes-area");
const entradaTexto  = document.getElementById("entrada-texto");
const chipsArchivos = document.getElementById("chips-archivos");
const estadoBadge   = document.getElementById("estado-badge");
const nombreIA      = document.getElementById("nombre-ia");
const nombreSidebar = document.getElementById("nombre-usuario-sidebar");
const bienvenida    = document.getElementById("bienvenida");

// ══════════════════════════════════════════════════════════════════════════════
// RECONEXIÓN
// ══════════════════════════════════════════════════════════════════════════════

function _mostrarOverlayReconexion() {
  if (_reconectando) return;
  _reconectando = true;
  if (!_overlayEl) {
    _overlayEl = document.createElement("div");
    _overlayEl.id = "overlay-reconexion";
    _overlayEl.innerHTML = `
      <div style="font-size:24px;animation:spin 1s linear infinite;font-family:monospace">⟳</div>
      <div style="font-size:10px">RECONECTANDO...</div>
      <div style="font-size:9px;opacity:0.6" id="overlay-contador">Intentando...</div>
      <style>@keyframes spin{to{transform:rotate(360deg)}}</style>`;
    document.body.appendChild(_overlayEl);
  }
  _overlayEl.style.display = "flex";
}

function _ocultarOverlayReconexion() {
  _reconectando = false;
  if (_overlayEl) _overlayEl.style.display = "none";
}

socket.on("reconnect_attempt", (n) => {
  _intentoReconexion = n;
  _mostrarOverlayReconexion();
  const el = document.getElementById("overlay-contador");
  if (el) el.textContent = `Intento ${n}...`;
});
socket.on("reconnect", () => { _intentoReconexion = 0; _ocultarOverlayReconexion(); });
socket.on("reconnect_failed", () => {
  const el = document.getElementById("overlay-contador");
  if (el) el.textContent = "No se pudo reconectar. Recargá la página.";
});
socket.on("disconnect", (reason) => {
  quitarPensando(); desbloquearEntrada();
  if (reason !== "io client disconnect") _mostrarOverlayReconexion();
});
socket.on("connect_error", () => { quitarPensando(); desbloquearEntrada(); _mostrarOverlayReconexion(); });
socket.on("connect", () => {
  _ocultarOverlayReconexion();
  const b = document.getElementById("banner-despertar");
  if (b) b.style.display = "none";
});

// ══════════════════════════════════════════════════════════════════════════════
// EVENTOS SOCKETIO
// ══════════════════════════════════════════════════════════════════════════════

socket.on("pensando", (data) => {
  if (data.activo) {
    mostrarPensando();
    estadoBadge.textContent = "THINKING";
    estadoBadge.className = "estado-badge curiosidad";
    actualizarSystemState("thinking");
  }
});

socket.on("respuesta_inicio", (data) => {
  _streamBuffer = "";
  _streamEstado = data.estado_emocional || "neutral";
  quitarPensando();
  _crearBurbujaStreaming();
});

socket.on("respuesta_chunk", (data) => {
  _streamBuffer += data.chunk;
  _actualizarBurbujaStreaming(_streamBuffer);
});

socket.on("respuesta_fin", (data) => {
  _finalizarBurbujaStreaming(data.texto || _streamBuffer, _streamEstado);
  if (data.estado_emocional) actualizarEstado(data.estado_emocional);
  desbloquearEntrada();
  cargarHistorial();
  actualizarSystemState("idle");
});

socket.on("respuesta", (data) => {
  quitarPensando();
  // Si viene con fuente "curiosidad" o "vision", es proactivo
  const fuente = data.fuente || "";
  agregarMensaje("ia", data.texto || "...", "ia", fuente === "curiosidad" ? "💭 " : "");
  if (data.estado_emocional) actualizarEstado(data.estado_emocional);
  desbloquearEntrada();
  cargarHistorial();
  actualizarSystemState("idle");
});

socket.on("propuesta_accion", (data) => {
  if (!data || !data.mensaje) return;
  const area = document.getElementById("mensajes-area");
  if (!area) return;
  const row = document.createElement("div");
  row.className = "mensaje-row ia";
  const nombre = document.createElement("div");
  nombre.className = "msg-nombre";
  nombre.textContent = nombreIA ? nombreIA.textContent : "Alisha";
  row.appendChild(nombre);
  const burbuja = document.createElement("div");
  burbuja.className = "burbuja ia propuesta-accion";
  const msg = document.createElement("p");
  msg.style.marginBottom = "10px";
  msg.textContent = data.mensaje;
  burbuja.appendChild(msg);
  const botones = data.botones || ["Sí, hacelo", "No gracias"];
  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;";
  botones.forEach((label, idx) => {
    const btn = document.createElement("button");
    btn.textContent = label;
    const esSi = idx === 0;
    btn.style.cssText = esSi
      ? "background:rgba(0,229,255,0.15);border:1px solid rgba(0,229,255,0.4);color:#00e5ff;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600;"
      : "background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.4);padding:6px 14px;border-radius:4px;cursor:pointer;font-size:12px;";
    btn.onclick = () => {
      btnRow.querySelectorAll("button").forEach(b => b.disabled = true);
      btnRow.style.opacity = "0.5";
      if (esSi) {
        agregarMensaje("usuario", label, "usuario");
        fetch("/api/confirmar_accion", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ accion_id: data.accion_id, contexto: data.contexto || {} }),
        }).catch(e => console.error(e));
      } else {
        agregarMensaje("usuario", "No gracias", "usuario");
        agregarMensaje("ia", "Dale, sin problema. Avisame si necesitás algo.", "ia");
        if (data.accion_id && data.accion_id.startsWith("sugerencia_")) {
          fetch("/api/sugerencia/rechazar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ accion_id: data.accion_id, tipo: (data.contexto || {}).tipo || "" }),
          }).catch(() => {});
        }
      }
    };
    btnRow.appendChild(btn);
  });
  burbuja.appendChild(btnRow);
  row.appendChild(burbuja);
  area.appendChild(row);
  scrollAbajo();
});

socket.on("nivel_3_unlock", (data) => {
  document.body.style.background = data.nuevo_fondo || "";
  mostrarToast("💎 ¡Nivel 3 desbloqueado! Ya sos mi partner.");
});

socket.on("lock_state", (data) => {
  mostrarToast(data.bloqueado ? "🔒 Control bloqueado" : "🔓 Control desbloqueado");
});

socket.on("progreso_grabacion", (data) => {
  const el = document.getElementById("grabacion-pasos");
  if (el) el.textContent = `${data.paso} pasos`;
});

socket.on("progreso_workflow", (data) => {
  if (!_barraProgreso) {
    _barraProgreso = document.createElement("div");
    _barraProgreso.id = "barra-progreso-workflow";
    _barraProgreso.style.cssText = `position:fixed;bottom:90px;left:50%;transform:translateX(-50%);
      background:var(--bg-2);border:1px solid var(--border-2);border-radius:4px;
      padding:12px 20px;z-index:9997;min-width:280px;text-align:center;
      box-shadow:4px 4px 0 rgba(0,0,0,0.5);`;
    document.body.appendChild(_barraProgreso);
  }
  const pct = Math.round((data.paso_actual / data.total) * 100);
  _barraProgreso.innerHTML = `
    <div style="font-size:9px;color:rgba(0,229,255,0.7);font-family:var(--font-pixel);margin-bottom:6px">
      WORKING — ${data.paso_actual}/${data.total}
    </div>
    <div style="background:rgba(255,255,255,0.06);border-radius:0;height:4px;overflow:hidden;margin-bottom:6px">
      <div style="width:${pct}%;height:100%;background:linear-gradient(90deg,var(--rosa),var(--cyan));transition:width 0.3s"></div>
    </div>
    <div style="font-size:11px;color:rgba(255,255,255,0.5)">${data.descripcion || ""}</div>`;
  if (data.completado) {
    setTimeout(() => { if (_barraProgreso) { _barraProgreso.remove(); _barraProgreso = null; } }, 2000);
  }
});

socket.on("habilidad_guardada", (data) => {
  const lista = document.getElementById("historial-lista");
  if (!lista) return;
  const div = document.createElement("div");
  div.className = "historial-item";
  div.style.borderLeft = "2px solid rgba(0,229,255,0.4)";
  div.textContent = `⚡ ${data.nombre}`;
  div.title = data.descripcion || data.nombre;
  div.onclick = () => fetch("/api/ejecutar_habilidad", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre: data.nombre }),
  });
  lista.insertBefore(div, lista.firstChild);
});

// ══════════════════════════════════════════════════════════════════════════════
// STREAMING
// ══════════════════════════════════════════════════════════════════════════════

function _crearBurbujaStreaming() {
  const area = document.getElementById("mensajes-area");
  if (!area) return;
  _streamMsgEl = document.createElement("div");
  _streamMsgEl.className = "mensaje-row ia streaming";
  _streamMsgEl.innerHTML = `
    <div class="msg-nombre">${nombreIA ? nombreIA.textContent : "Alisha"}</div>
    <div class="burbuja ia"><span class="stream-text"></span><span class="cursor">▌</span></div>`;
  area.appendChild(_streamMsgEl);
  scrollAbajo();
}

function _actualizarBurbujaStreaming(texto) {
  if (!_streamMsgEl) return;
  const span = _streamMsgEl.querySelector(".stream-text");
  if (span) span.textContent = texto;
  scrollAbajo();
}

function _finalizarBurbujaStreaming(texto, estado) {
  if (_streamMsgEl) { _streamMsgEl.remove(); _streamMsgEl = null; }
  agregarMensaje("ia", texto, estado || "ia");
}

// ══════════════════════════════════════════════════════════════════════════════
// MENSAJES
// ══════════════════════════════════════════════════════════════════════════════

function renderizarContenido(texto) {
  if (!texto) return "";
  if (typeof marked !== "undefined") {
    marked.setOptions({ breaks: true, gfm: true });
    try { return marked.parse(texto); } catch(e) {}
  }
  return texto.replace(/\n/g, "<br>");
}

function aplicarKatex(elemento) {
  if (typeof renderMathInElement !== "undefined") {
    try {
      renderMathInElement(elemento, {
        delimiters: [
          {left:"$$",right:"$$",display:true},{left:"$",right:"$",display:false},
          {left:"\\[",right:"\\]",display:true},{left:"\\(",right:"\\)",display:false},
        ],
        throwOnError: false, output: "html",
      });
    } catch(e) {}
  }
  if (typeof hljs !== "undefined") {
    elemento.querySelectorAll("pre code").forEach(block => {
      try { hljs.highlightElement(block); } catch(e) {}
    });
  }
}

function agregarMensaje(tipo, texto, clase, prefijo = "") {
  if (bienvenida) bienvenida.style.display = "none";
  const row = document.createElement("div");
  row.className = `mensaje-row ${tipo}`;
  if (clase === "pensando") row.id = "burbuja-pensando";

  const nombre = document.createElement("div");
  nombre.className = "msg-nombre";
  nombre.textContent = tipo === "ia" ? (nombreIA ? nombreIA.textContent : "Alisha") : "Tú";
  row.appendChild(nombre);

  const burbuja = document.createElement("div");
  burbuja.className = `burbuja ${tipo === "ia" ? "ia" : "usuario"}`;

  if (tipo === "ia" && clase !== "pensando") {
    burbuja.innerHTML = renderizarContenido(prefijo + texto);
    aplicarKatex(burbuja);
  } else {
    burbuja.textContent = prefijo + texto;
  }

  // Timestamp
  const ts = document.createElement("div");
  ts.className = "msg-timestamp";
  ts.textContent = new Date().toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });

  row.appendChild(burbuja);
  row.appendChild(ts);
  mensajesArea.appendChild(row);
  scrollAbajo();
  return row;
}

function mostrarPensando() {
  quitarPensando();
  const row = document.createElement("div");
  row.className = "mensaje-row ia";
  row.id = "burbuja-pensando";
  row.innerHTML = `
    <div class="msg-nombre">${nombreIA ? nombreIA.textContent : "Alisha"}</div>
    <div class="burbuja pensando"></div>`;
  mensajesArea.appendChild(row);
  scrollAbajo();
}

function quitarPensando() {
  const el = document.getElementById("burbuja-pensando");
  if (el) el.remove();
}

function scrollAbajo() {
  setTimeout(() => { mensajesArea.scrollTop = mensajesArea.scrollHeight; }, 50);
}

function actualizarEstado(estado) {
  if (estado === estadoActual) return;
  estadoActual = estado;
  const mapa = {
    "neutral":"IDLE","alegría":"HAPPY","entusiasmo":"ACTIVE",
    "curiosidad":"THINKING","preocupación":"ALERT","frustración":"ERROR","cansancio":"LOW",
  };
  estadoBadge.textContent = mapa[estado] || estado.toUpperCase();
  estadoBadge.className = "estado-badge " + estado;
}

function actualizarSystemState(state) {
  const el = document.getElementById("system-state-badge");
  if (!el) return;
  const mapa = { idle:"■ IDLE", working:"▶ WORKING", thinking:"◆ THINKING", overloaded:"⚠ OVERLOADED" };
  el.textContent = mapa[state] || state.toUpperCase();
  el.className = "system-state " + state;
}

function mostrarToast(msg, duracion = 3000) {
  const t = document.getElementById("lock-toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("visible");
  setTimeout(() => t.classList.remove("visible"), duracion);
}

function bloquearEntrada() {
  enviando = true;
  if (entradaTexto) entradaTexto.disabled = true;
  const btn = document.getElementById("btn-enviar-main");
  if (btn) btn.disabled = true;
}

function desbloquearEntrada() {
  enviando = false;
  if (entradaTexto) { entradaTexto.disabled = false; entradaTexto.focus(); }
  const btn = document.getElementById("btn-enviar-main");
  if (btn) btn.disabled = false;
}

// ══════════════════════════════════════════════════════════════════════════════
// ENVÍO DE MENSAJES
// ══════════════════════════════════════════════════════════════════════════════

function enviar() {
  const texto = entradaTexto.value.trim();
  if (!texto && archivosAdjuntos.length === 0) return;
  if (enviando) return;

  // Comandos especiales
  if (texto === "/test_mouse") {
    entradaTexto.value = "";
    agregarMensaje("usuario", "/test_mouse", "usuario");
    fetch("/api/test_mouse", { method: "POST" }).catch(() => {});
    return;
  }
  const matchEscribir = texto.match(/^\/escribir\s+(.+?):\s*(.+)$/i);
  if (matchEscribir) {
    entradaTexto.value = "";
    agregarMensaje("usuario", texto, "usuario");
    fetch("/api/escribir_en", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ app: matchEscribir[1].trim(), texto: matchEscribir[2].trim() }),
    }).catch(() => {});
    return;
  }
  const matchEntrenar = texto.match(/^\/entrenar\s*(.*)?$/i);
  if (matchEntrenar) {
    const nombre = (matchEntrenar[1] || "").trim();
    entradaTexto.value = "";
    agregarMensaje("usuario", texto, "usuario");
    fetch("/api/entrenar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre }),
    }).catch(() => {});
    _mostrarBarraGrabacion(nombre || "nueva habilidad");
    return;
  }
  if (texto === "/parar" || texto === "/stop") {
    entradaTexto.value = "";
    agregarMensaje("usuario", "/parar", "usuario");
    fetch("/api/parar_entrenamiento", { method: "POST" }).catch(() => {});
    _ocultarBarraGrabacion();
    return;
  }
  if (texto === "/habilidades" || texto === "/skills") {
    entradaTexto.value = "";
    agregarMensaje("usuario", "/habilidades", "usuario");
    fetch("/api/habilidades").then(r => r.json()).then(lista => {
      if (!lista || lista.length === 0) {
        agregarMensaje("ia", "No tengo habilidades entrenadas todavía. Usá /entrenar [nombre].", "ia");
        return;
      }
      let msg = "**Mis habilidades:**\n\n";
      lista.forEach(h => { msg += `• **${h.nombre}** — ${h.descripcion || "sin descripción"} (${h.veces_ejecutada}x)\n`; });
      agregarMensaje("ia", msg, "ia");
    }).catch(() => {});
    return;
  }
  const matchEjecutar = texto.match(/^\/ejecutar\s+(.+)$/i);
  if (matchEjecutar) {
    entradaTexto.value = "";
    agregarMensaje("usuario", texto, "usuario");
    fetch("/api/ejecutar_habilidad", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre: matchEjecutar[1].trim() }),
    }).catch(() => {});
    return;
  }

  if (bienvenida && bienvenida.style.display !== "none") bienvenida.style.display = "none";
  bloquearEntrada();
  if (texto) { agregarMensaje("usuario", texto, "usuario"); entradaTexto.value = ""; }

  if (archivosAdjuntos.length > 0) { procesarArchivos(texto); return; }

  // Construir mensaje con modificadores activos
  let mensajeFinal = texto;
  if (_razonamientoActivo) mensajeFinal = "[Pensá paso a paso antes de responder]\n" + mensajeFinal;
  if (_busquedaWebActiva)  mensajeFinal = "[BUSCAR_WEB]\n" + mensajeFinal;
  if (_investigacionActiva) mensajeFinal = "[INVESTIGACION_AVANZADA]\n" + mensajeFinal;

  mostrarPensando();
  actualizarSystemState("thinking");
  socket.emit("mensaje", { texto: mensajeFinal });
  archivosAdjuntos = [];
  renderizarChips();
}

function enviarSugerencia(texto) {
  if (entradaTexto) entradaTexto.value = texto;
  enviar();
}

function nuevoChat() {
  fetch("/api/nuevo_chat", { method: "POST" })
    .then(r => r.json())
    .then(() => {
      mensajesArea.innerHTML = "";
      if (bienvenida) {
        bienvenida.style.display = "flex";
        mensajesArea.appendChild(bienvenida);
      }
      cargarHistorial();
    }).catch(() => {});
}

function despertarAlisha() {
  fetch("/api/despertar", { method: "POST" }).catch(() => {});
  mostrarToast("Despertando a Alisha...");
}

// ══════════════════════════════════════════════════════════════════════════════
// ARCHIVOS Y UPLOADS
// ══════════════════════════════════════════════════════════════════════════════

function adjuntarArchivos(input) {
  const files = Array.from(input.files);
  files.forEach(file => {
    if (archivosAdjuntos.some(i => i.file.name === file.name && i.file.size === file.size)) return;
    if (file.size > 10 * 1024 * 1024) {
      agregarMensaje("ia", `${file.name} es muy pesado (máx 10 MB).`, "ia"); return;
    }
    const previewUrl = file.type.startsWith("image/") ? URL.createObjectURL(file) : null;
    archivosAdjuntos.push({ file, previewUrl, progress: 0, status: "pending", progressTimer: null });
  });
  input.value = "";
  renderizarChips();
}

function quitarArchivo(index) {
  const item = archivosAdjuntos[index];
  if (!item) return;
  if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
  archivosAdjuntos.splice(index, 1);
  renderizarChips();
}

function renderizarChips() {
  chipsArchivos.innerHTML = "";
  archivosAdjuntos.forEach((item, i) => {
    const file = item.file;
    const chip = document.createElement("div");
    chip.className = "chip-archivo";
    const label = document.createElement("div");
    label.className = "chip-label";
    label.textContent = file.name.length > 22 ? file.name.slice(0, 22) + "…" : file.name;
    chip.appendChild(label);
    if (item.previewUrl) {
      const thumb = document.createElement("img");
      thumb.className = "chip-preview";
      thumb.src = item.previewUrl;
      chip.appendChild(thumb);
    }
    const info = document.createElement("div");
    info.className = "chip-info";
    info.textContent = `${(file.size / 1024).toFixed(1)} KB`;
    chip.appendChild(info);
    if (item.status === "uploading") {
      const pw = document.createElement("div");
      pw.className = "progress-container";
      const pb = document.createElement("div");
      pb.className = "file-progress-bar";
      pb.style.width = `${item.progress}%`;
      pw.appendChild(pb);
      chip.appendChild(pw);
    }
    const removeBtn = document.createElement("button");
    removeBtn.textContent = "✕";
    removeBtn.onclick = () => quitarArchivo(i);
    chip.appendChild(removeBtn);
    chipsArchivos.appendChild(chip);
  });
}

function startArchivoProgress(index) {
  const item = archivosAdjuntos[index];
  if (!item) return;
  item.status = "uploading"; item.progress = 10;
  if (item.progressTimer) clearInterval(item.progressTimer);
  item.progressTimer = setInterval(() => {
    if (!item || item.progress >= 90) return;
    item.progress = Math.min(90, item.progress + Math.random() * 10);
    renderizarChips();
  }, 400);
  renderizarChips();
}

function finishArchivoProgress(index) {
  const item = archivosAdjuntos[index];
  if (!item) return;
  if (item.progressTimer) { clearInterval(item.progressTimer); item.progressTimer = null; }
  item.progress = 100; item.status = "done";
  renderizarChips();
}

async function procesarArchivos(pregunta) {
  if (archivosAdjuntos.length === 0) { desbloquearEntrada(); return; }
  actualizarEstado("curiosidad");
  mostrarPensando();
  for (let i = 0; i < archivosAdjuntos.length; i++) {
    const item = archivosAdjuntos[i];
    const formData = new FormData();
    formData.append("file", item.file);
    formData.append("pregunta", pregunta || "");
    startArchivoProgress(i);
    try {
      const resp = await fetch("/api/upload", { method: "POST", body: formData });
      const data = await resp.json();
      finishArchivoProgress(i);
      quitarPensando();
      // Si es imagen, mostrarla inline
      if (item.previewUrl) {
        const row = document.createElement("div");
        row.className = "mensaje-row ia";
        row.innerHTML = `<div class="msg-nombre">${nombreIA ? nombreIA.textContent : "Alisha"}</div>`;
        const burbuja = document.createElement("div");
        burbuja.className = "burbuja ia";
        burbuja.innerHTML = renderizarContenido(data.resultado || data.error || "Sin respuesta.");
        aplicarKatex(burbuja);
        row.appendChild(burbuja);
        mensajesArea.appendChild(row);
        scrollAbajo();
      } else {
        agregarMensaje("ia", data.resultado || data.error || "Sin respuesta.", "ia");
      }
    } catch(e) {
      finishArchivoProgress(i);
      quitarPensando();
      agregarMensaje("ia", `Error procesando ${item.file.name}.`, "ia");
    }
  }
  archivosAdjuntos = [];
  renderizarChips();
  desbloquearEntrada();
}

// ══════════════════════════════════════════════════════════════════════════════
// MENÚ DE ADJUNTOS
// ══════════════════════════════════════════════════════════════════════════════

function toggleMenuAdjuntos(event) {
  event.stopPropagation();
  const menu = document.getElementById("menu-adjuntos");
  if (!menu) return;
  const visible = menu.style.display !== "none";
  menu.style.display = visible ? "none" : "block";
}

function cerrarMenuAdjuntos() {
  const menu = document.getElementById("menu-adjuntos");
  if (menu) menu.style.display = "none";
}

// Cerrar menú al hacer click fuera
document.addEventListener("click", (e) => {
  const menu = document.getElementById("menu-adjuntos");
  const btn  = document.querySelector(".btn-attach");
  if (menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) {
    menu.style.display = "none";
  }
});

function toggleRazonamiento() {
  _razonamientoActivo = !_razonamientoActivo;
  const pill = document.getElementById("toggle-razonamiento");
  if (pill) { pill.textContent = _razonamientoActivo ? "ON" : "OFF"; pill.className = "toggle-pill " + (_razonamientoActivo ? "on" : "off"); }
  mostrarToast(_razonamientoActivo ? "🧠 Razonamiento activado" : "🧠 Razonamiento desactivado");
}

function toggleBusquedaWeb() {
  _busquedaWebActiva = !_busquedaWebActiva;
  const pill = document.getElementById("toggle-busqueda");
  if (pill) { pill.textContent = _busquedaWebActiva ? "ON" : "OFF"; pill.className = "toggle-pill " + (_busquedaWebActiva ? "on" : "off"); }
  mostrarToast(_busquedaWebActiva ? "🔍 Búsqueda web activada" : "🔍 Búsqueda web desactivada");
}

function toggleInvestigacion() {
  _investigacionActiva = !_investigacionActiva;
  const pill = document.getElementById("toggle-investigacion");
  if (pill) { pill.textContent = _investigacionActiva ? "ON" : "OFF"; pill.className = "toggle-pill " + (_investigacionActiva ? "on" : "off"); }
  mostrarToast(_investigacionActiva ? "📊 Investigación avanzada activada" : "📊 Investigación avanzada desactivada");
}

function mostrarArchivosRecientes() {
  cerrarMenuAdjuntos();
  // Mostrar los últimos archivos del historial de sesión (localStorage)
  const recientes = JSON.parse(localStorage.getItem("alisha_archivos_recientes") || "[]");
  if (recientes.length === 0) { mostrarToast("No hay archivos recientes."); return; }
  agregarMensaje("ia", "**Archivos recientes:**\n" + recientes.map(f => `• ${f}`).join("\n"), "ia");
}

function mostrarProyectos() {
  cerrarMenuAdjuntos();
  mostrarToast("📁 Proyectos — próximamente");
}

// ══════════════════════════════════════════════════════════════════════════════
// GENERACIÓN DE IMÁGENES (Imagen 3 de Google)
// ══════════════════════════════════════════════════════════════════════════════

function abrirGeneradorImagen() {
  cerrarMenuAdjuntos();
  const modal = document.getElementById("modal-imagen");
  if (modal) { modal.style.display = "flex"; document.getElementById("imagen-prompt").focus(); }
}

function cerrarModalImagen() {
  const modal = document.getElementById("modal-imagen");
  if (modal) modal.style.display = "none";
  const preview = document.getElementById("imagen-preview");
  if (preview) { preview.style.display = "none"; preview.innerHTML = ""; }
  const input = document.getElementById("imagen-prompt");
  if (input) input.value = "";
}

async function generarImagen() {
  const promptEl = document.getElementById("imagen-prompt");
  const btnEl    = document.getElementById("btn-generar-texto");
  const preview  = document.getElementById("imagen-preview");
  if (!promptEl || !promptEl.value.trim()) { mostrarToast("Escribí una descripción primero."); return; }

  const prompt = promptEl.value.trim();
  if (btnEl) btnEl.textContent = "⟳ Generando...";
  document.querySelector(".btn-generar-imagen").disabled = true;

  try {
    const resp = await fetch("/api/generar_imagen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await resp.json();

    if (data.error) { mostrarToast("Error: " + data.error); return; }

    // Mostrar preview en el modal
    if (preview && data.imagen_base64) {
      preview.style.display = "block";
      preview.innerHTML = `
        <img src="data:image/png;base64,${data.imagen_base64}" alt="${prompt}" style="max-width:100%;border-radius:4px;margin-bottom:8px;">
        <button class="btn-descargar-imagen" onclick="descargarImagen('${data.imagen_base64}', '${prompt.slice(0,20)}')">⬇ Descargar</button>
        <button class="btn-descargar-imagen" style="margin-left:8px" onclick="enviarImagenAlChat('${data.imagen_base64}', '${prompt.replace(/'/g,"\\'")}')">💬 Enviar al chat</button>`;
    }
  } catch(e) {
    mostrarToast("No se pudo generar la imagen. Verificá la API key de Google.");
  } finally {
    if (btnEl) btnEl.textContent = "✦ Generar";
    document.querySelector(".btn-generar-imagen").disabled = false;
  }
}

function descargarImagen(base64, nombre) {
  const a = document.createElement("a");
  a.href = "data:image/png;base64," + base64;
  a.download = (nombre || "imagen") + ".png";
  a.click();
}

function enviarImagenAlChat(base64, prompt) {
  cerrarModalImagen();
  // Mostrar imagen inline en el chat
  const row = document.createElement("div");
  row.className = "mensaje-row ia";
  row.innerHTML = `<div class="msg-nombre">${nombreIA ? nombreIA.textContent : "Alisha"}</div>`;
  const burbuja = document.createElement("div");
  burbuja.className = "burbuja ia";
  burbuja.innerHTML = `<p>Acá está tu imagen: <em>${prompt}</em></p>
    <img src="data:image/png;base64,${base64}" class="chat-image" alt="${prompt}">
    <button class="btn-descargar-imagen" onclick="descargarImagen('${base64}','${prompt.slice(0,20)}')">⬇ Descargar</button>`;
  row.appendChild(burbuja);
  mensajesArea.appendChild(row);
  scrollAbajo();
}

// ══════════════════════════════════════════════════════════════════════════════
// DRAG & DROP
// ══════════════════════════════════════════════════════════════════════════════

const dragOverlay = document.getElementById("drag-overlay");

document.addEventListener("dragenter", (e) => {
  if (e.dataTransfer.types.includes("Files")) {
    e.preventDefault();
    if (dragOverlay) dragOverlay.style.display = "flex";
  }
});
document.addEventListener("dragleave", (e) => {
  if (!e.relatedTarget || e.relatedTarget === document.documentElement) {
    if (dragOverlay) dragOverlay.style.display = "none";
  }
});
document.addEventListener("dragover", (e) => { e.preventDefault(); });
document.addEventListener("drop", (e) => {
  e.preventDefault();
  if (dragOverlay) dragOverlay.style.display = "none";
  const files = Array.from(e.dataTransfer.files);
  if (files.length === 0) return;
  files.forEach(file => {
    if (archivosAdjuntos.some(i => i.file.name === file.name)) return;
    const previewUrl = file.type.startsWith("image/") ? URL.createObjectURL(file) : null;
    archivosAdjuntos.push({ file, previewUrl, progress: 0, status: "pending", progressTimer: null });
  });
  renderizarChips();
  mostrarToast(`📎 ${files.length} archivo(s) adjuntado(s)`);
});

// Pegar imágenes con Ctrl+V
document.addEventListener("paste", (e) => {
  const items = Array.from(e.clipboardData.items || []);
  const imageItems = items.filter(i => i.type.startsWith("image/"));
  if (imageItems.length === 0) return;
  imageItems.forEach(item => {
    const file = item.getAsFile();
    if (!file) return;
    const renamedFile = new File([file], `pegado_${Date.now()}.png`, { type: file.type });
    const previewUrl = URL.createObjectURL(renamedFile);
    archivosAdjuntos.push({ file: renamedFile, previewUrl, progress: 0, status: "pending", progressTimer: null });
  });
  renderizarChips();
  mostrarToast("📋 Imagen pegada");
});

// ══════════════════════════════════════════════════════════════════════════════
// AUDIO / MIC
// ══════════════════════════════════════════════════════════════════════════════

function toggleMic() { grabando ? stopRecording() : startRecording(); }

async function startRecording() {
  if (!navigator.mediaDevices) { mostrarToast("Tu navegador no soporta grabación."); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.onstop = () => { stream.getTracks().forEach(t => t.stop()); enviarAudio(); };
    mediaRecorder.start();
    grabando = true;
    const btn = document.getElementById("mic-button");
    if (btn) btn.classList.add("grabando");
  } catch(e) { mostrarToast("No se pudo acceder al micrófono."); }
}

function stopRecording() {
  if (mediaRecorder && grabando) mediaRecorder.stop();
  grabando = false;
  const btn = document.getElementById("mic-button");
  if (btn) btn.classList.remove("grabando");
}

async function enviarAudio() {
  const blob = new Blob(audioChunks, { type: "audio/webm" });
  const formData = new FormData();
  formData.append("audio", blob, "upload.webm");
  agregarMensaje("usuario", "[Mensaje de voz]", "usuario");
  mostrarPensando();
  bloquearEntrada();
  try {
    const resp = await fetch("/api/audio", { method: "POST", body: formData });
    const data = await resp.json();
    quitarPensando();
    if (data.error) { agregarMensaje("ia", data.error, "ia"); }
    else {
      if (data.texto) agregarMensaje("usuario", data.texto, "usuario");
      agregarMensaje("ia", data.respuesta || "Sin respuesta.", "ia");
      if (data.estado_emocional) actualizarEstado(data.estado_emocional);
    }
  } catch(e) { quitarPensando(); agregarMensaje("ia", "Error enviando el audio.", "ia"); }
  desbloquearEntrada();
}

// ══════════════════════════════════════════════════════════════════════════════
// HISTORIAL Y POLLING
// ══════════════════════════════════════════════════════════════════════════════

async function cargarHistorial() {
  try {
    const resp = await fetch("/api/sesiones");
    const sesiones = await resp.json();
    const lista = document.getElementById("historial-lista");
    if (!lista || !sesiones) return;
    lista.innerHTML = "";
    sesiones.slice(0, 30).forEach(s => {
      const div = document.createElement("div");
      div.className = "historial-item";
      div.textContent = s.titulo || "Conversación";
      div.title = s.titulo || "";
      div.onclick = () => cargarSesion(s.id);
      lista.appendChild(div);
    });
  } catch(e) {}
}

async function cargarSesion(sessionId) {
  try {
    const resp = await fetch(`/api/sesion/${sessionId}/mensajes`);
    const msgs = await resp.json();
    mensajesArea.innerHTML = "";
    msgs.forEach(m => {
      agregarMensaje(m.rol === "user" ? "usuario" : "ia", m.contenido, m.rol === "user" ? "usuario" : "ia");
    });
    // Marcar activo
    document.querySelectorAll(".historial-item").forEach(el => el.classList.remove("activo"));
  } catch(e) {}
}

async function actualizarStatus() {
  try {
    const resp = await fetch("/api/status");
    const data = await resp.json();
    if (data.dopamina != null) {
      document.getElementById("barra-dopamina").style.width = `${Math.round(data.dopamina * 100)}%`;
    }
    if (data.energia != null) {
      document.getElementById("barra-energia").style.width = `${Math.round(data.energia)}%`;
    }
    if (data.media_actual && data.media_actual.title) {
      const m = data.media_actual;
      const text = document.getElementById("media-sync-text");
      const icon = document.getElementById("media-sync-icon");
      const bar  = document.getElementById("media-sync-bar");
      if (text) text.textContent = m.artist ? `${m.title} — ${m.artist}` : m.title;
      if (icon) icon.textContent = m.app === "Spotify" ? "♪" : "▶";
      if (bar)  bar.classList.add("visible");
    } else {
      const bar = document.getElementById("media-sync-bar");
      if (bar) bar.classList.remove("visible");
    }
    // Trust widget
    if (data.trust) {
      const t = data.trust;
      const label = document.getElementById("trust-label");
      const xp    = document.getElementById("trust-xp");
      const bar   = document.getElementById("trust-bar");
      const tasks = document.getElementById("trust-tasks");
      if (label) label.textContent = `${t.emoji || "🌱"} ${t.nombre || "Aprendiz"}`;
      if (xp)    xp.textContent = `XP: ${t.xp || 0}`;
      if (bar)   bar.style.width = `${Math.round((t.progreso || 0) * 100)}%`;
      if (tasks) tasks.textContent = `${t.tareas_completadas || 0} tareas completadas`;
    }
  } catch(e) {}
}

// ══════════════════════════════════════════════════════════════════════════════
// BARRA DE GRABACIÓN DE HABILIDADES
// ══════════════════════════════════════════════════════════════════════════════

function _mostrarBarraGrabacion(nombre) {
  if (_barraGrabacion) _barraGrabacion.remove();
  _barraGrabacion = document.createElement("div");
  _barraGrabacion.id = "barra-grabacion";
  _barraGrabacion.style.cssText = `position:fixed;top:0;left:0;right:0;z-index:9998;
    background:rgba(255,80,80,0.12);border-bottom:2px solid rgba(255,80,80,0.5);
    padding:8px 20px;display:flex;align-items:center;gap:12px;
    font-size:12px;color:#ff8080;backdrop-filter:blur(8px);`;
  _barraGrabacion.innerHTML = `
    <span style="animation:blink-dot 1s step-end infinite;font-size:14px">⏺</span>
    <span>GRABANDO: <strong>${nombre}</strong></span>
    <span id="grabacion-pasos" style="opacity:0.6">0 pasos</span>
    <button onclick="fetch('/api/parar_entrenamiento',{method:'POST'});_ocultarBarraGrabacion();"
      style="margin-left:auto;background:rgba(255,80,80,0.15);border:1px solid rgba(255,80,80,0.4);
             color:#ff8080;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;">
      ⏹ Parar
    </button>`;
  document.body.appendChild(_barraGrabacion);
}

function _ocultarBarraGrabacion() {
  if (_barraGrabacion) { _barraGrabacion.remove(); _barraGrabacion = null; }
}

// ══════════════════════════════════════════════════════════════════════════════
// INICIALIZACIÓN
// ══════════════════════════════════════════════════════════════════════════════

// Cargar historial al inicio
cargarHistorial();

// Polling de estado cada 3s
setInterval(actualizarStatus, 3000);
actualizarStatus();

// Foco en el input
if (entradaTexto) entradaTexto.focus();
