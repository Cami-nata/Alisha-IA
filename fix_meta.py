import json

path = r'C:\Users\User\.kiro\tasks\8233e4c51ad185c3\alisha-mejoras-core.meta.json'

with open(path, 'rb') as f:
    raw_bytes = f.read()

text = raw_bytes.decode('utf-8')
data = json.loads(text)
tasks = data['tasks']

# Fix mojibake keys: they were encoded as latin-1 interpreted utf-8
new_tasks = {}
for k, v in tasks.items():
    try:
        fixed_k = k.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        fixed_k = k  # already correct
    new_tasks[fixed_k] = v

data['tasks'] = new_tasks

# Print first 5 fixed keys to verify
print("Fixed keys sample:")
for k in list(new_tasks.keys())[:5]:
    print(repr(k[:80]))

# Mark confirmed-done tasks as succeed
confirmed_done_substrings = [
    'smooth_damp(current, target, vel',
    'calcular_amplitudes_rms(audio_bytes',
    'LipSyncThread` en el flujo de reproducci',
    'session_id` a la tabla `conversaciones',
    '_extract_pdf_with_vision(path)',
    'parsear_tool_call(texto)',
    'SmartRouter.analyze()` para consultar',
    'manejo de fallo de Ollama',
]

print("\nUpdating statuses:")
for key in list(new_tasks.keys()):
    for substr in confirmed_done_substrings:
        if substr in key:
            old = new_tasks[key].get('executionStatus', 'none')
            new_tasks[key]['executionStatus'] = 'succeed'
            print(f"  {old} -> succeed: {key[:70]}")
            break

# Write back with UTF-8 (no BOM)
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("\nDone. File written.")
