#!/usr/bin/env python3
"""
iniciar_web.py — Inicia solo la interfaz web de Alisha.

Uso: pythonw iniciar_web.py  (sin ventana negra)
"""
import os
import sys
import webbrowser
import time
from pathlib import Path

# Suprimir ventana de pygame antes de cualquier import
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "directsound")

def main():
    print("🌐 Iniciando Interfaz Web de Alisha")
    print("=" * 40)
    
    # Cambiar al directorio del script
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    print("✨ Iniciando servidor web...")
    print("📍 URL: http://localhost:5000")
    print("💡 Presiona Ctrl+C para cerrar")
    print()
    
    try:
        # Importar y ejecutar la aplicación web
        from web_app import app, socketio, _inicializar
        
        # Inicializar el sistema
        _inicializar()

        # Iniciar sistema analítico (comentarios espontáneos de Alisha)
        try:
            from alisha_analitica import start_alisha_analitica
            from memory import cargar_memoria
            memoria = cargar_memoria()
            user_name = memoria.get("perfil", {}).get("nombre", "Camila")
            start_alisha_analitica(user_name)
            print(f"💬 Sistema analítico iniciado para {user_name}")
        except Exception as e:
            print(f"⚠️ Sistema analítico no disponible: {e}")

        # Iniciar conciencia situacional (ve ventanas activas y comenta)
        try:
            from situational_awareness import SituationalAwareness
            from tts_engine import speak as _speak

            def _callback_situacional(texto: str):
                """Alisha comenta lo que ve en pantalla — con semáforo global."""
                if not texto or not texto.strip():
                    return
                try:
                    from alisha_voz_control import hablar
                    def _hablar_y_emitir(t):
                        _speak(t)
                        socketio.emit("respuesta", {"texto": t, "estado_emocional": "curiosidad"})
                        try:
                            from assistant_state import actualizar_estado
                            actualizar_estado(estado="curiosidad", hablando=True)
                            palabras = len(t.split())
                            duracion = max(2.0, (palabras / 150) * 60 + 1.0)
                            threading.Timer(duracion, lambda: actualizar_estado(hablando=False)).start()
                        except Exception:
                            pass
                    hablar(texto, _hablar_y_emitir)
                except Exception:
                    pass

            _sa = SituationalAwareness()
            _sa.iniciar(_callback_situacional)
            print("👁️ Conciencia situacional iniciada — Alisha puede ver tus ventanas")
        except Exception as e:
            print(f"⚠️ Conciencia situacional no disponible: {e}")
        
        # Abrir navegador después de un momento
        def abrir_navegador():
            time.sleep(2)
            try:
                webbrowser.open("http://localhost:5000")
                print("🌐 Navegador abierto automáticamente")
            except Exception as e:
                print(f"⚠️ No se pudo abrir el navegador: {e}")
                print("   Abre manualmente: http://localhost:5000")
        
        import threading
        threading.Thread(target=abrir_navegador, daemon=True).start()
        
        # Ejecutar servidor
        print("🚀 Servidor web iniciado")
        socketio.run(app, host="127.0.0.1", port=5000, debug=False, 
                    allow_unsafe_werkzeug=True)
        
    except KeyboardInterrupt:
        print("\n👋 Servidor web cerrado")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("💡 Verifica que Ollama esté ejecutándose")
        input("Presiona Enter para cerrar...")

if __name__ == "__main__":
    main()