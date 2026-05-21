"""Automatización de navegador con Playwright — navegación web real."""
import threading
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Browser, Page, Playwright
    _PLAYWRIGHT_OK = True
except ImportError:
    _PLAYWRIGHT_OK = False


class BrowserAgent:
    """Singleton que controla un navegador via Playwright."""

    _instance: Optional["BrowserAgent"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._playwright: Optional[Playwright] = None
                inst._browser: Optional[Browser] = None
                inst._page: Optional[Page] = None
                cls._instance = inst
        return cls._instance

    @classmethod
    def get_instance(cls) -> "BrowserAgent":
        return cls()

    def _verificar_playwright(self) -> None:
        if not _PLAYWRIGHT_OK:
            raise ImportError(
                "Playwright no está instalado. Ejecuta: pip install playwright && python -m playwright install chromium"
            )

    def _iniciar(self) -> None:
        """Lazy init — abre el navegador solo cuando se necesita."""
        self._verificar_playwright()
        if self._browser is not None and self._browser.is_connected():
            return
        self._playwright = sync_playwright().start()
        # Intentar Chromium → Edge → Firefox
        for launch_fn, kwargs in [
            (self._playwright.chromium.launch, {"headless": False}),
            (self._playwright.firefox.launch, {"headless": False}),
        ]:
            try:
                self._browser = launch_fn(**kwargs)
                self._page = self._browser.new_page()
                return
            except Exception:
                continue
        raise RuntimeError("No se pudo iniciar ningún navegador. Verifica que Chromium esté instalado.")

    def abrir_url(self, url: str) -> str:
        """Navega a una URL y espera a que cargue."""
        try:
            self._iniciar()
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return f"Navegando a {url}"
        except Exception as e:
            return f"Error al abrir URL: {e}"

    def buscar_en_google(self, query: str) -> str:
        """Abre Google y busca el query."""
        try:
            self._iniciar()
            self._page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=10000)
            self._page.fill('textarea[name="q"], input[name="q"]', query)
            self._page.keyboard.press("Enter")
            self._page.wait_for_load_state("domcontentloaded")
            return f"Buscando '{query}' en Google."
        except Exception as e:
            return f"Error al buscar en Google: {e}"

    def click_elemento(self, selector_o_texto: str) -> str:
        """Hace click en un elemento por selector CSS o texto visible."""
        try:
            self._iniciar()
            # Intentar por texto primero
            try:
                self._page.get_by_text(selector_o_texto, exact=False).first.click(timeout=5000)
                return f"Click en elemento con texto '{selector_o_texto}'."
            except Exception:
                pass
            # Intentar por selector CSS
            self._page.click(selector_o_texto, timeout=5000)
            return f"Click en selector '{selector_o_texto}'."
        except Exception as e:
            return f"No se encontró el elemento '{selector_o_texto}': {e}"

    def escribir_en_campo(self, selector: str, texto: str) -> str:
        """Llena un campo de formulario."""
        try:
            self._iniciar()
            self._page.fill(selector, texto, timeout=5000)
            return f"Texto escrito en '{selector}'."
        except Exception as e:
            return f"Error al escribir en campo '{selector}': {e}"

    def leer_pagina(self) -> str:
        """Extrae el texto visible de la página actual."""
        try:
            self._iniciar()
            texto = self._page.inner_text("body")
            # Limitar a 2000 caracteres para no saturar el prompt
            return texto[:2000].strip() if texto else "(página vacía)"
        except Exception as e:
            return f"Error al leer página: {e}"

    def screenshot_pagina(self, nombre: str = "pagina.png") -> str:
        """Captura la página actual."""
        try:
            self._iniciar()
            if not nombre.endswith(".png"):
                nombre += ".png"
            self._page.screenshot(path=nombre, full_page=False)
            return nombre
        except Exception as e:
            return f"Error al capturar página: {e}"

    def cerrar_navegador(self) -> str:
        """Cierra el navegador limpiamente."""
        try:
            if self._browser:
                self._browser.close()
                self._browser = None
                self._page = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            # Resetear singleton para permitir re-apertura
            BrowserAgent._instance = None
            return "Navegador cerrado."
        except Exception as e:
            return f"Error al cerrar navegador: {e}"
