/**
 * app.js — Lógica del chat: SocketIO, mensajes, archivos, chibi.
 */

const socket = io({
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 2000,   // máximo 2s entre intentos
  timeout: 20000,
  transports: ["websocket", "polling"],  // websocket primero, polling como fallback
});

// ── Overlay de reconexión ─────────────────────────────────────────────────────
let _reconectando = false;
let _overlayEl = null;

function _mostrarOverlayReconexion() {
  if (_reconectando) return;
  _reconectando = true;
  if (!_overlayEl) {
    _overlayEl = document.createElement("div");
    _overlayEl.id = "overlay-reconexion";
    _overlayEl.style.cssText = `
      position: fixed; inset: 0; z-index: 99999;
      background: rgba(13,10,20,0.85);
      backdrop-filter: blur(8px);
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      gap: 16px; color: #00e5ff; font-family: 'Segoe UI', sans-serif;
    `;
    _overlayEl.innerHTML = `
      <div style="font-size:32px;animation:spin 1s linear infinite">⟳</div>
      <div style="font-size:16px;font-weight:600">Reconectando con Alisha...</div>
      <div style="font-size:12px;color:rgba(0,229,255,0.6)" id="overlay-contador">Intentando...</div>
      <style>@keyframes spin{to{transform:rotate(360deg)}}</style>
    `;
    document.body.appendChild(_overlayEl);
  }
  _overlayEl.style.display = "flex";
}

function _ocultarOverlayReconexion() {
  _reconectando = false;
  if (_overlayEl) _overlayEl.style.display = "none";
}

let _intentoReconexion = 0;

socket.on("reconnect_attempt", (n) => {
  _intentoReconexion = n;
  _mostrarOverlayReconexion();
  const el = document.getElementById("overlay-contador");
  if (el) el.textContent = `Intento ${n}... (el servidor puede estar reiniciándose)`;
});

socket.on("reconnect", () => {
  _intentoReconexion = 0;
  _ocultarOverlayReconexion();
  console.log("✓ Reconectado al servidor");
});

socket.on("reconnect_failed", () => {
  const el = document.getElementById("overlay-contador");
  if (el) el.textContent = "No se pudo reconectar. Recargá la página manualmente.";
});

// Reset automático si se pierde la conexión
socket.on("disconnect", (reason) => {
  quitarPensando();
  desbloquearEntrada();
  if (reason !== "io client disconnect") {
    // Desconexión inesperada — mostrar overlay
    _mostrarOverlayReconexion();
  }
});

socket.on("connect_error", () => {
  quitarPensando();
  desbloquearEntrada();
  _mostrarOverlayReconexion();
});

socket.on("connect", () => {
  _ocultarOverlayReconexion();
  document.getElementById("banner-despertar").style.display = "none";
});
let estadoActual = "neutral";
let archivosAdjuntos = [];
let enviando = false;

// ── Elementos DOM ──
const mensajesArea  = document.getElementById("mensajes-area");
const entradaTexto  = document.getElementById("entrada-texto");
const btnEnviar     = document.querySelector(".btn-enviar");
const chipsArchivos = document.getElementById("chips-archivos");
const estadoBadge   = document.getElementById("estado-badge");
const nombreIA      = document.getElementById("nombre-ia");
const nombreSidebar = document.getElementById("nombre-usuario-sidebar");
const bienvenida    = document.getElementById("bienvenida");

// ── Inicialización ──
socket.on("connect", () => {
  console.log("Conectado al servidor");
});

// ── Eventos de entrenamiento ──────────────────────────────────────────────────

let _barraGrabacion = null;
let _barraProgreso  = null;

function _mostrarBarraGrabacion(nombre) {
  if (_barraGrabacion) _barraGrabacion.remove();
  _barraGrabacion = document.createElement("div");
  _barraGrabacion.id = "barra-grabacion";
  _barraGrabacion.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; z-index: 9998;
    background: rgba(255,80,80,0.15); border-bottom: 2px solid rgba(255,80,80,0.6);
    padding: 8px 20px; display: flex; align-items: center; gap: 12px;
    font-size: 13px; color: #ff8080; font-family: 'Consolas', monospace;
    backdrop-filter: blur(8px);
  `;
  _barraGrabacion.innerHTML = `
    <span style="animation:blink 1s step-end infinite;font-size:16px">⏺</span>
    <span>GRABANDO: <strong>${nombre}</strong></span>
    <span id="grabacion-pasos" style="color:rgba(255,128,128,0.7)">0 pasos</span>
    <button onclick="fetch('/api/parar_entrenamiento',{method:'POST'});_ocultarBarraGrabacion();"
      style="margin-left:auto;background:rgba(255,80,80,0.2);border:1px solid rgba(255,80,80,0.5);
             color:#ff8080;padding:4px 12px;border-radius:6px;cursor:pointer;font-size:12px;">
      ⏹ Parar
    </button>
  `;
  document.body.appendChild(_barraGrabacion);
}

function _ocultarBarraGrabacion() {
  if (_barraGrabacion) { _barraGrabacion.remove(); _barraGrabacion = null; }
}

socket.on("progreso_grabacion", (data) => {
  const el = document.getElementById("grabacion-pasos");
  if (el) el.textContent = `${data.paso} pasos`;
});

socket.on("progreso_workflow", (data) => {
  // Mostrar/actualizar barra de progreso de ejecución
  if (!_barraProgreso) {
    _barraProgreso = document.createElement("div");
    _barraProgreso.id = "barra-progreso-workflow";
    _barraProgreso.style.cssText = `
      position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%);
      background: rgba(13,10,20,0.9); border: 1px solid rgba(0,229,255,0.4);
      border-radius: 12px; padding: 12px 20px; z-index: 9997;
      min-width: 280px; text-align: center; backdrop-filter: blur(10px);
    `;
    document.body.appendChild(_barraProgreso);
  }

  const pct = Math.round((data.paso_actual / data.total) * 100);
  _barraProgreso.innerHTML = `
    <div style="font-size:11px;color:rgba(0,229,255,0.7);letter-spacing:1px;margin-bottom:6px">
      WORKING — Paso ${data.paso_actual}/${data.total}
    </div>
    <div style="background:rgba(255,255,255,0.08);border-radius:999px;height:4px;overflow:hidden;margin-bottom:6px">
      <div style="width:${pct}%;height:100%;background:linear-gradient(90deg,#00e5ff,#b388ff);border-radius:999px;transition:width 0.3s"></div>
    </div>
    <div style="font-size:12px;color:rgba(255,255,255,0.6)">${data.descripcion || ''}</div>
  `;

  if (data.completado) {
    setTimeout(() => {
      if (_barraProgreso) { _barraProgreso.remove(); _barraProgreso = null; }
    }, 2000);
  }
});

socket.on("habilidad_guardada", (data) => {
  // Agregar la nueva habilidad a la barra lateral
  const lista = document.getElementById("historial-lista");
  if (lista) {
    const div = document.createElement("div");
    div.className = "historial-item";
    div.style.borderLeft = "2px solid rgba(0,229,255,0.5)";
    div.textContent = `⚡ ${data.nombre}`;
    div.title = data.descripcion || data.nombre;
    div.onclick = () => {
      fetch("/api/ejecutar_habilidad", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre: data.nombre }),
      });
    };
    lista.insertBefore(div, lista.firstChild);
  }
});

// ── Propuesta de acción de Alisha — botones de confirmación ─────────────────
socket.on("propuesta_accion", (data) => {
  if (!data || !data.mensaje) return;

  // Crear burbuja especial con botones
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
  burbuja.style.cssText = "border-color: rgba(0,229,255,0.5); background: rgba(0,229,255,0.06);";

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
      ? "background:rgba(0,229,255,0.2);border:1px solid rgba(0,229,255,0.5);color:#00e5ff;padding:6px 14px;border-radius:8px;cursor:pointer;font-size:12px;font-weight:600;"
      : "background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.5);padding:6px 14px;border-radius:8px;cursor:pointer;font-size:12px;";

    btn.onclick = () => {
      // Deshabilitar todos los botones
      btnRow.querySelectorAll("button").forEach(b => b.disabled = true);
      btnRow.style.opacity = "0.5";

      if (esSi) {
        agregarMensaje("usuario", label, "usuario");
        // Ejecutar la acción confirmada
        fetch("/api/confirmar_accion", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            accion_id: data.accion_id,
            contexto: data.contexto || {},
          }),
        }).catch(e => console.error("Error confirmando acción:", e));
      } else {
        agregarMensaje("usuario", "No gracias", "usuario");
        agregarMensaje("ia", "Dale, sin problema. Avisame si necesitás algo.", "ia");
        // Registrar rechazo si es sugerencia proactiva (aprendizaje gradual)
        if (data.accion_id && data.accion_id.startsWith("sugerencia_")) {
          fetch("/api/sugerencia/rechazar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              accion_id: data.accion_id,
              tipo: (data.contexto || {}).tipo || "",
            }),
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
let _streamBuffer = "";
let _streamEstado = "neutral";

socket.on("pensando", (data) => {
  if (data.activo) {
    mostrarPensando();
    // Badge muestra THINKING mientras procesa
    estadoBadge.textContent = "THINKING";
    estadoBadge.className = "estado-badge curiosidad";
  }
});

socket.on("respuesta_inicio", (data) => {
  _streamBuffer = "";
  _streamEstado = data.estado_emocional || "neutral";
  quitarPensando();
  // Crear burbuja de streaming
  _crearBurbujaStreaming();
});

socket.on("respuesta_chunk", (data) => {
  _streamBuffer += data.chunk;
  _actualizarBurbujaStreaming(_streamBuffer);
});

socket.on("respuesta_fin", (data) => {
  // Finalizar burbuja con texto completo
  _finalizarBurbujaStreaming(data.texto || _streamBuffer, _streamEstado);
  if (data.estado_emocional) actualizarEstado(data.estado_emocional);
  desbloquearEntrada();
  cargarHistorial();
});

// Compatibilidad con respuesta directa (sin streaming)
socket.on("respuesta", (data) => {
  quitarPensando();
  agregarMensaje("ia", data.texto || "...", "ia");
  if (data.estado_emocional) actualizarEstado(data.estado_emocional);
  desbloquearEntrada();
  cargarHistorial();
});

let _streamMsgEl = null;

function _crearBurbujaStreaming() {
  const area = document.getElementById("mensajes-area");
  if (!area) return;
  _streamMsgEl = document.createElement("div");
  _streamMsgEl.className = "mensaje ia streaming";
  _streamMsgEl.innerHTML = '<div class="burbuja ia"><span class="stream-text"></span><span class="cursor">▌</span></div>';
  area.appendChild(_streamMsgEl);
  area.scrollTop = area.scrollHeight;
}

function _actualizarBurbujaStreaming(texto) {
  if (!_streamMsgEl) return;
  const span = _streamMsgEl.querySelector(".stream-text");
  if (span) span.textContent = texto;
  const area = document.getElementById("mensajes-area");
  if (area) area.scrollTop = area.scrollHeight;
}

function _finalizarBurbujaStreaming(texto, estado) {
  if (_streamMsgEl) {
    _streamMsgEl.remove();
    _streamMsgEl = null;
  }
  const msg = agregarMensaje("ia", texto, estado || "ia");
  // KaTeX ya se aplica dentro de agregarMensaje
}

// ── Chibi ──
const ESTADOS_CHIBI = ["neutral","alegría","entusiasmo","curiosidad","preocupación","frustración","cansancio"];
const _spriteCache = {};

function _cargarSprite(estado) {
  if (_spriteCache[estado] !== undefined) return _spriteCache[estado];
  const img = new Image();
  img.onload  = () => { _spriteCache[estado] = img; renderChibi(estado); };
  img.onerror = () => { _spriteCache[estado] = null; }; // null = usar canvas
  img.src = `/static/img/chibi/${estado}.png`;
  _spriteCache[estado] = "loading";
  return "loading";
}

function renderChibi(estado) {
  const sprite = _spriteCache[estado];
  const circle = document.getElementById("chibi-circle");

  // Si no hay elementos chibi en el DOM, salir silenciosamente
  if (!circle && !chibiCanvas) return;

  // Si hay sprite PNG, mostrarlo
  if (sprite && sprite !== "loading") {
    if (chibiCanvas) chibiCanvas.style.display = "none";
    if (circle) {
      let imgEl = circle.querySelector("img.chibi-sprite");
      if (!imgEl) {
        imgEl = document.createElement("img");
        imgEl.className = "chibi-sprite";
        imgEl.style.cssText = "width:100%;height:100%;object-fit:contain;position:absolute;top:0;left:0;";
        circle.appendChild(imgEl);
      }
      imgEl.src = sprite.src;
      imgEl.style.display = "block";
    }
    return;
  }

  // Fallback: canvas dibujado con código
  if (circle) {
    const imgEl = circle.querySelector("img.chibi-sprite");
    if (imgEl) imgEl.style.display = "none";
  }
  if (chibiCanvas) {
    chibiCanvas.style.display = "block";
    drawChibi(chibiCanvas, estado);
  }
}

function actualizarEstado(estado) {
  if (estado === estadoActual) return;
  estadoActual = estado;

  // Mapear estado emocional a texto tech para el badge
  const estadoTexto = {
    "neutral":      "IDLE",
    "alegría":      "HAPPY",
    "entusiasmo":   "ACTIVE",
    "curiosidad":   "THINKING",
    "preocupación": "ALERT",
    "frustración":  "ERROR",
    "cansancio":    "LOW",
  };

  estadoBadge.textContent = estadoTexto[estado] || estado.toUpperCase();
  estadoBadge.className = "estado-badge " + estado;
}

// Precargar todos los sprites al inicio
ESTADOS_CHIBI.forEach(_cargarSprite);

// Dibujar chibi inicial
renderChibi("neutral");

// ── Renderizado de Markdown + KaTeX ──────────────────────────────────────────
function renderizarContenido(texto) {
  if (!texto) return "";

  // Configurar marked para renderizado seguro
  if (typeof marked !== "undefined") {
    marked.setOptions({
      breaks: true,
      gfm: true,
    });
  }

  // Renderizar Markdown
  let html = texto;
  if (typeof marked !== "undefined") {
    try {
      html = marked.parse(texto);
    } catch(e) {
      html = texto.replace(/\n/g, "<br>");
    }
  } else {
    html = texto.replace(/\n/g, "<br>");
  }

  return html;
}

function aplicarKatex(elemento) {
  if (typeof renderMathInElement !== "undefined") {
    try {
      renderMathInElement(elemento, {
        delimiters: [
          {left: "$$", right: "$$", display: true},
          {left: "$", right: "$", display: false},
          {left: "\\[", right: "\\]", display: true},
          {left: "\\(", right: "\\)", display: false},
        ],
        throwOnError: false,
        output: "html",
      });
    } catch(e) {}
  }
  // Highlight.js para bloques de código
  if (typeof hljs !== "undefined") {
    elemento.querySelectorAll("pre code").forEach(block => {
      try { hljs.highlightElement(block); } catch(e) {}
    });
  }
}

// ── Mensajes ──
function agregarMensaje(tipo, texto, clase) {
  if (bienvenida) bienvenida.style.display = "none";

  const row = document.createElement("div");
  row.className = `mensaje-row ${tipo}`;
  if (clase === "pensando") row.id = "burbuja-pensando";

  const nombre = document.createElement("div");
  nombre.className = "msg-nombre";
  nombre.textContent = tipo === "ia" ? (nombreIA.textContent || "IA") : "Tú";
  row.appendChild(nombre);

  const burbuja = document.createElement("div");
  burbuja.className = `burbuja ${clase}`;

  if (tipo === "ia" && clase !== "pensando") {
    // Renderizar Markdown + KaTeX para mensajes de Alisha
    burbuja.innerHTML = renderizarContenido(texto);
    aplicarKatex(burbuja);
  } else {
    burbuja.textContent = texto;
  }

  row.appendChild(burbuja);
  mensajesArea.appendChild(row);
  scrollAbajo();
  return row;
}

function quitarPensando() {
  const el = document.getElementById("burbuja-pensando");
  if (el) el.remove();
}

function mostrarPensando() {
  quitarPensando();
  const row = document.createElement("div");
  row.className = "mensaje-row ia";
  row.id = "burbuja-pensando";
  row.innerHTML = `
    <div class="msg-nombre">${nombreIA ? nombreIA.textContent : "Alisha"}</div>
    <div class="burbuja pensando">
      <span class="dot-flashing"></span>
    </div>`;
  mensajesArea.appendChild(row);
  scrollAbajo();
}

function scrollAbajo() {
  setTimeout(() => {
    mensajesArea.scrollTop = mensajesArea.scrollHeight;
  }, 50);
}

// ── Envío de mensajes — función única ──
function enviar() {
  const texto = entradaTexto.value.trim();
  if (!texto && archivosAdjuntos.length === 0) return;
  if (enviando) return;

  // ── Comandos especiales ───────────────────────────────────────────────────
  if (texto === "/test_mouse") {
    entradaTexto.value = "";
    agregarMensaje("usuario", "/test_mouse", "usuario");
    agregarMensaje("ia", "Iniciando test de mouse... mirá el cursor.", "ia");
    fetch("/api/test_mouse", { method: "POST" }).catch(() => {});
    return;
  }

  // Comando: escribir en app — "/escribir bloc de notas: hola mundo"
  const matchEscribir = texto.match(/^\/escribir\s+(.+?):\s*(.+)$/i);
  if (matchEscribir) {
    const appDest = matchEscribir[1].trim();
    const textoEscribir = matchEscribir[2].trim();
    entradaTexto.value = "";
    agregarMensaje("usuario", texto, "usuario");
    fetch("/api/escribir_en", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ app: appDest, texto: textoEscribir }),
    }).catch(() => {});
    return;
  }

  // ── Comandos de entrenamiento ─────────────────────────────────────────────
  // /entrenar [nombre] → inicia grabación
  const matchEntrenar = texto.match(/^\/entrenar\s*(.*)?$/i);
  if (matchEntrenar) {
    const nombre = (matchEntrenar[1] || "").trim();
    entradaTexto.value = "";
    agregarMensaje("usuario", texto, "usuario");
    fetch("/api/entrenar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre }),
    }).catch(() => {});
    _mostrarBarraGrabacion(nombre || "nueva habilidad");
    return;
  }

  // /parar → detiene grabación
  if (texto === "/parar" || texto === "/stop") {
    entradaTexto.value = "";
    agregarMensaje("usuario", "/parar", "usuario");
    fetch("/api/parar_entrenamiento", { method: "POST" }).catch(() => {});
    _ocultarBarraGrabacion();
    return;
  }

  // /habilidades → lista habilidades
  if (texto === "/habilidades" || texto === "/skills") {
    entradaTexto.value = "";
    agregarMensaje("usuario", "/habilidades", "usuario");
    fetch("/api/habilidades")
      .then(r => r.json())
      .then(lista => {
        if (!lista || lista.length === 0) {
          agregarMensaje("ia", "No tengo habilidades entrenadas todavía. Usá /entrenar [nombre] para enseñarme algo.", "ia");
          return;
        }
        let msg = "**Mis habilidades:**\n\n";
        lista.forEach(h => {
          msg += `• **${h.nombre}** — ${h.descripcion || "sin descripción"} (ejecutada ${h.veces_ejecutada} veces)\n`;
        });
        agregarMensaje("ia", msg, "ia");
      }).catch(() => {});
    return;
  }

  // /ejecutar [nombre] → ejecuta habilidad
  const matchEjecutar = texto.match(/^\/ejecutar\s+(.+)$/i);
  if (matchEjecutar) {
    const nombre = matchEjecutar[1].trim();
    entradaTexto.value = "";
    agregarMensaje("usuario", texto, "usuario");
    fetch("/api/ejecutar_habilidad", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre }),
    }).catch(() => {});
    return;
  }
  // Ocultar bienvenida al primer mensaje
  if (bienvenida && bienvenida.style.display !== "none") {
    bienvenida.style.display = "none";
  }

  bloquearEntrada();

  if (texto) {
    agregarMensaje("usuario", texto, "usuario");
    entradaTexto.value = "";
  }

  // Si hay archivos, procesarlos primero
  if (archivosAdjuntos.length > 0) {
    procesarArchivos(texto);
    return;
  }

  // Solo texto — mostrar "pensando" y emitir
  agregarMensaje("ia", "pensando...", "pensando");
  socket.emit("mensaje", { texto });
  archivosAdjuntos = [];
  renderizarChips();
}

// ── Archivos ──
function adjuntarArchivos(input) {
  const files = Array.from(input.files);
  files.forEach(file => {
    const alreadyAdded = archivosAdjuntos.some(item => item.file.name === file.name && item.file.size === file.size);
    if (alreadyAdded) return;

    if (file.size > 10 * 1024 * 1024) {
      agregarMensaje("ia", `El archivo ${file.name} es muy pesado. Por favor subí archivos menores a 10 MB.`, "error");
      return;
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
  if (item.previewUrl) {
    URL.revokeObjectURL(item.previewUrl);
  }
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
    label.innerHTML = `<span>📎 ${file.name.length > 20 ? file.name.slice(0, 20) + "…" : file.name}</span>`;
    chip.appendChild(label);

    if (item.previewUrl) {
      const thumb = document.createElement("img");
      thumb.className = "chip-preview";
      thumb.src = item.previewUrl;
      thumb.alt = file.name;
      chip.appendChild(thumb);
    }

    const info = document.createElement("div");
    info.className = "chip-info";
    info.textContent = `${(file.size / 1024).toFixed(1)} KB`;
    chip.appendChild(info);

    if (item.status === "uploading") {
      const progressWrapper = document.createElement("div");
      progressWrapper.className = "progress-container";
      const progressBar = document.createElement("div");
      progressBar.className = "file-progress-bar";
      progressBar.style.width = `${item.progress}%`;
      progressWrapper.appendChild(progressBar);
      chip.appendChild(progressWrapper);
    }

    const removeBtn = document.createElement("button");
    removeBtn.textContent = "✕";
    removeBtn.onclick = () => quitarArchivo(i);
    chip.appendChild(removeBtn);

    chipsArchivos.appendChild(chip);
  });
}

function setArchivoProgress(index, percent) {
  const item = archivosAdjuntos[index];
  if (!item) return;
  item.progress = Math.min(100, Math.max(0, percent));
  renderizarChips();
}

function startArchivoProgress(index) {
  const item = archivosAdjuntos[index];
  if (!item) return;
  item.status = "uploading";
  item.progress = 10;
  if (item.progressTimer) {
    clearInterval(item.progressTimer);
  }
  item.progressTimer = window.setInterval(() => {
    if (!item || item.progress >= 90) return;
    item.progress = Math.min(90, item.progress + Math.random() * 10);
    renderizarChips();
  }, 400);
  renderizarChips();
}

function finishArchivoProgress(index) {
  const item = archivosAdjuntos[index];
  if (!item) return;
  if (item.progressTimer) {
    clearInterval(item.progressTimer);
    item.progressTimer = null;
  }
  item.progress = 100;
  item.status = "done";
  renderizarChips();
}

let grabando = false;
let mediaRecorder = null;
let audioChunks = [];

function toggleMic() {
  if (grabando) {
    stopRecording();
  } else {
    startRecording();
  }
}

async function startRecording() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert("Tu navegador no soporta grabación de audio.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = event => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = () => {
      stream.getTracks().forEach(track => track.stop());
      enviarAudio();
    };

    mediaRecorder.start();
    grabando = true;
    document.getElementById("mic-button").textContent = "⏹️";
  } catch (error) {
    console.error(error);
    alert("No se pudo acceder al micrófono.");
  }
}

function stopRecording() {
  if (mediaRecorder && grabando) {
    mediaRecorder.stop();
  }
  grabando = false;
  document.getElementById("mic-button").textContent = "🎙️";
}

async function enviarAudio() {
  const blob = new Blob(audioChunks, { type: "audio/webm" });
  const formData = new FormData();
  formData.append("audio", blob, "upload.webm");

  agregarMensaje("usuario", "[Mensaje de voz]", "usuario");
  agregarMensaje("ia", "Transcribiendo audio...", "pensando");
  bloquearEntrada();

  try {
    const resp = await fetch("/api/audio", { method: "POST", body: formData });
    const data = await resp.json();
    quitarPensando();
    if (data.error) {
      agregarMensaje("ia", data.error, "error");
    } else {
      agregarMensaje("usuario", data.texto, "usuario");
      agregarMensaje("ia", data.respuesta || "Sin respuesta.", "ia");
      if (data.estado_emocional) actualizarEstado(data.estado_emocional);
    }
  } catch (e) {
    quitarPensando();
    agregarMensaje("ia", "Error enviando el audio.", "error");
  }

  desbloquearEntrada();
}

async function actualizarStatus() {
  try {
    const resp = await fetch("/api/status");
    const data = await resp.json();
    if (data.dopamina != null) {
      const width = Math.round(Math.min(100, Math.max(0, data.dopamina * 100)));
      document.getElementById("barra-dopamina").style.width = `${width}%`;
    }
    if (data.energia != null) {
      const width = Math.round(Math.min(100, Math.max(0, data.energia)));
      document.getElementById("barra-energia").style.width = `${width}%`;
    }
  } catch (e) {
    console.warn("No se pudo actualizar el estado:", e);
  }
}

// ── Media Sync — "Escuchando ahora" ──────────────────────────────────────────
async function actualizarMediaSync() {
  try {
    const resp = await fetch("/api/status");
    const data = await resp.json();

    const bar  = document.getElementById("media-sync-bar");
    const text = document.getElementById("media-sync-text");
    const icon = document.getElementById("media-sync-icon");

    if (data.media_actual && data.media_actual.title) {
      const m = data.media_actual;
      const label = m.artist
        ? `${m.title} — ${m.artist}`
        : m.title;
      text.textContent = label;
      icon.textContent = m.app === "Spotify" ? "🎵" : m.app === "YouTube" ? "▶️" : "🎶";
      bar.classList.add("visible");
    } else {
      bar.classList.remove("visible");
    }
  } catch (e) { /* fail-silent */ }
}

// ── LED de Cuna Virtual ───────────────────────────────────────────────────────
async function actualizarCunaLed() {
  try {
    const resp = await fetch("/api/agent/status");
    const data = await resp.json();
    const led = document.getElementById("cuna-led");
    if (!led) return;
    // LED activo si el AgentLoop está corriendo y hay actividad
    const activo = data.agent_loop === "running" &&
                   (data.current_state === "WORKING" || data.current_state === "THINKING");
    led.classList.toggle("activo", activo);
  } catch (e) { /* fail-silent */ }
}

async function procesarArchivos(pregunta) {
  if (archivosAdjuntos.length === 0) {
    desbloquearEntrada();
    return;
  }

  const previousEstado = estadoActual;
  actualizarEstado("curiosidad");
  agregarMensaje("ia", "Analizando archivo...", "pensando");

  for (let i = 0; i < archivosAdjuntos.length; i++) {
    const item = archivosAdjuntos[i];
    const file = item.file;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("pregunta", pregunta || "");

    startArchivoProgress(i);

    try {
      const resp = await fetch("/api/upload", { method: "POST", body: formData });
      const data = await resp.json();
      finishArchivoProgress(i);
      quitarPensando();
      agregarMensaje("ia", data.resultado || data.error || "Sin respuesta.", data.error ? "error" : "ia");
    } catch (e) {
      finishArchivoProgress(i);
      quitarPensando();
      agregarMensaje("ia", "Error al procesar el archivo.", "error");
    }
  }

  archivosAdjuntos.forEach(item => {
    if (item.previewUrl) {
      URL.revokeObjectURL(item.previewUrl);
    }
  });
  archivosAdjuntos = [];
  renderizarChips();
  actualizarEstado(previousEstado || "neutral");
  desbloquearEntrada();
}

// ── Nuevo chat ──
function nuevoChat() {
  fetch("/api/nuevo_chat", { method: "POST" })
    .then(r => r.json())
    .then(data => {
      // Limpiar área de mensajes
      mensajesArea.innerHTML = `
        <div class="bienvenida" id="bienvenida">
          <div class="bienvenida-emoji">🌸</div>
          <h2>¡Hola! Soy Alisha</h2>
          <p>Tu asistente IA con personalidad. Escribime algo para empezar a conversar.</p>
          <div class="sugerencias">
            <button class="sugerencia" onclick="enviarSugerencia('¿Cómo estás hoy?')">¿Cómo estás?</button>
            <button class="sugerencia" onclick="enviarSugerencia('Cuéntame algo interesante')">Cuéntame algo</button>
            <button class="sugerencia" onclick="enviarSugerencia('¿Qué puedes hacer?')">¿Qué puedes hacer?</button>
          </div>
        </div>`;
      actualizarEstado("neutral");
      // Marcar la nueva sesión como activa
      if (data.session_id) _sesionActiva = data.session_id;
      // Recargar sidebar para mostrar la nueva sesión
      setTimeout(cargarHistorial, 500);
    })
    .catch(() => {
      mensajesArea.innerHTML = `
        <div class="bienvenida" id="bienvenida">
          <div class="bienvenida-emoji">🌸</div>
          <p>¡Hola! Escribime algo para empezar.</p>
        </div>`;
    });
}

// ── Bloqueo de entrada ──
function bloquearEntrada() {
  enviando = true;
  btnEnviar.disabled = true;
  entradaTexto.disabled = true;
}

function desbloquearEntrada() {
  enviando = false;
  btnEnviar.disabled = false;
  entradaTexto.disabled = false;
  entradaTexto.focus();
}

// ── Enter para enviar ──
entradaTexto.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    enviar();
  }
});

document.addEventListener("keydown", e => {
  if (e.key === "F12") {
    fetch("/api/stop", { method: "POST" });
    agregarMensaje("ia", "Deteniendo cualquier acción activa.", "sistema");
  }
});

// ── Restaurar mensajes recientes al recargar ──
// ── Función centralizada para filtrar observaciones de Alisha ──
function _esObservacionAlisha(entrada) {
  if (!entrada || typeof entrada !== 'string') return false;
  
  // Filtrar todas las variantes de mensajes de observación
  return (
    entrada.startsWith("[Alisha") ||
    entrada.startsWith("[Sugerencia") ||
    entrada === "[Alisha observa]" ||
    entrada === "[Alisha sugiere]" ||
    entrada.startsWith("[Sugerencia automática]") ||
    entrada.includes("Alisha observa") ||
    entrada.includes("Alisha sugiere") ||
    // Capturar patrones adicionales que puedan aparecer
    /^\[Alisha\s+\w+\]/.test(entrada) ||
    /^\[Sugerencia/.test(entrada)
  );
}

function cargarMensajesRecientes() {
  // Intentar desde SQLite primero
  fetch("/api/historial")
    .then(r => r.json())
    .then(historial => {
      if (!historial || historial.length === 0) return;
      if (bienvenida) bienvenida.style.display = "none";
      // Mostrar últimas 20 conversaciones
      historial.slice(-20).forEach(item => {
        // Filtrar entradas de sistema (observaciones de Alisha)
        const esObservacion = item.entrada && _esObservacionAlisha(item.entrada);
        if (!esObservacion && item.entrada && item.entrada.trim()) {
          agregarMensaje("usuario", item.entrada, "usuario");
        }
        if (item.respuesta && item.respuesta.trim()) {
          agregarMensaje("ia", item.respuesta, "ia");
        }
      });
      scrollAbajo();
    })
    .catch(() => {});
}
function cargarHistorial() {
  // Cargar sesiones desde SQLite para la barra lateral
  return fetch("/api/sesiones")
    .then(r => r.json())
    .then(sesiones => {
      const lista = document.getElementById("historial-lista");
      lista.innerHTML = "";

      if (!sesiones || sesiones.length === 0) {
        _cargarHistorialLegacy();
        return;
      }

      sesiones.forEach(s => {
        const div = document.createElement("div");
        div.className = "historial-item";
        const titulo = s.titulo && s.titulo !== "Nueva conversación"
          ? s.titulo
          : (s.inicio ? new Date(s.inicio).toLocaleDateString("es-AR", {day:"2-digit",month:"short"}) : "Chat");
        div.textContent = titulo;
        if (s.mensajes && s.mensajes > 0) {
          div.title = `${titulo} · ${s.mensajes} mensajes · ${s.inicio ? new Date(s.inicio).toLocaleDateString("es-AR") : ""}`;
        } else {
          div.title = s.inicio ? new Date(s.inicio).toLocaleDateString("es-AR") : "";
        }
        div.dataset.sessionId = s.id;
        if (s.id === _sesionActiva) div.classList.add("activa");
        div.onclick = () => _cargarSesion(s.id);
        lista.appendChild(div);
      });
    })
    .catch(() => _cargarHistorialLegacy());
}

function _cargarHistorialLegacy() {
  fetch("/api/historial")
    .then(r => r.json())
    .then(historial => {
      const lista = document.getElementById("historial-lista");
      lista.innerHTML = "";
      if (!historial || historial.length === 0) {
        lista.innerHTML = '<div style="color:rgba(255,255,255,0.3);font-size:11px;padding:8px 4px">Sin conversaciones aún</div>';
        return;
      }
      historial.slice(-15).reverse().forEach(item => {
        // Filtrar observaciones de Alisha del sidebar también
        const esObservacion = item.entrada && _esObservacionAlisha(item.entrada);
        if (!esObservacion) {
          const div = document.createElement("div");
          div.className = "historial-item";
          const texto = item.entrada || item.respuesta || "...";
          div.textContent = texto.slice(0, 38) + (texto.length > 38 ? "…" : "");
          div.title = texto;
          lista.appendChild(div);
        }
      });
    })
    .catch(() => {});
}

// ID de la sesión actualmente visible en el chat
let _sesionActiva = null;

async function _cargarSesion(sessionId) {
  try {
    const resp = await fetch(`/api/sesion/${sessionId}`);
    const convs = await resp.json();

    // Limpiar área de mensajes
    mensajesArea.innerHTML = "";
    if (bienvenida) bienvenida.style.display = "none";

    if (!convs || convs.length === 0) {
      mensajesArea.innerHTML = '<div style="color:rgba(255,255,255,0.3);text-align:center;padding:2rem">Sin mensajes en esta conversación</div>';
      return;
    }

    // Mostrar todos los mensajes del hilo
    convs.forEach(item => {
      // Filtrar entradas de sistema (observaciones de Alisha) usando función centralizada
      const esObservacion = item.entrada && _esObservacionAlisha(item.entrada);
      if (!esObservacion && item.entrada && item.entrada.trim()) {
        agregarMensaje("usuario", item.entrada, "usuario");
      }
      if (item.respuesta && item.respuesta.trim()) {
        agregarMensaje("ia", item.respuesta, "ia");
      }
    });

    scrollAbajo();

    // Marcar sesión activa en el sidebar
    _sesionActiva = sessionId;
    document.querySelectorAll(".historial-item").forEach(el => {
      el.classList.toggle("activa", parseInt(el.dataset.sessionId) === sessionId);
    });

  } catch (e) {
    console.warn("Error cargando sesión:", e);
  }
}

// Cargar historial cuando el socket conecta (datos ya disponibles)
socket.on("estado_inicial", (data) => {
  if (data.nombre_ia) nombreIA.textContent = data.nombre_ia;
  // Mostrar nombre del usuario — nunca mostrar vacío ni "Alisha"
  const nombreUsuario = data.nombre_usuario && data.nombre_usuario.toLowerCase() !== "alisha"
    ? data.nombre_usuario
    : "Cami";
  if (nombreSidebar) nombreSidebar.textContent = nombreUsuario;
  actualizarEstado(data.estado_emocional || "neutral");

  // Cargar sidebar primero, luego restaurar la sesión activa
  cargarHistorial().then(() => {
    if (data.session_id) {
      // Restaurar la sesión activa del servidor (no mezclar mensajes de sesiones distintas)
      _sesionActiva = data.session_id;
      _cargarSesion(data.session_id);
    } else {
      cargarMensajesRecientes();
    }
  }).catch(() => {
    cargarMensajesRecientes();
  });

  actualizarStatus();
  actualizarMediaSync();
  actualizarCunaLed();
  // Pollers periódicos
  setInterval(actualizarStatus,    10000);
  setInterval(actualizarMediaSync,  5000);
  setInterval(actualizarCunaLed,    8000);
  setInterval(cargarHistorial,     30000); // refrescar sidebar cada 30s
});

// Actualizar título de sesión en el sidebar cuando Alisha lo genera
socket.on("session_title_updated", (data) => {
  const item = document.querySelector(`[data-session-id="${data.session_id}"]`);
  if (item) {
    item.textContent = data.titulo;
    item.title = data.titulo;
  } else {
    // Sesión nueva — recargar sidebar rápido
    setTimeout(cargarHistorial, 500);
  }
});
// ── Función para sugerencias ──
function enviarSugerencia(texto) {
  document.getElementById("entrada-texto").value = texto;
  enviar();
}

// (función enviar() definida arriba — única instancia)


// ── Control de bloqueo (Ctrl+Shift+L) ──────────────────────────────────────

// Toast de notificación
function mostrarToastLock(mensaje) {
  let toast = document.getElementById("lock-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "lock-toast";
    document.body.appendChild(toast);
  }
  toast.textContent = mensaje;
  toast.classList.add("visible");
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => toast.classList.remove("visible"), 2500);
}

function actualizarBtnLock(bloqueado) {
  const btn = document.getElementById("lock-btn");
  if (!btn) return;
  if (bloqueado) {
    btn.textContent = "🔒 Control bloqueado";
    btn.className = "lock-btn bloqueado";
  } else {
    btn.textContent = "🔓 Control activo";
    btn.className = "lock-btn desbloqueado";
  }
}

async function toggleLock() {
  try {
    const res = await fetch("/api/lock");
    const data = await res.json();
    const nuevoEstado = !data.bloqueado;

    await fetch("/api/lock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bloqueado: nuevoEstado }),
    });

    actualizarBtnLock(nuevoEstado);
    mostrarToastLock(nuevoEstado
      ? "🔒 Control bloqueado — Alisha no puede controlar el PC"
      : "🔓 Control desbloqueado — Alisha puede controlar el PC"
    );
  } catch (e) {
    console.error("Error toggling lock:", e);
  }
}

// Escuchar cambios de bloqueo desde el servidor (cuando se usa el hotkey)
socket.on("lock_state", (data) => {
  actualizarBtnLock(data.bloqueado);
  mostrarToastLock(data.bloqueado
    ? "🔒 Control bloqueado — Alisha no puede controlar el PC"
    : "🔓 Control desbloqueado — Alisha puede controlar el PC"
  );
});

// Cargar estado inicial del lock
fetch("/api/lock")
  .then(r => r.json())
  .then(d => actualizarBtnLock(d.bloqueado))
  .catch(() => {});

// Hotkey Ctrl+Shift+L también desde el navegador
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.shiftKey && e.key === "L") {
    e.preventDefault();
    toggleLock();
  }
});


// ── Botón "Despertar a Alisha" ────────────────────────────────────────────────

async function despertarAlisha() {
  try {
    const r = await fetch("/api/despertar", { method: "POST" });
    const d = await r.json();
    if (d.ok) {
      document.getElementById("banner-despertar").style.display = "none";
      agregarMensaje("ia", "Despertando... dame un segundo.", "ia");
    }
  } catch(e) {
    console.error("Error despertando:", e);
  }
}

// Verificar si el servidor está vivo al cargar — manejado por el overlay de reconexión arriba

// ── Sistema de Confianza (Trust) ──────────────────────────────────────────────

function _actualizarTrustWidget(data) {
  try {
    const label  = document.getElementById("trust-label");
    const xpEl   = document.getElementById("trust-xp");
    const bar    = document.getElementById("trust-bar");
    const tasks  = document.getElementById("trust-tasks");
    if (!label) return;

    const emojis = { 1: "🌱", 2: "⭐", 3: "💎" };
    const nombres = { 1: "Aprendiz", 2: "Asistente", 3: "Partner" };
    const emoji  = emojis[data.nivel] || "🌱";
    const nombre = nombres[data.nivel] || "Aprendiz";

    label.textContent  = `${emoji} ${nombre}`;
    xpEl.textContent   = `XP: ${data.xp}`;
    bar.style.width    = `${Math.round((data.progreso || 0) * 100)}%`;
    tasks.textContent  = `${data.tareas_completadas || 0} tareas completadas`;
  } catch(e) {}
}

socket.on("trust_update", (data) => {
  _actualizarTrustWidget(data);
});

socket.on("nivel_3_unlock", (data) => {
  // Cambiar fondo del chat al llegar al Nivel 3
  try {
    if (data.nuevo_fondo) {
      document.body.style.background = data.nuevo_fondo;
    }
    // Mostrar notificación especial
    const notif = document.createElement("div");
    notif.style.cssText = `
      position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%);
      background: linear-gradient(135deg, #1a0533, #0d1b4b);
      border: 2px solid #ff66a5;
      border-radius: 20px; padding: 2rem 3rem;
      text-align: center; z-index: 99999;
      color: #fff; font-family: 'Segoe UI', sans-serif;
      box-shadow: 0 0 60px rgba(255,102,165,0.5);
      animation: fadeIn 0.5s ease;
    `;
    notif.innerHTML = `
      <div style="font-size:3rem;margin-bottom:1rem">💎</div>
      <div style="font-size:1.4rem;font-weight:700;margin-bottom:0.5rem">¡Nivel 3 desbloqueado!</div>
      <div style="color:#aaa;font-size:0.9rem">${data.mensaje || 'El Modo Práctica terminó.'}</div>
      <button onclick="this.parentElement.remove()" style="
        margin-top:1.5rem; padding:0.6rem 1.5rem;
        background:linear-gradient(135deg,#ff66a5,#c040a0);
        border:none; border-radius:8px; color:#fff;
        cursor:pointer; font-size:0.9rem;
      ">¡Genial!</button>
    `;
    document.body.appendChild(notif);
    setTimeout(() => notif.remove(), 15000);
  } catch(e) {}
});

// Cargar estado de confianza al iniciar
fetch("/api/trust")
  .then(r => r.json())
  .then(data => _actualizarTrustWidget(data))
  .catch(() => {});
