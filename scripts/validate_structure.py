"""
scripts/validate_structure.py — Validar la estructura del proyecto.

Verifica:
- Carpetas clave existen
- Archivos críticos existen
- Imports principales funcionan
- Configuración básica está presente
"""
import sys
from pathlib import Path

# Agregar raíz al path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

def check_structure():
    """Verificar estructura de carpetas."""
    print("🔍 Verificando estructura de carpetas...")
    
    required_dirs = [
        "channels",
        "core",
        "avatar",
        "memory",
        "personality",
        "vision",
        "tools",
        "services",
        "web",
        "desktop",
        "data",
        "docs",
        "config",
    ]
    
    missing = []
    for d in required_dirs:
        path = BASE_DIR / d
        if not path.exists():
            missing.append(d)
            print(f"  ❌ Falta: {d}/")
        else:
            print(f"  ✅ {d}/")
    
    return len(missing) == 0


def check_files():
    """Verificar archivos críticos."""
    print("\n🔍 Verificando archivos críticos...")
    
    required_files = [
        "main.py",
        "Alisha_IA.py",
        "config.py",
        ".env.example",
        ".gitignore",
        "README.md",
        "requirements.txt",
        "channels/base.py",
        "channels/channel_router.py",
        "channels/telegram_channel.py",
        "core/brain.py",
        "avatar/cabina_virtual.py",
        "docs/ARQUITECTURA.md",
        "docs/REFACTOR_SUMMARY.md",
    ]
    
    missing = []
    for f in required_files:
        path = BASE_DIR / f
        if not path.exists():
            missing.append(f)
            print(f"  ❌ Falta: {f}")
        else:
            print(f"  ✅ {f}")
    
    return len(missing) == 0


def check_imports():
    """Verificar imports principales."""
    print("\n🔍 Verificando imports principales...")
    
    tests = [
        ("config", "Configuración"),
        ("channels.base", "Canales base"),
        ("channels.channel_router", "ChannelRouter"),
        ("core.brain", "Brain"),
        ("core.assistant_state", "AssistantState"),
    ]
    
    failed = []
    for module, name in tests:
        try:
            __import__(module)
            print(f"  ✅ {name} ({module})")
        except ImportError as e:
            failed.append((module, str(e)))
            print(f"  ❌ {name} ({module}): {e}")
    
    return len(failed) == 0


def check_env():
    """Verificar configuración básica."""
    print("\n🔍 Verificando configuración...")
    
    env_example = BASE_DIR / ".env.example"
    env_file = BASE_DIR / ".env"
    
    if not env_example.exists():
        print("  ❌ .env.example no existe")
        return False
    else:
        print("  ✅ .env.example existe")
    
    if not env_file.exists():
        print("  ⚠️  .env no existe (copiar de .env.example)")
    else:
        print("  ✅ .env existe")
    
    return True


def check_data_dirs():
    """Verificar directorios de datos."""
    print("\n🔍 Verificando directorios de datos...")
    
    data_dirs = [
        "data",
        "data/telegram",
        "data/telegram/inbox",
        "data/telegram/inbox/audio",
        "data/telegram/inbox/images",
        "data/telegram/inbox/documents",
    ]
    
    for d in data_dirs:
        path = BASE_DIR / d
        if not path.exists():
            print(f"  ⚠️  Creando: {d}/")
            path.mkdir(parents=True, exist_ok=True)
        else:
            print(f"  ✅ {d}/")
    
    return True


def main():
    """Ejecutar todas las validaciones."""
    print("=" * 60)
    print("🎭 Validación de estructura de Alisha IA")
    print("=" * 60)
    
    results = []
    
    results.append(("Estructura", check_structure()))
    results.append(("Archivos", check_files()))
    results.append(("Imports", check_imports()))
    results.append(("Configuración", check_env()))
    results.append(("Datos", check_data_dirs()))
    
    print("\n" + "=" * 60)
    print("📊 Resumen")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 Todas las validaciones pasaron!")
        print("\n📝 Próximos pasos:")
        print("  1. Copiar .env.example a .env y configurar")
        print("  2. Instalar dependencias: pip install -r requirements.txt")
        print("  3. Iniciar Alisha: python main.py")
        return 0
    else:
        print("\n⚠️  Algunas validaciones fallaron")
        print("Revisar los errores arriba y corregir")
        return 1


if __name__ == "__main__":
    sys.exit(main())
