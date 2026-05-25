import os, sys, traceback

OUT = open("diagnostic_output.txt", "w", encoding="utf-8")

def log(msg=""):
    OUT.write(str(msg) + "\n")
    OUT.flush()

try:
    import live2d.v3 as live2d
    import glfw
    from OpenGL.GL import *
    from config import LIVE2D_MODEL_PATH

    glfw.init()
    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    win = glfw.create_window(400, 600, "diag", None, None)
    glfw.make_context_current(win)
    live2d.init()
    live2d.glInit()

    model = live2d.LAppModel()
    model.LoadModelJson(LIVE2D_MODEL_PATH)
    model.Resize(400, 600)
    log("modelo cargado OK")

    # --- PARAMETROS por indice numerico (evita crash de GetParameter(str)) ---
    log("\n=== PARAMETROS REALES DE ICEGIRL ===")
    param_ids = model.GetParamIds()
    count = model.GetParameterCount()
    log(f"GetParamIds count : {len(param_ids)}")
    log(f"GetParameterCount: {count}")
    log()

    for i, pid in enumerate(param_ids):
        try:
            # Intentar por indice entero
            val = model.GetParameterValue(i)
            log(f"  [{i:3d}] {pid:40s} val={val:6.2f}")
        except Exception as e1:
            try:
                # Intentar por nombre string
                val = model.GetParameterValue(pid)
                log(f"  [{i:3d}] {pid:40s} val={val:6.2f} (by name)")
            except Exception as e2:
                log(f"  [{i:3d}] {pid:40s} ERROR idx={e1} name={e2}")

    # --- PARTES ---
    log("\n=== PARTES DEL MODELO ===")
    try:
        part_ids = model.GetPartIds()
        log(f"Total partes: {len(part_ids)}")
        for pid in part_ids:
            log(f"  {pid}")
    except Exception as e:
        log(f"Error partes: {e}")

    # --- EXPRESIONES ---
    log("\n=== EXPRESIONES DISPONIBLES ===")
    try:
        expr_ids = model.GetExpressionIds()
        log(f"Total expresiones: {len(expr_ids)}")
        for eid in expr_ids:
            log(f"  {eid}")
    except Exception as e:
        log(f"Error expresiones: {e}")

    log("\n=== FIN OK ===")

except Exception as e:
    log(f"\nERROR FATAL: {e}")
    log(traceback.format_exc())

finally:
    OUT.flush()
    OUT.close()
