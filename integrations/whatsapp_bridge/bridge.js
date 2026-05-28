/**
 * bridge.js — Bridge de WhatsApp para Alisha IA
 *
 * Usa whatsapp-web.js con sesión persistente (LocalAuth).
 * Escanea QR una sola vez, luego reutiliza la sesión.
 *
 * Flujo:
 *   1. Inicia cliente WhatsApp Web con LocalAuth
 *   2. Al recibir mensaje de número en whitelist → POST a api_server (localhost:8000)
 *   3. Expone POST /send para que Python envíe mensajes de vuelta
 *   4. Reintentos automáticos si api_server no responde
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode  = require('qrcode-terminal');
const express = require('express');
const axios   = require('axios');
const path    = require('path');
const fs      = require('fs');

// ── Configuración ──────────────────────────────────────────────────────────────
const BRIDGE_PORT    = 3000;
const API_SERVER_URL = 'http://localhost:8000';
const RETRY_INTERVAL = 10000;   // ms entre reintentos si api_server no responde
const MAX_RETRIES    = 5;

// ── Cargar whitelist desde config/trusted_numbers.json ────────────────────────
function loadTrustedNumbers() {
  try {
    const configPath = path.join(__dirname, '..', '..', 'config', 'trusted_numbers.json');
    const raw = fs.readFileSync(configPath, 'utf8');
    const data = JSON.parse(raw);
    // Normalizar: quitar espacios y el prefijo "+"
    const numbers = (data.trusted_numbers || []).map(entry => {
      const num = (entry.number || entry).replace(/\s+/g, '').replace(/^\+/, '');
      return num;
    });
    console.log(`[Bridge] ✓ Whitelist cargada: ${numbers.length} número(s)`);
    return numbers;
  } catch (err) {
    console.warn(`[Bridge] ⚠ No se pudo cargar trusted_numbers.json: ${err.message}`);
    // Fallback: números de Ana hardcodeados como respaldo
    return ['51949103873', '51916853655'];
  }
}

let TRUSTED_NUMBERS = loadTrustedNumbers();

// Recargar whitelist cada 60 segundos (por si se actualiza en caliente)
setInterval(() => {
  TRUSTED_NUMBERS = loadTrustedNumbers();
}, 60000);

// ── Normalizar número de WhatsApp ──────────────────────────────────────────────
function normalizeNumber(waId) {
  // waId viene como "51949103873@c.us" o "+51949103873"
  return waId.replace('@c.us', '').replace(/^\+/, '').replace(/\s+/g, '');
}

function isTrusted(waId) {
  const normalized = normalizeNumber(waId);
  return TRUSTED_NUMBERS.includes(normalized);
}

// ── Cliente WhatsApp ───────────────────────────────────────────────────────────
const client = new Client({
  authStrategy: new LocalAuth({
    dataPath: path.join(__dirname, 'session'),
  }),
  puppeteer: {
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--no-first-run',
      '--no-zygote',
      '--disable-gpu',
    ],
  },
});

// ── Eventos del cliente ────────────────────────────────────────────────────────
client.on('qr', (qr) => {
  console.log('\n[Bridge] 📱 Escanea este QR con WhatsApp:');
  qrcode.generate(qr, { small: true });
  console.log('[Bridge] El QR expira en ~60 segundos.\n');
});

client.on('authenticated', () => {
  console.log('[Bridge] ✓ Autenticado — sesión guardada en session/');
});

client.on('auth_failure', (msg) => {
  console.error('[Bridge] ✗ Fallo de autenticación:', msg);
});

client.on('ready', () => {
  console.log('[Bridge] ✓ WhatsApp listo — escuchando mensajes...');
});

client.on('disconnected', (reason) => {
  console.warn('[Bridge] ⚠ Desconectado:', reason);
  // Reintentar conexión después de 5 segundos
  setTimeout(() => {
    console.log('[Bridge] Reconectando...');
    client.initialize().catch(err => console.error('[Bridge] Error al reconectar:', err));
  }, 5000);
});

// ── Recepción de mensajes ──────────────────────────────────────────────────────
client.on('message', async (msg) => {
  try {
    const from = msg.from;

    // Ignorar mensajes de grupos
    if (from.includes('@g.us')) return;

    // Log completo para debug
    let contactNumber = '';
    try {
      const contact = await msg.getContact();
      // contact.id.user tiene el número real, contact.number puede ser un ID interno
      contactNumber = (contact.id && contact.id.user) ? contact.id.user : (contact.number || '');
      console.log(`[Bridge] DEBUG — from: ${from}, número real: ${contactNumber}`);
    } catch (e) {
      console.log(`[Bridge] DEBUG — from: ${from}, getContact error: ${e.message}`);
    }

    // Intentar extraer número de múltiples fuentes
    let realNumber = '';
    if (from.includes('@c.us')) {
      realNumber = normalizeNumber(from);
    } else if (contactNumber) {
      realNumber = contactNumber.replace(/\D/g, '');
    } else if (msg.author) {
      realNumber = normalizeNumber(msg.author);
    }

    console.log(`[Bridge] Número resuelto: ${realNumber}`);

    // Verificar whitelist
    if (realNumber && !TRUSTED_NUMBERS.includes(realNumber)) {
      console.log(`[Bridge] Número ${realNumber} no está en whitelist: ${JSON.stringify(TRUSTED_NUMBERS)}`);
      return;
    }

    // Si no pudimos resolver el número, loguear y continuar de todas formas (modo debug)
    if (!realNumber) {
      console.log(`[Bridge] No se pudo resolver número — procesando de todas formas (modo debug)`);
    }

    const text    = msg.body || '';
    const fromNum = realNumber ? ('+' + realNumber) : from;
    const timestamp = new Date().toISOString();

    console.log(`[Bridge] 📨 Mensaje de ${fromNum}: ${text.substring(0, 60)}`);

    // Enviar al api_server con reintentos (Req 1.3, 1.12)
    await postToApiServer({
      from: fromNum,
      text: text,
      timestamp: timestamp,
    });

  } catch (err) {
    console.error('[Bridge] Error procesando mensaje:', err.message);
  }
});

// ── POST al api_server con reintentos ─────────────────────────────────────────
async function postToApiServer(payload, retries = 0) {
  try {
    const response = await axios.post(
      `${API_SERVER_URL}/whatsapp/incoming`,
      payload,
      { timeout: 8000 }
    );
    console.log(`[Bridge] ✓ Mensaje enviado al api_server (status: ${response.status})`);
  } catch (err) {
    if (retries < MAX_RETRIES) {
      console.warn(`[Bridge] ⚠ api_server no responde (intento ${retries + 1}/${MAX_RETRIES}). Reintentando en ${RETRY_INTERVAL / 1000}s...`);
      setTimeout(() => postToApiServer(payload, retries + 1), RETRY_INTERVAL);
    } else {
      console.error(`[Bridge] ✗ No se pudo enviar al api_server después de ${MAX_RETRIES} intentos.`);
    }
  }
}

// ── Servidor Express para recibir mensajes de Python ──────────────────────────
const app = express();
app.use(express.json());

/**
 * POST /send
 * Body: { "to": "+51949103873", "message": "texto" }
 * Envía un mensaje de WhatsApp al número especificado.
 */
app.post('/send', async (req, res) => {
  try {
    const { to, message } = req.body;

    if (!to || !message) {
      return res.status(400).json({ ok: false, error: 'Faltan campos: to, message' });
    }

    // Normalizar número al formato de WhatsApp
    const waId = to.replace(/^\+/, '').replace(/\s+/g, '') + '@c.us';

    await client.sendMessage(waId, message);
    console.log(`[Bridge] ✓ Mensaje enviado a ${to}: ${message.substring(0, 40)}`);
    res.json({ ok: true });

  } catch (err) {
    console.error('[Bridge] Error al enviar mensaje:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

/**
 * GET /status
 * Retorna el estado del bridge.
 */
app.get('/status', (req, res) => {
  res.json({
    ok: true,
    ready: client.info ? true : false,
    trusted_count: TRUSTED_NUMBERS.length,
  });
});

// ── Iniciar servidor y cliente ─────────────────────────────────────────────────
app.listen(BRIDGE_PORT, '127.0.0.1', () => {
  console.log(`[Bridge] ✓ Servidor Express en http://127.0.0.1:${BRIDGE_PORT}`);
});

console.log('[Bridge] Iniciando cliente WhatsApp...');
client.initialize().catch(err => {
  console.error('[Bridge] Error al inicializar WhatsApp:', err.message);
  process.exit(1);
});

// ── Manejo de señales de cierre ────────────────────────────────────────────────
process.on('SIGINT', async () => {
  console.log('\n[Bridge] Cerrando...');
  await client.destroy();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await client.destroy();
  process.exit(0);
});
