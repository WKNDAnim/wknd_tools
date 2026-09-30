"""
Script para Flow Production Tracking (Shotgun) Python Console.

Busca los Shots con Task "Comp" en estado "apr" dentro del proyecto 91,
localiza todos los renders de Nuke (work y publish) de esos shots,
guarda un backup en JSON, y borra todas las versiones excepto la ultima
de work y la ultima de publish, POR TASK (nunca se borra si una task
solo tiene una version).

Requiere: variables `sg` y `tk` ya disponibles en la consola de Flow PT.
"""

import os
import re
import json
import shutil
import datetime

sg = shotgun


def append_json_run(filepath, entry):
    """Añade `entry` (con timestamp) a una lista guardada en filepath,
    sin sobreescribir las ejecuciones anteriores."""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            try:
                runs = json.load(f)
            except json.JSONDecodeError:
                runs = []
    else:
        runs = []

    # Si el archivo ya existia de una version anterior del script (guardado
    # como un dict suelto en vez de una lista de ejecuciones), lo convertimos
    # en la primera entrada de la lista para no perder ese historial.
    if not isinstance(runs, list):
        runs = [{"timestamp": None, "legacy_data": runs}]

    entry_with_ts = {"timestamp": datetime.datetime.now().isoformat(), **entry}
    runs.append(entry_with_ts)

    with open(filepath, "w") as f:
        json.dump(runs, f, indent=2)


# ---------------------------------------------------------------------------
# 1. Buscar shots con Task "Comp" en estado "apr"
# ---------------------------------------------------------------------------

filters = [
    ["project", "is", {"type": "Project", "id": 91}],
    ["content", "is", "Comp"],
    ["sg_status_list", "is", "apr"],
    # ["entity.Shot.code", "in", ["sq0210_sh0010", "sq1240_sh0010"]],
]

fields = ["code", "sg_status_list", "content", "entity.Shot.code"]

tasks = sg.find("Task", filters, fields)

# Sacar los shots unicos a partir de las tasks encontradas
shots = {t["entity.Shot.code"] for t in tasks}

for shot in sorted(shots):
    print(shot)

print(f" ------- {len(shots)} will be processed")


# ---------------------------------------------------------------------------
# 2. Buscar renders (work y publish) de Nuke para cada shot, agrupados
#    por Task (un shot puede tener renders de varias tasks: Comp, Roto...)
# ---------------------------------------------------------------------------

tmpl_work = tk.templates["nuke_shot_render_final_exr"]
tmpl_pub = tk.templates["nuke_shot_render_final_exr_pub"]


def group_paths_by_task(tmpl, paths):
    """Agrupa una lista de paths (abstract) por el campo Task de la template."""
    by_task = {}
    for path in paths:
        try:
            path_fields = tmpl.get_fields(path)
        except Exception:
            # Si el path no encaja con la template, lo ignoramos
            continue
        task = path_fields.get("Task", "__unknown__")
        by_task.setdefault(task, []).append(path)
    return by_task


renders_by_shot = {}

for shot in sorted(shots):
    render_fields = {"Shot": shot}
    renders_by_shot[shot] = {"work": {}, "publish": {}}

    paths_work = tk.abstract_paths_from_template(tmpl_work, render_fields)
    renders_by_shot[shot]["work"] = group_paths_by_task(tmpl_work, sorted(paths_work))

    paths_pub = tk.abstract_paths_from_template(tmpl_pub, render_fields)
    renders_by_shot[shot]["publish"] = group_paths_by_task(tmpl_pub, sorted(paths_pub))

for shot, data in renders_by_shot.items():
    n_work = sum(len(v) for v in data["work"].values())
    n_pub = sum(len(v) for v in data["publish"].values())
    print(f"{shot}: {n_work} work / {n_pub} publish")

total = sum(
    sum(len(v) for v in d["work"].values()) + sum(len(v) for v in d["publish"].values())
    for d in renders_by_shot.values()
)
print(f" ------- {total} renders found across {len(renders_by_shot)} shots")


# ---------------------------------------------------------------------------
# 3. Backup del estado actual en JSON (se añade una entrada por ejecucion,
#    no se sobreescribe lo guardado en ejecuciones anteriores)
# ---------------------------------------------------------------------------

json_path = r"C:\Temp\renders_by_shot_backup.json"
append_json_run(json_path, {"renders_by_shot": renders_by_shot})

print(f"Backup añadido a {json_path}")


# ---------------------------------------------------------------------------
# 4. Calcular ultima version y versiones a borrar, POR TASK.
#    Si una task solo tiene 1 version, no se borra nada de esa task.
# ---------------------------------------------------------------------------

def get_version(path):
    match = re.search(r"_v(\d+)", path)
    return int(match.group(1)) if match else -1


def latest_and_rest(paths):
    """Devuelve (path_ultima_version, [resto_de_paths]).
    Si solo hay 1 path, 'rest' sale vacio (no se borra nada)."""
    if not paths:
        return None, []
    paths_sorted = sorted(paths, key=get_version)
    latest = paths_sorted[-1]
    rest = paths_sorted[:-1]
    return latest, rest


to_delete = {}

for shot, data in renders_by_shot.items():
    to_delete[shot] = {"work": [], "publish": []}

    for task, paths in data["work"].items():
        latest, rest = latest_and_rest(paths)
        to_delete[shot]["work"].extend(rest)
        if rest:
            print(f"{shot} [{task}] work: keep {latest} -> delete {len(rest)}")
        else:
            print(f"{shot} [{task}] work: 1 sola version, no se borra ({latest})")

    for task, paths in data["publish"].items():
        latest, rest = latest_and_rest(paths)
        to_delete[shot]["publish"].extend(rest)
        if rest:
            print(f"{shot} [{task}] publish: keep {latest} -> delete {len(rest)}")
        else:
            print(f"{shot} [{task}] publish: 1 sola version, no se borra ({latest})")


# ---------------------------------------------------------------------------
# 5. Construir lista final de carpetas a borrar (dry run / revision)
# ---------------------------------------------------------------------------

folders_to_delete = set()

for shot, data in to_delete.items():
    for path in data["work"] + data["publish"]:
        folder = os.path.dirname(path)
        folders_to_delete.add(folder)

folders_to_delete = sorted(folders_to_delete)

json_path_deleted = r"C:\Temp\delete_log.json"

if not folders_to_delete:
    print("Nada que borrar: todas las tasks tienen 1 sola version (o ninguna).")
else:
    print(f"Se van a borrar {len(folders_to_delete)} carpetas:")
    for folder in folders_to_delete:
        print("  ", folder)

    # -----------------------------------------------------------------------
    # 6. Borrado con confirmacion manual y log (solo si hay algo que borrar)
    # -----------------------------------------------------------------------

    confirm = input("\nEscribe 'BORRAR' para confirmar el borrado: ")

    if confirm == "BORRAR":
        deleted = []
        errors = []

        for folder in folders_to_delete:
            if not os.path.isdir(folder):
                print(f"[SKIP] No existe (o ya no es carpeta): {folder}")
                continue
            try:
                shutil.rmtree(folder)
                deleted.append(folder)
                print(f"[OK] Borrado: {folder}")
            except Exception as e:
                errors.append((folder, str(e)))
                print(f"[ERROR] {folder} -> {e}")

        print(f"\n------- {len(deleted)} carpetas borradas, {len(errors)} errores")

        append_json_run(json_path_deleted, {"deleted": deleted, "errors": errors})
    else:
        print("Cancelado, no se ha borrado nada.")